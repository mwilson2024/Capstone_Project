import DataStruct as ds
import DBConn
from pwdlib import PasswordHash


class Users:
    def __init__(self):
        self.db = DBConn.SQLbuilder()
        self.db.connect()
        self.pwhash = PasswordHash.recommended()

    def hashPWD(self, pwd: str) -> str:
        return self.pwhash.hash(pwd)
    
    def verifyPWD(self, userPWD: str, hashedPWD) -> bool:
        return self.pwhash.verify(userPWD, hashedPWD)
        
    def createUser(self, user: ds.userCreate):
        userData = user.model_dump(exclude={"pwd"})
        userData["password_hash"] = self.hashPWD(user.pwd)
        
        res = self.db.insertUser(userData)

        userData.clear()
        del userData

        if not res:
            return None
        
        return res
    
    def updateUser(self, userID: int):
        print('place')
    
    def getUserData(self, userID:int):
        return self.db.getUserInfo(userID)
    
    def loginUser(self, login: ds.userLogin ):
        user = self.db.getUserPWD(login.email, login.user_name)

        if not user:
            print('Record not found') 
            return None
        
        isValid = self.verifyPWD(login.pwd, user['password_hash'])

        user.pop("password_hash", None)

        if not isValid:
            user.clear()
            del dataDict   
            print('Invalid password')
            return None

        userData = self.db.getUserInfo(user["user_id"])
        print('Valid password')
        return userData

if __name__ == "__main__":
    # testUser = ds.userCreate(
    #     user_name="testuser100",
    #     first_name="Test",
    #     last_name="User",
    #     email="testuser5@example.com",
    #     phone="555-555-5555",
    #     role="user",
    #     pwd="TestPassword123!"
    # )

    test = ds.userLogin(email= "testuser5@example.com", pwd="TestPassword123!")
    userService = Users()
    #res = userService.createUser(testUser)
    result = userService.loginUser(test)
    print(result)