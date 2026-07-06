import logging
import os
import time
from logging.handlers import RotatingFileHandler
from typing import List

import fastapi
import jwt
import uvicorn
from fastapi import Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

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
qrCode = qrGen.genQR(db=db, log=logger)

if IS_PRODUCTION:
    app = fastapi.FastAPI(title='CSI4999', docs_url=None, redoc_url=None, openapi_url=None)
else:
    app = fastapi.FastAPI(title='CSI4999')
uploadManager = Uploads.UploadManager(db=db, blob=blob, logger=logger)

ALLOWED_ORIGINS = ['csi4999-api-h4exhuc3b3btafg3.eastus-01.azurewebsites.net','https://zealous-stone-0f78c580f.7.azurestaticapps.net/', "http://localhost:3000","http://localhost:5173",]

app.add_middleware(CORSMiddleware,allow_origins=ALLOWED_ORIGINS,allow_credentials=True,allow_methods=["*"],allow_headers=["*"],)

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
        event_id = msg.get("event_id")
        req_id = msg.get("request_id")
        job_type = msg.get("job_type")

        if event_id is None:
            raise HTTPException(status_code=400, detail="Missing event_id")

        if req_id is None:
            raise HTTPException(status_code=400, detail="Missing request_id")

        if not job_type:
            raise HTTPException(status_code=400, detail="Missing job_type")
        
        job = db.createJobQueue(req_id, job_type , status="pending")

        if not job:
                raise HTTPException(status_code=500,detail="Storyboard was created, but job_queue row could not be created.")
        jobID = job.get('job_id')

        if jobID is None:
            raise HTTPException(status_code=500,detail="job_queue row was created, but job_id was missing." )

        queueMessage = {
            "job_id": jobID,
            "job_type": job_type,
            "event_id": event_id,
            'request_id': req_id,
            'storyboard_id': msg.get('storyboard') | None
        }

        jobMsg = blob.sendQMsg(queueMessage)

        db.updateJobQueueStatus(jobID=jobID,status="queued")

        if not jobMsg:
            raise HTTPException(status_code=500, detail= f"Storyboard was created, but job_queue message not sent. ")
        
        db.updateJobQueueStatus(jobID=jobID,status="queued")

        return {
            "job_id": jobID,
            "job_type": job_type,
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
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Could not validate credentials.",headers={"WWW-Authenticate": "Bearer"},)
 
    try:
        payload = authMang.decodeToken(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token has expired.",headers={"WWW-Authenticate": "Bearer"},) from None
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

@app.post('/qr/generate')
async def createQR(req: dc.QRRequest, current_user_id: int = Depends(getCurrentUserID)):
    verifyEventOwner(req.event_id, current_user_id)
    qrCode.generateUrl(req.event_id)
    result = qrCode.generateQRcode(req.event_id, req.expires_at, req.max_uploads, req.purpose, req.is_active)

    return {
            "event_id": req.event_id,
            "status": "created",
            "url": 'temp',
            "result": result
        }

@app.post('/qr/validate')
async def validateQR(req: dc.validateToken, request: Request ):
    checkRateLimit(f"qr_validate:{getClientIp(request)}", maxCall= 20, windowSec=6)
    verifyGuestQRCode(req.event_id, req.token)

    return {
        "event_id": req.event_id,
        "valid": True,
        "reason": "QR code is valid."
    }

#API endpoint for the upload function
@app.post("/upload/user")
async def uploadUserPhotos(eventID: int = Form(...),files: List[UploadFile] = File(...),current_user_id: int = Depends(getCurrentUserID)):
    checkRateLimit(f"upload_user:{current_user_id}", 20, 3600)
    verifyEventOwner(eventID, current_user_id)

    return await uploadManager.upload_files(eventID=eventID,userID=current_user_id,guestID=None,files=files)



@app.post("/upload/guest")
async def uploadGuestPhotos(request: Request, eventID: int = Form(...),qrToken: str = Form(...),guestID: int = Form(...),files: List[UploadFile] = File(...)):
    checkRateLimit(f"upload_guest_ip:{getClientIp(request)}", 20, 3600)
    checkRateLimit(f"upload_guest_token:{qrToken}", 20, 3600)
    verifyGuestQRCode(eventID, qrToken)

    res = await uploadManager.upload_files(eventID=eventID,userID=None,guestID=guestID,files=files)

    if res["uploaded"] > 0:
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
    created_user = uc.createUser(user)

    if not created_user:
        raise HTTPException(
            status_code=400,
            detail="User could not be created."
        )

    return created_user

@app.post("/users/login",response_model=dc.tokenReturn)
async def loginUser(login: dc.userLogin, request: Request):
    checkRateLimit(f"login: {getClientIp(request)}", 5, 60 )
    try:

        user = uc.loginUser(login)

        if user is None:
            raise HTTPException(status_code=401,detail="Invalid email/username or password.")
        
        token = authMang.createAccessToken(user)
        return {"access_token": token, "token_type": "bearer"}
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

    return {
        "message": "Event created successfully.",
        "data": result
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
        raise HTTPException(
            status_code=404,
            detail="Event not found."
        )

    return {
        "message": "Event loaded successfully.",
        "event": result
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


if __name__ == "__main__":
    uvicorn.run("api.mainAPI:app", host="127.0.0.1", port=8000, reload=True)