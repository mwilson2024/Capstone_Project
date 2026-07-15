import os
import re
import json
from shared import DataStruct as ds
import torch
from shared.ProjectHelper import Helpers as ph
from transformers import BlipForConditionalGeneration, BlipProcessor, pipeline
from PIL import Image

class blipRanker():
    def __init__(self, db, log):
        self.device = self.selectDevice()
        self.hf_token = os.getenv("HF_TOKEN")
        self.blipProc = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base",token=self.hf_token)
        self.blipModel = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", token=self.hf_token)
        self.blipModel.to(self.device)
        self.clipClassify = pipeline(task="zero-shot-image-classification",model="openai/clip-vit-base-patch32", token=self.hf_token)
        self.log = log
        self.db = db
        self.eventType = None

    def selectDevice(self):
        if torch.cuda.is_available():
            device = torch.device('cuda:0')
        elif torch.mps.is_available(): #For a macos Metal Performace Shader
            device = torch.device("mps")
        else:
            device = torch.device("cpu")
        print(f'Using device {device}')
        return device
    
    def classifySafety(self, img) -> dict:
        labels = [
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

            # Original reject labels
            "a blurry low quality photo",
            "a random irrelevant photo",
            "nudity"
        ]

        results = self.clipClassify(
            img,
            candidate_labels=labels
        )

        if not results:
            return {
                "label": "unknown",
                "score": 0.0,
                "all_labels": [],
                "all_scores": [],
                "results": []
            }

        bestResult = results[0]

        return {
            "label": bestResult.get(
                "label",
                "unknown"
            ),
            "score": float(
                bestResult.get("score", 0.0)
            ),
            "all_labels": [
                result.get("label", "unknown")
                for result in results
            ],
            "all_scores": [
                float(result.get("score", 0.0))
                for result in results
            ],
            "results": results
        }

    def loadImage(self, photo):
        if isinstance(photo, Image.Image):
            return photo.convert('RGB')
        if isinstance(photo, (str, os.PathLike)):
            with Image.open(photo) as ph:
                return ph.convert('RGB')
            
        raise TypeError('Photo must be a pil image or a path')
    
    def captionImg(self, img: str):
        input = self.blipProc(img, return_tensors="pt").to(self.device)

        output = self.blipModel.generate(**input, max_new_tokens= 40)

        capt = self.blipProc.decode(output[0], skip_special_tokens=True)

        print(capt)

        return capt
    
    def classifyEventDetails(self,img) -> dict:
        eventType = self.eventType.lower().strip()

        profile = ds.EVENT_PROFILES.get(eventType,ds.EVENT_PROFILES["unknown"])

        candidateLabels = (profile.get_detail_candidate_labels())

        labelMap = profile.get_detail_label_map()

        if not candidateLabels:
            return {
                "event_detail_label": "unknown",
                "event_detail_conf_score": 0.0,
                "event_detail_scores": {}
            }

        results = self.clipClassify(img,candidate_labels=candidateLabels)

        if not results:
            return {
                "event_detail_label": "unknown",
                "event_detail_conf_score": 0.0,
                "event_detail_scores": {}
            }

        categoryScores = {}

        for result in results:
            label = result.get("label", "")
            score = float(result.get("score", 0))
            category = labelMap.get(label, "unknown")

            currentScore = categoryScores.get(
                category,
                0.0
            )

            if score > currentScore:
                categoryScores[category] = score

        bestResult = results[0]
        bestLabel = bestResult.get("label", "")
        bestCategory = labelMap.get(
            bestLabel,
            "unknown"
        )

        return {
            "event_detail_label": bestCategory,
            "event_detail_conf_score": float(
                bestResult.get("score", 0)
            ),
            "event_detail_scores": {
                category: round(score * 100)
                for category, score
                in categoryScores.items()
            }
        }
    
    def scoreEventDetailKeywords(self,caption: str) -> dict:
        profile = ds.EVENT_PROFILES.get(self.eventType,ds.EVENT_PROFILES["unknown"])

        caption = caption.lower()
        scores = {}

        for category, keywordMap in profile.detail_keywords.items():
            score = 0

            for phrase, points in keywordMap.items():
                if re.search(rf"\b{re.escape(phrase.lower())}\b", caption):
                    score += points

            scores[category] = min(score, 100)

        return scores
    
    def classifyMood(self, img) -> dict:
        eventType = self.eventType.lower().strip()

        profile = ds.EVENT_PROFILES.get(eventType,ds.EVENT_PROFILES["unknown"])

        detailLabelMap = profile.get_detail_label_map()
        moodLabelMap = profile.get_mood_label_map()

        labelMap = {
            **detailLabelMap,
            **moodLabelMap,
        }

        candidateLabels = list(dict.fromkeys(labelMap))

        if not candidateLabels:
            return {
                "label": "unknown",
                "score": 0.0,
                "all_mood_labels": [],
                "all_mood_scores": [],
                "category": "general",
                "category_scores": {},
                "event_detail_label": "unknown",
                "event_detail_conf_score": 0.0,
                "event_detail_scores": {},
            }

        results = self.clipClassify(img,candidate_labels=candidateLabels)

        if not results:
            return {
                "label": "unknown",
                "score": 0.0,
                "all_mood_labels": [],
                "all_mood_scores": [],
                "category": "general",
                "category_scores": {},
                "event_detail_label": "unknown",
                "event_detail_conf_score": 0.0,
                "event_detail_scores": {},
            }

        bestResult = results[0]
        bestLabel = bestResult.get("label", "unknown")
        bestScore = float(bestResult.get("score", 0))

        categoryScores = {}

        for result in results:
            label = result.get("label", "unknown")
            score = float(result.get("score", 0))
            category = labelMap.get(label, "general")

            categoryScores[category] = max(categoryScores.get(category, 0.0),score,)

        bestCategory = labelMap.get(bestLabel, "general")

        detailResults = [
            result for result in results
            if result.get("label") in detailLabelMap
        ]
        bestDetail = detailResults[0] if detailResults else None

        return {
            "label": bestLabel,
            "score": bestScore,
            "all_mood_labels": [
                result.get("label", "unknown")
                for result in results
            ],
            "all_mood_scores": [
                float(result.get("score", 0))
                for result in results
            ],
            "category": bestCategory,
            "category_scores": categoryScores,
            "event_detail_label": (
                detailLabelMap.get(bestDetail.get("label"), "unknown")
                if bestDetail else "unknown"
            ),
            "event_detail_conf_score": (
                float(bestDetail.get("score", 0))
                if bestDetail else 0.0
            ),
            "event_detail_scores": {
                category: round(score * 100)
                for category, score in categoryScores.items()
                if category in profile.detail_labels
            },
        }

    def scorePhotoCategories(self,caption: str) -> dict:
        if not caption:
            caption = ""

        eventType = self.eventType.lower().strip()

        profile = ds.EVENT_PROFILES.get(eventType,ds.EVENT_PROFILES["unknown"])

        text = caption.lower()

        qualityKeywords = {
            "blurry": 50,
            "blurred": 50,
            "out of focus": 60,
            "low quality": 70,
            "too dark": 50,
            "underexposed": 50,
            "overexposed": 50,
            "grainy": 40,
            "bad lighting": 45,
            "poor lighting": 45,
            "random": 50,
            "irrelevant": 60
        }

        nudityKeywords = {
            "nudity": 100,
            "nude": 100,
            "naked": 100,
            "explicit": 100
        }

        categories = {
            **profile.mood_keywords,
            "quality_reject": qualityKeywords,
            "nudity": nudityKeywords
        }

        scores = {}
        matched = {}

        for category, words in categories.items():
            score = 0
            matched[category] = []

            for phrase, points in words.items():
                if re.search(
                    rf"\b{re.escape(phrase.lower())}\b",
                    text
                ):
                    score += points
                    matched[category].append(phrase)

            scores[category] = min(score, 100)

        return {
            "scores": scores,
            "matched_keywords": matched
        }

    def scorePhotoCategories(self,caption: str) -> dict:
        if not caption:
            caption = ""

        eventType = self.eventType.lower().strip()

        profile = ds.EVENT_PROFILES.get(
            eventType,
            ds.EVENT_PROFILES["unknown"]
        )

        text = caption.lower()

        qualityKeywords = {
            "blurry": 50,
            "blurred": 50,
            "out of focus": 60,
            "low quality": 70,
            "too dark": 50,
            "underexposed": 50,
            "overexposed": 50,
            "grainy": 40,
            "bad lighting": 45,
            "poor lighting": 45,
            "random": 50,
            "irrelevant": 60
        }

        nudityKeywords = {
            "nudity": 100,
            "nude": 100,
            "naked": 100,
            "explicit": 100
        }

        categories = {
            **profile.mood_keywords,
            "quality_reject": qualityKeywords,
            "nudity": nudityKeywords
        }

        scores = {}
        matched = {}

        for category, words in categories.items():
            score = 0
            matched[category] = []

            for phrase, points in words.items():
                if re.search(
                    rf"\b{re.escape(phrase.lower())}\b",
                    text
                ):
                    score += points
                    matched[category].append(phrase)

            scores[category] = min(score, 100)

        return {
            "scores": scores,
            "matched_keywords": matched
        }
    
    def analyze(self, photoID: int, photo: str) -> dict | None:

        if photo is None:
            self.log.error(f"No photo supplied for photo_id={photoID}")
            return None

        try:

            img = self.loadImage(photo)

            eventType = self.eventType.lower().strip()

            if eventType not in ds.EVENT_PROFILES:
                self.log.warning(f"Unknown event type {eventType} for photo_id={photoID}. Using 'unknown'.")
                eventType = "unknown"

            # Generate BLIP caption

            caption = self.captionImg(img)

            if caption is None or caption.strip() == "":
                caption = "None"


            eventDetails = self.classifyEventDetails(img)

            if not isinstance(eventDetails, dict):
                self.log.error(f"classifyEventDetails returned {type(eventDetails).__name__}; expected dict for photo_id={photoID}")

                eventDetails = {}

            eventDetailLabel = eventDetails.get("event_detail_label","unknown")

            eventDetailConfScore = float(eventDetails.get("event_detail_conf_score",0.0))

            eventDetailScores = eventDetails.get("event_detail_scores",{})

            if not isinstance(eventDetailScores, dict):
                eventDetailScores = {}

           
            mood = self.classifyMood(img)

            if not isinstance(mood, dict):
                self.log.error(f"classifyMood returned {type(mood).__name__}; expected dict for photo_id={photoID}")      
                return None

            rawClipLabel = mood.get("label","unknown")

            # classifyMood returns the mapped mood in "category"
            moodLabel = mood.get("category","general")

            moodConfScore = float(mood.get("score",0.0))

            allMood = mood.get("all_mood_labels",[rawClipLabel])

            allMoodScore = mood.get("all_mood_scores",[moodConfScore])

            if not isinstance(allMood, list):
                allMood = [str(allMood)]

            if not isinstance(allMoodScore, list):
                allMoodScore = [float(allMoodScore)]

            safetyResult = self.classifySafety(img)

            if not isinstance(safetyResult, dict):
                self.log.error(f"classifySafety returned {type(safetyResult).__name__}; expected dict for photo_id={photoID}")

                safetyResult = {
                    "label": "unknown",
                    "score": 0.0,
                    "all_labels": [],
                    "all_scores": [],
                    "results": []
                }

            safetyLabel = safetyResult.get("label","unknown")

            safetyConfidence = float(safetyResult.get("score",0.0))
   
            categoryResult = self.scorePhotoCategories(caption)

            if not isinstance(categoryResult, dict):
                self.log.error(f"scorePhotoCategories returned {type(categoryResult).__name__}; expected dict for photo_id={photoID}")
                return None

            scores = categoryResult.get("scores",{})

            matchedByCategory = categoryResult.get("matched_keywords",{})

            if not isinstance(scores, dict):
                scores = {}

            if not isinstance(matchedByCategory, dict):
                matchedByCategory = {}

            keywords = []

            for category, matchedWords in matchedByCategory.items():
                if category in {"quality_reject", "nudity"}:
                    continue

                if not isinstance(matchedWords, list):
                    continue

                for word in matchedWords:
                    if word not in keywords:
                        keywords.append(word)

            
            positiveScoreFields = [
                "romantic",
                "professional",
                "friends",
                "family",
                "ceremony",
                "reception",
                "dancing",
                "food_decor",
                "venue_detail",
                "happy",
                "sentimental",
                "energetic",
                "calm",
                "dramatic",
                "nostalgic",
                "funny",
                "general"
            ]

            keywordScore = max([int(scores.get(field, 0))for field in positiveScoreFields],default=0)

            captionQualityRejectScore = int(scores.get("quality_reject",0))

            qualityRejectLabels = {"a blurry low quality photo","a random irrelevant photo"}

            visualQualityReject = (safetyLabel in qualityRejectLabels)

            visualQualityRejectScore = (round(safetyConfidence * 100)
                if visualQualityReject
                else 0
            )

            qualityRejectScore = max(captionQualityRejectScore,visualQualityRejectScore)


            nudityCheck = (safetyLabel == "nudity")

            nudityScore = (round(safetyConfidence * 100)
                if nudityCheck
                else 0
            )

            # Do not assign a positive ranking score to rejected images.
            if (
                nudityCheck
                or visualQualityReject
                or captionQualityRejectScore >= 70
            ):
                keywordScore = 0

            rankingData = ds.ImageRankingData(
                photo_id=photoID,

                caption=caption,
                mood_label=moodLabel,
                mood_conf_score=moodConfScore,
                all_mood_labels=allMood,
                keyword_score=keywordScore,
                keywords=keywords,
                nudity_check=nudityCheck,
                all_mood_scores=allMoodScore,

                event_type=eventType,
                event_type_conf_score=0.0,
                event_detail_label=eventDetailLabel,
                event_detail_conf_score=eventDetailConfScore,
                event_detail_scores=eventDetailScores,

                romantic=int(scores.get("romantic", 0)),
                professional=int(scores.get("professional", 0)),
                friends=int(scores.get("friends", 0)),
                family=int(scores.get("family", 0)),
                ceremony=int(scores.get("ceremony", 0)),
                reception=int(scores.get("reception", 0)),
                dancing=int(scores.get("dancing", 0)),
                food_decor=int(scores.get("food_decor", 0)),
                venue_detail=int(scores.get("venue_detail", 0)),
                happy=int(scores.get("happy", 0)),
                sentimental=int(scores.get("sentimental", 0)),
                energetic=int(scores.get("energetic", 0)),
                calm=int(scores.get("calm", 0)),
                dramatic=int(scores.get("dramatic", 0)),
                nostalgic=int(scores.get("nostalgic", 0)),
                funny=int(scores.get("funny", 0)),
                general=int(scores.get("general", 0)),

                quality_reject=qualityRejectScore,
                nudity=nudityScore,
                matched_keywords=matchedByCategory
            )

            dataDict = rankingData.model_dump()

            if not isinstance(dataDict, dict):
                raise TypeError("ImageRankingData.model_dump() did not return a dictionary")

            return dataDict

        except Exception:
            self.log.exception( f"IMAGE_ANALYSIS_FAILED photo_id={photoID} photo={photo}")
            raise
        
    def batchRunIR(self,media: list[dict],dtype: str = "photo_id"):
        if not media:
            raise ValueError("No files found")
        firstid = media[0].get(dtype)
        self.eventType = str(self.db.getEventTypeFromMedia(firstid, dtype).get('type'))
        

        return ph.batchRun(media,self.analyze,self.db.insertImageRanking,dtype)
    
