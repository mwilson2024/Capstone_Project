import datetime
import os

import jwt
from dotenv import load_dotenv

load_dotenv()

class Auth:
    def __init__(self):
        self.secretKey = os.environ["JWT_SECRET_KEY"]
        self.algo = 'HS256'
        self.ACCESS_TOKEN_EXPIRE_DAYS = 7
        
    def createAccessToken(self, user_id:int, extra:dict |None = None) -> str:
        expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days= self.ACCESS_TOKEN_EXPIRE_DAYS)

        payload = {'sub': str(user_id), 'exp': expires}
        if extra:
            payload.update(extra)

        return jwt.encode(payload= payload, key=self.secretKey, algorithm=self.algo)
    
    def decodeToken(self, token: str) -> dict:
        return jwt.decode(token, key=self.secretKey, algorithms=[self.algo])