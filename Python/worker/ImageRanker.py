import os
import re

import torch
from shared.ProjectHelper import Helpers as ph
from transformers import BlipForConditionalGeneration, BlipProcessor, pipeline


class blipRanker():
    def __init__(self, db, log):
        self.device = self.selectDevice()
        self.hf_token = os.getenv("HF_TOKEN")
        self.blipProc = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base",token=self.hf_token)
        self.blipModel = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blipModel.to(self.device)
        self.clipClassify = pipeline(task="zero-shot-image-classification",model="openai/clip-vit-base-patch32", token=self.hf_token)
        self.log = log
        self.db = db

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

        return {"score": score, "keyword": matched}
    
    def captionImg(self, img: str):
        input = self.blipProc(img, return_tensors="pt").to(self.device)

        output = self.blipModel.generate(**input, max_new_tokens= 40)

        capt = self.blipProc.decode(output[0], skip_special_tokens=True)

        print(capt)

        return capt
    
    def classifyMood(self, img: str):
        labels =  labels = [
        # Wedding / event scene types
        "a formal ceremony photo",
        "a reception party photo",
        "a cocktail hour photo",
        "a professional portrait photo",
        "a couple portrait photo",
        "a family portrait photo",
        "a wedding party group photo",
        "a first dance photo",
        "a speech or toast photo",
        "a cake cutting photo",
        "a photo of food or decorations",
        "a venue or room detail photo",
        "a dance floor photo",
        "a guest candid photo",

        # Emotional / mood labels
        "a romantic emotional photo",
        "a joyful celebration photo",
        "a funny candid photo",
        "a sentimental emotional photo",
        "a calm intimate photo",
        "an energetic party photo",

        # Bad / reject labels
        "a blurry low quality photo",
        "a random irrelevant photo",
        "nudity"
    ]
        
        res = self.clipClassify(img, candidate_labels = labels)
        best = res[0]
        print(best)
        return best 
    
    def romanticScorePhotos(self, caption: str):
        if not caption:
            return {
                "score": 0,
                "matched_keywords": []
            }

        caption = caption.lower()

        keywords = {
            # Strong romantic moments
            "kiss": 30,
            "kissing": 30,
            "first kiss": 35,
            "holding hands": 30,
            "hand in hand": 30,
            "first dance": 35,
            "slow dancing": 30,
            "dancing together": 30,
            "embracing": 25,
            "hugging": 20,
            "hug": 15,
            "forehead kiss": 35,
            "looking at each other": 25,
            "smiling at each other": 25,

            # Couple-related
            "bride": 15,
            "groom": 15,
            "couple": 25,
            "newlyweds": 30,
            "husband and wife": 30,
            "wedding couple": 30,
            "bride and groom": 35,
            "partner": 10,
            "spouse": 10,

            # Wedding scene moments
            "wedding": 10,
            "ceremony": 15,
            "altar": 15,
            "vows": 25,
            "exchanging vows": 30,
            "rings": 20,
            "wedding rings": 25,
            "walking down the aisle": 25,
            "aisle": 15,
            "reception": 10,
            "cake cutting": 15,
            "cutting cake": 15,
            "bouquet": 10,
            "veil": 10,

            # Emotional / romantic mood
            "romantic": 30,
            "intimate": 25,
            "emotional": 20,
            "sweet": 15,
            "tender": 20,
            "loving": 25,
            "joyful": 15,
            "happy couple": 25,
            "special moment": 20,
            "celebrating love": 25,

            # Visual style that often fits slideshow romance
            "portrait": 10,
            "close up": 10,
            "close-up": 10,
            "sunset": 15,
            "golden hour": 20,
            "flowers": 10,
            "candles": 10,
            "decorations": 5
        }

        negative_keywords = {
            "food": -10,
            "table": -5,
            "plates": -10,
            "random": -25,
            "blurry": -30,
            "low quality": -40,
            "dark": -15,
            "nudity": -100,
            "nude": -100,
            "bathroom": -40,
            "parking lot": -20
        }

        score = 0
        matched = []

        # Add romantic/wedding points
        for phrase, points in keywords.items():
            if re.search(rf"\b{re.escape(phrase)}\b", caption):
                score += points
                matched.append(phrase)

        # Subtract bad/random-photo points
        for phrase, points in negative_keywords.items():
            if re.search(rf"\b{re.escape(phrase)}\b", caption):
                score += points
                matched.append(phrase)

        score = max(0, min(score, 100))

        print(f"keyword_score: {score}, matched_keywords: {matched}")

        return {"score": score,"keywords": matched}

    
    def analyze(self, photoID:str, photo:str):
        #photos = self.db.getPhotos(eventID)

        if photo is None:
            return "No photos found"
        
        skippable = ["nudity", "a low quality random photo"]
        
        img = photo
        
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
            scoreResult  = self.romanticScorePhotos(caption)

            if isinstance(scoreResult, (int, float)):
                keywordScore = float(scoreResult)
                keywords = []


            elif isinstance(scoreResult, dict):
                keywordScore = float(scoreResult.get("score", 0))
                keywords = scoreResult.get("keywords", [])
    
        dataDict = self.buildDict(
            photo_id=photoID,
            caption=caption,
            moodLabel=moodLabel,
            moodConfScore=moodConfScore,
            allMood=allMood,
            allMoodScore=allMoodScore,
            kwScore=keywordScore,
            kw=keywords,
            nudityCheck=nudityCheck
        )

        return dataDict
    
    def batchRunIR(self, media: list[dict], dtype: str = 'photo_id'):
        if media is None:
            err = "No files found"
            raise ValueError(err)
        
        return ph.batchRun(media, self.analyze, self.db.insertImageRanking, dtype)
