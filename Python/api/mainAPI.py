import logging
import os
import time
from logging.handlers import RotatingFileHandler
from typing import List
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote, urlparse

import fastapi
import jwt
import uvicorn
from fastapi import Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse

from api import Auth
from api import ChatBot
from api import EventsClass
from api import qrGen
from api import StoryBoard
from api import Uploads
from api import UserClass

from shared.AzureClass import blobHandler
from shared.DBConn import SQLbuilder
from shared import DataStruct as dc

APP_ENV = os.getenv("APP_ENV", "development").lower().strip()
IS_PRODUCTION = APP_ENV == "production"

LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.getenv("LOG_FILE", "mainapi.log")

def setup_logger(name: str = "MainAPI") -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)

    app_logger = logging.getLogger(name)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False

    if app_logger.handlers:
        return app_logger

    log_format = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, LOG_FILE),
        maxBytes=10_000_000,
        backupCount=5,
    )
    file_handler.setFormatter(log_format)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)

    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)
    return app_logger

logger = setup_logger()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")
authMang = Auth.Auth()

blob = blobHandler(logger)
db = SQLbuilder(logger)
db.connect()

uc = UserClass.Users(db=db, log=logger)
ev = EventsClass.Manager(db=db, log=logger)
qrCode = qrGen.genQR(db=db, log=logger, blob=blob)

if IS_PRODUCTION:
    app = fastapi.FastAPI(title='CSI4999', docs_url=None, redoc_url=None, openapi_url=None)
else:
    app = fastapi.FastAPI(title='CSI4999')
uploadManager = Uploads.UploadManager(db=db, blob=blob, logger=logger)

ALLOWED_ORIGINS = [
    "https://zealous-stone-0f78c580f.7.azurestaticapps.net",
    "http://localhost:8081",
    "http://localhost:3000",
    "http://localhost:5173",
]

app.add_middleware(CORSMiddleware,allow_origins=ALLOWED_ORIGINS,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

RATE_LIMIT_BUCKETS: dict[str, list[float]] = {}


def getClientIp(req: Request) -> str:
    if req.client and req.client.host:
        return req.client.host
    return None

def checkRateLimit(key: str, maxCall: int, windowSec: int) -> None:
    now = time.monotonic()
    cutoff = now - windowSec

    calls = RATE_LIMIT_BUCKETS.get(key, [])
    calls = [timestamp for timestamp in calls if timestamp > cutoff]

    if len(calls)>= maxCall:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail = 'Too many request. Try again later')
    
    calls.append(now)
    RATE_LIMIT_BUCKETS[key]= calls

def enqueueJob(msg: dict):
    jobID = None
    try:

        logger.info(f"enqueueJob received msg: {msg}")

        event_id = msg.get("event_id")
        req_id = msg.get("request_id")
        job_type = msg.get("job_type")
        upload_id = msg.get("upload_id")

        if event_id is None:
            raise HTTPException(status_code=400, detail="Missing event_id")

        if not job_type:
            raise HTTPException(status_code=400, detail="Missing job_type")
        
        job = db.createJobQueue(req_id, job_type, status="pending", uploadID=upload_id)

        if not job:
                raise HTTPException(status_code=500,detail="Storyboard was created, but job_queue row could not be created.")
        jobID = job.get('job_id')

        if jobID is None:
            raise HTTPException(status_code=500,detail="job_queue row was created, but job_id was missing." )

        queueMessage = {
            "job_id": jobID,
            "job_type": job_type,
            "event_id": event_id,
            "request_id": req_id,
            "storyboard_id": msg.get("storyboard_id"),
            "type": msg.get("type"),
            "upload_id": upload_id,
            "upload_ids": msg.get("upload_ids", [])
        }

        logger.info(f"Sending queue message job: {jobID}")

        jobMsg = blob.sendQMsg(queueMessage)

        db.updateJobQueueStatus(jobID=jobID,status="queued")

        if not jobMsg:
            raise HTTPException(status_code=500, detail= f"Storyboard was created, but job_queue message not sent. ")
        
        db.updateJobQueueStatus(jobID=jobID,status="queued")

        logger.info(f"Job queued successfully. job_id={jobID}")

        return {
            "job_id": jobID,
            "job_type": job_type,
            "event_id": event_id,
            "request_id": req_id,
            "status": "queued"
        }
    except Exception as e:
        logger.error({e})
        if jobID is not None:
            db.updateJobQueueStatus(jobID=jobID,status="failed",errorMessage=str(e))


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

def getCurrentUserID(token: str = Depends(oauth2_scheme)) -> int:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Could not validate credentials.",headers={"WWW-Authenticate": "Bearer"})
 
    try:
        payload = authMang.decodeToken(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token has expired.",headers={"WWW-Authenticate": "Bearer"}) from None
    except jwt.InvalidTokenError:
        raise credentials_exception from None
 
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
 
    try:
        return int(user_id_str)
    except ValueError:
        raise credentials_exception from None
    
def verifyEventOwner(eventID: int, current_user_id: int) -> dict:
    event = ev.getEventByID(eventID)

    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Event not found.")

    owner_id = event.get("user_id") or event.get("owner_id")

    if owner_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You do not have access to this event.")

    return event

def verifyGuestQRCode(eventID: int, qrToken: str):
    if not qrToken:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="QR token is required.")

    valid, reason = qrCode.validateQRcode(eventID=eventID, token=qrToken)

    if not valid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail=reason or "Invalid or expired QR code.")

    return True

def userOwnsLocation(location: dict, current_user_id: int) -> bool:

    event_id = location.get("event_id") or location.get("eventID")
 
    if event_id is None:
        return False
 
    event = ev.getEventByID(event_id)
 
    if not event:
        return False
 
    owner_id = event.get("user_id") or event.get("owner_id")
    return owner_id == current_user_id

def normalizeMediaRecord(item: dict, mediaType: str) -> dict:
    upload = item.get("uploads") or {}
    guest = upload.get("guests") or None
    user = upload.get("app_user") or None

    uploaded_by = None
    if user:
        uploaded_by = {
            "type": "user",
            "id": user.get("user_id"),
            "display_name": " ".join(
                part for part in [user.get("first_name"), user.get("last_name")] if part
            ) or user.get("user_name"),
        }
    elif guest:
        uploaded_by = {
            "type": "guest",
            "id": guest.get("guest_id"),
            "display_name": guest.get("display_name"),
        }

    signed_media = blob.getSignedBlobUrl(upload.get("blob_name"), expiresInMinutes=15)
    normalized = {
        "id": item.get("photo_id") if mediaType == "photo" else item.get("video_id"),
        "media_type": mediaType,
        "event_id": item.get("event_id"),
        "upload_id": item.get("upload_id"),
        "original_file_name": upload.get("original_file_name"),
        "mime_type": upload.get("mime_type"),
        "file_size": upload.get("file_size"),
        "upload_status": upload.get("upload_status"),
        "processing_status": upload.get("processing_status"),
        "created_at": item.get("created_at") or upload.get("created_at"),
        "display_url": signed_media["url"] if signed_media else None,
        "display_url_expires_at": signed_media["expires_at"] if signed_media else None,
        "uploaded_by": uploaded_by,
    }

    if mediaType == "photo":
        normalized.update({
            "taken_at": item.get("photo_taken"),
            "last_updated": item.get("last_edit"),
            "nudity_check": item.get("nudity_check", False),
            "filter_status": item.get("filter_status"),
            "filter_reason": item.get("filter_reason"),
            "user_approved": item.get("user_approved", False),
        })
    else:
        normalized.update({
            "title": item.get("title"),
            "status": item.get("status"),
            "duration_seconds": item.get("duration_seconds"),
            "width": item.get("width"),
            "height": item.get("height"),
            "fps": item.get("fps"),
            "last_updated": item.get("last_updated"),
        })

    return normalized

def generatedVideoBlobName(video: dict) -> str:
    return (f"events/{video['event_id']}/generated_videos/{video['file_name']}")

def generateEventQRCode(event_id: int,expires_at: str,max_uploads: int = 50,replace_existing: bool = False):
    result = qrCode.generateQRcode(eventID=event_id,expirationDate=expires_at,maxUpload=max_uploads,purpose="guests",setActive=True)
    if replace_existing:
        db.deactivateEventQRCodes(event_id, exceptToken=result["token"])
    signed_image = blob.getSignedBlobUrl(
        result["qr_blob_name"],
        expiresInMinutes=60,
    )

    return {
        "event_id": event_id,
        "status": "created",
        "qr_image_url": signed_image["url"],
        "qr_image_url_expires_at": signed_image["expires_at"],
        "scan_url": result["qr_url"],
        "token": result["token"],
        "expires_at": result["expires_at"],
        "result": result,
    }

def getClientIp(req: Request) -> str:
    if req.client and req.client.host:
        return req.client.host
    return None

def checkRateLimit(key: str, maxCall: int, windowSec: int) -> None:
    now = time.monotonic()
    cutoff = now - windowSec

    calls = RATE_LIMIT_BUCKETS.get(key, [])
    calls = [timestamp for timestamp in calls if timestamp > cutoff]

    if len(calls)>= maxCall:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail = 'Too many request. Try again later')
    
    calls.append(now)
    RATE_LIMIT_BUCKETS[key]= calls


def enqueuePreprocessJobs(eventID: int, res: dict):
    uploads_by_type = {}

    for upload in res.get("uploads", []):
        file_type = upload.get("file_type")
        upload_id = upload.get("upload_id")

        if file_type not in ("photo", "video") or upload_id is None:
            continue

        uploads_by_type.setdefault(file_type, []).append(upload_id)

    if not uploads_by_type:
        saved_results = [
            item for item in res.get("results", [])
            if item.get("status") == "saved" and item.get("file_type") in ("photo", "video")
        ]

        for item, upload_id in zip(saved_results, res.get("upload_ids", [])):
            uploads_by_type.setdefault(item["file_type"], []).append(upload_id)

    jobs = []

    for file_type, upload_ids in uploads_by_type.items():
        jobs.append(enqueueJob({
            "event_id": eventID,
            "request_id": None,
            "job_type": "preprocess",
            "type": file_type,
            "upload_id": upload_ids[0],
            "upload_ids": upload_ids,
        }))

    return jobs

@app.get('/health')
def healthCheck():
    up = "healthy"
    down = "down"
    statusCnt = 0
    healthy = False
    totalChecks = 3
    health = {"api":up,
                    "database":down,
                    "blob_storage":down,
                    "queue":down}
    
    try:
        if db.connect():
            health['database'] = up
        statusCnt +=1
    except Exception as e:
        logger.exception(f'Database is down: {e}')

    try:
        blob.containerClient.get_container_properties()
        health['blob_storage'] = up
        statusCnt += 1
    except Exception as e:
        logger.exception(f'Blob storage is down: {e}')

    try:
        blob.queue.get_queue_properties()
        health['queue'] = up
        statusCnt += 1

    except Exception as e:
        logger.exception(f'queue is down: {e}')
    
    if statusCnt == totalChecks:
        healthy = True

    response = {
        "status": "healthy" if healthy else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": health,
    }

    return JSONResponse(status_code=status.HTTP_200_OK
        if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response)

@app.post("/guests/session", status_code=status.HTTP_201_CREATED)
def createGuestSession(req: dc.guestSessionRequest, request: Request):
    checkRateLimit(f"guest_session_ip:{getClientIp(request)}", maxCall=20, windowSec=3600)
    checkRateLimit(f"guest_session_token:{hash(req.qr_token)}", maxCall=20, windowSec=3600)
    verifyGuestQRCode(req.event_id, req.qr_token)

    guest = db.createOrGetGuestSession({
        "event_id": req.event_id,
        "display_name": req.display_name,
        "email": req.email,
        "phone_number": req.phone_number
    })

    if not guest:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Guest session could not be created.")

    if not guest.get("can_post", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="This guest is not permitted to upload media.")

    return {
        "message": "Guest session created successfully.",
        "guest": guest,
    }

@app.get('users/me')
def getCurrentUser(current_user_id: int = Depends(getCurrentUserID)):
    try:
        user = db.getUserInfo(current_user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found.")

        return user

    except HTTPException:
        raise

    except Exception:
        logger.exception(f"Could not load current user. user_id={current_user_id}",current_user_id)

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="User profile could not be loaded.") from None
    
@app.get('/users/me', response_model=dc.userResponse)
def getCurrentUser(current_user_id: int = Depends(getCurrentUserID)):
    try:
        user = db.getUserInfo(current_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        return user

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Could not load current user. user_id=%s",
            current_user_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User profile could not be loaded.",
        ) from None
    
    
@app.patch("/users/me", response_model=dc.userResponse)
def updateCurrentUser(user: dc.userProfileUpdate, current_user_id: int = Depends(getCurrentUserID)):
    updated_user = uc.updateUser(current_user_id, user)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile could not be updated. The username or email may already be in use.",
        )

    return updated_user

@app.patch("/users/me/password")
def updateCurrentUserPassword(passwords: dc.userPasswordUpdate,current_user_id: int = Depends(getCurrentUserID)):
    result = uc.changePassword(current_user_id,passwords.current_password,passwords.new_password)

    if result == "not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found.")

    if result == "invalid_password":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="The current password is incorrect.")

    if result != "updated":
        raise HTTPException(status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),detail="Password could not be updated.")

    return {"message": "Password updated successfully."}

@app.post("/qr/generate")
async def createQR(req: dc.QRRequest,current_user_id: int = Depends(getCurrentUserID)):
    verifyEventOwner(req.event_id, current_user_id)

    return generateEventQRCode(
        event_id=req.event_id,
        expires_at=req.expires_at,
        max_uploads=req.max_uploads if req.max_uploads > 0 else 50,
        replace_existing=True,
    )

@app.post('/qr/validate')
async def validateQR(req: dc.validateToken, request: Request ):
    checkRateLimit(f"qr_validate:{getClientIp(request)}", maxCall= 20, windowSec=6)
    verifyGuestQRCode(req.event_id, req.token)

    event = ev.getEventByID(req.event_id)

    return {
    "event_id": req.event_id,
    "event_name": event.get("name") if event else None,
    "valid": True,
    "reason": "QR code is valid.",
}

#API endpoint for the upload function
@app.post("/upload/user")
async def uploadUserPhotos(eventID: int = Form(...),files: List[UploadFile] = File(...),current_user_id: int = Depends(getCurrentUserID)):
    checkRateLimit(f"upload_user:{current_user_id}", 20, 3600)
    verifyEventOwner(eventID, current_user_id)

    res = await uploadManager.upload_files(eventID=eventID,userID=current_user_id,guestID=None,files=files)

    if res.get("uploaded", 0) > 0:
        jobs = enqueuePreprocessJobs(eventID, res)
        res["jobs"] = jobs
        res["job"] = jobs[0] if jobs else None

    return res

@app.post("/upload/guest")
async def uploadGuestPhotos(request: Request, eventID: int = Form(...),qrToken: str = Form(...),guestID: int = Form(...),files: List[UploadFile] = File(...)):
    checkRateLimit(f"upload_guest_ip:{getClientIp(request)}", 20, 3600)
    checkRateLimit(f"upload_guest_token:{qrToken}", 20, 3600)
    verifyGuestQRCode(eventID, qrToken)

    guest = db.getGuestForEvent(guestID, eventID)


    if not guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The guest session does not belong to this event.",
        )

    if not guest.get("can_post", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This guest is not permitted to upload media.",
        )

    res = await uploadManager.upload_files(eventID=eventID,userID=None,guestID=guestID,files=files)

    if res.get("uploaded", 0) > 0:
        jobs = enqueuePreprocessJobs(eventID, res)
        res["jobs"] = jobs
        res["job"] = jobs[0] if jobs else None

    db.incrementQRUploadCount(qrToken, res["uploaded"])

    return res

@app.post("/prompt/analyze")
async def analyzePrompt(request: dc.PromptRequest, current_user_id: int = Depends(getCurrentUserID)):
    checkRateLimit(f"prompt_analyze:{current_user_id}", maxCall=20, windowSec=3600)
    try:
        verifyEventOwner(request.eventID, current_user_id)
        bot = ChatBot.chatBotOpenAI(logger)
        result = bot.getResponse(request.prompt)

        if not isinstance(result, dict):
            return {
                "allowed": False,
                "out_of_scope": False,
                "unsafe_or_invalid": True,
                "reason": "The prompt analyzer returned data that was not a JSON object.",
                "response": "Sorry, I could not understand that request."
            }

        result["event_id"] = request.eventID
        result["user_id"] = current_user_id
        result["guest_id"] = request.guestID
        result["original_prompt"] = request.prompt

        inserted = db.insertPromptRequest(result)

        return {
            "event_id": request.eventID,
            "user_id": current_user_id,
            "guest_id": request.guestID,
            "inserted": inserted,
            "analysis": result
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Prompt analysis failed.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Prompt analysis failed.") from e
    
@app.post('/media/allmedia')
async def getMedia(req: dc.mediaModel, current_user_id: int = Depends(getCurrentUserID)):
    try:
        verifyEventOwner(req.eventID, current_user_id)
        media = db.getAllMedia(eventID=req.eventID,dataType=req.dataType)

        return {
            "status": "success",
            "eventID": req.eventID,
            "dataType": req.dataType,
            "photos_count": len(media["photos"]),
            "videos_count": len(media["videos"]),
            "data": media
        }

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception(f"Error getting media: {e}")
        raise HTTPException(status_code=500,detail="Error getting media")

@app.post("/users/create", response_model=dc.userResponse)
async def create_user(user: dc.userCreate):
    success, res = uc.createUser(user)

    if not success:
        raise HTTPException(status_code=400,detail=res)

    return res

@app.post("/users/login",response_model=dc.tokenReturn)
async def loginUser(login: dc.userLogin, request: Request):
    checkRateLimit(f"login: {getClientIp(request)}", 5, 60 )
    try:

        user  = uc.loginUser(login)

        if user is None:
            raise HTTPException(status_code=401,detail="Invalid email/username or password.")
        
        profile = db.getUserInfo(user)
        token = authMang.createAccessToken(user)
        return {"access_token": token, "token_type": "bearer", "user": profile}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login failed unexpectedly.")
        raise HTTPException(status_code=500, detail="Login failed.") from None

@app.post("/events/create")
def create_event(event: dc.eventCreate, location: dc.eventLocation,  current_user_id: int = Depends(getCurrentUserID)):
    event.user_id = current_user_id
    result = ev.createEvent(event=event, location= location)
    
    if not result:
        raise HTTPException(
            status_code=500,
            detail="Event could not be created."
        )

    created_event = result["event"]
    qr_code = None
    qr_error = None

    try:
        qr_code = generateEventQRCode(event_id=created_event["event_id"],expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),max_uploads=event.upload_limit if event.upload_limit > 0 else 50)
    
    except Exception:
        qr_error = ("Automatic QR generation failed. Use Recreate QR from the Events screen.")
        logger.exception(f"Event was created but QR generation failed. event_id={created_event['event_id']}")

    return {
        "message": "Event created successfully.",
        "data": result,
        "qr_code": qr_code,
        "qr_error": qr_error,
    }
    
@app.get("/locations/all")
def getAllLoc(current_user_id: int = Depends(getCurrentUserID)):


    result = ev.getAllLocations()

    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Locations could not be loaded."
        )

    searchableLocations = [loc for loc in result if loc.get("searchable")]

    return {
        "message": "Locations loaded successfully.",
        "locations": searchableLocations
    }

@app.get("/locations/{locationID}")
def getLocID(locationID: int, current_user_id: int = Depends(getCurrentUserID)):
    result = ev.getLocationByID(locationID)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Location not found."
        )

    return {
        "message": "Location loaded successfully.",
        "location": result}

@app.get("/events/{eventID}")
def getEvent(eventID: int, current_user_id: int = Depends(getCurrentUserID)):
    verifyEventOwner(eventID, current_user_id)
    result = ev.getEventByID(eventID)

    if not result:
        raise HTTPException(status_code=404,detail="Event not found.")

    return {
        "message": "Event loaded successfully.",
        "event": result
    }

@app.get("/events/{eventID}/media")
def getEventMedia(eventID: int, dataType: str = "both", current_user_id: int = Depends(getCurrentUserID)):
    verifyEventOwner(eventID, current_user_id)

    try:
        media = db.getAllMedia(eventID=eventID, dataType=dataType)
        photos = [normalizeMediaRecord(item, "photo") for item in media["photos"]]
        videos = [normalizeMediaRecord(item, "video") for item in media["videos"]]

        return {
            "event_id": eventID,
            "data_type": dataType.lower().strip(),
            "photo_count": len(photos),
            "video_count": len(videos),
            "photos": photos,
            "videos": videos,
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(f"Error getting normalized media for event_id={eventID}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Event media could not be loaded.",
        ) from e

@app.delete("/events/{eventID}/photos/{photoID}")
def hideEventPhoto(
    eventID: int,
    photoID: int,
    current_user_id: int = Depends(getCurrentUserID),
):
    verifyEventOwner(eventID, current_user_id)

    hidden = db.hidePhoto(eventID=eventID, photoID=photoID)

    if not hidden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo was not found or is already hidden.",
        )

    return {
        "message": "Photo removed from the gallery.",
        "event_id": eventID,
        "photo_id": photoID,
        "hidden": True,
    }

@app.patch("/events/{eventID}/photos/{photoID}/slideshow")
def updatePhotoSlideshowPreference(
    eventID: int,
    photoID: int,
    preference: dc.photoSlideshowAction,
    current_user_id: int = Depends(getCurrentUserID),
):
    verifyEventOwner(eventID, current_user_id)

    updated = db.updatePhotoSlideshowPreference(
        eventID=eventID,
        photoID=photoID,
        action=preference.action,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo or photo filter record could not be updated.",
        )

    return {
        "message": (
            "Photo approved for the slideshow."
            if preference.action == "approve"
            else "Photo excluded from the slideshow."
        ),
        "event_id": eventID,
        "photo": updated,
    }

@app.patch("/events/modify/{eventID}")
def modifyEvent(eventID: int, event: dc.eventModify, current_user_id: int = Depends(getCurrentUserID)):
    verifyEventOwner(eventID, current_user_id)

    result = ev.modifyEvent(eventID=eventID, event=event)

    if not result:
        raise HTTPException(status_code=404,detail="Event could not be modified.")

    return {
        "message": "Event modified successfully.",
        "event": result
    }

@app.get("/users/me/events")
def getMyEvents(current_user_id: int = Depends(getCurrentUserID)):
    events = db.getMyEvents(current_user_id)

    if events is None:
        logger.error(
            f"Could not load events for user_id={current_user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Events could not be loaded."
        )

    logger.info(
        f"Loaded {len(events)} event(s) for user_id={current_user_id}"
    )

    return {
        "message": "Events loaded successfully.",
        "count": len(events),
        "events": events
    }

def qrBlobNameFromURL(image_url: str) -> str:
    path = unquote(urlparse(image_url).path).lstrip("/")
    container_prefix = f"{blob.container}/"
    return path[len(container_prefix):] if path.startswith(container_prefix) else path

@app.get("/events/{eventID}/qr")
def getEventQRCode(eventID: int,current_user_id: int = Depends(getCurrentUserID)):
    verifyEventOwner(eventID, current_user_id)
    row = db.getActiveEventQRCode(eventID)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This event does not have an active QR code.",
        )

    signed_image = blob.getSignedBlobUrl(
        qrBlobNameFromURL(row["image_url"]),
        expiresInMinutes=60,
    )
    return {
        "event_id": eventID,
        "status": "active",
        "qr_image_url": signed_image["url"],
        "qr_image_url_expires_at": signed_image["expires_at"],
        "scan_url": qrCode.generateUrl(eventID, row["token"]),
        "token": row["token"],
        "expires_at": row["expires_at"],
    }

@app.patch("/locations/{locationID}")
def modifyLoc(locationID: int, location: dc.eventLocationModify, current_user_id: int = Depends(getCurrentUserID)):

    existing = ev.getLocationByID(locationID)

    if not existing:
        raise HTTPException(status_code=404,detail="Location not found.")
 
    if not userOwnsLocation(existing, current_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You do not have access to this location.")

    result = ev.modifyLocation(locationID=locationID, location=location)

    if not result:
        raise HTTPException(status_code=404,detail="Location could not be modified.")

    return {
        "message": "Location modified successfully.",
        "location": result
    }

@app.post('/creation/storyboard')
async  def createStoryBoard(req: dc.StoryboardCreateRequest , current_user_id: int = Depends(getCurrentUserID)):
    try:

        verifyEventOwner(req.event_id, current_user_id)
        sb = StoryBoard.StoryBoardGen(db=db, log=logger)

        res = sb.createStoryboardForEvent(req.event_id, req.request_id)
        
        if not res:
            raise HTTPException(status_code=404,detail="Storyboard could not be created. No approved photos may exist for this event.")

        storyboard = res.get("storyboard")
        items = res.get("items", [])

        storyboardID = storyboard.get("storyboard_id")
        dataSet = {'event_id': req.event_id,
                   "request_id": req.request_id,
                   'job_type': 'create',
            "storyboard_id": storyboardID
        }

        enqueueJob(dataSet)

        return {
            "message": "Storyboard created successfully.",
            "storyboard_id": storyboard.get("storyboard_id"),
            "event_id": storyboard.get("event_id"),
            "request_id": storyboard.get("request_id"),
            "status": storyboard.get("status"),
            "item_count": len(items),
            "storyboard": storyboard,
            "items": items
    }


    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Error creating storyboard")
        raise HTTPException(status_code=500,detail=f"Error creating storyboard: {str(e)}")
    
@app.get("/events/{eventID}/generated-videos")
def getEventGeneratedVideos(eventID: int,current_user_id: int = Depends(getCurrentUserID)):
    verifyEventOwner(eventID, current_user_id)

    videos = db.getGeneratedVideosByEvent(eventID)

    if videos is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Generated videos could not be loaded.")

    response_videos = []

    for video in videos:
        item = dict(video)

        # Only completed videos can be played.
        if video.get("status") == "completed":
            blob_name = generatedVideoBlobName(video)

            signed = blob.getSignedBlobUrl(blob_name,expiresInMinutes=60)

            item["stream_url"] = signed["url"]
            item["stream_url_expires_at"] = signed["expires_at"]

        else:
            item["stream_url"] = None
            item["stream_url_expires_at"] = None

        # Do not return the permanent private storage URL.
        item.pop("file_path", None)

        response_videos.append(item)

    return {
        "event_id": eventID,
        "count": len(response_videos),
        "videos": response_videos,
    }

@app.get("/generated-videos/{generatedVideoID}/playback-url")
def getGeneratedVideoPlaybackUrl(generatedVideoID: int,current_user_id: int = Depends(getCurrentUserID)):
    video = db.getGeneratedVideoByID(generatedVideoID)

    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Generated video not found.")

    verifyEventOwner(video["event_id"],current_user_id,)

    if video.get("status") != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Generated video is not ready for playback.")

    blob_name = generatedVideoBlobName(video)

    signed = blob.getSignedBlobUrl(blob_name,expiresInMinutes=60)

    return {
        "generated_video_id": generatedVideoID,
        "event_id": video["event_id"],
        "stream_url": signed["url"],
        "expires_at": signed["expires_at"],
    }
if __name__ == "__main__":
    uvicorn.run("api.mainAPI:app", host="127.0.0.1", port=8000, reload=True)
