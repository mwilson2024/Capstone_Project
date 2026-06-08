from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


class SQLbuilder:
    def __init__(self):
        db_path = Path("C:/CSI4999/supra_protege.db")

        if not db_path.exists(): 
            raise FileNotFoundError(f"Database file not found: {db_path}")

        self.connStr = f"sqlite:///{db_path.as_posix()}"
        self.engine = create_engine(self.connStr, echo=True, future=True)

    def connect(self):
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT sqlite_version();"))

                print("Connected to SQLite database.")
                print("SQLite version:", result.scalar())
                print("Database:", self.connStr)

                return True

        except SQLAlchemyError as error:
            print("Connection failed:", error)
            return False

    def postQRtoDB(self, eventID: int, url: str, token: str, expires_at: str, max_upload: int, purpose: str, is_active: bool):
        if eventID is None or url is None:
            print('Missing Values in arguments')
            return None
        sql = """INSERT into qrcodes(event_id, image_url, token, expires_at, max_uploads, purpose, is_active)
        VALUES  (?,?,?,?,?,?,?)"""

        try:
            with self.engine.begin() as connection:
                connection.exec_driver_sql(sql, (eventID, url, token, expires_at, max_upload, purpose, is_active))

            print('QR Saved')

        except SQLAlchemyError as e:
            print(f'Error Occurred: {e}')

    def getQRToken(self, token: str):
        if token is None or token.strip() == "":
            return False, "Missing Token"
        
        query = """SELECT * FROM qrcodes WHERE token = ?"""
        try:
            with self.engine.connect() as conn:
                result = conn.exec_driver_sql(query, (token.strip(),))
                row = result.mappings().first()

                if row is None:
                    return None

            return dict(row)
                
        except SQLAlchemyError as e:
            print(f'Error Occurred: {e}')
    
    def insertPreFilter(self, photo_id: int, dataDict: dict):
        if photo_id is None or dataDict is None:
            print("Missing photo_id or dataDict")
            return None

        sql = """
            INSERT INTO filter_photos (
                photo_id,
                status,
                blur_score,
                bright_score,
                contrast_score,
                width,
                height,
                user_approved
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """

        values = (
            photo_id,
            dataDict.get("status", "pending"),
            dataDict.get("blur_score", 0),
            dataDict.get("brightness_score", 0),
            dataDict.get("contrast_score", 0),
            dataDict.get("width", 0),
            dataDict.get("height", 0),
            dataDict.get("user_approved", 0)
        )

        try:
            with self.engine.begin() as connection:
                result = connection.exec_driver_sql(sql, values)

            print("Pre-filter data saved")
            return result.lastrowid

        except SQLAlchemyError as e:
            print(f"Error Occurred inserting pre-filter data: {e}")
            return None 
        
    def getPhotos(self, eventID: int):
        query = """SELECT photoID, photoURL
        FROM photos
        WHERE eventID = ?"""

        try:
            with self.engine.begin() as connection:
                result = connection.exec_driver_sql(query, eventID)
                rows = result.fetchall()

            print("Pre-filter data saved")
            return [dict(row) for row in rows]

        except SQLAlchemyError as e:
            print(f"Error Occurred inserting pre-filter data: {e}")
            return None 

        
    def selectAll(self, table: str):
        sql = f"""
        SELECT *
        FROM {table}
        """

        with self.engine.connect() as conn:
            result = conn.exec_driver_sql(sql)
            return result.fetchall()

if __name__ == "__main__":
    db = SQLbuilder()
    db.connect()
  #  db.postQRtoDB(35, "www.espn.com")
    rows = db.selectAll('photos')
    for row in rows:
        print(row)