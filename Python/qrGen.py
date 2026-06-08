import qrcode 
import DBConn 
from pathlib import Path
import secrets
from datetime import datetime, timedelta

class genQR():
    def __init__(self, path = "http://localhost:8000"):
        self.baseUrl = path
        self.fullUrl = None
        self.eventID = None
        self.token = None
        self.db = DBConn.SQLbuilder()
        self.localTesting = Path(r"C:\CSI4999\qrCodes")
        self.db.connect()

    def genToken(self):
       tokLen = 32
       return secrets.token_urlsafe(tokLen)
    
    def generateUrl(self, eventID: str):
        if eventID is None:
            raise ValueError('Event ID is empty')
        self.eventID = eventID
        self.token = self.genToken()

        self.fullUrl = f'{self.baseUrl}/upload?token={self.token}'

    def generateQRcode(self, expirationDate, maxUpload, purpose = "guests", setActive = True):
        if self.fullUrl is None or self.eventID is None:
            raise ValueError('URL must be generated')
        
        qrPath = self.localTesting / f"event_{self.eventID}_qr.png"

        qr = qrcode.make(self.fullUrl)
        qr.save(fr"{qrPath}")

        expires = datetime.strptime(expirationDate, "%m/%d/%y")

        self.db.postQRtoDB(eventID= self.eventID, url=str(qrPath), token= self.token, expires_at= expires.isoformat(), max_upload= maxUpload, purpose=purpose, is_active = setActive)

        return qrPath
    
    def validateQRcode(self, tokenID: str):
        if self.token is None or self.token.strip == "":
            return False, "Missing Token"

        qrToken = self.db.getQRToken(token= tokenID)

        if qrToken is None:
            return False, "No Data"
        
        if not qrToken["is_active"]:
            return False, "QR_Token not active"
        
        if qrToken["expires_at"] is not None:
            expires = datetime.fromisoformat(qrToken["expires_at"])

            if datetime.now() > expires:
                return False, "QR code expired"

        if qrToken["max_uploads"] is not None:
            if qrToken["upload_count"] >= qrToken["max_uploads"]:
                return False, "Upload limit reached"

        return True, "QR code is valid"


def main():
    qrCo = genQR("http://localhost:8000")

    qrCo.generateUrl(195)
    qrPath = qrCo.generateQRcode("10/23/26", 5000)

    print(f"QR code created: {qrPath}")
    print(f"Upload URL: {qrCo.fullUrl}")
    print(f"Token: {qrCo.token}")

    valid, message = qrCo.validateQRcode(qrCo.token)
    print(valid, message)


if __name__ == "__main__":
    main()

