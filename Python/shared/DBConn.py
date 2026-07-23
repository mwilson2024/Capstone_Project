import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from dotenv import load_dotenv
from shared.ProjectHelper import Helpers as ph
from supabase import Client, create_client


class SQLbuilder:
    def __init__(self, log):
        load_dotenv()

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not self.supabase_url or not self.service_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")

        self.client: Client = create_client(self.supabase_url, self.service_key)
        self.log = log

    def connect(self):
        try:
            # Simple lightweight call to confirm the client can reach Supabase
            self.client.table("photos").select("photo_id").limit(1).execute()
            return True
        except Exception as error:
            self.log.info("Connection failed:", error)
            return False

    def executeWithRetry(self, operation, description: str, maxAttempts: int = 3):
        for attempt in range(1, maxAttempts + 1):
            try:
                return operation()
            except httpx.TransportError as error:
                if attempt == maxAttempts:
                    raise

                delay = 0.2 * (2 ** (attempt - 1))
                self.log.warning(
                    "Transient Supabase transport error while %s (attempt %s/%s): %s. Retrying in %.1fs.",
                    description,
                    attempt,
                    maxAttempts,
                    error,
                    delay,
                )
                time.sleep(delay)

    def insertToDB(self, values, table: str = "Basic",  kwMatch: str ="photo_id"):
        try:
            query = self.client.table(table)
            if kwMatch:
                result = query.upsert(values, on_conflict=kwMatch).execute()
            else:
                result = query.insert(values).execute()

            count = len(values) if isinstance(values, list) else 1
            self.log.info(f"Saved {count} row(s) to {table}")
            return result.data

        except Exception as e:
            self.log.info(f"Error inserting into {table}: {e}")
            return None

    def postQRtoDB(self, eventID: int, url: str, token: str, expires_at: str, max_uploads: int, purpose: str, is_active: bool):
        if eventID is None or url is None:
            self.log.info('Missing Values in arguments')
            return None

        try:
            data = {
                "event_id": eventID,
                "image_url": url,
                "token": token,
                "expires_at": expires_at,
                "max_uploads": max_uploads,
                "purpose": purpose,
                "is_active": is_active
            }

            result = (
                self.client
                .table("qrcodes")
                .insert(data)
                .select("*")
                .execute()
            )

            if not result.data:
                self.log.warning("QR code insert returned no data")
                return None

            return result.data[0]

        except Exception as e:
            self.log.exception(f"Error posting QR code to DB: {e}")
            return None

    def incrementQRUploadCount(self, token: str, amount: int = 1):
        if token is None or token.strip() == "":
            return False

        try:
            qr = self.getQRToken(token)

            if not qr:
                return False

            current_count = qr.get("upload_count", 0)

            result = (
                self.client
                .table("qrcodes")
                .update({"upload_count": current_count + amount})
                .eq("token", token.strip())
                .execute()
            )

            return bool(result.data)

        except Exception as e:
            self.log.info(f"Error incrementing QR upload count: {e}")
            return False


    def getQRToken(self, token: str):
        try:
            result = (
                self.client
                .table("qrcodes")
                .select("*")
                .eq("token", token)
                .limit(1)
                .execute()
            )

            if not result.data:
                return None

            return result.data[0]

        except Exception as e:
            self.log.exception(f"Error getting QR token: {e}")
            return None

    def insertPreFilter(self, results: list[dict], dtype: str = 'photo_id'):
        
        if not results:
            self.log.info("No filter results to insert.")
            return None
        table = 'photo_filter'

        if dtype == 'frame_id':
            table = 'video_filter'

        values = [
            {
                dtype: item.get(dtype),
                "status": item.get("status", "pending"),
                "reason": item.get("reason", ""),
                "blur_score": item.get("blur_score", 0),
                "bright_score": item.get("bright_score", 0),
                "contrast_score": item.get("contrast_score", 0),
                "width": item.get("width", 0),
                "height": item.get("height", 0),
                "image_hash": item.get("image_hash"),
                "photo_original_date": ph.formatTimeStamps(item.get("photo_original_date")),
                "camera_model": item.get("camera_model"),
                "gps": item.get("gps"),
                "user_approved": item.get("user_approved", 0)
            }
            for item in results
        ]
        return self.insertToDB(values, table, dtype)

    def insertContent(self, results: list[dict], dtype = 'photo_id'):
        if not results:
            self.log.info("No filter results to insert.")
            return None
        
        table = 'photo_content'

        if dtype == 'frame_id':
            table = 'video_content'

        values = [
            {
                dtype: item.get(dtype),
                "person_count": item.get("person_count", 0),
                "max_person_conf": item.get("max_person_conf", 0.0),
                "obj_class": item.get("obj_class", ""),
                "confidence": item.get("confidence", 0.0),
                "content_score": item.get("content_score", 0)
            }
            for item in results
        ]
        return self.insertToDB(values, table, dtype)

    def insertImageRanking(self,dataDict: list[dict] | dict, dtype: str = "photo_id"):
        if not dataDict:
            self.log.info("Missing image ranking data")
            return None

        if dtype not in {"photo_id", "frame_id"}:
            self.log.error(f"Invalid image ranking dtype: {dtype}")
            return None

        table = "photo_ranking"

        if dtype == "frame_id":
            table = "video_ranking"

        if isinstance(dataDict, dict):
            dataDict = [dataDict]

        if not isinstance(dataDict, list):
            self.log.error("Image ranking data must be a dict or list of dicts")
            return None

        invalidItems = [index
            for index, item in enumerate(dataDict)
            if not isinstance(item, dict)
        ]

        if invalidItems:
            self.log.error(f"Invalid image ranking results at indexes: {invalidItems}")
            return None

        values = [
            {
                dtype: item.get(dtype),
                "caption": item.get("caption",""),
                "mood_label": item.get("mood_label","unknown"),
                "mood_conf_score": item.get("mood_conf_score",0.0),
                "all_mood_labels": item.get("all_mood_labels",""),
                "keyword_score": item.get("keyword_score",0 ),
                "keywords": item.get("keywords",""),
                "nudity_check": item.get("nudity_check",False),
                "all_mood_scores": item.get("all_mood_scores",""),
                "event_type": item.get("event_type","unknown"),
                "event_type_conf_score": item.get("event_type_conf_score",0.0),
                "event_detail_label": item.get("event_detail_label","unknown"),
                "event_detail_conf_score": item.get("event_detail_conf_score",0.0),
                "event_detail_scores": item.get("event_detail_scores",""),
                "romantic": item.get("romantic",0),
                "professional": item.get("professional",0),
                "friends": item.get("friends",0),
                "family": item.get("family",0),
                "ceremony": item.get("ceremony",0),
                "reception": item.get("reception",0),
                "dancing": item.get("dancing",0),
                "food_decor": item.get("food_decor",0),
                "venue_detail": item.get("venue_detail",0),
                "happy": item.get("happy",0),
                "sentimental": item.get("sentimental",0),
                "energetic": item.get("energetic",0),
                "calm": item.get("calm",0),
                "dramatic": item.get("dramatic",0),
                "nostalgic": item.get("nostalgic",0),
                "funny": item.get("funny",0),
                "general": item.get("general",0),
                "quality_reject": item.get("quality_reject",0),
                "nudity": item.get("nudity",0),
                "matched_keywords": item.get("matched_keywords",""
                )
            }
            for item in dataDict
            if item.get(dtype) is not None
        ]

        if not values:
            self.log.info(
                f"No valid image ranking rows contained {dtype}"
            )
            return None

        return self.insertToDB(
            values=values,
            table=table,
            kwMatch=dtype
        )

    def selectAll(self, table: str):
        try:
            result = self.client.table(table).select("*").execute()
            return result.data
        except Exception as e:
            self.log.info(f"Error selecting all from {table}: {e}")
            return None

    # def getApprovedPhotosForStoryboard(self, eventID: int):
    #     if eventID is None:
    #         self.log.info("Missing eventID")
    #         return []

    #     try:
    #         result = self.client.rpc(
    #             "get_approved_photos_for_storyboard",
    #             {"p_event_id": eventID}
    #         ).execute()

    #         return result.data or []

    #     except Exception as e:
    #         self.log.info(f"Error getting approved photos for storyboard: {e}")
    #         return []
        
    def createStoryboard(self,eventID: int,requestID: int | None = None,status: str = "created"):
        if eventID is None:
            self.log.info("Missing eventID")
            return None

        values = {
            "event_id": eventID,
            "status": status
        }

        if requestID is not None:
            values["request_id"] = requestID

        try:
            query = self.client.table("storyboards")

            if requestID is not None:
                # Use upsert only when request_id exists
                result = (
                    query
                    .upsert(values, on_conflict="request_id")
                    .select("*")
                    .execute()
                )
            else:
                # No request_id, so just create a new storyboard
                result = (
                    query
                    .insert(values)
                    .select("*")
                    .execute()
                )

            rows = result.data or []

            if not rows:
                self.log.info("Storyboard was not created.")
                return None

            storyboard = rows[0]

            if self.log:
                self.log.info(
                    f"Created storyboard_id={storyboard.get('storyboard_id')} "
                    f"for event_id={eventID}"
                )

            return storyboard

        except Exception as e:
            self.log.info(f"Error creating storyboard: {e}")
            return None
        
    
    def insertStoryboardItems(self, storyboardID: int, storyboard_items: list[dict]):
        if storyboardID is None:
            self.log.info("Missing storyboardID")
            return []

        if not storyboard_items:
            self.log.info("No storyboard items to upsert.")
            return []

        values = []
        seen_sequence_orders = set()

        for index, item in enumerate(storyboard_items, start=1):
            sequence_order = item.get("sequence_order")

            # If sequence_order is missing, None, blank, or duplicate, use the next available index
            if sequence_order is None or sequence_order == "":
                sequence_order = index

            sequence_order = int(sequence_order)

            while sequence_order in seen_sequence_orders:
                sequence_order += 1

            seen_sequence_orders.add(sequence_order)

            values.append({
                "storyboard_id": storyboardID,
                "photo_id": item.get("photo_id"),
                "sequence_order": sequence_order,
                "scene_label": item.get("scene_label", "General Event Moment"),
                "confidence": item.get("confidence", 0),
                "reason": item.get("reason", "")
            })

        try:
            result = (
                self.client
                .table("storyboard_items")
                .upsert(
                    values,
                    on_conflict="storyboard_id,sequence_order"
                )
                .select("*")
                .execute()
            )

            rows = result.data or []

            self.log.info(f"Upserted {len(rows)} storyboard item(s).")
            return rows

        except Exception as e:
            self.log.info(f"Error upserting storyboard items: {e}")
            return []

    # def createStoryboardWithItems(self,eventID: int,storyboard_items: list[dict],requestID: int | None = None):
    #     storyboard = self.createStoryboard(eventID=eventID,requestID=requestID,status="created")

    #     if not storyboard:
    #         return None

    #     storyboardID = storyboard["storyboard_id"]

    #     inserted_items = self.insertStoryboardItems(storyboardID=storyboardID,storyboard_items=storyboard_items)

    #     if not inserted_items:
    #         self.updateStoryboardStatus(storyboardID, "failed")
    #         return None

    #     self.updateStoryboardStatus(storyboardID, "completed")
        

    #     return {
    #         "storyboard": storyboard,
    #         "items": inserted_items
    #     }
    
    #def getStoryboardByEvent(self, eventID: int):
    #     if eventID is None:
    #         self.log.info("Missing eventID")
    #         return []

    #     try:

    #         result = (
    #             self.client.table("storyboard_items")
    #             .select(
    #                 "storyboard_id, photo_id, sequence_order, "
    #                 "scene_label, confidence, reason, "
    #                 "photos(upload_id, uploads(file_path, blob_name))" 
    #             )
    #             .eq("event_id", eventID)
    #             .order("sequence_order", desc=False)
    #             .execute()
    #         )

    #         rows = result.data or []

    #         cleaned = []
    #         for row in rows:
    #             photo = row.pop("photos", None) or {}
    #             upload = photo.get("uploads") or {}
    #             row["file_path"] = upload.get("file_path")
    #             row["blob_name"] = upload.get("blob_name")
    #             row["scene_label"] = row.get("scene_label") or "General Event Moment"
    #             row["confidence"] = row.get("confidence") or 0
    #             row["reason"] = row.get("reason") or ""
    #             cleaned.append(row)

    #         return cleaned

    #     except Exception as e:
    #         self.log.info(f"Error fetching storyboard for event {eventID}: {e}")
    #         return []

    #     except Exception as e:
    #         self.log.info(f"Error getting storyboard: {e}")
    #         return []

    def insertMusic(self, title: str, fileName: str, filePath: str, artist: str = None, eventType: str = "general",moodLabel: str = "general", 
                durationSeconds: float = 0, source: str = "local file",licenseType: str = "project testing", isActive: bool = True):
        table = 'music'

        values = {
            "title": title,
            "artist": artist,
            "event_type": eventType,
            "mood_label": moodLabel,
            "file_name": fileName,
            "file_path": filePath,
            "duration_seconds": durationSeconds,
            "source": source,
            "license_type": licenseType,
            "is_active": isActive
        }
        return self.insertToDB(values, table, kwMatch=None)

    def insertGeneratedVideo(self,eventID: int,fileName: str,filePath: str,musicID: int | None = None,title: str = "Final Event Video",
        videoType: str = "slideshow",status: str = "completed",durationSeconds: float = 0,width: int = 1280,height: int = 720,fps: int = 30,fileSize: int = 0):
        try:
            values = {
                "event_id": eventID,
                "music_id": musicID,
                "title": title,
                "file_name": fileName,
                "file_path": filePath,
                "video_type": videoType,
                "status": status,
                "duration_seconds": durationSeconds,
                "width": width,
                "height": height,
                "fps": fps,
                "file_size": fileSize
            }

            self.log.info("Generated video insert values:", values)

            result = (
                self.client
                .table("generated_videos")
                .insert(values)
                .execute()
            )

            self.log.info("Generated video inserted.")
            return result.data

        except Exception as e:
            self.log.exception(f"Error inserting into generated_videos: {e}")
            return None
            
    def insertUploads(self, uploads: list[dict]):
        if not uploads:
            self.log.info("No uploads to insert.")
            return []

        try:
            rows = []

            for item in uploads:
                rows.append({
                    "event_id": item["event_id"],
                    "qr_code_id": item.get("qr_code_id"),
                    "guest_id": item.get("guest_id"),
                    "user_id": item.get("user_id"),

                    "original_file_name": item["original_file_name"],
                    "blob_name": item["blob_name"],
                    "file_path": item["file_path"],

                    "media_type": item["media_type"],
                    "mime_type": item.get("mime_type"),
                    "file_size": item.get("file_size", 0),

                    "upload_status": item.get("upload_status", "uploaded"),
                    "processing_status": item.get("processing_status", "not_started"),

                })

            result = (
                self.client
                .table("uploads")
                .insert(rows)
                .execute()
            )

            self.log.info(f"Inserted {len(result.data)} upload records.")
            return result.data

        except Exception as e:
            self.log.exception(f"Error inserting uploads: {e}")
            return None
    
    def insertMediaRecordsFromUploads(self, insertedUploads: list[dict]):
        if not insertedUploads:
            self.log.info("No inserted uploads to process.")
            return {
                "photos": [],
                "videos": []
            }

        inserted_photos = []
        inserted_videos = []

        try:
            photoRows = []
            videoRows = []

            for upload in insertedUploads:
                media_type = upload["media_type"]
                upload_id = upload["upload_id"]
                event_id = upload["event_id"]

                if media_type == "photo":
                    photoRows.append({
                        "event_id": event_id,
                        "upload_id": upload_id
                    })

                elif media_type == "video":
                    videoRows.append({
                        "event_id": event_id,
                        "upload_id": upload_id,
                        "title": upload.get("original_file_name", "Event Video"),
                        "status": "pending"
                    })

            if photoRows:
                photo_result = (
                    self.client
                    .table("photos")
                    .insert(photoRows)
                    .execute()
                )

                inserted_photos = photo_result.data
                self.log.info(f"Inserted {len(inserted_photos)} photo row(s).")

            if videoRows:
                video_result = (
                    self.client
                    .table("videos")
                    .insert(videoRows)
                    .execute()
                )

                inserted_videos = video_result.data
                self.log.info(f"Inserted {len(inserted_videos)} video row(s).")

            self.updateUploadsWithMediaIds(inserted_photos, inserted_videos)

            return {
                "photos": inserted_photos,
                "videos": inserted_videos
            }

        except Exception as e:
            self.log.exception(f"Error inserting media records: {e}")
            return {
                "photos": inserted_photos,
                "videos": inserted_videos
            }

    def updateUploadsWithMediaIds(self, photos: list[dict], videos: list[dict]):
        try:
            for photo in photos:
                self.client.table("uploads").update({
                    "photo_id": photo["photo_id"]
                }).eq("upload_id", photo["upload_id"]).execute()

            for video in videos:
                self.client.table("uploads").update({
                    "video_id": video["video_id"]
                }).eq("upload_id", video["upload_id"]).execute()

            self.log.info("Updated uploads with photo_id/video_id.")

        except Exception as e:
            self.log.exception(f"Error updating uploads with media ids: {e}")

    def getMedia(self, eventID: int, mediaType: str, uploadIDs: Optional[list[int]] = None):

        if eventID is None:
            self.log.error("Missing eventID")
            return []

        mediaType = mediaType.lower().strip()


        table = "photos" if mediaType == "photos" else "videos"
        id_field = "photo_id" if mediaType == "photos" else "video_id"

        uploads_select = ("uploads!photos_upload_id_fkey" if mediaType == "photos" else "uploads")

        try:
            query = (
                self.client
                .table(table)
                .select(f"""
                    {id_field},
                    event_id,
                    upload_id,
                    status,
                    {uploads_select} (
                        blob_name,
                        file_path
                    )
                """)
                .eq("event_id", eventID)
                .in_("status", ["pending", "failed"])
            )

            if uploadIDs:
                query = query.in_("upload_id", uploadIDs)

            if mediaType == "videos":
                query = query.or_("hide_video.eq.false,hide_video.is.null")

            result = query.execute()
                
            rows = result.data or []
            media_list = []

            for row in rows:
                upload = row.get("uploads") or {}

                media_list.append({
                    id_field: row.get(id_field),
                    "event_id": row.get("event_id"),
                    "upload_id": row.get("upload_id"),
                    "status": row.get("status"),
                    "blob_name": upload.get("blob_name"),
                    "file_path": upload.get("file_path"),
                })

            self.log.info(
                f"{mediaType.capitalize()} data obtained: "
                f"{len(media_list)} pending/failed item(s)"
            )

            return media_list

        except Exception as e:
            self.log.exception(f"Error occurred getting {mediaType}: {e}")
            return []

    def updateVideoMetadata(self, eventID: int, videoID: int, metadata: dict):
        if not eventID or not videoID or not metadata:
            return None

        values = {
            "duration_seconds": metadata.get("duration_seconds"),
            "width": metadata.get("width"),
            "height": metadata.get("height"),
            "fps": metadata.get("fps"),
            "thumbnail_path": metadata.get("thumbnail_path"),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        if metadata.get("video_original_date"):
            values["video_original_date"] = metadata["video_original_date"]

        values = {key: value for key, value in values.items() if value is not None}

        try:
            result = (
                self.client
                .table("videos")
                .update(values)
                .eq("video_id", videoID)
                .eq("event_id", eventID)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as error:
            self.log.exception(
                "Could not update metadata for video_id=%s event_id=%s: %s",
                videoID,
                eventID,
                error,
            )
            return None

    def updateUploadImageFormat(self,uploadID: int,blobName: str,filePath: str,fileSize: int):
        if not uploadID or not blobName or not filePath or fileSize is None:
            return None

        try:
            result = (
                self.client
                .table("uploads")
                .update({
                    "blob_name": blobName,
                    "file_path": filePath,
                    "mime_type": "image/jpeg",
                    "file_size": int(fileSize),
                })
                .eq("upload_id", uploadID)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as error:
            self.log.exception(
                "Could not update JPEG metadata for upload_id=%s: %s",
                uploadID,
                error,
            )
            return None

    def getVideosForMetadataBackfill(self, offset: int = 0, limit: int = 100, videoID: int | None = None):
        offset = max(int(offset or 0), 0)
        limit = min(max(int(limit or 100), 1), 1000)

        try:
            query = (
                self.client
                .table("videos")
                .select("""
                    video_id,
                    event_id,
                    upload_id,
                    duration_seconds,
                    width,
                    height,
                    fps,
                    thumbnail_path,
                    video_original_date,
                    uploads!inner(
                        blob_name,
                        file_path,
                        original_file_name
                    )
                """)
                .order("video_id")
                .range(offset, offset + limit - 1)
            )
            if videoID is not None:
                query = query.eq("video_id", int(videoID))

            result = query.execute()
            rows = []
            for row in result.data or []:
                upload = row.pop("uploads", None) or {}
                if isinstance(upload, list):
                    upload = upload[0] if upload else {}
                row["blob_name"] = upload.get("blob_name")
                row["file_path"] = upload.get("file_path")
                row["original_file_name"] = upload.get("original_file_name")
                rows.append(row)
            return rows
        except Exception as error:
            self.log.exception("Could not load videos for metadata backfill: %s", error)
            return []

    def insertPromptRequest(self, promptData: dict):

        if not promptData:
            self.log.info("No prompt request data to insert.")
            return None

        try:
            row = {
                "event_id": promptData.get("event_id") or promptData.get("eventID"),
                "user_id": promptData.get("user_id") or promptData.get("userID"),
                "guest_id": promptData.get("guest_id") or promptData.get("guestID"),

                "original_prompt": promptData.get("original_prompt") or promptData.get("prompt"),

                "intent": promptData.get("intent", "unknown"),
                "content_type": promptData.get("content_type", "Both"),
                "theme": promptData.get("theme", "general"),
                "mood": promptData.get("mood", "general"),
                "event_type": promptData.get("event_type", "unknown"),
                "timing_preference": promptData.get("timing_preference", "unknown"),
                "music_preference": promptData.get("music_preference", "unknown"),

                "allowed": promptData.get("allowed", True),
                "out_of_scope": promptData.get("out_of_scope", False),
                "unsafe_or_invalid": promptData.get("unsafe_or_invalid", False),

                "reason": promptData.get("reason", "No reason provided."),
                "response": promptData.get("response", ""),
                "processing_status": promptData.get("processing_status", "not_started")
            }

            required = [
                "event_id",
                "user_id",
                "original_prompt",
                "intent",
                "content_type",
                "theme",
                "mood",
                "event_type",
                "timing_preference",
                "music_preference",
                "reason",
                "response"
            ]

            missing = [field for field in required if row.get(field) is None]

            if missing:
                self.log.info(f"Missing required prompt request fields: {missing}")
                return None

            result = (
                self.client
                .table("prompt_requests")
                .insert(row)
                .execute()
            )

            self.log.info("Prompt request inserted.")
            return result.data

        except Exception as e:
            self.log.exception(f"Error inserting prompt request: {e}")
            return None 
        
    def _apply_upload_owner_filter(self,query,userID: Optional[int] = None,guestID: Optional[int] = None):

        if userID is not None and guestID is not None:
            return query.or_(
                f"user_id.eq.{userID},guest_id.eq.{guestID}",
                reference_table="uploads"
            )

        if userID is not None:
            return query.eq("uploads.user_id", userID)

        if guestID is not None:
            return query.eq("uploads.guest_id", guestID)

        return query

    def getAllMedia(self, eventID: int, dataType: str = "both", limit: int = 30, offset: int = 0):
        dataType = dataType.lower().strip()

        if dataType not in ["both", "videos", "photos"]:
            raise ValueError("dataType must be 'both', 'videos', or 'photos'.")


        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100.")

        if offset < 0:
            raise ValueError("offset cannot be negative.")
        
        rangeEnd = offset + limit - 1

        result = {"photos": [], "videos": [], "photo_total": 0, "video_total": 0}

        if dataType in ["both", "photos"]:
            photos = self.executeWithRetry(
                lambda: self.client
                .table("photos")
                .select(
                    """
                    photo_id,
                    event_id,
                    created_at,
                    photo_taken,
                    last_edit,
                    upload_id,
                    uploads!inner(
                        upload_id,
                        guest_id,
                        user_id,
                        original_file_name,
                        blob_name,
                        file_path,
                        media_type,
                        mime_type,
                        file_size,
                        upload_status,
                        processing_status,
                        created_at,
                        guests(
                            guest_id,
                            display_name,
                            email,
                            phone_number
                        ),
                        app_user(
                            user_id,
                            user_name,
                            first_name,
                            last_name,
                            email
                        )
                    )
                    """,
                    count="exact",
                )
                .eq("event_id", eventID)
                .eq("hide_photo", False)
                .eq("uploads.media_type", "photo")
                .order("created_at", desc=True)
                .range(offset, rangeEnd)
                .execute(),
                "loading event photos",
            )
            photoRows = photos.data or []
            result["photo_total"] = int(photos.count or 0)
            photoIDs = [row["photo_id"] for row in photoRows]

            rankingByID = {}
            filterByID = {}
            if photoIDs:
                filters = self.executeWithRetry(
                    lambda: self.client
                    .table("photo_filter")
                    .select("photo_id,status,reason,user_approved,image_hash")
                    .in_("photo_id", photoIDs)
                    .execute(),
                    "loading photo filter results",
                )
                filterByID = {
                    row["photo_id"]: row
                    for row in filters.data or []
                }
                rankings = self.executeWithRetry(
                    lambda: self.client
                    .table("photo_ranking")
                    .select("photo_id,nudity_check")
                    .in_("photo_id", photoIDs)
                    .execute(),
                    "loading photo ranking results",
                )
                rankingByID = {
                    row["photo_id"]: row
                    for row in rankings.data or []
                }
            for photo in photoRows:
                ranking = rankingByID.get(photo["photo_id"], {})
                photoFilter = filterByID.get(photo["photo_id"], {})
                photo["nudity_check"] = ranking.get("nudity_check", False)
                photo["filter_status"] = photoFilter.get("status")
                photo["filter_reason"] = photoFilter.get("reason")
                photo["user_approved"] = photoFilter.get("user_approved", False)
                photo["image_hash"] = photoFilter.get("image_hash")

            result["photos"] = photoRows
            
        if dataType in ["both", "videos"]:
            videos = self.executeWithRetry(
                lambda: self.client
                .table("videos")
                .select(
                    """
                    video_id,
                    event_id,
                    title,
                    status,
                    duration_seconds,
                    width,
                    height,
                    fps,
                    thumbnail_path,
                    created_at,
                    last_updated,
                    upload_id,
                    uploads!inner(
                        upload_id,
                        guest_id,
                        user_id,
                        original_file_name,
                        blob_name,
                        file_path,
                        media_type,
                        mime_type,
                        file_size,
                        upload_status,
                        processing_status,
                        created_at,
                        guests(
                            guest_id,
                            display_name,
                            email,
                            phone_number
                        ),
                        app_user(
                            user_id,
                            user_name,
                            first_name,
                            last_name,
                            email
                        )
                    )
                    """,
                    count="exact",
                )
                .eq("event_id", eventID)
                .eq("hide_video", False)
                .eq("uploads.media_type", "video")
                .order("created_at", desc=True)
                .range(offset, rangeEnd)
                .execute(),
                "loading event videos",
            )
            result["videos"] = videos.data or []
            result["video_total"] = int(videos.count or 0)

        return result

    def insertUser(self, user_data: dict):
        try:
            result = (
                self.client
                .table("app_user")
                .insert(user_data)
                .execute()
            )

            if result.data:
                return result.data[0]

            return None

        except Exception as e:
            self.log.exception(f"Error creating user: {e}")
            return None
    
    def getUserPWD(self, email: str = None, userName: str = None):
        try:
            if not email and not userName:
                self.log.info("Email or username is required.")
                return None

            query = (
                self.client
                .table("app_user")
                .select('user_id', "password_hash")
            )
            
            if email:
                query = query.eq("email", email)
            elif userName:
                query = query.eq("user_name", userName)

            result = query.execute()

            return result.data[0] if result.data else None

        except Exception as e:
            self.log.exception(f"Error getting user password: {e}")
            return None

    def getUserInfo(self, userID):
        if not userID:
            return None

        query = (self.client
                 .table('app_user')
                 .select("user_id, user_name, first_name, last_name, email, phone, role, created, last_updated")
                 .eq('user_id', userID)
                 .execute())

        return query.data[0] if query.data else None
    
    def eventCreate(self, eventData: dict):
        try:
            result = (
                self.client
                .table("event")
                .insert(eventData)
                .execute()
            )

            if result.data:
                return result.data[0]

            return None

        except Exception as e:
            self.log.exception(f"Error creating event: {e}")
            return None
            
    def locationCreate(self, location: dict):
        try:
            res = (
                self.client
                .table('location')
                .insert(location)
                .execute()
            )
            if res.data:
                return res.data[0]

            return None

        except Exception as e:
            self.log.exception(f"Error creating event location: {e}")
            return None
        
    def locationGetAll(self):
        try:
            result = (
                self.client
                .table("location")
                .select(
                    "location_id, venue_name, street, city, state, zip, searchable"
                )
                .order("venue_name", desc=False)
                .execute()
            )

            return result.data

        except Exception as e:
            self.log.exception(f"Error getting locations: {e}")
            return None
        
    def locationGetByID(self, locationID: int):
        try:
            result = (
                self.client
                .table("location")
                .select("*")
                .eq("location_id", locationID)
                .single()
                .execute()
            )

            return result.data

        except Exception as e:
            self.log.info(f"Error getting location: {e}")
            return None
        
    def eventGetAllByUser(self, userID: int):
        try:
            result = (
                self.client
                .table("event")
                .select(
                    """
                    event_id,
                    user_id,
                    name,
                    type,
                    event_date,
                    location_id,
                    status,
                    uploads_enabled,
                    upload_limit,
                    created_at,
                    last_updated
                    """
                )
                .eq("user_id", userID)
                .order("event_date", desc=False)
                .execute()
            )

            return result.data

        except Exception as e:
            self.log.exception(f"Error getting user events: {e}")
            return None
        
    def eventGetByID(self, eventID: int):
        try:
            result = (
                self.client
                .table("event")
                .select(
                    """
                    event_id,
                    user_id,
                    name,
                    type,
                    event_date,
                    location_id,
                    status,
                    uploads_enabled,
                    upload_limit,
                    created_at,
                    last_updated,
                    location:location_id (
                        location_id,
                        venue_name,
                        street,
                        city,
                        state,
                        zip,
                        searchable
                    )
                    """
                )
                .eq("event_id", eventID)
                .single()
                .execute()
            )

            return result.data

        except Exception as e:
            self.log.exception(f"Error getting event: {e}")
            return None
        
    def eventModify(self, eventID: int, eventData: dict):
        try:
            result = (
                self.client
                .table("event")
                .update(eventData)
                .eq("event_id", eventID)
                .execute()
            )

            if result.data:
                return result.data[0]

            return None

        except Exception as e:
            self.log.exception(f"Error modifying event: {e}")
            return None
    
    def locationModify(self, locationID: int, locData: dict):
        try:
            result = (
                self.client
                .table("location")
                .update(locData)
                .eq("location_id", locationID)
                .execute()
            )

            if result.data:
                return result.data[0]

            return None

        except Exception as e:
            self.log.exception(f"Error modifying location: {e}")
            return None
        
    def updateStatus(self, tblName: str, idColName: str, rowID: int, status: str, statusColName: str = "status"):
        try:
            result = (
                self.client
                .table(tblName)
                .update({statusColName: status})
                .eq(idColName, rowID)
                .select("*")
                .execute()
            )

            if not result.data:
                self.log.warning(f"No row updated in {tblName}. {idColName}={rowID}")
                return None

            return result.data[0]

        except Exception as e:
            self.log.exception(
                f"Error updating {tblName}.{statusColName} where {idColName}={rowID}"
            )
            return None
    def batchStatusUodate(self,tblName: str,idColName: str,rowIDs: list[int],status: str, statusColName: str = "status"):
        try:
            if not rowIDs:
                self.log.warning(f"No IDs provided for {tblName} batch status update.")
                return []

            result = (
                self.client
                .table(tblName)
                .update({statusColName: status})
                .in_(idColName, rowIDs)
                .select("*")
                .execute()
            )

            if not result.data:
                self.log.warning(
                    f"No rows updated in {tblName}. {idColName} in {rowIDs}"
                )
                return []

            return result.data

        except Exception:
            self.log.exception(
                f"Error batch updating {tblName}.{statusColName} where {idColName} in {rowIDs}"
            )
            return []
        
    def updateStoryboardStatus(self, storyboardID: int, status: str):
        if storyboardID is None:
            self.log.info("Missing storyboardID")
            return None

        try:
            result = (
                self.client
                .table("storyboards")
                .update({"status": status})
                .eq("storyboard_id", storyboardID)
                .select("*")
                .execute()
            )

            rows = result.data or []

            if not rows:
                self.log.info(f"No storyboard updated for storyboard_id={storyboardID}")
                return None

            return rows[0]

        except Exception as e:
            self.log.exception(f"Error updating storyboard status: {e}")
            return None
    
    def upsertVideoFrames(self, frames: list[dict]):
        if not frames:
            self.log.exception("No frames provided")
            return []

        try:
            result = self.client.rpc("upsert_video_frames", {
                "p_frames": frames
            }).execute()

            inserted = result.data or []

            # Build a lookup from (video_id, frame_num) -> file_path from the input
            file_path_lookup = {
                (f["video_id"], f["frame_num"]): f.get("file_path")
                for f in frames
            }

            # Attach file_path back onto each returned row
            for row in inserted:
                key = (row.get("video_id"), row.get("frame_num"))
                row["file_path"] = file_path_lookup.get(key)

            self.log.info(f"Upserted {len(inserted)} video frame(s)")
            return inserted

        except Exception as e:
            self.log.exception(f"Error occurred upserting video frames: {e}")
            return []
        
    def getStoryboardItems(self, storyboardID: int):
        if storyboardID is None:
            self.log.exception("Missing storyboardID")
            return []

        try:
            result = (
                self.client
                .table("storyboard_items")
                .select("*")
                .eq("storyboard_id", storyboardID)
                .order("sequence_order", desc=False)
                .execute()
            )

            rows = result.data or []
            cleaned = []

            for row in rows:
                row["scene_label"] = row.get("scene_label") or "General Event Moment"
                row["confidence"] = row.get("confidence") or 0
                row["reason"] = row.get("reason") or ""

                cleaned.append(row)

            return cleaned

        except Exception as e:
            self.log.exception(f"Error fetching storyboard_id={storyboardID}: {e}")
            return []
        
    def getStoryboardsByEvent(self, eventID: int):
        if eventID is None:
            self.log.info("Missing eventID")
            return []

        try:
            result = (
                self.client
                .table("storyboards")
                .select("*")
                .eq("event_id", eventID)
                .order("created_at", desc=True)
                .execute()
            )

            return result.data or []

        except Exception as e:
            self.log.exception(f"Error fetching storyboards for event_id={eventID}: {e}")
            return []

    def getLatestStoryboardByEvent(self, eventID: int):
        if eventID is None:
            self.log.exception("Missing eventID")
            return []

        try:
            result = (
                self.client
                .table("storyboards")
                .select("*")
                .eq("event_id", eventID)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            rows = result.data or []

            if not rows:
                self.log.info(f"No storyboard found for event_id={eventID}")
                return []

            storyboardID = rows[0]["storyboard_id"]

            return self.getStoryboardItems(storyboardID)

        except Exception as e:
            self.log.exception(f"Error getting latest storyboard for event_id={eventID}: {e}")
            return []

    def createJobQueue(self,promptID: int | None,jobType: str,status: str = "pending", uploadID: int | None = None):
        if promptID is None and jobType != "preprocess":
            self.log.error("Missing promptID")
            return None


        try:
            values = {
                "job_type": jobType,
                "status": status,
            }

            if promptID is not None:
                values["prompt_id"] = promptID

            if uploadID is not None:
                values["upload_id"] = uploadID

            result = (
                self.client
                .table("job_queue")
                .insert(values)
                .select("*")
                .execute()
            )

            rows = result.data or []

            if not rows:
                self.log.info("Job queue row was not created.")
                return None

            return rows[0]

        except Exception as e:
            self.log.exception(f"Error creating job queue row: {e}")
            return None
        
    def updateJobQueueStatus(self,jobID: int,status: str,errorMessage: str | None = None):
        if jobID is None:
            self.log.exception("Missing jobID")
            return None

        try:
            now = datetime.now(timezone.utc).isoformat()

            values = {
                "status": status
            }

            if status in ["processing", "running"]:
                values["started_at"] = now

            if status in ["completed", "failed"]:
                values["finished_at"] = now

            if errorMessage is not None:
                values["error_message"] = errorMessage

            result = (
                self.client
                .table("job_queue")
                .update(values)
                .eq("job_id", jobID)
                .select("*")
                .execute()
            )

            rows = result.data or []

            if not rows:
                self.log.info(f"No job_queue row updated for job_id={jobID}")
                return None

            return rows[0]

        except Exception as e:
            self.log.exception(f"Error updating job_queue status: {e}")
            return None


    def getJobQueueByID(self, jobID: int):
        if jobID is None:
            self.log.exception("Missing jobID")
            return None

        try:
            result = (
                self.client
                .table("job_queue")
                .select("*")
                .eq("job_id", jobID)
                .single()
                .execute()
            )

            return result.data

        except Exception as e:
            self.log.exception(f"Error getting job_queue row: {e}")
            return None
        
    def updateJobStatus(self, jobID: int, status: str, error_message: str | None = None,prompt_id: int | None = None):
        if jobID is None:
            self.log.info("Missing jobID")
            return None

        if not status:
            self.log.info("Missing status")
            return None

        now = datetime.now(timezone.utc).isoformat()

        update_data = {
            "status": status
        }

        # If the job starts
        if status in ["processing", "running", "started"]:
            update_data["started_at"] = now

        # If the job finishes
        if status in ["complete", "completed", "success", "failed", "error"]:
            update_data["finished_at"] = now

        # Save error message if provided
        if error_message is not None:
            update_data["error_message"] = error_message

        # Save prompt_id if provided
        if prompt_id is not None:
            update_data["prompt_id"] = prompt_id

        try:
            result = (
                self.client
                .table("job_queue")
                .update(update_data)
                .eq("job_id", jobID)
                .execute()
            )

            updated = result.data or []

            if not updated:
                self.log.info(f"No job_queue row found for job_id={jobID}")
                return None

            self.log.info(f"Updated job_queue job_id={jobID} to status={status}")
            return updated[0]

        except Exception as e:
            self.log.exception(f"Error updating job_queue status: {e}")
            return None
    
    def getMyEvents(self, userID: int):
        if userID is None or userID <= 0:
            self.log.error("A valid userID is required to load events")
            return None

        try:
            result = (
                self.client
                .table("event")
                .select(
                    """
                    event_id,
                    user_id,
                    name,
                    type,
                    event_date,
                    location_id,
                    status,
                    uploads_enabled,
                    upload_limit,
                    created_at,
                    last_updated
                    """
                )
                .eq("user_id", userID)
                .order("event_date", desc=False)
                .execute()
            )

            return result.data or []

        except Exception as e:
            self.log.exception(f"Error getting events for user_id={userID}: {e}")
            return None
        
    def getEventTypeFromMedia(self, mediaID: int, dtype: str = "photo_id") -> str:

        if mediaID is None:
            self.log.error("getEventIDFromMedia: mediaID is required")
            return None

        if dtype not in {"photo_id", "frame_id"}:
            self.log.error("getEventIDFromMedia: invalid dtype=%s", dtype)
            return None

        try:
            if dtype == "photo_id":
                result = (
                    self.client
                    .table("photos")
                    .select("event_id")
                    .eq("photo_id", mediaID)
                    .limit(1)
                    .execute()
                )

                rows = result.data or []

                if not rows:
                    self.log.warning(f"No photo found for photo_id={mediaID}")
                    return None

                eventID = rows[0].get("event_id")

                if eventID is None:
                    self.log.warning(f"Photo photo_id={mediaID} has no event_id")
                    return None

            else:
                frameResult = (
                    self.client
                        .table("video_frames")
                        .select("video_id")
                        .eq("frame_id", mediaID)
                        .limit(1)
                        .execute()
                )

                frameRows = frameResult.data or []

                if not frameRows:
                    self.log.warning(f"No video frame found for frame_id={mediaID}")
                    return None

                videoID = frameRows[0].get("video_id")

                if videoID is None:
                    self.log.warning(f"Video frame frame_id={mediaID} has no video_id")
                    return None

                videoResult = (
                    self.client
                        .table("videos")
                        .select("event_id")
                        .eq("video_id", videoID)
                        .limit(1)
                        .execute()
                )

                videoRows = videoResult.data or []

                if not videoRows:
                    self.log.warning(f"No video found for video_id={videoID} from frame_id={mediaID}")
                    return None

                eventID = videoRows[0].get("event_id")

                if eventID is None:
                    self.log.warning(f"Video video_id={videoID} has no event_id")
                    return None

            eventID = int(eventID)

            # Now fetch the full row from the "event" table
            eventResult = (
                self.client
                    .table("event")
                    .select("type")
                    .eq("event_id", eventID)
                    .limit(1)
                    .execute()
            )

            eventRows = eventResult.data or []

            if not eventRows:
                self.log.warning(f"No event found for event_id={eventID}")
                return None

            return eventRows[0]

        except Exception:
            self.log.exception(f"Failed to get event_id for dtype={dtype} media_id={mediaID}")
            return None

    def getPromptRequestByID(self, promptID: int):
        if promptID is None:
            self.log.error("Missing promptID")
            return None

        try:
            result = (self.client.table("prompt_requests")
                      .select("*")
                      .eq("prompt_request_id", promptID)
                      .limit(1)
                      .execute())
            return result.data[0] if result.data else None
        except Exception as e:
            self.log.error(f"Error getting prompt request prompt_id={promptID}: {e}")
            return None

    def getEventByID(self, eventID: int):
        if eventID is None:
            self.log.error("Missing eventID")
            return None

        try:
            result = (self.client.table("event")
                      .select("event_id,user_id,name,type,event_date,location_id,status,created_at,last_updated,uploads_enabled,upload_limit")
                      .eq("event_id", eventID)
                      .limit(1)
                      .execute())
            return result.data[0] if result.data else None
        except Exception as e:
            self.log.error(f"Error getting event event_id={eventID}: {e}")
            return None

    def getActiveMusic(self):
        try:
            result = (self.client.table("music")
                      .select("music_id,title,artist,event_type,mood_label,file_name,file_path,duration_seconds,source,license_type,is_active")
                      .eq("is_active", True)
                      .order("title", desc=False)
                      .execute())
            return result.data or []
        except Exception as e:
            self.log.error(f"Error getting active music: {e}")
            return []

    def getApprovedPhotosForStoryboard(self, eventID: int):
        if eventID is None:
            self.log.error("Missing eventID")
            return []

        try:
            photoResult = (self.client.table("photos")
                           .select("photo_id,event_id,upload_id,photo_taken,created_at")
                           .eq("event_id", eventID)
                           .or_("hide_photo.eq.false,hide_photo.is.null")
                           .execute())
            photos = photoResult.data or []

            if not photos:
                return []

            photoIDs = [row["photo_id"] for row in photos]
            uploadIDs = list({row["upload_id"] for row in photos if row.get("upload_id") is not None})

            filterResult = (self.client.table("photo_filter")
                            .select("photo_id,status,reason,blur_score,bright_score,contrast_score,gps,image_hash,photo_original_date,camera_model,user_approved")
                            .in_("photo_id", photoIDs)
                            .execute())
            approvedFilters = {
                row["photo_id"]: row
                for row in filterResult.data or []
                if row.get("status") == "approved"
                or row.get("user_approved") in (True, 1, "1")
            }

            if not approvedFilters:
                return []

            approvedIDs = list(approvedFilters.keys())
            contentResult = (self.client.table("photo_content")
                             .select("photo_id,person_count,max_person_conf,obj_class,content_score")
                             .in_("photo_id", approvedIDs)
                             .execute())
            rankingResult = (self.client.table("photo_ranking")
                             .select("photo_id,caption,mood_label,mood_conf_score,all_mood_labels,keyword_score,keywords," \
                             "nudity_check,all_mood_scores,event_type,event_type_conf_score,event_detail_label,event_detail_conf_score," \
                             "event_detail_scores,romantic,professional,friends,family,ceremony,reception,dancing,food_decor,venue_detail,happy," \
                             "sentimental,energetic,calm,dramatic,nostalgic,funny,general,quality_reject,nudity,matched_keywords")
                             .in_("photo_id", approvedIDs)
                             .execute())
            uploadResult = (self.client.table("uploads")
                            .select("upload_id,file_path,created_at")
                            .in_("upload_id", uploadIDs)
                            .execute())if uploadIDs else None

            contentByID = {row["photo_id"]: row for row in contentResult.data or []}
            rankingByID = {row["photo_id"]: row for row in rankingResult.data or []}
            uploadByID = {row["upload_id"]: row for row in uploadResult.data or []} if uploadResult else {}
            approvedPhotos = []

            for photo in photos:
                photoID = photo["photo_id"]
                if photoID not in approvedFilters:
                    continue

                upload = uploadByID.get(photo.get("upload_id"), {})
                row = dict(photo)
                row.update(approvedFilters.get(photoID, {}))
                row.update(contentByID.get(photoID, {}))
                row.update(rankingByID.get(photoID, {}))
                row["file_path"] = upload.get("file_path")
                row["upload_created_at"] = upload.get("created_at")
                approvedPhotos.append(row)

            approvedPhotos.sort(key=lambda row: row.get("photo_original_date") or row.get("photo_taken") or row.get("created_at") or "")
            return approvedPhotos
        except Exception as e:
            self.log.error(f"Error getting approved photos for storyboard event_id={eventID}: {e}")
            return []

    def getVideoFramesForStoryboard(self, eventID: int):
        if eventID is None:
            self.log.error("Missing eventID")
            return []

        try:
            frameResult = (self.client.table("video_frames")
                           .select("frame_id,video_id,event_id,frame_num,time_stamp,created_at,status")
                           .eq("event_id", eventID)
                           .execute())
            frames = frameResult.data or []

            if not frames:
                return []

            frameIDs = [row["frame_id"] for row in frames]
            videoIDs = list({row["video_id"] for row in frames if row.get("video_id") is not None})
            if not videoIDs:
                return []

            videoResult = (self.client.table("videos")
                           .select("video_id,event_id,status,duration_seconds,video_original_date,created_at,upload_id,hide_video")
                           .in_("video_id", videoIDs)
                           .execute())
            videos = [
                row for row in videoResult.data or []
                if row.get("event_id") == eventID
                and row.get("hide_video") is not True
                and row.get("status") not in {"failed", "rejected"}
            ]

            if not videos:
                return []

            visibleVideoIDs = {row["video_id"] for row in videos}
            uploadIDs = list({row["upload_id"] for row in videos if row.get("upload_id") is not None})
            contentResult = (self.client.table("video_content")
                             .select("frame_id,person_count,max_person_conf,obj_class,content_score")
                             .in_("frame_id", frameIDs)
                             .execute())
            rankingResult = (self.client.table("video_ranking")
                             .select("frame_id,caption,mood_label,mood_conf_score,all_mood_labels,keyword_score,keywords,nudity_check," \
                             "all_mood_scores,event_type,event_type_conf_score,event_detail_label,event_detail_conf_score,event_detail_scores,romantic,professional," \
                             "friends,family,ceremony,reception,dancing,food_decor,venue_detail,happy,sentimental,energetic,calm,dramatic,nostalgic,funny,general," \
                             "quality_reject,nudity,matched_keywords")
                             .in_("frame_id", frameIDs).
                             execute())
            uploadResult = (self.client.table("uploads")
                            .select("upload_id,file_path,created_at")
                            .in_("upload_id", uploadIDs)
                            .execute()) if uploadIDs else None

            videoByID = {row["video_id"]: row for row in videos}
            contentByID = {row["frame_id"]: row for row in contentResult.data or []}
            rankingByID = {row["frame_id"]: row for row in rankingResult.data or []}
            uploadByID = {row["upload_id"]: row for row in uploadResult.data or []} if uploadResult else {}
            frameRows = []

            for frame in frames:
                videoID = frame.get("video_id")
                if videoID not in visibleVideoIDs:
                    continue

                video = videoByID.get(videoID, {})
                upload = uploadByID.get(video.get("upload_id"), {})
                row = dict(frame)
                row.update(contentByID.get(frame["frame_id"], {}))
                row.update(rankingByID.get(frame["frame_id"], {}))
                row["duration_seconds"] = video.get("duration_seconds")
                row["video_original_date"] = video.get("video_original_date")
                row["video_created_at"] = video.get("created_at")
                row["upload_created_at"] = upload.get("created_at")
                row["file_path"] = upload.get("file_path")
                frameRows.append(row)

            return frameRows
        except Exception:
            self.log.exception(f"Error getting video frames for storyboard event_id={eventID}")
            return []

    def createStoryboardWithItems(self, eventID: int, requestID: int, musicID: int | None, storyboardData: dict, storyboard_items: list[dict]):
        if eventID is None or requestID is None:
            self.log.error("Missing eventID or requestID")
            return None

        if not storyboard_items:
            self.log.error(f"No storyboard items provided for prompt_id={requestID}")
            return None

        sequenceOrders = set()
        for item in storyboard_items:
            sourceType = item.get("source_type")
            sequenceOrder = item.get("sequence_order")
            if sourceType not in {"photo", "video"}:
                self.log.error(f"Invalid storyboard source_type={sourceType!r}")
                return None
            if not isinstance(sequenceOrder, int) or sequenceOrder <= 0 or sequenceOrder in sequenceOrders:
                self.log.error(f"Invalid or duplicate storyboard sequence_order={sequenceOrder!r}")
                return None
            if sourceType == "photo" and item.get("photo_id") is None:
                self.log.error("Photo storyboard item is missing photo_id")
                return None
            if sourceType == "video" and (item.get("video_id") is None or item.get("frame_id") is None):
                self.log.error("Video storyboard item is missing video_id or frame_id")
                return None
            sequenceOrders.add(sequenceOrder)

        storyboardID = None
        previousItems = []
        previousStatus = None
        itemsReplaced = False

        def restorePreviousStoryboard():
            if storyboardID is None or not itemsReplaced:
                return
            try:
                self.client.table("storyboard_items").delete().eq("storyboard_id", storyboardID).execute()
                if previousItems:
                    self.client.table("storyboard_items").insert(previousItems).execute()
                self.client.table("storyboards").update(
                    {"status": previousStatus or "failed"}
                ).eq("storyboard_id", storyboardID).execute()
            except Exception:
                self.log.exception(f"Failed to restore storyboard_id={storyboardID} after replacement error")

        try:
            previousStoryboardResult = (self.client.table("storyboards")
                                        .select("storyboard_id,status")
                                        .eq("request_id", requestID)
                                        .limit(1)
                                        .execute())
            previousStoryboard = previousStoryboardResult.data[0] if previousStoryboardResult.data else None
            if previousStoryboard:
                previousStatus = previousStoryboard.get("status")
                previousItemResult = (self.client.table("storyboard_items")
                                      .select("*")
                                      .eq("storyboard_id", previousStoryboard["storyboard_id"])
                                      .execute())
                previousItems = [
                    {
                        key: value for key, value in row.items()
                        if key not in {"storyboard_item_id", "created_at"}
                    }
                    for row in previousItemResult.data or []
                ]

            storyboardValues = {"event_id": eventID, "request_id": requestID, "music_id": musicID, "status": "processing", "video_type": storyboardData.get("video_type", "highlight"), "content_type": storyboardData.get("content_type", "Both"), "theme": storyboardData.get("theme", "general"), "mood": storyboardData.get("mood", "general"), "timing_preference": storyboardData.get("timing_preference", "unknown"), "target_duration_seconds": storyboardData.get("target_duration_seconds", 0), "estimated_duration_seconds": storyboardData.get("estimated_duration_seconds", 0), "window_start": storyboardData.get("window_start"), "event_date": storyboardData.get("event_date")}
            storyboardResult = (self.client.table("storyboards")
                                .upsert(storyboardValues, on_conflict="request_id")
                                .select("*")
                                .execute())

            if not storyboardResult.data:
                self.log.error(f"Storyboard was not created for prompt_id={requestID}")
                return None

            storyboard = storyboardResult.data[0]
            storyboardID = storyboard["storyboard_id"]
            self.client.table("storyboard_items").delete().eq("storyboard_id", storyboardID).execute()
            itemsReplaced = True

            itemValues = []
            for item in storyboard_items:
                itemValues.append({"storyboard_id": storyboardID, "source_type": item.get("source_type", "photo"), "photo_id": item.get("photo_id"), "video_id": item.get("video_id"), "frame_id": item.get("frame_id"), "sequence_order": item.get("sequence_order"), "sequence_group": item.get("sequence_group", 1), "scene_label": item.get("scene_label", "General Event Moment"), "confidence": item.get("confidence", 0), "reason": item.get("reason"), "file_path": item.get("file_path"), "occurred_at": item.get("occurred_at"), "time_delta_seconds": item.get("time_delta_seconds", 0), "days_from_event": item.get("days_from_event", 0), "clip_start_seconds": item.get("clip_start_seconds"), "clip_end_seconds": item.get("clip_end_seconds"), "duration_seconds": item.get("duration_seconds", 0), "selection_score": item.get("selection_score", 0), "score_breakdown": item.get("score_breakdown", {})})

            itemResult = self.client.table("storyboard_items").insert(itemValues).select("*").execute()
            insertedItems = itemResult.data or []

            if len(insertedItems) != len(itemValues):
                restorePreviousStoryboard()
                self.log.error(f"Storyboard item insert count mismatch storyboard_id={storyboardID} expected={len(itemValues)} inserted={len(insertedItems)}")
                return None

            completedResult = self.client.table("storyboards").update({"status": "completed"}).eq("storyboard_id", storyboardID).select("*").execute()
            completedStoryboard = completedResult.data[0] if completedResult.data else storyboard
            self.log.info(f"Created storyboard_id={storyboardID} prompt_id={requestID} items={len(insertedItems)}")
            return {"storyboard": completedStoryboard, "items": insertedItems}
        except Exception as e:
            if itemsReplaced:
                restorePreviousStoryboard()
            elif storyboardID is not None:
                try:
                    self.client.table("storyboards").update({"status": "failed"}).eq("storyboard_id", storyboardID).execute()
                except Exception:
                    self.log.exception(f"Failed to mark storyboard_id={storyboardID} as failed")
            self.log.error(f"Error creating storyboard with items prompt_id={requestID}: {e}")
            return None

    def getStoryboardByID(self, storyboardID: int):
        if storyboardID is None:
            self.log.error("Missing storyboardID")
            return None

        try:
            result = (
                self.client.table("storyboards")
                .select("*")
                .eq("storyboard_id", storyboardID)
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception as e:
            self.log.exception(
                f"Error fetching storyboard_id={storyboardID}: {e}"
            )
            return None

    def getMusicByID(self, musicID: int):
        if musicID is None:
            return None

        try:
            result = (
                self.client.table("music")
                .select(
                    "music_id,title,artist,event_type,mood_label,"
                    "file_name,file_path,duration_seconds,source,"
                    "license_type,is_active"
                )
                .eq("music_id", musicID)
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception as e:
            self.log.exception(
                f"Error fetching music_id={musicID}: {e}"
            )
            return None  
    def updateUserProfile(self,userID: int,profileData: dict):
        if not userID or not profileData:
            return None

        try:
            values = dict(profileData)
            values["last_updated"] = (
                datetime.now(timezone.utc).isoformat()
            )

            result = (
                self.client
                .table("app_user")
                .update(values)
                .eq("user_id", userID)
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception as e:
            self.log.exception(f"Error updating user_id={userID}: {e}")
            return None
        
    def getUserPasswordByID(self, userID: int):
        if not userID:
            return None

        try:
            result = (
                self.client
                .table("app_user")
                .select("user_id,password_hash")
                .eq("user_id", userID)
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception as e:
            self.log.exception(f"Error getting password for user_id={userID}: {e}")
            return None
        
    def updateUserPassword(self,userID: int,passwordHash: str):
        if not userID or not passwordHash:
            return False

        try:
            result = (
                self.client
                .table("app_user")
                .update({
                    "password_hash": passwordHash,
                    "last_updated": (
                        datetime.now(timezone.utc).isoformat()
                    ),
                })
                .eq("user_id", userID)
                .execute()
            )

            return bool(result.data)

        except Exception as e:
            self.log.exception(f"Error updating password for user_id={userID}: {e}")
            return False
        
    def createOrGetGuestSession(self, guestData: dict):
        if (
            not guestData
            or not guestData.get("event_id")
            or not guestData.get("display_name")
        ):
            return None

        try:
            existing = []
            email = guestData.get("email")
            phone = guestData.get("phone_number")

            if email:
                result = (
                    self.client
                    .table("guests")
                    .select(
                        "guest_id,event_id,display_name,email,"
                        "phone_number,can_post,created_at"
                    )
                    .eq("event_id", guestData["event_id"])
                    .eq("email", email)
                    .limit(1)
                    .execute()
                )

                existing = result.data or []

            elif phone:
                result = (
                    self.client
                    .table("guests")
                    .select(
                        "guest_id,event_id,display_name,email,"
                        "phone_number,can_post,created_at"
                    )
                    .eq("event_id", guestData["event_id"])
                    .eq("phone_number", phone)
                    .limit(1)
                    .execute()
                )

                existing = result.data or []

            if existing:
                return existing[0]

            result = (
                self.client
                .table("guests")
                .insert({
                    "event_id": guestData["event_id"],
                    "display_name": guestData["display_name"],
                    "email": email,
                    "phone_number": phone,
                    "can_post": True,
                })
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception as e:
            self.log.exception(f"Error creating guest session: {e}")
            return None
        
    def getGuestForEvent(self,guestID: int,eventID: int):
        if not guestID or not eventID:
            return None

        try:
            result = (
                self.client
                .table("guests")
                .select(
                    "guest_id,event_id,display_name,email,"
                    "phone_number,can_post,created_at"
                )
                .eq("guest_id", guestID)
                .eq("event_id", eventID)
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception as e:
            self.log.exception(f"Error getting guest_id={guestID} for event_id={eventID}: {e}")
            return None
    
    def getGeneratedVideosByEvent(self, eventID: int):
        if not eventID:
            return []

        try:
            result = (
                self.client
                .table("generated_videos")
                .select(
                    "gen_vid_id,event_id,music_id,title,"
                    "file_name,file_path,video_type,status,"
                    "duration_seconds,width,height,fps,file_size,"
                    "created_at,last_updated"
                )
                .eq("event_id", eventID)
                .order("created_at", desc=True)
                .execute()
            )

            return result.data or []

        except Exception as e:
            self.log.exception(f"Error loading generated videos for event_id={eventID}: {e}")
            return None

    def getGeneratedVideoByID(self, generatedVideoID: int):
        if not generatedVideoID:
            return None

        try:
            result = (
                self.client
                .table("generated_videos")
                .select(
                    "gen_vid_id,event_id,music_id,title,"
                    "file_name,file_path,video_type,status,"
                    "duration_seconds,width,height,fps,file_size,"
                    "created_at,last_updated"
                )
                .eq("gen_vid_id", generatedVideoID)
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception as e:
            self.log.exception(f"Error loading generated video id={generatedVideoID}: {e}")
            return None
        
    def deactivateEventQRCodes(self, eventID: int, exceptToken: str | None = None):
        if not eventID:
            return False

        try:
            query = (
                self.client
                .table("qrcodes")
                .update({"is_active": False})
                .eq("event_id", eventID)
                .eq("is_active", True)
            )
            if exceptToken:
                query = query.neq("token", exceptToken)
            result = query.execute()
            return result.data is not None
        except Exception as e:
            self.log.exception(
                f"Error deactivating QR codes for event_id={eventID}: {e}"
            )
            return False

    def getActiveEventQRCode(self, eventID: int):
        if not eventID:
            return None

        try:
            result = (
                self.client
                .table("qrcodes")
                .select("*")
                .eq("event_id", eventID)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            self.log.exception(
                f"Error loading active QR code for event_id={eventID}: {e}"
            )
            return None

    def updatePhotoSlideshowPreference(self, eventID: int, photoID: int, action: str):
        if not eventID or not photoID or action not in {"approve", "exclude"}:
            return None

        try:
            photoResult = (
                self.client
                .table("photos")
                .select("photo_id")
                .eq("photo_id", photoID)
                .eq("event_id", eventID)
                .limit(1)
                .execute()
            )
            if not photoResult.data:
                return None

            filterResult = (
                self.client
                .table("photo_filter")
                .select("*")
                .eq("photo_id", photoID)
                .limit(1)
                .execute()
            )
            current = filterResult.data[0] if filterResult.data else None
            reasons = [
                reason.strip()
                for reason in str((current or {}).get("reason") or "").split(",")
                if reason.strip() and reason.strip() != "N/A"
            ]

            if action == "approve":
                reasons = [reason for reason in reasons if reason != "user_excluded"]
                values = {
                    "status": (current or {}).get("status") or "approved",
                    "reason": ",".join(reasons) or "user_approved",
                    "user_approved": True,
                }
            else:
                if "user_excluded" not in reasons:
                    reasons.append("user_excluded")
                values = {
                    "status": "rejected",
                    "reason": ",".join(reasons),
                    "user_approved": False,
                }

            if current:
                result = (
                    self.client
                    .table("photo_filter")
                    .update(values)
                    .eq("photo_id", photoID)
                    .execute()
                )
            else:
                result = (
                    self.client
                    .table("photo_filter")
                    .insert({
                        "photo_id": photoID,
                        "blur_score": 0,
                        "bright_score": 0,
                        "contrast_score": 0,
                        "width": 0,
                        "height": 0,
                        **values,
                    })
                    .execute()
                )

            if not result.data:
                return None

            updated = result.data[0]
            return {
                "photo_id": photoID,
                "filter_status": updated.get("status"),
                "filter_reason": updated.get("reason"),
                "user_approved": updated.get("user_approved", False),
            }

        except Exception:
            self.log.exception(
                "Could not update slideshow preference for photo_id=%s event_id=%s",
                photoID,
                eventID,
            )
            return None

    def hidePhoto(self, eventID: int, photoID: int):
        if not eventID or not photoID:
            return None

        try:
            result = (
                self.client
                .table("photos")
                .update({
                    "hide_photo": True,
                    "last_edit": datetime.now(timezone.utc).isoformat(),
                })
                .eq("photo_id", photoID)
                .eq("event_id", eventID)
                .or_("hide_photo.eq.false,hide_photo.is.null")
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception:
            self.log.exception(
                "Could not hide photo_id=%s for event_id=%s",
                photoID,
                eventID,
            )
            return None

    def hideVideo(self, eventID: int, videoID: int):
        if not eventID or not videoID:
            return None

        try:
            result = (
                self.client
                .table("videos")
                .update({
                    "hide_video": True,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                })
                .eq("video_id", videoID)
                .eq("event_id", eventID)
                .or_("hide_video.eq.false,hide_video.is.null")
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception:
            self.log.exception(
                "Could not hide video_id=%s for event_id=%s",
                videoID,
                eventID,
            )
            return None
