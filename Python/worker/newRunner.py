import json
import os
import time
from azure.storage.queue import QueueClient
import logging
import tempfile
from pathlib import Path

from shared.AzureClass import blobHandler
from worker.ContentScorer import ContentScoring
from shared.DBConn import SQLbuilder
from worker.ImageRanker import blipRanker
from worker.PreFilter import ImgQualFilt
from worker.SlideShow import SlideShowGenerator
from api.StoryBoard import StoryBoardGen
from worker.VideoExtraction import ExtractVidFrames

logging.basicConfig(level=logging.INFO)

class newRunner:
    def __init__(self, db = None, log = None, blob = None):
        self.log = log or logging.getLogger("Worker")
        self.blob = blob or blobHandler(self.log)
        self.db = db or SQLbuilder(self.log)
        #self.queue = QueueClient.from_connection_string(conn_str=os.getenv("AZURE_STORAGE_CONNECTION_STRING"), queue_name=os.getenv("VIDEO_QUEUE_NAME", "video-jobs"))
        self.cs = ContentScoring(db= self.db, log=self.log)
        self.ir = blipRanker(db= self.db, log=self.log)
        self.pf = ImgQualFilt(db= self.db, log= self.log)
        self.ve = ExtractVidFrames(db= self.db, log= self.log)
        self.ss = SlideShowGenerator(db=db, log= self.log, azure= self.blob)
        self.sb = StoryBoardGen(db=self.db, log=self.log)


    def manageQueue(self):
        def updateCall(jobID, update:str):
            self.db.updateStatus('job_queue', 'job_id', jobID, update)

        while True:
            msg = self.queue.receive_message(visibility_timeout=300)

            
            if msg is None:
                time.sleep(5)
                continue

            jobID = None

            try:
                data = json.loads(msg.content)
    
                eventID = data['event_id']
                jobType = data['job_type']
                jobID = data.get("job_id")

                self.log.info(f'Message Received: {msg}')

                
                if jobType== 'preprocess':

                    mediaType = data["type"]
                    if mediaType == "photo":
                        mediaType = "photos"
                    elif mediaType == "video":
                        mediaType = 'videos'

                    self.runProcess(eventID, mediaType)

                elif jobType == 'create':
                    if not jobID:
                        raise ValueError("Missing job_id for video job")
                    
                    storyBoardID = data.get('storyboard_id')

                    if not storyBoardID:
                        raise ValueError
                    
                    updateCall(jobID, 'processing')

                    sb = self.db.getStoryboardItems(storyBoardID)

                    if not sb:
                        raise ValueError(f"No approved storyboard photos found for event {eventID}")
                    
                    videoPath = self.ss.generateVideo(sb, eventID)    

                    updateCall(jobID, 'Completed')

                else:
                    raise ValueError(f"Unknown job_type: {jobType}")

                self.queue.delete_message(msg)

            except Exception as e:
                self.log.exception(f"Queue job failed: {e}")

                if jobID:
                    updateCall(jobID, 'Failed')

                self.queue.delete_message(msg)

    def runProcess(self, eventID: int, dt: str = 'photos'):
        dt = dt.lower().strip()

        if dt not in ("photos", "videos"):
            raise ValueError("dt must be either 'photos' or 'videos'")

        videoFlag = None
        vidID = None
        dType = dt2 = 'photo_id'

        if dt == 'videos':
            dType = 'frame_id'
            dt2 = 'video_id'

        try:
            photos = self.db.getMedia(eventID, dt)

            if not photos or len(photos) == 0:
                return "No Photos found"

            prefilt = imgRank = contScore = 'Success'

            with tempfile.TemporaryDirectory() as tempDir:
                tempDir = Path(tempDir)
                mediaSet = self.blob.downloadToTemp(photos, tempDir, dt2)

                if dt == 'videos':
                    videoFlag = 'videos'
                    mediaSet = self.ve.batchRun(videos=mediaSet, tempDir=tempDir, eventID=eventID)
                    dt = 'video_frames'

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
                    self.batchStatus(videoFlag, dt2, vidID, "processing")
        
            return {f"Pre Filter: {prefilt}\n Results: {pfr}\nImage Ranker: {imgRank}\nResults: {irr}\nContent Score: {contScore}\nResults: {csr}"}

        except Exception as e:
            self.log.exception(f"job failed: {e}")

    def batchStatus(self, tblName, idColName, rowID, Status):
        self.db.batchStatusUodate(tblName=tblName, idColName=idColName, rowIDs=rowID, status= Status)
    
    
        
if __name__ == "__main__":
    test = newRunner()
    res = test.runProcess(1, 'videos')