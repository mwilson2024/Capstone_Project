import os
import time
import logging
from logging.handlers import RotatingFileHandler
import tempfile
from pathlib import Path, PurePosixPath
from azure.core.exceptions import ResourceNotFoundError
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
from shared.ProjectHelper import Helpers as ph
from shared.AzureClass import blobHandler
from worker.ContentScorer import ContentScoring
from shared.DBConn import SQLbuilder
from worker.ImageRanker import blipRanker
from worker.PreFilter import ImgQualFilt
from worker.SlideShow import SlideShowGenerator
from api.StoryBoard import StoryBoardGen
from worker.VideoExtraction import ExtractVidFrames
from worker.VideoMetadata import VideoMetadataProcessor

register_heif_opener(thumbnails=False)

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
        self.vm = VideoMetadataProcessor(db=self.db, log=self.log, blob=self.blob)
        self.ss = SlideShowGenerator(db=self.db, log= self.log, azure= self.blob)
        self.sb = StoryBoardGen(db=self.db, log=self.log)

    def convertHeifMedia(self, mediaSet: list[dict]) -> list[dict]:
        for media in mediaSet:
            filePath = media.get("file_path")

            if not filePath:
                continue

            sourcePath = Path(filePath)

            if sourcePath.suffix.lower() not in {".heif", ".heic"}:
                continue

            convertedPath = sourcePath.with_suffix(".jpg")

            try:
                with Image.open(sourcePath) as sourceImage:
                    iccProfile = sourceImage.info.get("icc_profile")

                    with ImageOps.exif_transpose(sourceImage) as orientedImage:
                        exif = orientedImage.getexif()
                        exifBytes = exif.tobytes() if exif else None

                        with orientedImage.convert("RGB") as rgbImage:
                            saveOptions = {
                                "format": "JPEG",
                                "quality": 95,
                                "subsampling": 0,
                            }

                            if exifBytes:
                                saveOptions["exif"] = exifBytes

                            if iccProfile:
                                saveOptions["icc_profile"] = iccProfile

                            rgbImage.save(convertedPath, **saveOptions)

                blobName = media.get("blob_name")
                if not blobName:
                    raise ValueError(f"Missing blob name for HEIF image: {sourcePath.name}")

                jpegBlobName = str(PurePosixPath(blobName).with_suffix(".jpg"))
                uploaded = self.blob.uploadLocalFile(
                    blobName=jpegBlobName,
                    localPath=str(convertedPath),
                    contentType="image/jpeg",
                )
                if not uploaded:
                    raise RuntimeError(f"Could not upload converted JPEG blob: {jpegBlobName}")

                updatedUpload = self.db.updateUploadImageFormat(
                    uploadID=media.get("upload_id"),
                    blobName=uploaded["blob_name"],
                    filePath=uploaded["url"],
                    fileSize=uploaded["size_bytes"],
                )
                if not updatedUpload:
                    raise RuntimeError(
                        f"Could not update converted upload metadata: {media.get('upload_id')}"
                    )

                if not self.blob.deleteBlob(blobName):
                    self.log.warning(
                        "Converted HEIF upload but could not remove original blob: %s",
                        blobName,
                    )

                media["file_path"] = str(convertedPath)
                media["blob_name"] = uploaded["blob_name"]
                media["mime_type"] = "image/jpeg"
                media["file_size"] = uploaded["size_bytes"]
                self.log.info(f"Converted HEIF image {sourcePath.name} to {convertedPath.name}")

            except Exception as error:
                self.log.exception("Could not convert HEIF image %s", sourcePath)
                raise ValueError(f"Unable to convert HEIF image: {sourcePath.name}") from error

        return mediaSet

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

                if not mediaSet:
                    raise ValueError(f"No {dt} files downloaded for preprocess.")

                if dt == 'photos':
                    mediaSet = self.convertHeifMedia(mediaSet)

                if dt == 'videos':
                    videoFlag = 'videos'
                    metadataResults = self.vm.batchRun(videos=mediaSet, eventID=eventID)
                    self.log.info("Video metadata results: %s", metadataResults)
                    retryableMetadataFailures = [
                        row for row in metadataResults.get("failed", [])
                        if not row.get("hidden")
                    ]
                    if retryableMetadataFailures:
                        raise RuntimeError(
                            f"Video metadata processing failed: {retryableMetadataFailures}"
                        )
                    hiddenVideoIDs = {
                        row.get("video_id")
                        for row in metadataResults.get("failed", [])
                        if row.get("hidden")
                    }
                    mediaSet = [
                        video for video in mediaSet
                        if video.get("video_id") not in hiddenVideoIDs
                    ]
                    if not mediaSet:
                        self.log.warning("All videos in this job were unreadable and have been hidden.")
                        return {"Video metadata": metadataResults}
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
