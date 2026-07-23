from pathlib import Path

import cv2 as cv
import imagehash
import numpy as np
from PIL import Image
from shared.ProjectHelper import Helpers as ph


class ImgQualFilt:
    def __init__(self, db, log, minWidth=800, minHeight=600, blurThreshold=100., darkThreshold = 45.0, brightThreshold = 215.0, contrastThreshold = 30.0, noiseThreshold = 12.0):
        self.minWidth = minWidth
        self.minHeight = minHeight
        self.blurThres = blurThreshold
        self.darkThres = darkThreshold
        self.brightThres = brightThreshold
        self.contrastThres = contrastThreshold
        self.noiseThres = noiseThreshold
        self.db = db
        self.log = log

    
    def buildDict(self, photo_id: int, status: str, reasons: list[str], blurScore: float, brightScore: float, contScore: float, width: float, height: float, 
                  imgHash: str, model: str, gps: str, photoOriginalDate: str, userApproved: int = 0):
        id = "photo_id"
        
        if reasons:
            reasonStr = ",".join(reasons)
        else:
            reasonStr = "N/A"

        return {id: photo_id,
                "status":status,
                "reason": reasonStr,
                "blur_score": blurScore,
                "bright_score": brightScore,
                "contrast_score": contScore,
                "width": width,
                "height": height,
                "image_hash": imgHash,
                "camera_model": model,
                "gps": gps,
                "photo_original_date": photoOriginalDate,
                "user_approved": userApproved}
    
    def hashToStr(self, h):
        if h is None:
            return None
        # already a string
        if isinstance(h, str):
            return h
        # imagehash object (correct case)
        if isinstance(h, imagehash.ImageHash):
            return str(h)
        # numpy array (shouldn't happen, but just in case)
        if hasattr(h, 'flatten'):
            return ''.join(h.flatten().astype(int).astype(str))
        return str(h)

    def strToHash(self, s):
        if s is None:
            return None
        return imagehash.hex_to_hash(s)

    def setImagePath(self, imgPath: str):
        path = Path(imgPath)

        if not path.exists():
          return self.buildDict(0,"error",["FNF"],101.0,-1,-1,0,0,None, None,None,None)
        
        self.img = cv.imread(str(path))

    def errorDict(self, photoID):
        return self.buildDict(photoID,"error",["FNF"],101.0,-1,-1,0,0,None, None,None,None)

    def noiseJudgement(self, img, height, width):
    # Immerkaer method

        if height < 3 or width < 3:
            return 0.0
        kernal = np.array([[1, -2, 1],
                            [-2, 4, -2],
                            [1, -2, 1]], dtype=np.float64)

        response = cv.filter2D(img.astype(np.float64), cv.CV_64F, kernal)

        valid_response = response[1:-1, 1:-1]
        sigma = np.sum(np.abs(valid_response))
        sigma *= np.sqrt(0.5 * np.pi) / (6 * (width - 2) * (height - 2))

        return sigma

    def analyze(self, photoID: int, imgPath: str):
        path = Path(imgPath)

        rejectNum = 1

        imgHash = self.hashImages(path)
        imgHash = self.hashToStr(imgHash)
        #print(imgHash)

        if not path.exists():
          return self.errorDict(photoID)
        
        img = cv.imread(str(path))

        md = ph.getMetaData(path) #metadata
        if img is None:
            return self.errorDict(photoID)
        
        singleColor = np.all(img == img[0,0])
        height, width = img.shape[:2]
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

        blurScore = cv.Laplacian(gray, cv.CV_64F).var()
        brightScore = float(np.mean(gray))
        contrastScore = float(np.std(gray))

        noise = self.noiseJudgement(gray, height, width)

        reason = []

        if width < self.minWidth or height < self.minHeight:
            reason.append("low_resolution")

        if blurScore < self.blurThres:
            reason.append('blurry')

        if singleColor:
            reason.append('single_color')

        if brightScore < self.darkThres:
            reason.append('dark')
        
        if brightScore > self.brightThres:
            reason.append('bright')
        
        if contrastScore < self.contrastThres:
            reason.append('low_contrast')

        if noise > self.noiseThres:
            reason.append('noisy_photo')

        if len(reason) > rejectNum:
            status = 'rejected'
        else:
            status = 'approved'
            reason.append('passed_filter')

        return self.buildDict(photoID, status, reason, round(float(blurScore), 2), round(float(brightScore),2), round(float(contrastScore),2), width, height, imgHash,
                              md["camera_model"], md["gps"], md["photo_original_date"])
    
    def batchRunPF(self, media: list[dict], dtype: str = 'photo_id'):
        if media is None:
            err = "No files found"
            raise ValueError(err)
        
        return ph.batchRun(mediaList=media, procFunc=self.analyze, insFunc=self.db.insertPreFilter, dtype=dtype)
    
    def hashImages(self, imgPath: str):
        try:
            hash = imagehash.phash(Image.open(imgPath))
            #print (hash)
            return hash
        
        except Exception as e:
            print(f"Hash error: {e}")
            return None

def main():
    ts = ImgQualFilt()

    result2 = ts.batchRunPhotos(2)
    #for result in result2:
    #    print(result)
    #result = ts.batchRunVideos(r'C:\CSI4999\Videos\tempFrames\event_1_35iz4tfs_frames', 1)

if __name__ == "__main__":
    main()