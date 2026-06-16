from pathlib import Path
import cv2 as cv
import numpy as np
from moviepy import VideoFileClip, AudioFileClip
import DBConn

class SlideShowGenerator:
    def __init__(self, outputDir: str = r'C:\CSI4999\Videos\Output', width: int = 1280, height: int = 720, fps: int = 30, secPerPhoto: int = 3):
        self.outputDir = Path(outputDir)
        self.outputDir.mkdir(parents=True, exist_ok=True)
        self.width = width
        self.height = height
        self.fps = fps
        self.secPerPhoto = secPerPhoto

    def resizePadding(self, img: str):
        h,w = img.shape[:2]
        scale = min(self.width/w, self.height/h)
        newW = int(w * scale)
        newH = int(h * scale)

        resized = cv.resize(img, (newW, newH))

        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        xOffset = (self.width - newW) // 2
        yOffset = (self.height - newH) // 2

        canvas[yOffset:yOffset + newH, xOffset:xOffset + newW] = resized

        return canvas
    
    def drawCaption(self, frame, sceneLabel, reason=None):
        overlay = frame.copy()

        barHeight = 120
        yStart = self.height - barHeight

        cv.rectangle(overlay,(0,yStart), (self.width, self.height), (0,0,0), -1)

        alpha = .65

        frame = cv.addWeighted(overlay, alpha, frame, 1- alpha, 0)

        title = str(sceneLabel) if sceneLabel else "Start"
        subtitle = str(reason) if reason else ""

        cv.putText(frame, title, (40, yStart + 45), cv.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255,), 2, cv.LINE_AA)

        if subtitle:
            cv.putText(frame, subtitle[:95], (40, yStart +90), cv.FONT_HERSHEY_SIMPLEX, .65, (220, 220, 220), 1, cv.LINE_AA)
        
        return frame
    
    def writeSlide(self, writer, frame):
        totalFrames = self.fps * self.secPerPhoto
        fadeFrames = int(self.fps * .5)

        black = np.zeros_like(frame)

        for i in range(totalFrames):
            displayFrame = frame.copy()

            #fade in
            if i < fadeFrames:
                alpha = i / fadeFrames
                displayFrame = cv.addWeighted(frame, alpha, black, 1 - alpha, 0)
                
            #fade out
            elif i > totalFrames - fadeFrames:
                alpha = (totalFrames - i) / fadeFrames
                displayFrame = cv.addWeighted(frame, alpha, black, 1 - alpha, 0)

            writer.write(displayFrame)

    def generateVideo(self, storyboard, outputname="final_slideshow.mp4"):
        if not storyboard:
            print("storyboard is empty")
            return None
        
        outPutPath = self.outputDir / outputname

        fourcc = cv.VideoWriter_fourcc(*"mp4v")
        writer = cv.VideoWriter(str(outPutPath), fourcc, self.fps, (self.width, self.height))

        usedCount = 0

        for item in storyboard:
            filePath = item.get('file_path')

            if not filePath:
                errMsg = "Skipping item with missing file_path."
                print(errMsg)
                continue

            path = Path(filePath)

            if not path.exists():
                errMsg = f'File not found: {path}'
                print(errMsg)
                continue
            
            img = cv.imread(str(path))

            if img is None:
                errMsg = f'could not read image: {path}'
                print(errMsg)
                continue

            frame = self.resizePadding(img)

            frame = self.drawCaption(frame, item.get('scene_label', 'Scene'), item.get('reason', ''))

            self.writeSlide(writer, frame)
            usedCount += 1
        
        writer.release()

        if usedCount == 0:
            errMsg = 'No valid images were added to the video'
            print(errMsg)

        print(f'Video generated: {outPutPath}')
        return str(outPutPath)
    
    def pickMusic(self, event_type: str):
        event_type = event_type.lower()

        if event_type == "wedding":
            return "C:\CSI4999\Music\jonasblakewood-wedding-519603.mp3"

        if event_type == "graduation":
            return "C:\CSI4999\Music\jonasblakewood-wedding-519603.mp3"

        if event_type == "concert":
            return "C:\CSI4999\Music\jonasblakewood-wedding-519603.mp3"

        return "C:\CSI4999\Music\jonasblakewood-wedding-519603.mp3"
    
    def attachMusic(self, videoPath, musicPath, outPutPath):
        db = DBConn.SQLbuilder()
        db.connect()
        video = VideoFileClip(videoPath)
        music = AudioFileClip(musicPath)

        music = music.subclipped(0, video.duration)

        finalVideo =  video.with_audio(music)
        finalVideo.write_videofile(outPutPath, codec="libx264", audio_codec="aac")

        video.close()
        music.close()
        finalVideo.close

def main():
    db = DBConn.SQLbuilder()
    eventID = 1 
    db.connect()
    storyboard = db.getStoryboardByEvent(eventID)
    if not storyboard:
        print(f"No storyboard found for event_id {eventID}")
    else:
        generator = SlideShowGenerator(
            outputDir=r"C:\CSI4999\Videos\Output",
            width=1280,
            height=720,
            fps=30,
            secPerPhoto=3
        )

        rawVideoPath = generator.generateVideo(
            storyboard,
            outputname=f"event_{eventID}_slideshow_no_music.mp4"
        )

        if rawVideoPath:
            musicPath = generator.pickMusic(event_type="genral")

            finalVideoPath = rf"C:\CSI4999\Videos\Output\event_{eventID}_slideshow_with_music.mp4"

            if Path(musicPath).exists():
                generator.attachMusic(
                    videoPath=rawVideoPath,
                    musicPath=musicPath,
                    outPutPath=finalVideoPath
                )

                print(f"Final video created: {finalVideoPath}")
            else:
                print(f"Music file not found: {musicPath}")
                print(f"Video without music created: {rawVideoPath}")

if __name__ == "__main__":
    main()