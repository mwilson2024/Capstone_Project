import os
import time
import logging
from logging.handlers import RotatingFileHandler
import tempfile
from pathlib import Path
from azure.core.exceptions import ResourceNotFoundError
from shared.ProjectHelper import Helpers as ph
from shared.AzureClass import blobHandler
from worker.ContentScorer import ContentScoring
from shared.DBConn import SQLbuilder
from worker.ImageRanker import blipRanker
from worker.PreFilter import ImgQualFilt
from worker.SlideShow import SlideShowGenerator
from api.StoryBoard import StoryBoardGen
from worker.VideoExtraction import ExtractVidFrames

LOG_DIR = os.environ.get("LOG_DIR", "logs")
LOG_FILE = os.environ.get("LOG_FILE", "worker.log")
QUEUE_VISIBILITY_TIMEOUT = max(int(os.environ.get("QUEUE_VISIBILITY_TIMEOUT", "3600")), 1)
QUEUE_MAX_ATTEMPTS = max(int(os.environ.get("QUEUE_MAX_ATTEMPTS", "3")), 1)

def setup_logger(name: str = "workerLog") -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)

    app_logger = logging.getLogger(name)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False

    if app_logger.handlers:
        return app_logger

    log_format = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler = RotatingFileHandler(os.path.join(LOG_DIR, LOG_FILE),maxBytes=10_000_000,backupCount=5)
    file_handler.setFormatter(log_format)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)

    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)
    return app_logger


class newRunner:
    def __init__(self, db = None, log = None, blob = None):
        self.log = log or setup_logger()
        self.blob = blob or blobHandler(self.log)
        self.db = db or SQLbuilder(self.log)
       
        self.cs = ContentScoring(db= self.db, log=self.log)
        self.ir = blipRanker(db= self.db, log=self.log)
        self.pf = ImgQualFilt(db= self.db, log= self.log)
        self.ve = ExtractVidFrames(db= self.db, log= self.log)
        self.ss = SlideShowGenerator(db=self.db, log= self.log, azure= self.blob)
        self.sb = StoryBoardGen(db=self.db, log=self.log)

    def deleteQueueMessage(self, msg) -> bool:
        try:
            self.blob.queue.delete_message(msg)
            return True
        except ResourceNotFoundError as error:
            if getattr(error, "error_code", None) == "MessageNotFound" or "MessageNotFound" in str(error):
                self.log.warning(
                    "Queue message %s was already deleted or its receipt expired; treating delete as complete.",
                    getattr(msg, "id", None),
                )
                return False
            self.log.exception("Azure could not find the queue message during deletion")
            return False
        except Exception:
            self.log.exception("Could not delete queue message")
            return False


    def manageQueue(self):
        def updateCall(jobID, update:str, err: str | None = None, prompt: int | None = None):
            self.db.updateJobStatus(jobID, update, err, prompt)

        self.log.info("Queue worker started.") 

        while True:
            msg = self.blob.queue.receive_message(visibility_timeout=QUEUE_VISIBILITY_TIMEOUT)
            
            if msg is None:
                time.sleep(10)
                continue

            jobID = None

            try:
                self.log.info(f"Raw queue message received: {msg.content}")
                data = ph.parseQueueMessage(msg.content)

                self.log.info(f"Parsed queue message: {data}")
    
                eventID = data['event_id']
                jobType = data['job_type']
                jobID = data.get("job_id")

                self.log.info(f'Parsed msg Received: {data}')

                
                if jobType== 'preprocess':

                    mediaType = data["type"]
                    uploadIDs = data.get("upload_ids") or []
                    
                    if not uploadIDs and data.get("upload_id") is not None:
                        uploadIDs = [data.get("upload_id")]

                    if mediaType == "photo":
                        mediaType = "photos"
                    elif mediaType == "video":
                        mediaType = 'videos'

                    self.log.info(f'Parsed msg Received: {data}')

                    updateCall(jobID, 'processing')
                    res = self.runProcess(eventID, mediaType, uploadIDs)

                    if res:
                        updateCall(jobID, 'completed')


                elif jobType == 'create':
                    if not jobID:
                        raise ValueError("Missing job_id for video job")
                    
                    storyBoardID = data.get('storyboard_id')

                    self.log.info(f"Running video creation for event_id={eventID}, storyboard_id={storyBoardID}")

                    if not storyBoardID:
                        raise ValueError
                    
                    updateCall(jobID, 'processing')
                    storyboard = self.db.getStoryboardByID(storyBoardID)
                    if not storyboard:
                        raise ValueError(f"Storyboard {storyBoardID} was not found")
                    if str(storyboard.get("event_id")) != str(eventID):
                        raise ValueError(
                            f"Storyboard {storyBoardID} does not belong to event {eventID}"
                        )
                    sb = self.db.getStoryboardItems(storyBoardID)

                    if not sb:
                        raise ValueError(f"No approved storyboard photos found for event {eventID}")
                    music = self.db.getMusicByID(storyboard.get("music_id"))
                    package = {"storyboard": storyboard, "items": sb, "music": music}
                    videoPath = self.ss.generateVideo(package , eventID)    

                    self.log.info(f"Video created successfully: {videoPath}")

                    updateCall(jobID, 'completed')

                else:
                    raise ValueError(f"Unknown job_type: {jobType}")

                self.deleteQueueMessage(msg)

            except Exception as e:
                self.log.exception(f"Queue job failed: {e}")

                if jobID:
                    updateCall(jobID, 'failed', str(e))

                attempts = int(getattr(msg, "dequeue_count", 1) or 1)
                if attempts >= QUEUE_MAX_ATTEMPTS:
                    self.log.error("Deleting queue message after %s failed attempts", attempts)
                    self.deleteQueueMessage(msg)
                                            
    def runProcess(self, eventID: int, dt: str = 'photos', uploadIDs: list[int] | None = None):
        print(f'Starting Event {eventID}, for {dt}')
        dt = dt.lower().strip()
        
        uploadIDs = uploadIDs or []

        if dt not in ("photos", "videos"):
            raise ValueError("dt must be either 'photos' or 'videos'")

        videoFlag = None
        vidID = None
        dType = dt2 = 'photo_id'

        if dt == 'videos':
            dType = 'frame_id'
            dt2 = 'video_id'

        try:
            photos = self.db.getMedia(eventID, dt, uploadIDs = uploadIDs or [])
    
            if not photos or len(photos) == 0:
                raise ValueError(f"No {dt} found to preprocess.")

            prefilt = imgRank = contScore = 'Success'

            with tempfile.TemporaryDirectory() as tempDir:
                tempDir = Path(tempDir)
                mediaSet = self.blob.downloadToTemp(photos, tempDir, dt2)
                mediaSet = ph.normalizeImages(mediaSet)

                if not mediaSet:
                    raise ValueError(f"No {dt} files downloaded for preprocess.")

                if dt == 'videos':
                    videoFlag = 'videos'
                    mediaSet = self.ve.batchRun(videos=mediaSet, tempDir=tempDir, eventID=eventID)
                    dt = 'video_frames'

                    if not mediaSet:
                        raise ValueError(f"No {dt} files downloaded for preprocess.")

                ids = [row[dType] for row in mediaSet]

                if videoFlag:
                    vidID = list(set(row[dt2] for row in mediaSet))
                    self.batchStatus(videoFlag, dt2, vidID, "processing")

                self.batchStatus(dt, dType, ids, "processing")
                
                pfr = self.pf.batchRunPF(mediaSet, dType)
                if not pfr:
                    prefilt = 'Failed'

                self.batchStatus(dt, dType, ids, "stage1")

                irr = self.ir.batchRunIR(mediaSet, dType)
                if not irr:
                    imgRank = 'Failed'

                self.batchStatus(dt, dType, ids, "stage2")

                csr = self.cs.batchRunCS(mediaSet, dType)

                if not csr:
                    contScore = 'Failed'
                
                self.batchStatus(dt, dType, ids, "completed")

                if videoFlag:
                    self.batchStatus(videoFlag, dt2, vidID, "completed")
        
            return {f"Pre Filter: {prefilt}\n Results: {pfr}\nImage Ranker: {imgRank}\nResults: {irr}\nContent Score: {contScore}\nResults: {csr}"}

        except Exception as e:
            self.log.exception(f"job failed: {e}")
            raise

    def batchStatus(self, tblName, idColName, rowID, Status):
        self.db.batchStatusUodate(tblName=tblName, idColName=idColName, rowIDs=rowID, status= Status)

        
# if __name__ == "__main__":
#       test = newRunner()
#       res = test.runProcess(1, 'videos')
if __name__ == "__main__":
    runner = newRunner()

    runner.manageQueue()
