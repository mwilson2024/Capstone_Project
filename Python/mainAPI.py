import fastapi
import qrGen
from pydantic import BaseModel
from fastapi import File, UploadFile, Form
from typing import List
import DBConn
import AzureClass
from pathlib import Path
from DataStruct import uploadResults as dc
from dataclasses import asdict
import newRunner

nr = newRunner.newRunner()
blob = AzureClass.blobHandler()
db = DBConn.SQLbuilder()
db.connect()

class uploadModel(BaseModel):
    eventID: int
    files: List[UploadFile] = File(...)
    userID: int

    
class QRRequest(BaseModel):
    eventID: int
    expirationDate: str
    maxUploads: int = 50
    purpose: str = "guests"
    is_active: bool = True

class Validate(BaseModel):
    token: str

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
            #saved.append({"file_name": file.filename, "status": "skipped", "reason": "Unsupported file type"})
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

    nr.runProcess(eventID, fType)
        
    return {
        "event_id": eventID,
        "user_id": userID,
        "uploaded": len([item for item in saved if item["status"] == "saved"]),
        "db_records_inserted": len(inserted) if inserted else 0,
        "photo_records_inserted": len(mediaInserts["photos"]),
        "video_records_inserted": len(mediaInserts["videos"]),
        "results": saved
    }
        