import shared.DataStruct as ds
from shared.ProjectHelper import Helpers as ph


class Manager:
    def __init__(self, db, log):
        self.db = db
        self.log = log

    def createEvent(self, event: ds.eventCreate, location: ds.eventLocation):
        try:
            eventData = event.model_dump(mode="json", exclude={'password'})        
            eventData['password_hash'] = ph.hashPwd(event.password)

            locData = location.model_dump()

            locaRes = self.db.locationCreate(locData)

            if not locaRes:
                print("Location was not created.")
                return None

            eventData['location_id'] = locaRes['location_id']
            eventRes = self.db.eventCreate(eventData)

            if not eventRes:
                print("Event was not created.")
                return None

            return {
                "event": eventRes,
                "location": locaRes
            }

        except Exception as e:
            print(f"Error creating event: {e}")
            return None
        
    def getAllLocations(self):
        try:
            locations = self.db.locationGetAll()

            if locations is None:
                return None

            return locations

        except Exception as e:
            print(f"Error loading locations: {e}")
            return None
        
    def getLocationByID(self, locationID: int):
        try:
            return self.db.locationGetByID(locationID)

        except Exception as e:
            print(f"Error loading location: {e}")
            return None

    def getEventsByUser(self, userID: int):
        try:
            events = self.db.eventGetAllByUser(userID)

            if events is None:
                return None

            return events

        except Exception as e:
            print(f"Error loading events: {e}")
            return None

    def getEventByID(self, eventID: int):
        try:
            return self.db.eventGetByID(eventID)

        except Exception as e:
            print(f"Error loading event: {e}")
            return None
        
    def modifyEvent(self, eventID: int, event: ds.eventModify):
        try:
            eventData = event.model_dump(mode="json",exclude_unset=True,exclude_none=True)

            if not eventData:
                print("No event fields were provided.")
                return None

            if "password" in eventData:
                pwd = eventData.pop("password")
                eventData["password_hash"] = ph.hashPwd(pwd)

            eventRes = self.db.eventModify(eventID, eventData)

            if not eventRes:
                print("Event was not modified.")
                return None

            return eventRes

        except Exception as e:
            print(f"Error modifying event: {e}")
            return None
        
    def modifyLocation(self, locationID: int, location: ds.eventLocationModify):
        try:
            locData = location.model_dump(mode="json",exclude_unset=True,exclude_none=True)

            if not locData:
                print("No location fields were provided.")
                return None

            locRes = self.db.locationModify(locationID, locData)

            if not locRes:
                print("Location was not modified.")
                return None

            return locRes

        except Exception as e:
            print(f"Error modifying location: {e}")
            return None