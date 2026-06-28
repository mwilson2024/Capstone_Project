import fastapi
from fastapi import File, UploadFile, Form, HTTPException, Depends, Query, status
import qrGen
from pydantic import BaseModel, Field
from typing import List
import DBConn
import AzureClass
from pathlib import Path
from DataStruct import uploadResults as dc
from dataclasses import asdict
import newRunner
import StoryBoard
import SlideShow
import uvicorn
import ChatBot
import logging
import json


logger = logging.getLogger('MainAPI')
logging.basicConfig(level=logging.INFO)

blob = AzureClass.blobHandler()
db = DBConn.SQLbuilder()
db.connect()

class uploadModel(BaseModel):
    eventID: int
    files: List[UploadFile] = File(...)
    guestID: int
    userID: int

class PromptRequest(BaseModel):
    eventID: int = Field(..., gt=0)
    userID: int = Field(..., gt=0)
    guestID: int | None = None
    prompt: str = Field(..., min_length=1, max_length=1000)


class MakeVideoRequest(BaseModel):
    eventID: int
    userID: int
    feeling: str
 
    
class QRRequest(BaseModel):
    eventID: int
    expirationDate: str
    maxUploads: int = 50
    purpose: str = "guests"
    is_active: bool = True

class Validate(BaseModel):
    token: str

class mediaModel(BaseModel):
    eventID: int
    dataType: str
app = fastapi.FastAPI()

@app.post('/qr/generate')
async def createQR(req: QRRequest):
    qrCode = qrGen.genQR()
    qrCode.generateUrl(req.eventID)
    qrCode.generateQRcode(req.expirationDate, req.maxUploads, req.purpose, req.is_active)
    print("done")

@app.get('/qr/validate')
async def validateQR(req: Validate):
    qrCode = qrGen.genQR()
    valid, reason = qrCode.validateQRcode(req.eventID)
    print(valid, reason)
    return {"eventID": req.eventID, "valid": valid, "reason": reason}

@app.get('/users/me')
async def readUserMe():
    return {'userID': "The Current User"}

@app.get('/users/{userID}')
async def readUser(userID : str):
    return{'userID': userID}

#API endpoint for the upload function
@app.post('/upload')
async def uploadPhotos(eventID:int = Form(...), userID:int = Form(...), files: List[UploadFile] = File(...)):
    nr = newRunner.newRunner()
    photosExt = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic")
    vidExt = (".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv")

    saved = []
            
    for file in files:
        orgName = Path(file.filename).name
        suffix = Path(orgName).suffix.lower()

        if suffix in photosExt:
            fType = "photo"
        elif suffix in vidExt:
            fType = "video"
        else:
            saved.append(asdict(dc(orgName, "skipped", None, None, None, None, "Unsupported file type")))
            continue

        try:
            res = await blob.fileUpload(file, eventID, fType)
            saved.append(asdict(dc(res["original_name"],"saved", fType, res["size_bytes"], res["url"], res["blob_name"], 'success', res["content_type"] )))
            print(f'File: {res["url"]}, Size: {res["size_bytes"]} bytes, Type: {fType}')

   
        except Exception as e:
            saved.append(asdict(dc(orgName, "failed", None, None, None, None, str(e))))

    uploadRows = []

    for item in saved:
        if item["status"] != "saved":
            continue

        uploadRows.append({"event_id": eventID,"user_id": userID,"original_file_name": item["file_name"],"blob_name": item["blob_name"],"file_path": item["url"], 
        "media_type": item["file_type"],"mime_type": item["content_type"],"file_size": item["size_bytes"],"upload_status": "uploaded","processing_status": "not_started"})

    inserted = db.insertUploads(uploadRows)
    mediaInserts = db.insertMediaRecordsFromUploads(inserted)

    #nr.runProcess(eventID, 'photo')
    #nr.runProcess(eventID, 'video')
        
    return {
        "event_id": eventID,
        "user_id": userID,
        "uploaded": len([item for item in saved if item["status"] == "saved"]),
        "db_records_inserted": len(inserted) if inserted else 0,
        "photo_records_inserted": len(mediaInserts["photos"]),
        "video_records_inserted": len(mediaInserts["videos"]),
        "results": saved
    }
  
@app.post("/video/generate")
async def generateVideo(request: MakeVideoRequest, req: MakeVideoRequest):
    try:
        ss = SlideShow.SlideShowGenerator()
        sb = StoryBoard.StoryBoardGen()
        
        media = db.getApprovedPhotosForStoryboard(req.eventID)

        if not media:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No media found for event')
        
        sb.generateSeq(media)
        sboard =db.getStoryboardByEvent(req.eventID)

        if not sboard:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = 'Storyboard not created. no records found')
        

        outPutThat = ss.generateVideo(sboard, req.eventID)
        return {
            "event_id": req.eventID,
            "user_id": req.userID,
            "feeling": req.feeling,
            "status": "generated",
            "output_path": str(outPutThat) if outPutThat else None
        }
    
    except HTTPException:
        raise

    except [Exception] as e:
        logger.exception('Video Generation failed')
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail= "Video Generation Failed") from e

@app.post("/prompt/analyze")
async def analyzePrompt(request: PromptRequest):
    try:
        bot = ChatBot.chatBotOpenAI()
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
        result["user_id"] = request.userID
        result["guest_id"] = request.guestID
        result["original_prompt"] = request.prompt

        inserted = db.insertPromptRequest(result)

        return {
            "event_id": request.eventID,
            "user_id": request.userID,
            "guest_id": request.guestID,
            "inserted": inserted,
            "analysis": result
        }

    except Exception as e:
        logger.exception("Prompt analysis failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prompt analysis failed."
        ) from e
    
@app.post('/media/allmedia')
async def getMedia(req: mediaModel):
    try:
        media = db.getAllMedia(eventID=req.eventID,dataType=req.dataType)

        return {
            "status": "success",
            "eventID": req.eventID,
            "dataType": req.dataType,
            "photos_count": len(media["photos"]),
            "videos_count": len(media["videos"]),
            "data": media
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting media: {e}"
        )

    
    
if __name__ == "__main__":
    uvicorn.run("mainAPI:app", host="127.0.0.1", port=8000, reload=True)