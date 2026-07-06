import time

import shared.DataStruct as ds
from shared.ProjectHelper import Helpers as ph


class Users:
    failedLoginAttempts = {}

    def __init__(self, db, log):
        self.db = db
        self.log = log

    def isLoginBlocked(self, login_key: str) -> bool:
        record = self.failedLoginAttempts.get(login_key)

        if not record:
            return False

        failed_count = record["count"]
        last_failed_time = record["last_failed_time"]

        lockout_seconds = 300  # 5 minutes

        if failed_count >= 5:
            if time.time() - last_failed_time < lockout_seconds:
                return True
            else:
                self.failedLoginAttempts.pop(login_key, None)
                return False

        return False

    def recordFailedLogin(self, login_key: str):
        record = self.failedLoginAttempts.get(login_key)

        if not record:
            self.failedLoginAttempts[login_key] = {
                "count": 1,
                "last_failed_time": time.time()
            }
            return

        record["count"] += 1
        record["last_failed_time"] = time.time()

    def clearFailedLogins(self, login_key: str):
        self.failedLoginAttempts.pop(login_key, None)
  
    def createUser(self, user: ds.userCreate):
        isStrong, message = ph.validateStrongPassword(user.pwd)

        if not isStrong:
            print(f"Weak password rejected: {message}")
            return None

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
    
    def getUserData(self, userID: int):
        return self.db.getUserInfo(userID)
    
    def loginUser(self, login: ds.userLogin) -> int:
        login_key = login.email or login.user_name

        if self.isLoginBlocked(login_key):
            print("Too many failed login attempts. Try again later.")
            return None

        user = self.db.getUserPWD(login.email, login.user_name)

        if not user:
            print('Record not found')
            self.recordFailedLogin(login_key)
            return None
        
        isValid = ph.verifyPwd(login.pwd, user['password_hash'])

        user.pop("password_hash", None)

        if not isValid:
            print('Invalid password')
            self.recordFailedLogin(login_key)
            return None

        self.clearFailedLogins(login_key)

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

    userService = Users()
    res = userService.createUser(testUser)
    print(res)