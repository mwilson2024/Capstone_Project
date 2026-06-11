from PIL import Image
import torch
from transformers import (BlipProcessor, BlipForConditionalGeneration, pipeline)
import os
import DBConn

class blipRanker():
    def __init__(self):
        self.device = self.selectDevice()
        self.blipProc = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blipModel = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blipModel.to(self.device)
        self.clipClassify = pipeline(task="zero-shot-image-classification",model="openai/clip-vit-base-patch32")
        self.db = DBConn.SQLbuilder()
        self.db.connect()

    def buildDict(self, photo_id: int, caption: str, moodLabel: str, moodConfScore: float, allMood: list[str], 
                  allMoodScore: list[float], kwScore: int, kw: list[str] | str, nudityCheck: bool = False):
       
        allMoodStr = ",".join(allMood)

        allMoodScoreStr = ",".join(str(score) for score in allMoodScore)

        if isinstance(kw, list):
            kwStr = ",".join(kw)
        else:
            kwStr = kw

        return {
            "photo_id": photo_id,
            "caption": caption,
            "mood_label": moodLabel,
            "mood_conf_score": moodConfScore,
            "all_mood_labels": allMoodStr,
            "keyword_score": kwScore,
            "keywords": kwStr,
            "nudity_check": nudityCheck,
            "all_mood_scores": allMoodScoreStr
        }

    def selectDevice(self):
        if torch.cuda.is_available():
            device = torch.device('cuda:0')
        elif torch.mps.is_available(): #For a macos Metal Performace Shader
            device = torch.device("mps")
        else:
            device = torch.device("cpu")
        print(f'Using device {device}')
        return device

    def scorePhotos(self, caption: str, kw: dict):
        caption.lower()
        score = 0
        matched = []
        
        for word, points in kw.items():
            if word in caption:
                score += points
                matched.append(word)
        
        score = min(score, 100)

        print(f"keyword_score: {score}, matched_keyword: {matched}")

        return {"keyword_score": score, "matched_keyword": matched}
    
    def captionImg(self, img: str):
        input = self.blipProc(img, return_tensors="pt").to(self.device)

        output = self.blipModel.generate(**input, max_new_tokens= 40)

        capt = self.blipProc.decode(output[0], skip_special_tokens=True)

        print(capt)

        return capt
    
    def classifyMood(self, img: str):
        labels = ["a romantic wedding photo","a fun group photo", "a formal ceremony photo",
            "a candid emotional photo", "a photo of food or decorations", "a low quality random photo", "nudity"]
        
        res = self.clipClassify(img, candidate_labels = labels)
        best = res[0]
        print(best)
        return best 
    
    def romanticScorePhotos(self, caption: str):

        keywords = {"bride": 15,
            "groom": 15,
            "couple": 20,
            "kiss": 25,
            "kissing": 25,
            "hugging": 15,
            "dancing": 15,
            "holding hands": 25,
            "wedding": 10,
            "first dance": 30,
            "couple": 10,
            "cutting cake": 15
        }

        """score = 0
        matched = []
        
        for word, points in keywords.items():
            if word in caption:
                score += points
                matched.append(word)
        
        score = min(score, 100)

        print(f"keyword_score: {score}, matched_keyword: {matched}")"""
        score = self.scorePhotos(caption, keywords)
        return score

    
    def analyze(self, eventID):
        photos = self.db.getPhotos(eventID)

        if photos is None:
            return "No photos found"
        
        skippable = ["nudity", "a low quality random photo"]
        
        results = []

        for photo in photos:
            img = photo["file_path"]
            photo_id = photo["photo_id"]

            caption = self.captionImg(img)
            if caption is None:
                caption = "None"
            mood = self.classifyMood(img)

            moodLabel = mood.get("label", "unknown")
            moodConfScore = float(mood.get("score", 0)) 

            allMood = mood.get("all_mood_labels", [moodLabel])
            allMoodScore = mood.get("all_mood_scores", [moodConfScore])

            keywordScore = 0
            keywords = []
            nudityCheck = 0

            if moodLabel in skippable:
                keywordScore = 0

                if moodLabel == "nudity":
                    nudityCheck = True

                    print(f"Scoring skipped: {moodLabel}")
            else:
                scoreResult  = self.romanticScorePhotos(img)

                if isinstance(scoreResult, (int, float)):
                    keywordScore = float(scoreResult)
                    keywords = []


                elif isinstance(scoreResult, dict):
                    keywordScore = float(scoreResult.get("keyword_score", 0))
                    keywords = scoreResult.get("keywords", [])
        
            dataDict = self.buildDict(
                photo_id=photo_id,
                caption=caption,
                moodLabel=moodLabel,
                moodConfScore=moodConfScore,
                allMood=allMood,
                allMoodScore=allMoodScore,
                kwScore=keywordScore,
                kw=keywords,
                nudityCheck=nudityCheck
            )

            ranking_id = self.db.insertImageRanking(dataDict)

            results.append({
                "photo_id": photo_id,
                "ranking_id": ranking_id,
                "caption": caption,
                "mood_label": moodLabel,
                "keyword_score": keywordScore,
                "nudity_check": nudityCheck
            })

        return results
        
def main():
    print(os.getenv("HF_TOKEN"))
    test = blipRanker()
    test.analyze(1)

if __name__ == "__main__":
    main()