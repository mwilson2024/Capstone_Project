import shared.DataStruct as ds
from shared.ProjectHelper import Helpers as ph


class Users:
    def __init__(self, db, log):
            self.db = db
            self.log = log
  
    def createUser(self, user: ds.userCreate):
        userData = user.model_dump(exclude={"pwd"})
        userData["password_hash"] = ph.hashPwd(user.pwd)
        
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
    
    def loginUser(self, login: ds.userLogin) -> int:
        user = self.db.getUserPWD(login.email, login.user_name)


        if not user:
            print('Record not found') 
            return None
        
        isValid = ph.verifyPwd(login.pwd, user['password_hash'])

        user.pop("password_hash", None)

        if not isValid:
            print('Invalid password')
            return None

        #userData = self.db.getUserInfo(user["user_id"])
        print('Valid password')
        return user["user_id"]


if __name__ == "__main__":
    testUser = ds.userCreate(
        user_name="testuser100",
        first_name="Test",
        last_name="User",
        email="testuser5@example.com",
        phone="555-555-5555",
        role="user",
        pwd="TestPassword123!"
    )

    #test = ds.userLogin(email= "testuser5@example.com", pwd="TestPassword123!")
    userService = Users()
    res = userService.createUser(testUser)
    #result = userService.loginUser(test)
    print(res)