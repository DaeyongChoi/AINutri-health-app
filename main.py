# main.py (최종 DB 연동 버전)
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List
import google.generativeai as genai
import PIL.Image
import io
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime

# 1. 구글 클라우드(Firestore) 열쇠 연결
# (secrets.json 파일이 같은 폴더에 있어야 합니다)
cred = credentials.Certificate("secrets.json")

# 이미 연결되어 있지 않다면 연결하기
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client() # 공책(DB) 열기

# 2. AI(Gemini) 설정
# [중요] 여기에 본인의 API 키를 넣어주세요!
genai.configure(api_key="AIzaSyBfTxbOmHDo8Pqq1-o6QLUCam_x9AahbuQ")
model = genai.GenerativeModel('models/gemini-2.5-flash')

app = FastAPI(title="든든 타이거")

class UserProfile(BaseModel):
    nickname: str
    height: float
    weight: float
    goals: List[str]

# --- [인사 및 저장 기능] ---
@app.post("/api/v1/greeting")
async def get_welcome_message(profile: UserProfile):
    # AI 인사말 생성
    prompt = f"시니어 앱 '든든 타이거'로서 {profile.nickname} 어르신(목표: {', '.join(profile.goals)})에게 씩씩한 환영 인사를 3문장 이내로 해줘."
    response = model.generate_content(prompt)
    ai_msg = response.text
    
    # [핵심] Firestore에 저장하기 💾
    doc_ref = db.collection(u'users').document(profile.nickname)
    doc_ref.set({
        u'nickname': profile.nickname,
        u'height': profile.height,
        u'weight': profile.weight,
        u'goals': profile.goals,
        u'last_login': datetime.now(),
        u'last_message': ai_msg
    }, merge=True) # merge=True는 기존 정보가 있으면 덮어쓰기

    print(f"✅ {profile.nickname} 님의 정보가 DB에 저장되었습니다!")
    return {"message": ai_msg}

# --- [식단 분석 기능] ---
@app.post("/api/v1/analyze_food")
async def analyze_food(file: UploadFile = File(...)):
    contents = await file.read()
    image = PIL.Image.open(io.BytesIO(contents))
    
    prompt = "이 음식 사진을 보고 메뉴 이름, 영양소 평가, 시니어를 위한 조언을 씩씩하게 해줘."
    response = model.generate_content([prompt, image])
    
    return {"message": response.text}