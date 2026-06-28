from datetime import datetime, timedelta
import DBConn
import ProjectHelper
from pathlib import Path

class StoryBoardGen():
    def __init__(self, eventTimeGap: int = 20):
        self.eventTimeGap = eventTimeGap
        self.db = DBConn.SQLbuilder()
        self.db.connect()
        self.PH = ProjectHelper.Helpers()

    def parseTime(self, value):
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
        
    def classifyScene(self, row: dict):
        personCount = row.get("person_count", 0) or 0
        objClass = row.get("obj_class") or ""
        contentScore = row.get("content_score", 0) or 0

        if isinstance(objClass, str):
            objClass = objClass.lower()

        if personCount >= 5:
            return "Group / Crowd Moment", 0.75, "Many people detected"

        if personCount == 2:
            return "Couple / Small Group Moment", 0.70, "Two people detected"

        if "dining table" in objClass or "chair" in objClass:
            return "Reception / Seating Area", 0.65, "Tables or chairs detected"

        if contentScore >= 70:
            return "Highlight Moment", 0.70, "High content score"

        if personCount == 1:
            return "Portrait / Individual Moment", 0.60, "One person detected"

        return "General Event Moment", 0.50, "Default scene classification"

    def findDuplicates(self, temp: list):
        dupes = []

        for i in range(len(temp) - 1):
            hash1 = temp [i]["image_hash"]
            hash2 = temp [i+1]["image_hash"]
            truth = self.PH.findDuplicateImage(hash1, hash2)
            print(f'Photo_id:{temp[i]["photo_id"]} Hash1: {hash1} vs. phot_id: {temp[i + 1]["photo_id"]} Hash2: {hash2} Result: {truth}')
            if truth:
                dupes.append(temp[i + 1]["photo_id"])
        return dupes
    

    def generateSeq(self, photos: list[dict]):
        board = []
        currentgroup = []
        lastTime = None
        seqOrder = 1
        skip = self.findDuplicates(photos)

        for photo in photos:
            if photo["photo_id"] in skip:
                continue
            photoTime = self.parseTime(photo.get("photo_taken"))

            if lastTime is None:
                currentgroup.append(photo)
                lastTime = photoTime 
                continue

            timeGap = photoTime - lastTime 

            if timeGap > timedelta(minutes=self.eventTimeGap):
                board += self.processGroup(currentgroup, seqOrder)
                seqOrder += 1
                currentgroup = [photo]
            else:
                currentgroup.append(photo)

            lastTime = photoTime

        if currentgroup:
            board += self.processGroup(currentgroup, seqOrder)

        return board    

    def processGroup(self, group: list[dict], sequenceOrder: int):
        output= []

        for photo in group:
            sceneLabel, confidence, reason = self.classifyScene(photo)
            photo_id = photo.get("photo_id")
            file_path = photo.get("file_path")

            # if not file_path or not Path(file_path).is_file():
            #     print(f"Skipping LLaVA for photo_id {photo_id}: invalid file path: {file_path}")
            #     llava_result = None
            # else:
            #     llava_result = self.LV.sendPromptBatch( "wedding",
            #         photo_id=photo_id,
            #         file_path=file_path
            #     )


            output.append({"photo_id": photo['photo_id'], "event_id": photo['event_id'], 'sequence_order': sequenceOrder,
            'scene_label': sceneLabel, 'confidence': confidence, "reason": reason, 'file_path': photo['file_path']})

        return output

    
if __name__ == "__main__":

    db = DBConn.SQLbuilder()
    db.connect()
    photos = db.getApprovedPhotosForStoryboard(1)
    generator = StoryBoardGen(1)

    storyboard = generator.generateSeq(photos)
    
    db.insertStoryboardItems(1, storyboard)

    print("\nGenerated Storyboard:")
    print("-" * 60)

    for item in storyboard:
        print(f"Sequence Order: {item['sequence_order']}")
        print(f"Photo ID: {item['photo_id']}")
        print(f"Event ID: {item['event_id']}")
        print(f"Scene Label: {item['scene_label']}")
        print(f"Confidence: {item['confidence']}")
        print(f"Reason: {item['reason']}")
        print(f"File Path: {item['file_path']}")
        print("-" * 60)