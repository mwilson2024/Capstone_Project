from ultralytics import YOLO
import DBConn
from pathlib import Path
from ProjectHelper import Helpers as ph

class ContentScoring:
    def __init__(self, modelPath ="yolo26n.pt"):
        self.model = YOLO(modelPath)
        self.db = DBConn.SQLbuilder()
        self.db.connect()

    def buildDict(self, photoID: int, perCount: int, maxPerConf: float, objClass: list[str], conf: float, contScore: int, isVideo: bool = False):
        #objects = ",".join(objClass)
        id = "photo_id"
        if isVideo:
            id = "video_id"
        if objClass:
            reasonStr = ",".join(objClass)
        else:
            reasonStr = "N/A"

        return{"photo_id": photoID,
               "person_count": perCount,
               "max_person_conf": maxPerConf,
               "obj_class": objClass,
               "confidence": conf,
                "content_score": contScore
               }

    def analyze(self, photo_id: int, imgPath: str, isVideo: bool = False):
        results = self.model(imgPath)
        detectedObj = []
        perCnt = 0 #person count
        maxPerCof = 0.00
        conf = 0.0

        for result in results:
            for box in result.boxes:
                classID = int(box.cls[0])
                conf = float(box.conf[0])
                className = self.model.names[classID]

                detectedObj.append({ "class": className,"confidence": round(conf, 3)})

                if className == "person":
                    perCnt += 1
                    maxPerCof = max(maxPerCof, conf)
        
        contScore = 0
    
        if perCnt > 0:
            contScore += 25
        
        if maxPerCof > .8:
            contScore += 25

        if perCnt >= 2:
            contScore += +15

        classNames = [obj["class"] for obj in detectedObj]
        #print(f'People: {perCnt}\nCofidence: {conf}\nMax perConf: {maxPerCof}\nContent Score: {contScore}\nDetected Objects {detectedObj}')
        return(self.buildDict(photo_id, perCnt, maxPerCof, classNames,conf, contScore, isVideo=isVideo))
    
    
    def batchRunCS(self, media: list[dict], dtype: str = 'photo_id'):
        if media is None:
            err = "No files found"
            raise ValueError(err)
        
        return ph.batchRun(media, self.analyze, self.db.insertContent, dtype)
    
def main():
    scorer = ContentScoring()
    #scorer.batchRun(1)
    scorer.batchRunVideos(r'C:\CSI4999\Videos\tempFrames\event_1_35iz4tfs_frames', 1)
   # print(f)


if __name__ == "__main__":
    main()      