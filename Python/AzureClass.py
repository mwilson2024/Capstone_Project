import os
from pathlib import Path
from uuid import uuid4

from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv
from fastapi import UploadFile


class blobHandler:
    def __init__(self, log):
        load_dotenv()

        self.connectString = os.getenv("AZURE_CONNECTION_STRING")
        if not self.connectString:
            raise ValueError("Missing Connection String")
        
        self.container = os.getenv("CONTAINER_NAME")

        if not self.container:
            raise ValueError("Missing Container Name")
        
        self.log = log
        
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
        downloaded = []

        for photo in photos:
            photoID = photo[retID]
            blobName = photo["blob_name"]

            fileName = Path(blobName).name
            localPath = tempDir / fileName

            try:
                self.downloadBlobToFile(blobName, str(localPath))

                downloaded.append({retID: photoID,"blob_name": blobName,"file_path": str(localPath)})

                print(f"Downloaded {retID} {photoID}: {localPath}")

            except Exception as e:
                print(f"Failed downloading photo_id {photoID}: {e}")
                downloaded.append({retID: photoID,"blob_name": blobName,"local_path": None,"error": str(e)})
            
            
        return downloaded
