import os
from pathlib import Path
from uuid import uuid4
from azure.storage.queue import QueueClient
from azure.storage.blob import (BlobServiceClient,BlobSasPermissions,ContentSettings,generate_blob_sas)
from azure.core.exceptions import ResourceNotFoundError
from dotenv import load_dotenv
from fastapi import UploadFile
import json
from datetime import datetime, timedelta, timezone

class blobHandler:
    def __init__(self, log):
        load_dotenv()

        self.log = log

        self.connectString = os.getenv("AZURE_CONNECTION_STRING")
        if not self.connectString:
            raise ValueError("Missing AZURE_CONNECTION_STRING")

        self.container = os.getenv("CONTAINER_NAME")
        if not self.container:
            raise ValueError("Missing CONTAINER_NAME")

        self.queueName = os.getenv("AZURE_QUEUE_NAME")
        if not self.queueName:
            raise ValueError("Missing AZURE_QUEUE_NAME")

        self.queue = QueueClient.from_connection_string(conn_str=self.connectString,queue_name=self.queueName)

        self.blobClient = BlobServiceClient.from_connection_string(self.connectString)

        self.containerClient = self.blobClient.get_container_client(self.container)


    def createBlobName(self, eventId: int,fType: str, orgName: str):
        name = Path(orgName).name
        unqName = f'{uuid4().hex}_{name}'
        return f"events/{eventId}/{fType}s/{unqName}"

    async def fileUpload(self,file: UploadFile, eventID: str, fType: str):

        orgName = Path(file.filename).name
        blobName = self.createBlobName(eventID, fType, orgName)

        contents = await file.read()

        contentType = file.content_type or "application/octet-stream"

        blob_client = self.containerClient.get_blob_client(blobName)

        blob_client.upload_blob(data =contents, overwrite=True, content_settings=ContentSettings(content_type=contentType))

        return {"original_name": orgName, "blob_name": blobName, "url": blob_client.url, "size_bytes": len(contents), "content_type": contentType}

    def getBlobUrl(self, blobName:str):
        blobClient = self.containerClient.get_blob_client(blobName)
        return blobClient.url
    
    def downloadBlob(self, blobName):
        blobClient = self.containerClient.get_blob_client(blobName)
        return blobClient.download_blob().readall()

    def deleteBlob(self, blobName: str) -> bool:
        if not blobName:
            return False

        try:
            self.containerClient.get_blob_client(blobName).delete_blob(
                delete_snapshots="include"
            )
            return True
        except ResourceNotFoundError:
            return False
        except Exception as error:
            self.log.exception("Could not delete blob %s: %s", blobName, error)
            return False
    
    def downloadBlobToFile(self, blobName: str, localPath: str):
        blob_client = self.containerClient.get_blob_client(blobName)

        data = blob_client.download_blob().readall()

        with open(localPath, "wb") as file:
            file.write(data)

        return localPath
    
    def downloadBlobToFile(self, blobName: str, localPath: str):
        blob_client = self.containerClient.get_blob_client(blobName)

        with open(localPath, "wb") as file:
            download_stream = blob_client.download_blob()
            file.write(download_stream.readall())

        return localPath
    
    def downloadToTemp(self, photos: list[dict], tempDir: Path, retID: str = 'photo_id'):
        tempDir = Path(tempDir)
        downloaded = []

        for photo in photos:
            photoID = photo.get(retID) or photo.get("photo_id") or photo.get("video_id") or photo.get("frame_id")
            blobName = photo["blob_name"]

            fileName = Path(blobName).name
            localPath = tempDir / fileName

            try:
                self.downloadBlobToFile(blobName, str(localPath))

                item = dict(photo)
                item.update({retID: photoID, "blob_name": blobName, "file_path": str(localPath)})
                downloaded.append(item)

            except Exception as e:
                item = dict(photo)
                item.update({retID: photoID, "blob_name": blobName, "file_path": None, "error": str(e)})
                downloaded.append(item)
              
        return downloaded
    
    def sendQMsg(self, msg):
        try:
            if isinstance(msg, dict):
                msg = json.dumps(msg)

            if not isinstance(msg, str):
                msg = str(msg)

            result = self.queue.send_message(msg)

            print("Queue message sent successfully.")
            
            return result

        except Exception as e:
            errMsg =(f"Error sending queue message: {e}")
            print(errMsg)
            
            self.log.exception(errMsg)
            return None

    def uploadBytes(self, blobName: str, data: bytes, contentType: str = "application/octet-stream"):
        try:
            blob_client = self.containerClient.get_blob_client(blobName)

            blob_client.upload_blob(data=data,overwrite=True,content_settings=ContentSettings(content_type=contentType))

            return {
                "blob_name": blobName,
                "url": blob_client.url,
                "size_bytes": len(data),
                "content_type": contentType
            }

        except Exception as e:
            errMsg = f"Error uploading bytes to blob: {e}"
            print(errMsg)
            self.log.exception(errMsg)
            return None
        
    def uploadLocalFile(self, blobName: str, localPath: str, contentType: str = "application/octet-stream"):
        try:
            path = Path(localPath)
            blob_client = self.containerClient.get_blob_client(blobName)

            with path.open("rb") as file:
                blob_client.upload_blob(
                    data=file,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=contentType)
                )

            return {
                "blob_name": blobName,
                "url": blob_client.url,
                "size_bytes": path.stat().st_size,
                "content_type": contentType
            }

        except Exception as e:
            errMsg = f"Error uploading local file to blob: {e}"
            print(errMsg)
            self.log.exception(errMsg)
            return None

    def getSignedBlobUrl(self,blobName: str,expiresInMinutes: int = 15):
        if not blobName:
            return None

        credential = self.blobClient.credential
        account_key = getattr(credential, "account_key", None)

        if not account_key:
            raise RuntimeError(
                "Azure account-key credentials are required "
                "to generate a blob SAS URL"
            )

        expires_at = (datetime.now(timezone.utc)+ timedelta(minutes=expiresInMinutes))

        sas_token = generate_blob_sas(
            account_name=self.blobClient.account_name,
            container_name=self.container,
            blob_name=blobName,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expires_at,
        )

        blob_client = self.containerClient.get_blob_client(blobName)

        return {
            "url": f"{blob_client.url}?{sas_token}",
            "expires_at": expires_at.isoformat(),
        }
