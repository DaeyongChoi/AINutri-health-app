import streamlit as st
import google.generativeai as genai
import PIL.Image
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json
import os

# 1. 페이지 설정
st.set_page_config(page_title="든든 타이거", page_icon="🐯")

# 2. [중요] API 키 설정 (여기에 본인 키를 넣어주세요!)
API_KEY = "AIzaSyBfTxbOmHDo8Pqq1-o6QLUCam_x9AahbuQ"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# 3. 데이터베이스 연결 (똑똑한 연결 방식)
if not firebase_admin._apps:
    try:
        # 1) 내 컴퓨터: secrets.json 파일이 있으면 그걸 쓴다
        if os.path.exists("secrets.json"):
            cred = credentials.Certificate("secrets.json")
            firebase_admin.initialize_app(cred)
        # 2) 클라우드: 파일이 없으면 '환경변수'에 있는 암호를 쓴다
        else:
            # 환경변수에서 키 꺼내기 (문자열 -> 딕셔너리 변환)
            key_json = os.environ.get("FIREBASE_KEY")
            if key_json:
                cred_dict = json.loads(key_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            else:
                st.warning("⚠️ DB 연결 키를 찾을 수 없습니다.")
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")

# DB 클라이언트 가져오기 (연결 성공 시)
try:
    db = firestore.client()
except:
    db = None

# 4. 화면 구성 (UI)
st.title("🐯 든든 타이거 (Cloud 버전)")

tab1, tab2 = st.tabs(["🐯 인사 나누기", "📸 식단 분석하기"])

with tab1:
    st.subheader("어르신, 반갑습니다!")
    nickname = st.text_input("닉네임(이름)", "김건강")
    goals = st.multiselect("건강 목표", ["체중 감량", "근육", "활력"], ["활력"])
    
    if st.button("인사 건네기 👋"):
        # AI에게 질문
        prompt = f"시니어 앱 마스코트로서 {nickname} 어르신(목표: {', '.join(goals)})에게 씩씩한 환영 인사를 해줘."
        res = model.generate_content(prompt)
        st.success(res.text)
        
        # DB 저장
        if db:
            db.collection(u'users').document(nickname).set({
                u'nickname': nickname,
                u'goals': goals,
                u'last_login': datetime.now(),
                u'last_message': res.text
            }, merge=True)
            st.caption("✅ 내 정보가 클라우드에 안전하게 기록되었습니다.")

with tab2:
    st.subheader("오늘 드신 음식을 보여주세요")
    uploaded_file = st.file_uploader("사진 업로드", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        st.image(uploaded_file, width=300)
        if st.button("영양소 분석해줘! 🥗"):
            with st.spinner("호랑이가 분석 중입니다..."):
                img = PIL.Image.open(uploaded_file)
                prompt = "이 음식의 이름과 영양소를 분석하고, 시니어를 위한 조언을 해줘."
                res = model.generate_content([prompt, img])
                st.info(res.text)