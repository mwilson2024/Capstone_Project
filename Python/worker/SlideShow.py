import math
import os
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

import cv2 as cv
import numpy as np
from moviepy import AudioFileClip, VideoFileClip, concatenate_audioclips


class SlideShowGenerator:
    def __init__(self, db, log, azure, width: int = 1280, height: int = 720,
                 fps: int = 30, secPerPhoto: int = 3):
        self.width = width
        self.height = height
        self.fps = fps
        self.secPerPhoto = secPerPhoto
        self.db = db
        self.log = log
        self.azure = azure

    def resizePadding(self, img):
        if img is None or not hasattr(img, "shape") or len(img.shape) < 2:
            raise ValueError("Cannot resize an empty media frame.")
        h, w = img.shape[:2]
        if h <= 0 or w <= 0:
            raise ValueError("Cannot resize a media frame with invalid dimensions.")

        scale = min(self.width / w, self.height / h)
        newW = max(int(round(w * scale)), 1)
        newH = max(int(round(h * scale)), 1)
        resized = cv.resize(img, (newW, newH))
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        xOffset = (self.width - newW) // 2
        yOffset = (self.height - newH) // 2
        canvas[yOffset:yOffset + newH, xOffset:xOffset + newW] = resized
        return canvas

    def drawCaption(self, frame, sceneLabel, reason=None):
        title = str(sceneLabel).strip() if sceneLabel is not None else ""
        subtitle = str(reason).strip() if reason is not None else ""
        if not title and not subtitle:
            return frame
        overlay = frame.copy()
        barHeight = min(120, self.height)
        yStart = self.height - barHeight
        cv.rectangle(overlay, (0, yStart), (self.width, self.height), (0, 0, 0), -1)
        frame = cv.addWeighted(overlay, 0.65, frame, 0.35, 0)
        title = str(sceneLabel) if sceneLabel else "Scene"
        subtitle = str(reason) if reason else ""
        cv.putText(frame, title[:55], (40, yStart + 45), cv.FONT_HERSHEY_SIMPLEX,1.2, (255, 255, 255), 2, cv.LINE_AA)
        if subtitle:
            cv.putText(frame, subtitle[:95], (40, yStart + 90), cv.FONT_HERSHEY_SIMPLEX,0.65, (220, 220, 220), 1, cv.LINE_AA)
        return frame

    @staticmethod
    def positiveFloat(value, default=None):
        try:
            result = float(value)
        except (TypeError, ValueError):
            return default
        return result if math.isfinite(result) and result > 0 else default

    def writeSlide(self, writer, frame, durationSeconds=None):
        duration = self.positiveFloat(durationSeconds, float(self.secPerPhoto))
        totalFrames = max(int(round(self.fps * duration)), 1)
        fadeFrames = min(max(int(round(self.fps * 0.5)), 1), max(totalFrames // 2, 1))
        black = np.zeros_like(frame)

        for i in range(totalFrames):
            if i < fadeFrames:
                alpha = min((i + 1) / fadeFrames, 1.0)
                displayFrame = cv.addWeighted(frame, alpha, black, 1 - alpha, 0)
            elif i >= totalFrames - fadeFrames:
                alpha = max((totalFrames - i) / fadeFrames, 0.0)
                displayFrame = cv.addWeighted(frame, alpha, black, 1 - alpha, 0)
            else:
                displayFrame = frame
            writer.write(displayFrame)
        return totalFrames

    def writeVideoSegment(self, writer, videoPath, startSec=0, endSec=None,durationSeconds=None, sceneLabel=None, reason=None):
        cap = cv.VideoCapture(str(videoPath))
        if not cap.isOpened():
            raise ValueError(f"Could not open video clip: {videoPath}")

        sourceFps = self.positiveFloat(cap.get(cv.CAP_PROP_FPS), float(self.fps))
        totalFrames = max(float(cap.get(cv.CAP_PROP_FRAME_COUNT) or 0), 0)
        sourceDuration = totalFrames / sourceFps if totalFrames else 0.0
        try:
            start = max(float(startSec or 0), 0.0)
        except (TypeError, ValueError):
            start = 0.0

        requestedDuration = self.positiveFloat(durationSeconds)
        if endSec is None:
            end = start + requestedDuration if requestedDuration else sourceDuration
        else:
            try:
                end = float(endSec)
            except (TypeError, ValueError):
                end = sourceDuration
        if sourceDuration > 0:
            start = min(start, sourceDuration)
            end = min(end, sourceDuration)
        if not math.isfinite(end) or end <= start:
            cap.release()
            return 0

        outputFrames = max(int(round((end - start) * self.fps)), 1)
        framesWritten = 0
        startFrame = max(int(math.floor(start * sourceFps)), 0)
        currentSourceFrame = startFrame - 1
        lastFrame = None
        cap.set(cv.CAP_PROP_POS_FRAMES, startFrame)
        try:
            for index in range(outputFrames):
                timestamp = start + index / self.fps
                wantedSourceFrame = max(int(math.floor(timestamp * sourceFps)), startFrame)
                while currentSourceFrame < wantedSourceFrame:
                    ok, sourceFrame = cap.read()
                    if not ok:
                        break
                    lastFrame = sourceFrame
                    currentSourceFrame += 1
                if lastFrame is None:
                    break
                frame = self.resizePadding(lastFrame)
                #if sceneLabel or reason:
                #    frame = self.drawCaption(frame, sceneLabel, reason)
                writer.write(frame)
                framesWritten += 1
        finally:
            cap.release()
        return framesWritten

    def generatedBlobName(self, eventID: int, fileName: str):
        return f"events/{eventID}/generated_videos/{uuid4().hex}_{Path(fileName).name}"

    @staticmethod
    def blobNameFromUrl(filePath):
        if not filePath or not isinstance(filePath, str):
            return None
        parsed = urlparse(filePath)
        if parsed.scheme not in {"http", "https"}:
            return None
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        return "/".join(parts[1:]) if len(parts) > 1 else None

    def normalizeStoryboard(self, storyboard):
        if isinstance(storyboard, dict):
            metadata = dict(storyboard.get("storyboard") or storyboard.get("metadata") or {})
            music = dict(storyboard.get("music") or {})
            items = storyboard.get("items") or storyboard.get("storyboard_items") or []
        else:
            metadata, music, items = {}, {}, storyboard
        if not isinstance(items, list) or not items:
            raise ValueError("Storyboard is empty.")
        normalized = [dict(item) for item in items if isinstance(item, dict)]
        if not normalized:
            raise ValueError("Storyboard has no valid media items.")
        normalized.sort(key=lambda item: item.get("sequence_order") or 0)
        return metadata, music, normalized

    def prepareMedia(self, items, tempPath):
        ready, remote = [], []
        for item in items:
            localPath = item.get("file_path")
            if localPath and Path(str(localPath)).is_file():
                ready.append(item)
                continue
            prepared = dict(item)
            prepared["blob_name"] = prepared.get("blob_name") or self.blobNameFromUrl(localPath)
            if not prepared.get("blob_name"):
                prepared["error"] = "No local file or Azure blob name was available"
                ready.append(prepared)
                continue
            remote.append(prepared)
        if remote:
            ready.extend(self.azure.downloadToTemp(remote, tempPath, "storyboard_item_id"))
        ready.sort(key=lambda item: item.get("sequence_order") or 0)
        return ready

    def getDefaultMusicPath(self):
        return os.getenv("DEFAULT_MUSIC_PATH") or None

    def downloadMusicToTemp(self, tempPath: Path, blobName=None):
        musicBlob = blobName or os.getenv("DEFAULT_MUSIC_BLOB_NAME")
        if not musicBlob:
            return None
        localPath = tempPath / Path(musicBlob).name
        self.azure.downloadBlobToFile(musicBlob, str(localPath))
        return str(localPath)

    def resolveMusicPath(self, tempPath: Path, musicPath=None, music=None, useDefault=True):
        music = music or {}
        candidate = musicPath or music.get("file_path")
        if candidate and Path(str(candidate)).is_file():
            return str(candidate)
        blobName = music.get("blob_name") or self.blobNameFromUrl(candidate)
        if not blobName and candidate and "/" in str(candidate) and not urlparse(str(candidate)).scheme:
            blobName = str(candidate)
        if not blobName and music.get("file_name") and "/" in str(music.get("file_name")):
            blobName = music.get("file_name")
        if blobName:
            return self.downloadMusicToTemp(tempPath, blobName)
        if not useDefault:
            return None
        localPath = self.getDefaultMusicPath()
        if localPath:
            return localPath
        return self.downloadMusicToTemp(tempPath)

    def generateVideo(self, storyboard, eventID: int, outputname=None, musicPath=None):
 
        metadata, music, items = self.normalizeStoryboard(storyboard)
        outputname = outputname or f"event_{eventID}_slideshow.mp4"
        finalOutputName = outputname if outputname.lower().endswith(".mp4") else f"{outputname}.mp4"

        with tempfile.TemporaryDirectory() as tempDir:
            tempPath = Path(tempDir)
            rawVideoPath = tempPath / f"raw_{finalOutputName}"
            finalVideoPath = tempPath / finalOutputName
            # A new storyboard with music_id=None deliberately has no music.
            useDefaultMusic = not isinstance(storyboard, dict)
            resolvedMusic = self.resolveMusicPath(tempPath, musicPath, music, useDefaultMusic)
            media = self.prepareMedia(items, tempPath)
            writer = cv.VideoWriter(str(rawVideoPath), cv.VideoWriter_fourcc(*"mp4v"),
                                    self.fps, (self.width, self.height))
            if not writer.isOpened():
                raise RuntimeError("Could not open slideshow video writer.")

            itemsUsed = 0
            framesWritten = 0
            try:
                for item in media:
                    itemID = item.get("storyboard_item_id") or item.get("photo_id") or item.get("video_id")
                    if item.get("error"):
                        self.log.warning("Skipping storyboard item %s: %s", itemID, item["error"])
                        continue
                    path = Path(str(item.get("file_path") or ""))
                    if not path.is_file():
                        self.log.warning("Skipping missing local storyboard media: %s", path)
                        continue

                    mediaType = str(item.get("source_type") or item.get("media_type")
                                    or item.get("type") or "photo").lower()
                    if mediaType == "video":
                        written = self.writeVideoSegment(
                            writer, path,
                            startSec=item.get("clip_start_seconds", item.get("clip_start", 0)),
                            endSec=item.get("clip_end_seconds", item.get("clip_end")),
                            durationSeconds=item.get("duration_seconds"),
                            sceneLabel=item.get("scene_label"), reason=item.get("reason"))
                    else:
                        img = cv.imread(str(path))
                        if img is None:
                            self.log.warning("Skipping unreadable slideshow image: %s", path)
                            continue
                        frame = self.resizePadding(img)
                        #frame = self.drawCaption(frame, item.get("scene_label"), item.get("reason"))
                        written = self.writeSlide(writer, frame, item.get("duration_seconds"))
                    if written > 0:
                        itemsUsed += 1
                        framesWritten += written
            finally:
                writer.release()

            if itemsUsed == 0:
                raise ValueError("No valid media items were added to the slideshow.")
            if not rawVideoPath.is_file() or rawVideoPath.stat().st_size == 0:
                raise RuntimeError("Raw slideshow video file was not created.")

            return self.attachMusic(
                videoPath=str(rawVideoPath), musicPath=resolvedMusic,
                outPutPath=str(finalVideoPath), eventID=eventID,
                fileName=finalOutputName, durationSeconds=framesWritten / self.fps,
                itemsUsed=itemsUsed, musicID=metadata.get("music_id") or music.get("music_id"),
                videoType=metadata.get("video_type") or "slideshow",
                title=f"Event {eventID} {str(metadata.get('video_type') or 'slideshow').replace('_', ' ').title()}")

    def attachMusic(self, videoPath, musicPath, outPutPath, eventID=None, fileName=None,durationSeconds=None, itemsUsed=None, musicID=None,videoType="slideshow", title=None):
        video = VideoFileClip(videoPath)
        music = None
        audio = None
        finalVideo = video
        videoDuration = float(video.duration or durationSeconds or 0)
        try:
            if musicPath:
                music = AudioFileClip(musicPath)
                if music.duration <= 0:
                    raise ValueError("The selected music file has no playable duration.")
                if music.duration < videoDuration:
                    repeats = max(int(math.ceil(videoDuration / music.duration)), 1)
                    audio = concatenate_audioclips([music] * repeats).subclipped(0, videoDuration)
                else:
                    audio = music.subclipped(0, videoDuration)
                finalVideo = video.with_audio(audio)
            finalVideo.write_videofile(outPutPath, codec="libx264",
                                       audio=bool(musicPath),
                                       audio_codec="aac" if musicPath else None,
                                       logger=None)
        finally:
            if finalVideo is not video:
                finalVideo.close()
            if audio is not None and audio is not music:
                audio.close()
            if music is not None:
                music.close()
            video.close()

        finalPath = Path(outPutPath)
        if not finalPath.is_file() or finalPath.stat().st_size == 0:
            raise RuntimeError("Final slideshow video was not created.")
        if eventID is None:
            return str(finalPath)

        blobName = self.generatedBlobName(eventID, fileName or finalPath.name)
        uploadResult = self.azure.uploadLocalFile(blobName=blobName, localPath=str(finalPath),contentType="video/mp4")
        if not uploadResult:
            raise RuntimeError("Final slideshow was created but could not be uploaded to Azure Blob Storage.")
        savedDuration = durationSeconds if durationSeconds is not None else videoDuration
        dbRows = self.db.insertGeneratedVideo(
            eventID=eventID, fileName=Path(blobName).name, filePath=uploadResult["url"],
            musicID=musicID, title=title or f"Event {eventID} Final Slideshow",
            videoType=videoType, status="completed", durationSeconds=savedDuration,
            width=self.width, height=self.height, fps=self.fps,
            fileSize=uploadResult["size_bytes"])
        if not dbRows:
            raise RuntimeError("Final slideshow was uploaded to Azure but could not be recorded in Supabase.")

        result = {
            "event_id": eventID, "items_used": itemsUsed,
            "duration_seconds": savedDuration, "blob_name": uploadResult["blob_name"],
            "url": uploadResult["url"],
            "generated_video": dbRows[0] if isinstance(dbRows, list) else dbRows,
        }
        self.log.info("Uploaded final slideshow for event_id=%s: %s", eventID, uploadResult["url"])
        return result
