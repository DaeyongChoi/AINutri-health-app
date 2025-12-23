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

# 모델 설정 (Gemini 3 Flash 적용)
try:
    model = genai.GenerativeModel('gemini-3-flash-preview')
except:
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
    # 기본값 설정
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
    carbs = int((tdee * 0.55) / 4)
    protein = int((tdee * 0.20) / 4)
    fat = int((tdee * 0.25) / 9)
    return {
        "calories": tdee, "carbs": carbs, "protein": protein, "fat": fat,
        "sugar": 50, "sodium": 2000, "cholesterol": 300, "calcium": 700
    }

# --- 헬퍼 함수: 데이터 로드 (핵심 기능!) ---
def load_user_data(nickname):
    if not db or not nickname: return False
    
    doc_ref = db.collection(u'users').document(nickname)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        # 저장된 정보 불러오기
        if 'info' in data:
            st.session_state.user_info = data['info']
        if 'needs' in data:
            st.session_state.needs = data['needs']
        # 목표 같은 것도 불러오면 좋음 (여기선 생략하거나 추가 가능)
        return True
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
st.title("🐯 든든 타이거 (이어하기 기능 탑재)")

tab1, tab2, tab3, tab4 = st.tabs(["🐯 인사 나누기", "📸 식단 기록/분석", "📊 건강 보고서", "💬 영양 상담소"])

# ---------------------------------------------------------
# [탭 1] 인사 및 정보 입력 (안전장치 추가 버전)
# ---------------------------------------------------------
with tab1:
    st.subheader("어르신, 성함(닉네임)을 알려주세요")
    
    col_nick, col_btn = st.columns([3, 1])
    with col_nick:
        # 불러오기용 입력창
        input_nickname = st.text_input("닉네임 입력 후 엔터 ↵", st.session_state.user_info.get("nickname", ""))
    with col_btn:
        if st.button("내 정보 불러오기 📂"):
            if load_user_data(input_nickname):
                st.success(f"✅ {input_nickname}님의 정보를 불러왔습니다!")
                st.rerun() # 화면 새로고침하여 데이터 반영
            else:
                st.warning("등록된 정보가 없습니다.")

    st.divider()
    st.subheader("📝 상세 정보 수정")
    
    col1, col2 = st.columns(2)
    with col1:
        # [수정 1] 불러온 세션 정보(user_info)를 value에 직접 연결하여 빈 값 방지
        current_nick = st.session_state.user_info.get("nickname", "")
        # 만약 세션에 없으면 위에서 입력한 값이라도 가져옴
        if not current_nick:
            current_nick = input_nickname
            
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

    # 세션 상태 갱신
    st.session_state.user_info = {"nickname": nickname, "age": age, "gender": gender, "height": height, "weight": weight}

    if height > 0 and weight > 0:
        height_m = height / 100
        bmi = weight / (height_m ** 2)
        needs = calculate_needs(age, gender, height, weight)
        st.session_state.needs = needs
        
        if bmi < 18.5: status = "저체중"
        elif bmi < 23: status = "정상"
        elif bmi < 25: status = "과체중"
        else: status = "비만"
        
        st.info(f"📏 BMI: **{bmi:.1f}** ({status}) | 💪 하루 권장 칼로리: **{needs['calories']} kcal**")
    else:
        bmi, status = 0, "정보 없음"
        needs = calculate_needs(65, "남성", 170, 60)

    goals = st.multiselect("건강 목표", ["체중 감량", "근육 유지", "혈당 관리", "혈압 관리", "뼈 건강"], ["혈당 관리"])
    
    if st.button("설정 저장 및 인사 👋"):
        # [수정 2] 핵심 안전장치: 닉네임이 비어있으면 절대 DB로 넘어가지 않음
        if not nickname or nickname.strip() == "":
            st.error("⚠️ 닉네임이 비어있습니다! 위 칸에 닉네임을 입력해주세요.")
        else:
            prompt = f"""
            당신은 시니어 헬스케어 마스코트 '든든 타이거'입니다.
            사용자: {nickname}, {age}세, {gender}, BMI {bmi:.1f}({status}).
            목표: {', '.join(goals)}.
            어서오세요 인사를 해주세요.
            """
            try:
                res = model.generate_content(prompt)
                st.success(res.text)
                
                if db:
                    # 이제 nickname이 확실히 있으므로 에러가 나지 않습니다.
                    db.collection(u'users').document(nickname).set({
                        u'info': st.session_state.user_info,
                        u'needs': needs,
                        u'goals': goals,
                        u'last_login': datetime.now()
                    }, merge=True)
                    st.caption("✅ 정보가 안전하게 저장되었습니다.")
            except Exception as e:
                st.error(f"오류 발생: {e}")

# ---------------------------------------------------------
# [탭 2] 식단 기록 및 분석
# ---------------------------------------------------------
with tab2:
    st.subheader("📸 식사를 기록하고 분석해요")
    
    # 로그인 체크
    if not st.session_state.user_info["nickname"]:
        st.warning("먼저 [인사 나누기] 탭에서 닉네임을 입력해주세요!")
    else:
        col_date, col_meal = st.columns(2)
        with col_date:
            record_date = st.date_input("식사 날짜", datetime.now())
        with col_meal:
            meal_type = st.selectbox("어떤 식사인가요?", ["아침", "점심", "저녁", "간식"])

        uploaded_file = st.file_uploader("음식 사진 업로드", type=["jpg", "png", "jpeg"])
        
        if uploaded_file:
            st.image(uploaded_file, width=300)
            
            if st.button("Gemini 3 정밀 분석 ⚡"):
                with st.spinner("호랑이가 분석 중입니다..."):
                    try:
                        img = PIL.Image.open(uploaded_file)
                        safety_settings = {HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE}
                        
                        system_prompt = f"""
                        당신은 임상영양사 '든든 타이거'입니다. JSON 응답 필수.
                        {{
                            "food_name": "음식명", "calories": 0, "carbs": 0, "protein": 0, "fat": 0, 
                            "sugar": 0, "sodium": 0, "cholesterol": 0, "calcium": 0,
                            "vitamin_info": "비타민 정보", "analysis": "분석내용", "tips": "팁"
                        }}
                        """
                        res = model.generate_content([system_prompt, img], safety_settings=safety_settings)
                        data = parse_ai_json(res.text)
                        
                        if data:
                            st.divider()
                            st.markdown(f"### 🍱 {data['food_name']}")
                            c1, c2, c3 = st.columns(3)
                            c1.metric("칼로리", f"{data['calories']} kcal")
                            c2.metric("나트륨", f"{data['sodium']} mg")
                            c3.metric("당류", f"{data['sugar']} g")
                            st.info(data['vitamin_info'])
                            st.success(data['tips'])
                            
                            # 채팅 기록에 추가
                            chat_summary = f"[식단 분석 결과] 메뉴: {data['food_name']}, 칼로리: {data['calories']}kcal, 조언: {data['tips']}"
                            st.session_state.chat_history.append({"role": "model", "text": chat_summary})
                            
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
                                st.toast("저장 완료!", icon="✅")
                        else:
                            st.error("분석 실패")
                    except Exception as e:
                        st.error(f"오류: {e}")

# ---------------------------------------------------------
# [탭 3] 건강 보고서
# ---------------------------------------------------------
with tab3:
    st.subheader("📊 호랑이 정밀 건강 보고서")
    
    if not st.session_state.user_info["nickname"]:
        st.warning("먼저 닉네임을 입력하고 정보를 불러오세요.")
    elif db:
        report_type = st.radio("종류", ["일간 분석", "기간별 추이"], horizontal=True)
        docs_ref = db.collection('users').document(st.session_state.user_info["nickname"]).collection('diet_logs')
        my_needs = st.session_state.needs if st.session_state.needs else calculate_needs(65, "남성", 170, 60)

        if report_type == "일간 분석":
            report_date = st.date_input("날짜", datetime.now(), key="report_date")
            date_str = report_date.strftime("%Y-%m-%d")
            query = docs_ref.where("date", "==", date_str).stream()
            daily_logs = [doc.to_dict() for doc in query]
            
            if daily_logs:
                df = pd.DataFrame(daily_logs)
                
                # 1. 탄단지당 (g)
                chart_data_g = pd.DataFrame({
                    "영양소": ["탄수화물", "탄수화물", "단백질", "단백질", "지방", "지방", "당류", "당류"],
                    "구분": ["섭취량", "권장량"] * 4,
                    "값(g)": [df['carbs'].sum(), my_needs['carbs'], df['protein'].sum(), my_needs['protein'], 
                              df['fat'].sum(), my_needs['fat'], df.get('sugar', 0).sum(), my_needs['sugar']]
                })
                st.altair_chart(alt.Chart(chart_data_g).mark_bar().encode(x='값(g)', y='영양소', color='구분'), use_container_width=True)

                # 2. 나트륨 등 (mg)
                chart_data_mg = pd.DataFrame({
                    "영양소": ["나트륨", "나트륨", "콜레스테롤", "콜레스테롤", "칼슘", "칼슘"],
                    "구분": ["섭취량", "상한선"] * 2 + ["섭취량", "권장량"],
                    "값(mg)": [df.get('sodium', 0).sum(), my_needs['sodium'], df.get('cholesterol', 0).sum(), my_needs['cholesterol'], df.get('calcium', 0).sum(), my_needs['calcium']]
                })
                st.altair_chart(alt.Chart(chart_data_mg).mark_bar().encode(x='값(mg)', y='영양소', color='구분'), use_container_width=True)
                
                st.dataframe(df[['meal_type', 'food_name', 'calories', 'sodium']])
            else:
                st.info("해당 날짜의 기록이 없습니다.")

        else: # 기간별
            # 간단하게 최근 100개 가져와서 필터링 (쿼리 효율화)
            all_logs = docs_ref.order_by("date", direction=firestore.Query.DESCENDING).limit(50).stream()
            data_list = [d.to_dict() for d in all_logs]
            
            if data_list:
                df_period = pd.DataFrame(data_list)
                df_period['date'] = pd.to_datetime(df_period['date']) # 날짜 형식 변환
                daily_stats = df_period.groupby('date')[['sodium', 'sugar']].sum().reset_index()
                
                st.line_chart(daily_stats, x='date', y=['sodium', 'sugar'])
            else:
                st.info("기록이 없습니다.")

# ---------------------------------------------------------
# [탭 4] 영양 상담소
# ---------------------------------------------------------
with tab4:
    st.subheader(f"💬 {st.session_state.user_info['nickname']}님의 전담 상담소")
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])

    if prompt := st.chat_input("질문 입력"):
        st.chat_message("user").markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "text": prompt})

        with st.chat_message("model"):
            with st.spinner("생각 중..."):
                try:
                    full_prompt = f"당신은 영양사 든든타이거입니다. 사용자: {st.session_state.user_info['nickname']}.\n\n[이전 대화]\n" + \
                                  "\n".join([f"{m['role']}: {m['text']}" for m in st.session_state.chat_history]) + \
                                  f"\n사용자: {prompt}\n답변:"
                    
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "model", "text": response.text})
                except Exception as e:
                    st.error(f"오류: {e}")