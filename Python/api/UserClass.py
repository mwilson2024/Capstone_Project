import shared.DataStruct as ds
from shared.ProjectHelper import Helpers as ph


class Users:
    def __init__(self, db, log):
            self.db = db
            self.log = log
  
    def verifyCreatePW(self, pw: str):
        reqMinLen = 8
        reqMaxLen = 15
        pwLen = len(pw)
        specialSym = ['$', '@', '#', '%', '!']
        valid = True
        reason = []

        hasDigit = False
        hasUppercase = False
        hasLowercase = False
        hasSpecial = False

        for char in pw:
            if char.isdigit():
                hasDigit = True
            elif char.isupper():
                hasUppercase = True
            elif char.islower():
                hasLowercase = True

            if char in specialSym:
                hasSpecial = True

        if pwLen < reqMinLen:
            valid = False
            reason.append(f"password must be at least length {reqMinLen} current pw: {pwLen}")

        if pwLen > reqMaxLen:
            valid = False
            reason.append(f"password must be no more than length {reqMaxLen} current pw: {pwLen}")

        if not hasDigit:
            valid = False
            reason.append("password must have at least one numeral")

        if not hasUppercase:
            valid = False
            reason.append("password must have at least one uppercase letter")

        if not hasLowercase:
            valid = False
            reason.append("password must have at least one lowercase letter")

        if not hasSpecial:
            valid = False
            reason.append("password must have at least one of the symbols $@#%")

        problemDict = {
            'valid': valid,
            'reason': reason if not valid else ["Password valid"],
            'has_digit': hasDigit,
            'has_uppercase': hasUppercase,
            'has_lowercase': hasLowercase,
            'has_symbol': hasSpecial,
            'min_length': pwLen >= reqMinLen,
            'max_length': pwLen <= reqMaxLen
        }

        return problemDict
        
       
        
    def createUser(self, user: ds.userCreate):
        userData = user.model_dump(exclude={"pwd"})
        
        pwResult = self.verifyCreatePW(user.pwd)
        if not pwResult['valid']:
            return  False, pwResult['reason']
        
        userData["password_hash"] = ph.hashPwd(user.pwd)
        
        res = self.db.insertUser(userData)

        userData.clear()
        del userData

        if not res:
            return False, ["User could not be created."]
        
        return True, res
    
    def updateUser(self,userID: int,user: ds.userProfileUpdate,):
        changes = user.model_dump(exclude_none=True)
        return self.db.updateUserProfile(userID, changes)
    
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

    def changePassword(self,userID: int,currentPassword: str,newPassword: str,):
        user = self.db.getUserPasswordByID(userID)

        if not user:
            return "not_found"
        
        pwResult = self.verifyCreatePW(newPassword)
        if not pwResult['valid']:
            return  pwResult['reason']

        if not ph.verifyPwd(currentPassword,user["password_hash"]):
            return "invalid_password"

        password_hash = ph.hashPwd(newPassword)

        if not self.db.updateUserPassword(userID,password_hash):
            return "failed"

        return "updated"
