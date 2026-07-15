from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from math import ceil

from shared import DataStruct as ds
from shared.ProjectHelper import Helpers as ph

class StoryBoardGen():
    def __init__(self, db, log, eventTimeGap: int = 20, maxPhotoCount: int = 100, maxVideoClips: int = 15, maxClipsPerVideo: int = 3):
        self.eventTimeGap = max(1, int(eventTimeGap))
        self.log = log
        self.db = db
        self.maxPhotoCount = max(1, int(maxPhotoCount))
        self.maxVideoClips = max(1, int(maxVideoClips))
        self.maxClipsPerVideo = max(1, int(maxClipsPerVideo))

    def parseTime(self, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, date):
            parsed = datetime.combine(value, datetime.min.time())
        elif isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None
            if cleaned.endswith("Z"):
                cleaned = cleaned[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(cleaned)
            except ValueError:
                self.log.warning("Could not parse datetime value: %r", value)
                return None
        else:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def makeFloat(value, default: float = 0.0):
        try:
            return float(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def makeInt(value, default: int = 0):
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def clamp(value: float, low: float = 0.0, high: float = 100.0):
        return max(low, min(high, value))

    def promptProfile(self, prompt):
        rawContentType = str(prompt.get("content_type") or "Both").strip().lower()
        contentType = {
            "photo only": "Photo Only",
            "photos only": "Photo Only",
            "video only": "Videos Only",
            "videos only": "Videos Only",
            "both": "Both",
        }.get(rawContentType, "Both")

        return {
            "event_id": self.makeInt(prompt.get("event_id")),
            "content_type": contentType,
            "theme": str(prompt.get("theme") or "general").strip().lower(),
            "mood": str(prompt.get("mood") or "general").strip().lower(),
            "event_type": str(prompt.get("event_type") or "unknown").strip().lower(),
            "timing_preference": str(prompt.get("timing_preference") or "unknown").strip().lower(),
            "music_preference": str(prompt.get("music_preference") or "unknown").strip().lower(),
        }

    def selectMusic(self, profile, musicRows):
        if profile["music_preference"] == "none":
            return None

        musicMap = getattr(ds.MediaMappingConfig, "MUSIC_MOOD_MAP", {})
        wantedMoods = musicMap.get(profile["music_preference"], ())
        selected = None
        bestScore = -1

        for music in musicRows or []:
            if music.get("is_active") is False:
                continue

            score = 0
            musicMood = str(music.get("mood_label") or "general").lower()
            musicEvent = str(music.get("event_type") or "general").lower()

            if musicEvent == profile["event_type"]:
                score += 40
            elif musicEvent == "general":
                score += 10

            if musicMood in wantedMoods:
                score += 40
            if musicMood == profile["mood"]:
                score += 30

            if score > bestScore:
                selected = music
                bestScore = score

        return selected

    def peopleScore(self, personCount: int, profile):
        personCount = self.makeInt(personCount)

        if profile["theme"] == "celebration" or profile["mood"] == "energetic":
            return min(100.0, 30.0 + (personCount * 12.0))

        if profile["theme"] in {"romance", "emotional"} or profile["mood"] in {"romantic", "sentimental", "calm"}:
            if personCount == 2:
                return 100.0
            if personCount == 1:
                return 80.0
            if 3 <= personCount <= 5:
                return 70.0
            return 40.0

        if personCount == 2:
            return 100.0
        if 3 <= personCount <= 6:
            return 90.0
        if personCount == 1:
            return 75.0
        return 40.0

    def scoreMedia(self, row, profile):
        themeMap = ds.MediaMappingConfig.THEME_CATEGORY_MAP
        eventMap = ds.MediaMappingConfig.EVENT_CATEGORY_MAP
        themeFields = themeMap.get(profile["theme"], themeMap["general"])
        eventFields = eventMap.get(profile["event_type"], eventMap["general"])
        moodField = profile["mood"] if profile["mood"] != "unknown" else "general"

        themeScore = max((self.clamp(self.makeFloat(row.get(field))) for field in themeFields), default=0.0)
        eventScore = max((self.clamp(self.makeFloat(row.get(field))) for field in eventFields), default=0.0)
        moodScore = self.clamp(self.makeFloat(row.get(moodField)))
        categoryScore = (themeScore * 0.45) + (moodScore * 0.35) + (eventScore * 0.20)

        contentScore = self.clamp(self.makeFloat(row.get("content_score")))
        keywordScore = self.clamp(self.makeFloat(row.get("keyword_score")))
        moodConfidence = self.clamp(self.makeFloat(row.get("mood_conf_score")), 0.0, 1.0) * 100.0
        personScore = self.peopleScore(row.get("person_count"), profile)

        score = (
            contentScore * 0.30
            + keywordScore * 0.20
            + categoryScore * 0.30
            + moodConfidence * 0.10
            + personScore * 0.10
        )
        breakdown = {
            "content": round(contentScore, 2),
            "keyword": round(keywordScore, 2),
            "category": round(categoryScore, 2),
            "mood_confidence": round(moodConfidence, 2),
            "people": round(personScore, 2),
        }
        return round(self.clamp(score), 2), breakdown

    def rejectMedia(self, row):
        nudityCheck = row.get("nudity_check")
        if isinstance(nudityCheck, str):
            nudityCheck = nudityCheck.strip().lower() in {"1", "true", "yes"}
        return bool(
            nudityCheck
            or self.makeFloat(row.get("nudity")) >= 50
            or self.makeFloat(row.get("quality_reject")) >= 70
        )

    def classifyScene(self, row: dict):
        personCount = self.makeInt(row.get("person_count"))
        objClass = str(row.get("obj_class") or "").lower()
        contentScore = self.makeFloat(row.get("content_score"))
        detailLabel = str(row.get("event_detail_label") or "unknown").lower()

        if detailLabel not in {"unknown", "general"}:
            confidence = self.clamp(self.makeFloat(row.get("event_detail_conf_score")), 0.0, 1.0)
            return detailLabel.replace("_", " ").title(), max(0.50, confidence), "Highest ranked event detail"
        if personCount >= 6:
            return "Group / Crowd Moment", 0.82, "Six or more people detected"
        if personCount == 2:
            return "Couple / Two-Person Moment", 0.80, "Two people detected"
        if 3 <= personCount <= 5:
            return "Small Group Moment", 0.76, "Three to five people detected"
        if "dining table" in objClass or "chair" in objClass:
            return "Reception / Seating Area", 0.70, "Tables or chairs detected"
        if contentScore >= 70:
            return "Highlight Moment", 0.74, "High content score"
        if personCount == 1:
            return "Portrait / Individual Moment", 0.68, "One person detected"
        return "General Event Moment", 0.50, "Default scene classification"

    def findDuplicates(self, photos: list):
        dupes = set()
        keptHashes = []

        for photo in photos:
            imageHash = photo.get("image_hash")
            if not imageHash:
                continue

            try:
                duplicate = any(ph.findDuplicateImage(oldHash, imageHash) for oldHash in keptHashes[-10:])
            except Exception as exc:
                self.log.warning("Duplicate check failed for photo_id=%s: %s", photo.get("photo_id"), exc)
                duplicate = False

            if duplicate:
                dupes.add(photo.get("photo_id"))
            else:
                keptHashes.append(imageHash)
        return dupes

    def preparePhotos(self, photos, profile, eventDate, windowStart, photoSeconds):
        prepared = []

        for photo in photos or []:
            if self.rejectMedia(photo):
                continue

            photoTime = (
                self.parseTime(photo.get("photo_original_date"))
                or self.parseTime(photo.get("photo_taken"))
                or self.parseTime(photo.get("created_at"))
            )
            if photoTime is None or photoTime < windowStart:
                continue

            score, breakdown = self.scoreMedia(photo, profile)
            sceneLabel, confidence, reason = self.classifyScene(photo)
            prepared.append({
                **photo,
                "source_type": "photo",
                "occurred_at": photoTime,
                "time_delta_seconds": (photoTime - windowStart).total_seconds(),
                "days_from_event": (photoTime - eventDate).total_seconds() / 86400.0,
                "duration_seconds": photoSeconds,
                "selection_score": score,
                "score_breakdown": breakdown,
                "scene_label": sceneLabel,
                "confidence": confidence,
                "reason": reason,
            })

        prepared.sort(key=lambda row: row["occurred_at"])
        dupes = self.findDuplicates(prepared)
        return [photo for photo in prepared if photo["photo_id"] not in dupes]

    def boundedClipWindow(self, frameTime, clipSeconds, videoDuration):
        if videoDuration <= 0:
            return None

        clipSeconds = min(max(clipSeconds, 15.0), 30.0, videoDuration)
        clipStart = frameTime - (clipSeconds / 2.0)
        clipStart = max(0.0, min(clipStart, videoDuration - clipSeconds))
        clipEnd = min(videoDuration, clipStart + clipSeconds)

        if clipEnd <= clipStart:
            return None
        return round(clipStart, 3), round(clipEnd, 3)

    def prepareVideoClips(self, frameRows, profile, eventDate, windowStart, clipSeconds):
        grouped = defaultdict(list)

        for frame in frameRows or []:
            videoID = self.makeInt(frame.get("video_id"))
            frameID = self.makeInt(frame.get("frame_id"))
            if not self.rejectMedia(frame) and videoID > 0 and frameID > 0:
                grouped[videoID].append(dict(frame))

        clips = []

        for videoID, frames in grouped.items():
            if videoID <= 0:
                continue

            videoDate = (
                self.parseTime(frames[0].get("video_original_date"))
                or self.parseTime(frames[0].get("upload_created_at"))
                or self.parseTime(frames[0].get("video_created_at"))
            )
            videoDuration = self.makeFloat(frames[0].get("duration_seconds"))

            if videoDate is None or videoDate < windowStart or videoDuration <= 0:
                continue

            for frame in frames:
                frame["selection_score"], frame["score_breakdown"] = self.scoreMedia(frame, profile)

            frames.sort(key=lambda row: row["selection_score"], reverse=True)
            selectedWindows = []
            perVideoLimit = min(self.maxClipsPerVideo, max(1, ceil(videoDuration / 60.0)))

            for frame in frames:
                if len(selectedWindows) >= perVideoLimit:
                    break

                frameTime = self.makeFloat(frame.get("time_stamp"), -1.0)
                if frameTime < 0 or frameTime > videoDuration:
                    continue

                clipWindow = self.boundedClipWindow(frameTime, clipSeconds, videoDuration)
                if clipWindow is None:
                    continue

                clipStart, clipEnd = clipWindow
                overlaps = any(clipStart < oldEnd and clipEnd > oldStart for oldStart, oldEnd in selectedWindows)
                if overlaps:
                    continue

                selectedWindows.append((clipStart, clipEnd))
                clipTime = videoDate + timedelta(seconds=clipStart)
                sceneLabel, confidence, reason = self.classifyScene(frame)

                clips.append({
                    **frame,
                    "source_type": "video",
                    "photo_id": None,
                    "video_id": videoID,
                    "occurred_at": clipTime,
                    "time_delta_seconds": (clipTime - windowStart).total_seconds(),
                    "days_from_event": (clipTime - eventDate).total_seconds() / 86400.0,
                    "clip_start_seconds": clipStart,
                    "clip_end_seconds": clipEnd,
                    "duration_seconds": clipEnd - clipStart,
                    "selection_score": frame["selection_score"],
                    "score_breakdown": frame["score_breakdown"],
                    "scene_label": sceneLabel,
                    "confidence": confidence,
                    "reason": reason,
                })

        return clips

    def generateSeq(self, media: list):
        media.sort(key=lambda row: row["occurred_at"])
        lastTime = None
        sequenceGroup = 1

        for sequenceOrder, item in enumerate(media, start=1):
            if lastTime is not None and item["occurred_at"] - lastTime > timedelta(minutes=self.eventTimeGap):
                sequenceGroup += 1

            item["sequence_order"] = sequenceOrder
            item["sequence_group"] = sequenceGroup
            lastTime = item["occurred_at"]

        return media

    def createStoryboardForPrompt(self, promptID: int):
        promptID = self.makeInt(promptID)
        if promptID <= 0:
            raise ValueError("promptID must be a positive integer")

        prompt = self.db.getPromptRequestByID(promptID)
        if not prompt:
            self.log.error(f"Prompt request not found: prompt_id={promptID}")
            return None

        if not prompt.get("allowed", True) or prompt.get("out_of_scope") or prompt.get("unsafe_or_invalid"):
            self.log.error(f"Prompt request is not allowed: prompt_id={promptID}")
            return None

        profile = self.promptProfile(prompt)
        eventID = profile["event_id"]
        event = self.db.getEventByID(eventID)
        eventDate = self.parseTime(event.get("event_date")) if event else None

        if eventDate is None:
            self.log.error(f"Event not found or invalid date: event_id={eventID}")
            return None

        windowStart = eventDate - timedelta(days=5)
        timing = ds.MediaMappingConfig.TIMING_SETTINGS.get(
            profile["timing_preference"],
            ds.MediaMappingConfig.TIMING_SETTINGS["unknown"],
        )
        photoSeconds = self.makeFloat(timing.get("photo_seconds"), 4.0)
        clipSeconds = min(max(self.makeFloat(timing.get("video_clip_seconds"), 22.0), 15.0), 30.0)

        music = self.selectMusic(profile, self.db.getActiveMusic() or [])
        musicDuration = self.makeFloat(music.get("duration_seconds")) if music else 0.0
        targetDuration = musicDuration if musicDuration > 0 else 120.0

        photos = []
        videoClips = []

        if profile["content_type"] in {"Photo Only", "Both"}:
            photos = self.preparePhotos(
                self.db.getApprovedPhotosForStoryboard(eventID) or [],
                profile,
                eventDate,
                windowStart,
                photoSeconds,
            )

        if profile["content_type"] in {"Videos Only", "Both"}:
            videoClips = self.prepareVideoClips(
                self.db.getVideoFramesForStoryboard(eventID) or [],
                profile,
                eventDate,
                windowStart,
                clipSeconds,
            )

        if profile["content_type"] == "Photo Only":
            photoLimit = min(self.maxPhotoCount, max(1, int(targetDuration // photoSeconds)))
            clipLimit = 0
            videoType = "slideshow"
        elif profile["content_type"] == "Videos Only":
            photoLimit = 0
            clipLimit = min(self.maxVideoClips, max(1, int(targetDuration // clipSeconds)))
            videoType = "full_video"
        else:
            photoLimit = min(self.maxPhotoCount, max(1, int((targetDuration * 0.65) // photoSeconds)))
            clipLimit = min(self.maxVideoClips, max(1, int((targetDuration * 0.35) // clipSeconds)))
            videoType = "highlight"

            if not videoClips:
                photoLimit = min(self.maxPhotoCount, max(1, int(targetDuration // photoSeconds)))
            elif not photos:
                clipLimit = min(self.maxVideoClips, max(1, int(targetDuration // clipSeconds)))

        photos.sort(key=lambda row: row["selection_score"], reverse=True)
        videoClips.sort(key=lambda row: row["selection_score"], reverse=True)
        selectedMedia = self.generateSeq(photos[:photoLimit] + videoClips[:clipLimit])

        if not selectedMedia:
            self.log.error(f"No eligible media found for prompt_id={promptID}")
            return None

        storyboardItems = [ds.StoryboardItemData.fromRow(row).toDict() for row in selectedMedia]
        storyboardData = {
            "video_type": videoType,
            "content_type": profile["content_type"],
            "theme": profile["theme"],
            "mood": profile["mood"],
            "timing_preference": profile["timing_preference"],
            "target_duration_seconds": targetDuration,
            "estimated_duration_seconds": sum(item["duration_seconds"] for item in storyboardItems),
            "window_start": windowStart.isoformat(),
            "event_date": eventDate.isoformat(),
            "photo_count": min(len(photos), photoLimit),
            "video_clip_count": min(len(videoClips), clipLimit),
        }

        return self.db.createStoryboardWithItems(
            eventID=eventID,
            requestID=promptID,
            musicID=music.get("music_id") if music else None,
            storyboardData=storyboardData,
            storyboard_items=storyboardItems,
        )

    def createStoryboardForEvent(self, eventID: int, requestID: int | None = None):
        eventID = self.makeInt(eventID)
        requestID = self.makeInt(requestID)
        if eventID <= 0:
            raise ValueError("eventID must be a positive integer")
        if requestID <= 0:
            raise ValueError("requestID/promptID must be a positive integer")

        prompt = self.db.getPromptRequestByID(requestID)
        if not prompt or self.makeInt(prompt.get("event_id")) != eventID:
            raise ValueError("The prompt request does not belong to the supplied eventID")
        return self.createStoryboardForPrompt(requestID)
