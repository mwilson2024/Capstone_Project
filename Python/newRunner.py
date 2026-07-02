import logging
import tempfile
from pathlib import Path

import AzureClass
import ContentScorer
import DBConn
import ImageRanker
import PreFilter
from ProjectHelper import Helpers as ph

import VideoExtraction


class newRunner:
    def __init__(self, db = None, log = None, blob = None):
        self.log = log or logging.getLogger(__name__)
        self.blob = blob or AzureClass.blobHandler(self.log)
        self.db = db or DBConn.SQLbuilder(self.log)
        
        self.cs = ContentScorer.ContentScoring(db= self.db, log=self.log)
        self.ir = ImageRanker.blipRanker(db= self.db, log=self.log)
        self.pf = PreFilter.ImgQualFilt(db= self.db, log= self.log)
        self.ve = VideoExtraction.ExtractVidFrames(db= self.db, log= self.log)

    def runProcess(self, eventID: int, dt: str = 'photo'):
        dType = dt2 = 'photo_id'

        if dt == 'video':
            dType = 'frame_id'
            dt2 = 'video_id'

        photos = self.db.getMedia(eventID, dt)
        if not photos or len(photos) == 0:
            return "No Photos found"

        prefilt = imgRank = contScore = 'Success'

        with tempfile.TemporaryDirectory() as tempDir:
            tempDir = Path(tempDir)
            mediaSet = self.blob.downloadToTemp(photos, tempDir, dt2)
            if dt == 'video':
                mediaSet = self.ve.batchRun(videos=mediaSet, tempDir=tempDir, eventID=eventID)
            
            pfr = self.pf.batchRunPF(mediaSet, dType)
            if not pfr:
                prefilt = 'Failed'

            irr = self.ir.batchRunIR(mediaSet, dType)
            if not irr:
                imgRank = 'Failed'
            
            csr = self.cs.batchRunCS(mediaSet, dType)
            if not csr:
                contScore = 'Failed'
            
        return {f"Pre Filter: {prefilt}\n Results: {pfr}\nImage Ranker: {imgRank}\nResults: {irr}\nContent Score: {contScore}\nResults: {csr}"}

