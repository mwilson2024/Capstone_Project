
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import qrcode


class genQR():
    def __init__(self, db, log, path = "http://localhost:8000"):
        self.baseUrl = path
        self.fullUrl = None
        self.log = log

        self.localTesting = Path(r"C:\CSI4999\qrCodes")
        self.db = db


    def genToken(self):
       tokLen = 32
       return secrets.token_urlsafe(tokLen)
    
    def generateUrl(self, eventID: int, token: str) -> str:
        if eventID is None:
            raise ValueError("Event ID is empty")

        if not token:
            raise ValueError("Token is empty")

        query = urlencode(
            {
                "eventID": eventID,
                "qrToken": token
            }
        )

    def generateQRcode(self, eventID:int, expirationDate, maxUpload, purpose = "guests", setActive = True):
        if eventID is None:
            raise ValueError("Event ID is required")
        
        token = self.genToken()
        fullUrl = self.generateUrl(eventID=eventID, token=token)
        
        qrPath = self.localTesting / f"event_{self.eventID}_qr.png"

        qr = qrcode.make(self.fullUrl)
        qr.save(fr"{qrPath}")

        expires = datetime.strptime(expirationDate, "%m/%d/%y")

        self.db.postQRtoDB(eventID= eventID, url=str(qrPath), token= self.token, expires_at= expires.isoformat(), max_upload= maxUpload, purpose=purpose, is_active = setActive)

        return {
            "event_id": eventID,
            "qr_path": str(qrPath),
            "qr_url": fullUrl,
            "token": token,
            "expires_at": expires.isoformat(),
            "max_uploads": maxUpload,
            "purpose": purpose,
            "is_active": setActive
        }
    
    def validateQRcode(self, eventID: int, token:str):
        if token is None or token.strip == "":
            return False, "Missing Token"
        
        if eventID is None:
            return False, "Missing event ID"

        qrToken = self.db.getQRToken(token=token)

        if qrToken is None:
            return False, "No Data"
        
        tokenEventID = qrToken.get("event_id")

        if tokenEventID is None:
            return False, "QR token is missing event ID"

        if int(tokenEventID) != int(eventID):
            return False, "QR token does not match this event"

        if not qrToken.get("is_active", False):
            return False, "QR token is not active"

        expires_at = qrToken.get("expires_at")

        if expires_at is not None:
            expires = datetime.fromisoformat(str(expires_at))

            if expires.tzinfo is None:
                now = datetime.now()
            else:
                now = datetime.now(timezone.utc)

            if now > expires:
                return False, "QR code expired"

        max_uploads = qrToken.get("max_uploads")
        upload_count = qrToken.get("upload_count", 0)

        if max_uploads is not None:
            if int(upload_count) >= int(max_uploads):
                return False, "Upload limit reached"

        return True, "QR code is valid"
