import os
from supabase import create_client, Client
from dotenv import load_dotenv
from ProjectHelper import Helpers as ph

class SQLbuilder:
    def __init__(self):
        load_dotenv()

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not self.supabase_url or not self.service_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")

        self.client: Client = create_client(self.supabase_url, self.service_key)

    def connect(self):
        try:
            # Simple lightweight call to confirm the client can reach Supabase
            self.client.table("photos").select("photo_id").limit(1).execute()
            return True
        except Exception as error:
            print("Connection failed:", error)
            return False

    def insertToDB(self, values, table: str = "Basic",  kwMatch: str ="photo_id"):
        try:
            query = self.client.table(table)
            if kwMatch:
                result = query.upsert(values, on_conflict=kwMatch).execute()
            else:
                result = query.insert(values).execute()

            count = len(values) if isinstance(values, list) else 1
            print(f"Saved {count} row(s) to {table}")
            return result.data

        except Exception as e:
            print(f"Error inserting into {table}: {e}")
            return None

    def postQRtoDB(self, eventID: int, url: str, token: str, expires_at: str, max_upload: int, purpose: str, is_active: bool):
        if eventID is None or url is None:
            print('Missing Values in arguments')
            return None

        table = 'qrcodes'
        values = {
            "event_id": eventID,
            "image_url": url,
            "token": token,
            "expires_at": expires_at,
            "max_uploads": max_upload,
            "purpose": purpose,
            "is_active": is_active
        }

        return self.insertToDB(values, table)

    def getQRToken(self, token: str):
        if token is None or token.strip() == "":
            return False, "Missing Token"

        try:
            result = (
                self.client.table("qrcodes")
                .select("*")
                .eq("token", token.strip())
                .execute()
            )

            rows = result.data
            if not rows:
                return None

            return rows[0]

        except Exception as e:
            print(f'Error Occurred: {e}')
            return None

    def insertPreFilter(self, results: list[dict], dtype: str = 'photo_id'):
        
        if not results:
            print("No filter results to insert.")
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
        return self.insertToDB(values, table)

    def insertContent(self, results: list[dict], dt = 'photo_id'):
        if not results:
            print("No filter results to insert.")
            return None
        
        table = 'photo_content'

        if dt == 'frame_id':
            table = 'video_content'

        values = [
            {
                dt: item.get(dt),
                "person_count": item.get("person_count", 0),
                "max_person_conf": item.get("max_person_conf", 0.0),
                "obj_class": item.get("obj_class", ""),
                "confidence": item.get("confidence", 0.0),
                "content_score": item.get("content_score", 0)
            }
            for item in results
        ]
        return self.insertToDB(values, table)

    def insertImageRanking(self, dataDict: list[dict], dtype: str ='photo_id'):
        if dataDict is None:
            print("Missing image ranking data")
            return None

        table ='photo_ranking'

        if dtype == 'frame_id':
            table = 'video_ranking'

        values = [{
            "caption": item.get("caption", ""),
            "mood_label": item.get("mood_label", ""),
            "mood_conf_score": item.get("mood_conf_score", 0),
            "all_mood_labels": item.get("all_mood_labels", ""),
            "keyword_score": item.get("keyword_score", 0),
            "keywords": item.get("keywords", ""),
            "nudity_check": item.get("nudity_check", 0),
            "all_mood_scores": item.get("all_mood_scores", ""),
            dtype: item.get(dtype)
        } for item in dataDict]

        return self.insertToDB(values, table)

    def selectAll(self, table: str):
        try:
            result = self.client.table(table).select("*").execute()
            return result.data
        except Exception as e:
            print(f"Error selecting all from {table}: {e}")
            return None

    def getApprovedPhotosForStoryboard(self, eventID: int):
        if eventID is None:
            print("Missing eventID")
            return []

        try:
            # Supabase/PostgREST can't do this exact multi-join + OR + COALESCE-order-by
            # in one fluent call, so we use an RPC call to a Postgres function instead.
            # See the matching SQL function `get_approved_photos_for_storyboard`
            # provided below this file to create it once in Supabase's SQL editor.
            result = self.client.rpc(
                "get_approved_photos_for_storyboard",
                {"p_event_id": eventID}
            ).execute()

            return result.data or []

        except Exception as e:
            print(f"Error getting approved photos for storyboard: {e}")
            return []

    def insertStoryboardItems(self, event_id: int, storyboard_items: list[dict]):
        if not storyboard_items:
            print("No storyboard items to insert.")
            return None

        values = []

        for index, item in enumerate(storyboard_items, start=1):
            values.append({
                "event_id": event_id,
                "photo_id": item.get("photo_id"),
                "sequence_order": index,
                "scene_label": item.get("scene_label", "unknown"),
                "confidence": item.get("confidence", 0),
                "reason": item.get("reason", "")
            })

        print("Storyboard rows being inserted:")
        for row in values:
            print(row["event_id"], row["photo_id"], row["sequence_order"])

        try:
            response = (
                self.client
                .table("storyboard_items")
                .insert(values)
                .execute()
            )

            print(f"Inserted {len(values)} storyboard items.")
            return response

        except Exception as e:
            print(f"Error inserting storyboard items: {e}")
            return None

    def getStoryboardByEvent(self, eventID: int):
        if eventID is None:
            print("Missing eventID")
            return []

        try:
  
            result = (
                self.client.table("storyboard_items")
                .select(
                    "storyboard_id, event_id, photo_id, sequence_order, "
                    "scene_label, confidence, reason, "
                    "photos(file_path)"
                )
                .eq("event_id", eventID)
                .order("sequence_order", desc=False)
                .execute()
            )

            rows = result.data or []

            cleaned = []
            for row in rows:
                photo = row.pop("photos", None) or {}
                row["file_path"] = photo.get("file_path")
                row["scene_label"] = row.get("scene_label") or "General Event Moment"
                row["confidence"] = row.get("confidence") or 0
                row["reason"] = row.get("reason") or ""
                cleaned.append(row)

            return cleaned

        except Exception as e:
            print(f"Error getting storyboard: {e}")
            return []

    def insertMusic(self, title: str, fileName: str, filePath: str, artist: str = None, eventType: str = "general",
                     moodLabel: str = "general", durationSeconds: float = 0, source: str = "local file",
                     licenseType: str = "project testing", isActive: bool = True):
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
        return self.insertToDB(values, table)

    def insertGeneratedVideo(self, eventID: int, fileName: str, filePath: str, musicID: int = None,
                              title: str = "Final Event Video", videoType: str = "slideshow",
                              status: str = "completed", durationSeconds: float = 0, width: int = 1280,
                              height: int = 720, fps: int = 30, fileSize: int = 0):
        table = 'generated_videos'

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
        return self.insertToDB(values, table)
            
    def insertUploads(self, uploads: list[dict]):
        if not uploads:
            print("No uploads to insert.")
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

                    "photo_id": item.get("photo_id"),
                    "video_id": item.get("video_id")
                })

            result = (
                self.client
                .table("uploads")
                .insert(rows)
                .execute()
            )

            print(f"Inserted {len(result.data)} upload records.")
            return result.data

        except Exception as e:
            print(f"Error inserting uploads: {e}")
            return None
    
    def insertMediaRecordsFromUploads(self, insertedUploads: list[dict]):
        if not insertedUploads:
            print("No inserted uploads to process.")
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
                print(f"Inserted {len(inserted_photos)} photo row(s).")

            if videoRows:
                video_result = (
                    self.client
                    .table("videos")
                    .insert(videoRows)
                    .execute()
                )

                inserted_videos = video_result.data
                print(f"Inserted {len(inserted_videos)} video row(s).")

            self.updateUploadsWithMediaIds(inserted_photos, inserted_videos)

            return {
                "photos": inserted_photos,
                "videos": inserted_videos
            }

        except Exception as e:
            print(f"Error inserting media records: {e}")
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

            print("Updated uploads with photo_id/video_id.")

        except Exception as e:
            print(f"Error updating uploads with media ids: {e}")

    def getMedia(self, eventID: int, mediaType: str):

        if eventID is None:
            print("Missing eventID")
            return []

        if mediaType not in ("photo", "video"):
            print(f"Invalid mediaType: {mediaType}")
            return []

        table = "photos" if mediaType == "photo" else "videos"
        id_field = "photo_id" if mediaType == "photo" else "video_id"
        
        uploads_select = (
            "uploads!photos_upload_id_fkey" if mediaType == "photo" else "uploads"
        )

        try:
            result = (
                self.client
                .table(table)
                .select(f"""
                    {id_field},
                    event_id,
                    upload_id,
                    {uploads_select} (
                        blob_name,
                        file_path
                    )
                """)
                .eq("event_id", eventID)
                .execute()
            )

            rows = result.data or []
            media_list = []

            for row in rows:
                upload = row.get("uploads") or {}

                media_list.append({
                    id_field: row.get(id_field),
                    "blob_name": upload.get("blob_name"),
                    "file_path": upload.get("file_path"),
                })

            print(f"{mediaType.capitalize()} data obtained: {len(media_list)} item(s)")
            return media_list

        except Exception as e:
            print(f"Error occurred getting {mediaType}: {e}")
            return []
        
    def upsertVideoFrames(self, frames: list[dict]):
        if not frames:
            print("No frames provided")
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

            print(f"Upserted {len(inserted)} video frame(s)")
            return inserted

        except Exception as e:
            print(f"Error occurred upserting video frames: {e}")
            return []
        
if __name__ == "__main__":
    db = SQLbuilder()
    if db.connect():
        print("Connected to Supabase.")

    rows = db.selectAll('storyboard_items')
    for row in rows or []:
        print(row)
