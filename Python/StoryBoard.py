from datetime import datetime, timedelta
import DBConn

class StoryBoardGen():
    def __init__(self, eventTimeGap):
        self.eventTimeGap = 20
        self.db = DBConn.SQLbuilder()
        self.db.connect()

    def parseTime(self, value):
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
        
    def classifyScene(self, row:dict):
        personCount = row.get("person_count", 0) or 0
        objClass = row.get('obj_class') or ''
        contentScore = row.get('content_score', 0) or 0

        objClass = row.get('content_score', 0) or 0

        if objClass is str:
            objClass = objClass.lower()

        if personCount >= 5:
            return "Group / Crowd Moment", 0.75, "Many people detected"

        if personCount == 2:
            return "Couple / Small Group Moment", 0.70, "Two people detected"

        #if "dining table" in objClass or "chair" in objClass:
        #    return "Reception / Seating Area", 0.65, "Tables or chairs detected"

        if contentScore >= 70:
            return "Highlight Moment", 0.70, "High content score"

        if personCount == 1:
            return "Portrait / Individual Moment", 0.60, "One person detected"

        return "General Event Moment", 0.50, "Default scene classification"

    def generateSeq(self, photos: list[dict]):
        board = []
        currentgroup = []
        lastTime = None
        seqOrder = 1

        for photo in photos:
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

            output.append({"photo_id": photo['photo_id'], "event_id": photo['event_id'], 'sequence_order': sequenceOrder,
            'scene_label': sceneLabel, 'confidence': confidence, "reason": reason, 'file_path': photo['file_path']})

        return output

    
if __name__ == "__main__":
    # Fake photo data like what would come back from your database
    # fake_photos = [
    #     {
    #         "photo_id": 1,
    #         "event_id": 1,
    #         "file_path": r"C:\CSI4999\Photos\arrival1.jpg",
    #         "photo_taken": "2026-06-15T16:00:00",
    #         "created_at": "2026-06-15T16:01:00",
    #         "person_count": 3,
    #         "max_person_conf": 0.91,
    #         "obj_class": "person",
    #         "content_score": 65
    #     },
    #     {
    #         "photo_id": 2,
    #         "event_id": 1,
    #         "file_path": r"C:\CSI4999\Photos\arrival2.jpg",
    #         "photo_taken": "2026-06-15T16:08:00",
    #         "created_at": "2026-06-15T16:09:00",
    #         "person_count": 6,
    #         "max_person_conf": 0.88,
    #         "obj_class": "person",
    #         "content_score": 80
    #     },
    #     {
    #         "photo_id": 3,
    #         "event_id": 1,
    #         "file_path": r"C:\CSI4999\Photos\ceremony1.jpg",
    #         "photo_taken": "2026-06-15T16:45:00",
    #         "created_at": "2026-06-15T16:46:00",
    #         "person_count": 2,
    #         "max_person_conf": 0.95,
    #         "obj_class": "person",
    #         "content_score": 90
    #     },
    #     {
    #         "photo_id": 4,
    #         "event_id": 1,
    #         "file_path": r"C:\CSI4999\Photos\reception1.jpg",
    #         "photo_taken": "2026-06-15T18:10:00",
    #         "created_at": "2026-06-15T18:11:00",
    #         "person_count": 0,
    #         "max_person_conf": 0.0,
    #         "obj_class": "dining table, chair",
    #         "content_score": 55
    #     },
    #     {
    #         "photo_id": 5,
    #         "event_id": 1,
    #         "file_path": r"C:\CSI4999\Photos\dancing1.jpg",
    #         "photo_taken": "2026-06-15T20:30:00",
    #         "created_at": "2026-06-15T20:31:00",
    #         "person_count": 10,
    #         "max_person_conf": 0.89,
    #         "obj_class": "person",
    #         "content_score": 95
    #     }
    # ]
    db = DBConn.SQLbuilder()
    db.connect()
    fake_photos = db.getApprovedPhotosForStoryboard(1)
    generator = StoryBoardGen(20)

    storyboard = generator.generateSeq(fake_photos)
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