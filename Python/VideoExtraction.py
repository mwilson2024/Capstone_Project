import cv2 as cv
from pathlib import Path


class ExtractVidFrames():
    def __init__(self):
        pass

    def extractFrames(self, inPath: str, outPath: str, eventID: int, setSeconds: int= 3):

        vidPath = Path(inPath)
        outPut = Path(outPath) / f"videoID{eventID}"
        outPut.mkdir(parents=True, exist_ok=True)

        if not vidPath.exists():
            print(f'Video not found: {vidPath}')
            return []
        
        cap = cv.VideoCapture(str(vidPath))
        if not cap.isOpened():
            print(f"could not open video: {vidPath}")
            return []
        
        fps = cap.get(cv.CAP_PROP_FPS)

        if fps == 0:
            fps = 30

        frameInt = int(fps * setSeconds)

        savedFrames = []
        frameCount = 0
        savedCount = 0

        while True:
            success, frame = cap.read()

            if not success: 
                break

            if frameCount % frameInt == 0:
                frameFile = outPut/f'{vidPath.stem}_frame_{savedCount}.jpg'
                cv.imwrite(str(frameFile), frame)
                savedFrames.append(str(frameFile))
                savedCount += 1

            frameCount += 1

        cap.release()

        return savedFrames
    
def main():
    frames = ExtractVidFrames()
    frames.extractFrames(r"C:\Users\Micha\Downloads\ProjectDemo2.mp4", r'C:\CSI4999\Videos\Frames', 1 )
    print(frames)

if __name__ == "__main__":
    main()