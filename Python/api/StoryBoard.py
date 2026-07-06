from datetime import datetime, timedelta

from shared.ProjectHelper import Helpers as ph


class StoryBoardGen():
    def __init__(self, db, log, eventTimeGap: int = 20):
        self.eventTimeGap = eventTimeGap
        self.log = log
        self.db = db

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
            truth = ph.findDuplicateImage(hash1, hash2)
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

    def createStoryboardForEvent(self, eventID: int, requestID: int | None = None):
        if eventID is None:
            print("Missing eventID")
            return None

        photos = self.db.getApprovedPhotosForStoryboard(eventID)

        if not photos:
            print(f"No approved photos found for event_id={eventID}")
            return None

        storyboardItems = self.generateSeq(photos)

        if not storyboardItems:
            print(f"No storyboard items generated for event_id={eventID}")
            return None

        result = self.db.createStoryboardWithItems(eventID=eventID,requestID=requestID,storyboard_items=storyboardItems)

        return result
    
if __name__ == "__main__":
    import logging
    from shared.DBConn import SQLbuilder

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    log = logging.getLogger("StoryboardLocalTest")

    EVENT_ID = 1
    REQUEST_ID = 1

    db = SQLbuilder(log)
    db.connect()

    generator = StoryBoardGen(
        db=db,
        log=log,
        eventTimeGap=20
    )

    print("\nStarting local storyboard test...")
    print(f"event_id: {EVENT_ID}")
    print(f"request_id: {REQUEST_ID}")
    print("-" * 60)

    result = generator.createStoryboardForEvent(eventID=EVENT_ID,requestID=REQUEST_ID)

    if not result:
        print("Storyboard was not created.")
        raise SystemExit

    storyboard = result.get("storyboard")
    items = result.get("items", [])

    print("\nStoryboard Created Successfully")
    print("-" * 60)
    print(f"Storyboard ID: {storyboard.get('storyboard_id')}")
    print(f"Event ID: {storyboard.get('event_id')}")
    print(f"Request ID: {storyboard.get('request_id')}")
    print(f"Status: {storyboard.get('status')}")
    print(f"Item Count: {len(items)}")

    print("\nStoryboard Items:")
    print("-" * 60)

    for item in items:
        print(f"Storyboard Item ID: {item.get('storyboard_item_id')}")
        print(f"Storyboard ID: {item.get('storyboard_id')}")
        print(f"Photo ID: {item.get('photo_id')}")
        print(f"Sequence Order: {item.get('sequence_order')}")
        print(f"Scene Label: {item.get('scene_label')}")
        print(f"Confidence: {item.get('confidence')}")
        print(f"Reason: {item.get('reason')}")
        print("-" * 60)