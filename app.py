import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import PIL.Image
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json
import os

# 1. 페이지 설정
st.set_page_config(page_title="든든 타이거", page_icon="🐯")

# 2. API 키 설정 (환경변수 사용)
if "GOOGLE_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
else:
    st.error("⚠️ API 키가 없습니다. 구글 클라우드 설정을 확인해주세요.")

# 모델 설정
model = genai.GenerativeModel('models/gemini-2.5-flash')

# 3. 데이터베이스 연결
if not firebase_admin._apps:
    try:
        # 1) 내 컴퓨터: secrets.json 파일 사용
        if os.path.exists("secrets.json"):
            cred = credentials.Certificate("secrets.json")
            firebase_admin.initialize_app(cred)
        # 2) 클라우드: 환경변수 FIREBASE_KEY 사용
        else:
            key_json = os.environ.get("FIREBASE_KEY")
            if key_json:
                cred_dict = json.loads(key_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            else:
                st.warning("⚠️ DB 연결 키를 찾을 수 없습니다.")
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")

try:
    db = firestore.client()
except:
    db = None

# 채팅 기록 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 4. 화면 구성 (UI)
st.title("🐯 든든 타이거 (Cloud 버전)")

tab1, tab2, tab3 = st.tabs(["🐯 인사 나누기", "📸 식단 분석하기", "💬 영양 상담소"])

# --- 탭 1: 인사 및 정보 입력 (BMI 포함) ---
with tab1:
    st.subheader("어르신, 기본 정보를 알려주세요!")
    
    col1, col2 = st.columns(2)
    with col1:
        nickname = st.text_input("닉네임(이름)", "김건강")
        age = st.number_input("나이 (세)", min_value=0, max_value=120, value=65)
    with col2:
        gender = st.selectbox("성별", ["남성", "여성"])
    
    col3, col4 = st.columns(2)
    with col3:
        height = st.number_input("키 (cm)", min_value=0, value=170)
    with col4:
        weight = st.number_input("몸무게 (kg)", min_value=0, value=60)

    # BMI 자동 계산 및 표시
    if height > 0 and weight > 0:
        height_m = height / 100
        bmi = weight / (height_m ** 2)
        
        if bmi < 18.5:
            status = "저체중"
            color = "blue"
        elif bmi < 23:
            status = "정상"
            color = "green"
        elif bmi < 25:
            status = "과체중"
            color = "orange"
        else:
            status = "비만"
            color = "red"
            
        st.info(f"📏 현재 신체 질량 지수(BMI): **{bmi:.1f}** ({status})")
    else:
        bmi = 0
        status = "정보 없음"

    goals = st.multiselect("건강 목표", ["체중 감량", "근육 유지", "활력 증진", "만성질환 관리"], ["활력 증진"])
    
    if st.button("인사 건네기 👋"):
        # AI에게 BMI 정보 전달
        prompt = f"""
        당신은 시니어 헬스케어 앱의 마스코트 '든든 타이거'입니다.
        사용자 정보:
        - 이름: {nickname}
        - 나이: {age}세
        - 성별: {gender}
        - 신체: {height}cm, {weight}kg
        - BMI: {bmi:.1f} ({status} 단계)
        - 목표: {', '.join(goals)}
        
        위 정보를 바탕으로 어르신에게 씩씩하고 다정한 환영 인사를 건네세요.
        특히 BMI 상태({status})를 고려하여, 건강 목표 달성을 위한 짧고 따뜻한 조언을 덧붙여주세요.
        """
        
        with st.spinner("호랑이가 건강 상태를 살피는 중입니다..."):
            try:
                res = model.generate_content(prompt)
                st.success(res.text)
                
                # DB 저장 (모든 정보 기록)
                if db:
                    doc_ref = db.collection(u'users').document(nickname)
                    doc_ref.set({
                        u'nickname': nickname,
                        u'age': age,
                        u'gender': gender,
                        u'height': height,
                        u'weight': weight,
                        u'bmi': bmi,
                        u'goals': goals,
                        u'last_login': datetime.now(),
                        u'last_message': res.text
                    }, merge=True)
                    st.caption("✅ 내 정보(BMI 포함)가 클라우드에 안전하게 기록되었습니다.")
            except Exception as e:
                st.error(f"에러가 발생했습니다: {e}")

# --- 탭 2: 식단 분석 (전문가 프롬프트) ---
with tab2:
    st.subheader("오늘 드신 음식을 보여주세요")
    uploaded_file = st.file_uploader("사진 업로드", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        st.image(uploaded_file, width=300)
        if st.button("전문가 분석 요청 🥗"):
            with st.spinner("세계 최고의 임상영양사가 분석 중입니다..."):
                try:
                    img = PIL.Image.open(uploaded_file)
                    
                    # 안전 필터 해제
                    safety_settings = {
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                    
                    system_prompt = """
                    # ROLE
                    당신은 세계 최고의 영양학자이자 노인 영양학(Geriatric Nutrition)을 전공한 30년 경력의 임상영양사 '든든 타이거'입니다.
                    
                    # TASK
                    음식 사진을 분석하여 전문적이면서도 어르신이 이해하기 쉬운 맞춤형 식단 조언을 제공하십시오.
                    
                    # OUTPUT FORMAT
                    ## 🍱 음식 이름: [음식명]
                    ## 📊 영양 성분 추정 (1인분 기준)
                    - 칼로리 및 주요 영양소
                    
                    ## 🩺 임상영양사 타이거의 정밀 분석
                    [건강 관점 상세 분석]
                    
                    ## 💡 더 건강하게 드시는 꿀팁
                    [구체적 조언]
                    """
                    
                    res = model.generate_content([system_prompt, img], safety_settings=safety_settings)
                    st.info(res.text)
                    
                    # 분석 결과를 채팅 기록에 추가 (상담 연동)
                    st.session_state.chat_history.append({"role": "model", "text": f"식단 분석 결과:\n{res.text}"})

                except Exception as e:
                    st.error(f"앗! 오류가 발생했습니다: {e}")

# --- 탭 3: 영양 상담소 (챗봇) ---
with tab3:
    st.subheader("💬 무엇이든 물어보세요")
    st.caption("방금 분석한 식단에 대해 물어보거나, 평소 궁금한 건강 상식을 물어보세요!")

    # 대화 기록 표시
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])

    # 사용자 입력
    if prompt := st.chat_input("예: 고혈압이 있는데 국물 마셔도 되나요?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "text": prompt})

        with st.chat_message("model"):
            with st.spinner("호랑이 영양사가 답변을 준비 중입니다..."):
                try:
                    # 채팅용 페르소나
                    chat_system_prompt = f"""
                    당신은 30년 경력의 세계 최고 임상영양사 '든든 타이거'입니다.
                    사용자({nickname} 어르신)와 대화하고 있습니다.
                    
                    [지침]
                    1. 항상 전문적이지만, 손주처럼 친절하고 예의 바른 말투(해요체)를 사용하세요.
                    2. 어려운 의학 용어 대신 쉬운 비유를 사용하세요.
                    3. 질문에 명확한 답변을 주고, 실천 가능한 건강 팁을 하나씩 덧붙이세요.
                    4. 이전 대화 내용을 기억하고 연결해서 답변하세요.
                    """
                    
                    # 전체 대화 맥락 구성
                    full_prompt = chat_system_prompt + "\n\n[이전 대화]\n"
                    for msg in st.session_state.chat_history:
                        speaker = "어르신" if msg["role"] == "user" else "든든 타이거"
                        full_prompt += f"{speaker}: {msg['text']}\n"
                    
                    full_prompt += f"\n든든 타이거(답변):"
                    
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "model", "text": response.text})
                    
                except Exception as e:
                    st.error(f"답변 중 오류가 났어요: {e}")