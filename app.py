import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import PIL.Image
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import json
import os
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="든든 타이거", page_icon="🐯", layout="wide")

# 2. API 키 설정
if "GOOGLE_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
else:
    st.error("⚠️ API 키가 없습니다. 구글 클라우드 설정을 확인해주세요.")

# ---------------------------------------------------------
# [핵심] 최짱님이 원하시는 'Gemini 3.0 Flash Preview' 적용
# ---------------------------------------------------------
try:
    model = genai.GenerativeModel('gemini-3-flash-preview')
except Exception as e:
    st.error(f"모델 설정 오류: {e}")
    # 만약 3.0이 일시적 오류라면 비상용으로 1.5를 쓰도록 예외처리 (혹시 몰라서)
    model = genai.GenerativeModel('gemini-1.5-flash')

# 3. 데이터베이스 연결
if not firebase_admin._apps:
    try:
        if os.path.exists("secrets.json"):
            cred = credentials.Certificate("secrets.json")
            firebase_admin.initialize_app(cred)
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

# --- 세션 상태 초기화 ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_info" not in st.session_state:
    st.session_state.user_info = {"nickname": "", "age": 65, "gender": "남성", "height": 170, "weight": 60}
if "needs" not in st.session_state:
    st.session_state.needs = {}

# --- 헬퍼 함수: 권장 섭취량 계산 ---
def calculate_needs(age, gender, height, weight):
    if gender == "남성":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    tdee = int(bmr * 1.2)
    return {
        "calories": tdee,
        "carbs": int((tdee * 0.55) / 4),
        "protein": int((tdee * 0.20) / 4),
        "fat": int((tdee * 0.25) / 9),
        "sugar": 50, "sodium": 2000, "cholesterol": 300, "calcium": 700
    }

# --- 헬퍼 함수: 데이터 로드 (불러오기) ---
def load_user_data(nickname):
    if not db or not nickname: return False
    try:
        doc_ref = db.collection(u'users').document(nickname)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            if 'info' in data: st.session_state.user_info = data['info']
            if 'needs' in data: st.session_state.needs = data['needs']
            return True
    except:
        return False
    return False

# --- 헬퍼 함수: JSON 파싱 ---
def parse_ai_json(text):
    try:
        cleaned_text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_text)
    except:
        return None

# =========================================================
# 4. 화면 구성 (UI)
# =========================================================
st.title("🐯 든든 타이거 (Gemini 3.0 Powered)")

tab1, tab2, tab3, tab4 = st.tabs(["🐯 인사 나누기", "📸 식단 기록/분석", "📊 건강 보고서", "💬 영양 상담소"])

# ---------------------------------------------------------
# [탭 1] 인사 및 정보 입력 (400 에러 해결 버전)
# ---------------------------------------------------------
with tab1:
    st.subheader("어르신, 성함(닉네임)을 알려주세요")
    
    col_nick, col_btn = st.columns([3, 1])
    with col_nick:
        input_nickname = st.text_input("닉네임 입력 후 엔터 ↵", st.session_state.user_info.get("nickname", ""))
    with col_btn:
        if st.button("내 정보 불러오기 📂"):
            if load_user_data(input_nickname):
                st.success(f"✅ {input_nickname}님의 정보를 불러왔습니다!")
                st.rerun()
            else:
                st.warning("등록된 정보가 없습니다.")

    st.divider()
    
    # [안전장치] 닉네임 동기화
    current_nick = st.session_state.user_info.get("nickname", "")
    if not current_nick: current_nick = input_nickname
    
    col1, col2 = st.columns(2)
    with col1:
        nickname = st.text_input("닉네임(확인)", value=current_nick, key="nick_confirm")
        age = st.number_input("나이 (세)", 0, 120, st.session_state.user_info["age"])
    with col2:
        gender_index = 0 if st.session_state.user_info["gender"] == "남성" else 1
        gender = st.selectbox("성별", ["남성", "여성"], index=gender_index)
    
    col3, col4 = st.columns(2)
    with col3:
        height = st.number_input("키 (cm)", 0, 250, st.session_state.user_info["height"])
    with col4:
        weight = st.number_input("몸무게 (kg)", 0, 200, st.session_state.user_info["weight"])

    st.session_state.user_info = {"nickname": nickname, "age": age, "gender": gender, "height": height, "weight": weight}
    
    if height > 0 and weight > 0:
        height_m = height / 100
        bmi = weight / (height_m ** 2)
        needs = calculate_needs(age, gender, height, weight)
        st.session_state.needs = needs
        status = "정상" # 간략화
        st.info(f"📏 BMI: **{bmi:.1f}** | 💪 하루 권장 칼로리: **{needs['calories']} kcal**")
    else:
        needs = calculate_needs(65, "남성", 170, 60)

    goals = st.multiselect("건강 목표", ["체중 감량", "근육 유지", "혈당 관리", "혈압 관리", "뼈 건강"], ["혈당 관리"])
    
    if st.button("설정 저장 및 인사 👋"):
        # [핵심] 400 에러 방지용 체크
        if not nickname.strip():
            st.error("⚠️ 닉네임이 비어있습니다! 닉네임을 입력해주세요.")
        else:
            prompt = f"당신은 영양사입니다. {nickname}님({age}세)에게 환영 인사를 하세요."
            try:
                res = model.generate_content(prompt)
                st.success(res.text)
                if db:
                    db.collection(u'users').document(nickname).set({
                        u'info': st.session_state.user_info,
                        u'needs': needs,
                        u'goals': goals,
                        u'last_login': datetime.now()
                    }, merge=True)
                    st.caption("✅ 저장 완료")
            except Exception as e:
                st.error(f"오류: {e}")

# ---------------------------------------------------------
# [탭 2] 식단 기록 (Gemini 3.0 활용)
# ---------------------------------------------------------
with tab2:
    st.subheader("📸 식사를 기록하고 분석해요")
    
    if not st.session_state.user_info["nickname"]:
        st.warning("먼저 [인사 나누기] 탭에서 닉네임을 설정해주세요.")
    else:
        col_date, col_meal = st.columns(2)
        with col_date:
            record_date = st.date_input("식사 날짜", datetime.now())
        with col_meal:
            meal_type = st.selectbox("어떤 식사인가요?", ["아침", "점심", "저녁", "간식"])

        uploaded_file = st.file_uploader("음식 사진 업로드", type=["jpg", "png", "jpeg"])
        
        if uploaded_file:
            st.image(uploaded_file, width=300)
            
            if st.button("Gemini 3.0 정밀 분석 ⚡"):
                with st.spinner("슈퍼 호랑이가 분석 중입니다..."):
                    try:
                        img = PIL.Image.open(uploaded_file)
                        
                        system_prompt = f"""
                        당신은 시니어 전문 임상영양사 '든든 타이거'입니다.
                        사진 속 음식을 정밀 분석하여 아래 JSON 포맷으로 응답하세요.
                        
                        {{
                            "food_name": "음식 이름",
                            "calories": 000,
                            "carbs": 00, "protein": 00, "fat": 00, 
                            "sugar": 00, "sodium": 000, "cholesterol": 000, "calcium": 000,
                            "vitamin_info": "비타민/무기질 정보 (한 줄 요약)",
                            "analysis": "영양 평가",
                            "tips": "건강 섭취 조언"
                        }}
                        """
                        res = model.generate_content([system_prompt, img])
                        data = parse_ai_json(res.text)
                        
                        if data:
                            st.divider()
                            st.markdown(f"### 🍱 {data['food_name']}")
                            c1, c2, c3 = st.columns(3)
                            c1.metric("칼로리", f"{data['calories']} kcal")
                            c2.metric("나트륨", f"{data['sodium']} mg")
                            c3.metric("당류", f"{data['sugar']} g")
                            st.info(f"💊 {data['vitamin_info']}")
                            st.success(f"💡 {data['tips']}")
                            
                            # 상담 내역에 자동 추가
                            log_text = f"[식단 기록] {data['food_name']} ({data['calories']}kcal). 나트륨:{data['sodium']}mg, 당류:{data['sugar']}g. 조언:{data['tips']}"
                            st.session_state.chat_history.append({"role": "model", "text": log_text})

                            # DB 저장
                            if db:
                                log_data = {
                                    "date": record_date.strftime("%Y-%m-%d"),
                                    "datetime": datetime.combine(record_date, datetime.now().time()),
                                    "meal_type": meal_type,
                                    "food_name": data['food_name'],
                                    "calories": data['calories'], "carbs": data['carbs'], "protein": data['protein'], "fat": data['fat'],
                                    "sugar": data.get('sugar', 0), "sodium": data.get('sodium', 0),
                                    "cholesterol": data.get('cholesterol', 0), "calcium": data.get('calcium', 0),
                                    "vitamin_info": data.get('vitamin_info', ''),
                                    "timestamp": datetime.now()
                                }
                                db.collection('users').document(st.session_state.user_info["nickname"]).collection('diet_logs').add(log_data)
                                st.toast("기록되었습니다!", icon="✅")
                        else:
                            st.error("분석 실패 (AI 응답 오류)")
                    except Exception as e:
                        st.error(f"오류: {e}")

# ---------------------------------------------------------
# [탭 3] 건강 보고서
# ---------------------------------------------------------
with tab3:
    st.subheader("📊 호랑이 정밀 건강 보고서")
    
    if not st.session_state.user_info["nickname"]:
        st.info("닉네임을 설정하면 보고서가 보입니다.")
    elif db:
        report_type = st.radio("종류", ["일간 분석", "최근 추이"], horizontal=True)
        docs_ref = db.collection('users').document(st.session_state.user_info["nickname"]).collection('diet_logs')
        my_needs = st.session_state.needs if st.session_state.needs else calculate_needs(65, "남성", 170, 60)

        if report_type == "일간 분석":
            report_date = st.date_input("날짜 선택", datetime.now())
            date_str = report_date.strftime("%Y-%m-%d")
            daily_logs = [doc.to_dict() for doc in docs_ref.where("date", "==", date_str).stream()]
            
            if daily_logs:
                df = pd.DataFrame(daily_logs)
                st.markdown("#### 1️⃣ 영양소 섭취량 (g)")
                chart_data_g = pd.DataFrame({
                    "영양소": ["탄수화물", "탄수화물", "단백질", "단백질", "지방", "지방", "당류", "당류"],
                    "구분": ["섭취량", "권장량"] * 4,
                    "값(g)": [df['carbs'].sum(), my_needs['carbs'], df['protein'].sum(), my_needs['protein'], df['fat'].sum(), my_needs['fat'], df.get('sugar', pd.Series([0])).sum(), my_needs['sugar']]
                })
                st.altair_chart(alt.Chart(chart_data_g).mark_bar().encode(x='값(g)', y='영양소', color='구분'), use_container_width=True)
                
                st.markdown("#### 2️⃣ 관리 지표 (mg)")
                chart_data_mg = pd.DataFrame({
                    "영양소": ["나트륨", "나트륨", "콜레스테롤", "콜레스테롤"],
                    "구분": ["섭취량", "상한선"] * 2,
                    "값(mg)": [df.get('sodium', pd.Series([0])).sum(), my_needs['sodium'], df.get('cholesterol', pd.Series([0])).sum(), my_needs['cholesterol']]
                })
                st.altair_chart(alt.Chart(chart_data_mg).mark_bar().encode(x='값(mg)', y='영양소', color='구분'), use_container_width=True)
            else:
                st.info("기록이 없습니다.")
        else:
            all_logs = docs_ref.order_by("date", direction=firestore.Query.DESCENDING).limit(50).stream()
            data_list = [d.to_dict() for d in all_logs]
            if data_list:
                df_period = pd.DataFrame(data_list)
                stats = df_period.groupby('date')[['sodium', 'sugar']].sum().reset_index()
                st.line_chart(stats, x='date', y=['sodium', 'sugar'])
            else:
                st.info("데이터가 없습니다.")

# ---------------------------------------------------------
# [탭 4] 영양 상담소 (Gemini 3.0 맞춤형 프롬프트 강화)
# ---------------------------------------------------------
with tab4:
    st.subheader(f"💬 {st.session_state.user_info.get('nickname', '어르신')}님의 전담 상담소")
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])

    if prompt := st.chat_input("예: 방금 먹은 음식 영양소 괜찮아?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "text": prompt})

        with st.chat_message("model"):
            with st.spinner("호랑이가 생각 중입니다..."):
                try:
                    # [상담 강화] 3.0 모델이 잘 알아듣도록 명확한 페르소나와 정보를 줍니다.
                    info = st.session_state.user_info
                    needs = st.session_state.needs
                    
                    full_system_prompt = f"""
                    [시스템 설정]
                    당신은 대학병원 임상영양사 '든든 타이거'입니다.
                    사용자 정보: {info.get('nickname')} ({info.get('age')}세/{info.get('gender')})
                    건강 목표: {needs.get('sodium', 2000)}mg 미만 나트륨 섭취, 혈당 관리.
                    
                    [지시사항]
                    1. 사용자의 질문에 대해 '영양학적 근거'를 바탕으로 답변하세요.
                    2. 말투는 따뜻하고 정중한 존댓말(해요체)을 쓰세요.
                    3. 이전 대화에 식단 기록이 있다면, 그 음식의 영양 성분을 언급하며 구체적으로 조언하세요.
                    4. 너무 길지 않게 핵심만 답변하세요.
                    """
                    
                    # 대화 기록 누적
                    history_text = "\n".join([f"{m['role']}: {m['text']}" for m in st.session_state.chat_history])
                    final_input = f"{full_system_prompt}\n\n[대화 내용]\n{history_text}\n\n사용자: {prompt}\n답변:"
                    
                    response = model.generate_content(final_input)
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "model", "text": response.text})
                    
                except Exception as e:
                    st.error(f"응답 오류: {e}")