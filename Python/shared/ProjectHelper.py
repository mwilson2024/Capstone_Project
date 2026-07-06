from datetime import date, datetime

import imagehash
from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS
from pwdlib import PasswordHash


class Helpers():
    def __init__(self):
        self.name = "placeholder"
    @staticmethod
    def convertGPS(value):

        d = float(value[0])
        m = float(value[1])
        s = float(value[2])

        return d + (m / 60.0) + (s / 3600.0)

    @staticmethod
    def getGPS(exif_data):
        gps_info = {}

        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)

            if tag_name == "GPSInfo":
                for gps_id, gps_value in value.items():
                    gps_name = GPSTAGS.get(gps_id, gps_id)
                    gps_info[gps_name] = gps_value

        if not gps_info:
            return None

        lat = gps_info.get("GPSLatitude")
        lat_ref = gps_info.get("GPSLatitudeRef")
        lon = gps_info.get("GPSLongitude")
        lon_ref = gps_info.get("GPSLongitudeRef")

        if lat is None or lon is None or lat_ref is None or lon_ref is None:
            return None

        latitude = Helpers.convertGPS(lat)
        longitude = Helpers.convertGPS(lon)

        if lat_ref != "N":
            latitude = -latitude

        if lon_ref != "E":
            longitude = -longitude

        return f"{latitude},{longitude}"

    @staticmethod
    def getMetaData(image_path: str):
  
        metadata = {
            "photo_original_date": None,
            "camera_model": None,
            "gps": None
        }

        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()

                if not exif_data:
                    metadata["photo_original_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    metadata["camera_model"] = "N/A"
                    metadata["gps"] = "N/A"
                    return metadata

                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)

                    if tag_name == "DateTimeOriginal":
                        metadata["photo_original_date"] = str(value)

                    elif tag_name == "Model":
                        metadata["camera_model"] = str(value)

                metadata["gps"] = Helpers.getGPS(exif_data)

                return metadata

        except FileNotFoundError:
            print("Metadata error: file not found")
            return metadata

        except Exception as e:
            print(f"Metadata error: {e}")
            return metadata
    @staticmethod
    def getIDNum(s:str, pos:int, symbol : str = '_'):
        return int(s.split(symbol)[pos])
    
    @staticmethod    
    def formatTimeStamps(value):
      
        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time()).isoformat()

        value = str(value).strip()

        possible_formats = [
            "%Y:%m:%d %H:%M:%S",   # EXIF format
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d"
        ]

        for fmt in possible_formats:
            try:
                parsed_date = datetime.strptime(value[:19], fmt)
                return parsed_date.isoformat()
            except ValueError:
                continue

        print(f"Invalid date format skipped: {value}")
        return None

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
    
    @staticmethod
    def strToHash(s):
        if s is None:
            return None

        if isinstance(s, imagehash.ImageHash):
            return s

        if isinstance(s, str):
            s = s.strip()

            if s == "":
                return None

            try:
                return imagehash.hex_to_hash(s)
            except Exception as e:
                print(f"Hash conversion error: {e}")
                return None

        return None

    @staticmethod
    def findDuplicateImage( hash1, hash2, threshold: int = 6):
        if hash1 is None or hash2 is  None:
            return None
        
        hash1 = Helpers.strToHash(hash1)
        hash2 = Helpers.strToHash(hash2)
        dist = hash1 - hash2

        if dist <= threshold:
            return True
        else:
            return False
        
    @staticmethod
    def batchRun(mediaList: list[dict], procFunc, insFunc, dtype: str = 'photo_id'):
        results = []


        try:
            for media in mediaList:
                
                tempId = media.get(dtype)

                if tempId is None:
                    raise ValueError(f"Missing {dtype} in media row: {media}")
                
                filePath = media.get("file_path")
                if not filePath:
                    raise ValueError(f"Missing file_path for {dtype}={tempId}")
                

                res = procFunc(tempId, filePath)

                if not res:
                    raise ValueError(f"Processing returned no result for {dtype}={tempId}")


                if dtype == 'frame_id':
                    res["frame_id"] = res.pop("photo_id")

                results.append(res)


            insFunc(results, dtype)
            return results
    
        except Exception as e:
            errMsg = f'Error: {e}'
            print(errMsg)


    @staticmethod
    def hashPwd(pwd: str) -> str:
        return PasswordHash.recommended().hash(pwd)
    
    @staticmethod
    def verifyPwd(userpwd: str, hashpwd: str) -> bool:
        return PasswordHash.recommended().verify(password= userpwd, hash=hashpwd)
    
def main():
    proj = Helpers()
    md = proj. getMetaData(r"C:\CSI4999\Photos\IMG_0182.jpeg")
    print(md)
if __name__ == "__main__":
    main()