from ultralytics import YOLO
import cv2
from pathlib import Path
class ContentScoring:
    def __init__(self, modelPath ="yolo26n.pt"):
        self.model = YOLO(modelPath)

    def analyze(self, imgPath):
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

        print(f'People: {perCnt}\nCofidence: {conf}\nMax perConf: {maxPerCof}\nContent Score: {contScore}\nDetected Objects {detectedObj}')

    def batchRun(self, eventID):
        print('t')
def main():
    scorer = ContentScoring()
    photos = Path('C:\CSI4999\Photos')
    #for photo in photos.iterdir():
    #    print(photo.name)
    #    result = scorer.analyze(str(photo))
    #    print(result)
    scorer.analyze(str(photos))

if __name__ == "__main__":
    main()      