import math
import os
from pathlib import Path

import cv2 as cv


class ExtractVidFrames():
    def __init__(self, log, db):
        self.log = log
        self.db = db
        
    def extractFrames(self, inPath: str, outPath: str, videoID: int, eventID: int, setSeconds: int= 3):

        vidPath = Path(inPath)
    
        if not vidPath.exists():
            print(f'Video not found: {vidPath}')
            return []
        
        cap = cv.VideoCapture(str(vidPath))

        if not cap.isOpened():
            print(f"could not open video: {vidPath}")
            return []
        
        fps = cap.get(cv.CAP_PROP_FPS)
        totFrames = cap.get(cv.CAP_PROP_FRAME_COUNT)

        if fps == 0:
            fps = 30

        frameInt = int(fps * setSeconds)
        frameForVid = int(math.ceil(totFrames / frameInt))

       # frameData = {'saved_frames': str, "time_stamp": float}
        savedFrames = []
        frameCount = 0
        savedCount = 0

        while True:
            outPut = Path(outPath) / f"video_ID_{videoID}"
            outPut.mkdir(parents=True, exist_ok=True)
            success, frame = cap.read()
  
            if not success: 
                break

            if frameCount % frameInt == 0:
                frameSec = frameCount / fps 
                frameFile = outPut/f'{vidPath.stem}_frame_{savedCount}.jpg'
                cv.imwrite(str(frameFile), frame)
                frameData = {'event_id': eventID, 'video_id': videoID, 'file_path': str(frameFile), 'frame_num': frameCount, 'time_stamp': round(frameSec, 4)}
                savedFrames.append(frameData)
                savedCount += 1
                print(f"{savedCount}/{frameForVid}")

            frameCount += 1
        cap.release()
        frameData = self.db.upsertVideoFrames(savedFrames) #getting the frame_id back 
     
        return frameData
    
    def batchRun(self, videos: list[dict], tempDir: str, eventID: int = None):
        if not os.path.exists(tempDir):
            #os.makedirs(tempDir)
            print(f'No Directory found: {tempDir}')
        #tempDir = tempfile.mkdtemp(prefix=f"event_{eventID}_", suffix="_frames", dir=outPath)
        #if eventID:
        #    videos = self.db.getMedia(eventID, 'video')
  
        if not videos:
            print("No videos found for the given event.")
            return
        results = []
        for video in videos:
            res = self.extractFrames(video["file_path"], tempDir, video["video_id"], eventID)
            results.extend(res)
            print(f"Extracted frames for event {eventID} to {tempDir}")
            os.remove(video["file_path"])

        return results    

def main():
    frames = ExtractVidFrames()
    #frames.extractFrames(r"C:\CSI4999\Videos\kelly_&_michael's_wedding_day_teaser (2160p).mp4", r'C:\CSI4999\Videos\Frames', 1 )
    frames.batchRun(1, r'C:\CSI4999\Videos\tempFrames')
    print('done')

if __name__ == "__main__":
    main()