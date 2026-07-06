from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

import shared.DataStruct as dc
from fastapi import HTTPException, UploadFile, status


class UploadManager:
    MAX_FILES_PER_REQUEST = 20
    MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB

    ALLOWED_MIME_TYPES = {
        "image/jpeg": "photo",
        "image/png": "photo",
        "image/gif": "photo",
        "image/webp": "photo",
        "image/heic": "photo",
        "image/heif": "photo",
        "video/mp4": "video",
        "video/quicktime": "video",
        "video/webm": "video",
        "video/x-msvideo": "video",
        "video/x-ms-wmv": "video",
        "video/x-matroska": "video",
    }

    ALLOWED_EXTENSIONS = {
        ".jpg": "photo",
        ".jpeg": "photo",
        ".png": "photo",
        ".gif": "photo",
        ".webp": "photo",
        ".heic": "photo",
        ".heif": "photo",
        ".mp4": "video",
        ".avi": "video",
        ".mov": "video",
        ".wmv": "video",
        ".webm": "video",
        ".mkv": "video",
    }
    def __init__(self, db, blob, logger):
        self.db = db
        self.blob = blob
        self.log = logger
    
    async def validate_file(self, file: UploadFile) -> tuple[str, str]:
      
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Missing file name.")

        org_name = Path(file.filename).name
        suffix = Path(org_name).suffix.lower()
        content_type = file.content_type

        ext_type = self.ALLOWED_EXTENSIONS.get(suffix)
        mime_type = self.ALLOWED_MIME_TYPES.get(content_type)

        if not ext_type:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,detail=f"Unsupported file extension: {suffix}")

        if not mime_type:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,detail=f"Unsupported file content type: {content_type}")

        if ext_type != mime_type:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,detail="File extension does not match file content type.")

        size = 0
        chunk_size = 1024 * 1024

        while True:
            chunk = await file.read(chunk_size)

            if not chunk:
                break

            size += len(chunk)

            if size > self.MAX_FILE_SIZE_BYTES:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,detail="File is too large.")

        await file.seek(0)

        return ext_type, org_name

    async def upload_files(self,eventID: int,files: List[UploadFile],userID: Optional[int] = None,guestID: Optional[int] = None):
        if userID is None and guestID is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Either userID or guestID is required.")

        if userID is not None and guestID is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Upload cannot be both user and guest.")

        if len(files) > self.MAX_FILES_PER_REQUEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Maximum {self.MAX_FILES_PER_REQUEST} files allowed per request.")

        saved = []

        for file in files:
            try:
                fType, orgName = await self.validate_file(file)

                res = await self.blob.fileUpload(file, eventID, fType)

                saved.append(
                    asdict(
                        dc.uploadResults(
                            file_name=res["original_name"],
                            status="saved",
                            file_type=fType,
                            size_bytes=res["size_bytes"],
                            url=res["url"],
                            blob_name=res["blob_name"],
                            reason="success",
                            content_type=res["content_type"]
                        )
                    )
                )

            except HTTPException as e:
                saved.append(
                    asdict(
                        dc.uploadResults(
                            file_name=Path(file.filename or "unknown_file").name,
                            status="skipped",
                            reason=e.detail
                        )
                    )
                )

            except Exception:
                if self.logger:
                    self.logger.exception("File upload failed.")

                saved.append(
                    asdict(
                        dc.uploadResults(
                            file_name=Path(file.filename or "unknown_file").name,
                            status="failed",
                            reason="Upload failed."
                        )
                    )
                )

        uploadRows = []

        for item in saved:
            if item["status"] != "saved":
                continue

            uploadRows.append(
                {
                    "event_id": eventID,
                    "user_id": userID,
                    "guest_id": guestID,
                    "original_file_name": item["file_name"],
                    "blob_name": item["blob_name"],
                    "file_path": item["url"],
                    "media_type": item["file_type"],
                    "mime_type": item["content_type"],
                    "file_size": item["size_bytes"],
                    "upload_status": "uploaded",
                    "processing_status": "not_started"
                }
            )

        if not uploadRows:
            return {
                "event_id": eventID,
                "user_id": userID,
                "guest_id": guestID,
                "uploaded": 0,
                "db_records_inserted": 0,
                "photo_records_inserted": 0,
                "video_records_inserted": 0,
                "results": saved
            }

        inserted = self.db.insertUploads(uploadRows)

        if not inserted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Files uploaded, but database insert failed."
            )

        mediaInserts = self.db.insertMediaRecordsFromUploads(inserted)

        if not mediaInserts:
            mediaInserts = {"photos": [], "videos": []}

        return {
            "event_id": eventID,
            "user_id": userID,
            "guest_id": guestID,
            "uploaded": len([item for item in saved if item["status"] == "saved"]),
            "db_records_inserted": len(inserted),
            "photo_records_inserted": len(mediaInserts["photos"]),
            "video_records_inserted": len(mediaInserts["videos"]),
            "results": saved
        }
