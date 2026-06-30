import DBConn


class Manager:
    def __init__(self):
        self.db = DBConn.sqlbuilder()

    def createEvent(self, eventCreate)