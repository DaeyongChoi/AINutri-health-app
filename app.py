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

# 모델 설정
# model = genai.GenerativeModel('models/gemini-2.5-flash')

# 모델 설정 (2025년 12월 17일 출시된 최신상 모델!)
# PhD급 추론 능력을 가진 초고속 모델입니다.
model = genai.GenerativeModel('models/gemini-3-flash-preview')

# [추가할 코드] 사이드바에 모델 이름 표시하기
with st.sidebar:
    st.header("🔧 개발자 모드")
    # model.model_name 변수에 현재 설정된 모델 이름이 들어있습니다.
    st.info(f"🚀 현재 모델: **{model.model_name}**")

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

# 채팅 기록 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 헬퍼 함수: 권장 섭취량 계산 (상세 영양소 포함) ---
def calculate_needs(age, gender, height, weight):
    # 기초대사량(BMR) & 활동대사량(TDEE)
    if gender == "남성":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    tdee = int(bmr * 1.2)
    
    # [주요 영양소]
    carbs = int((tdee * 0.55) / 4)
    protein = int((tdee * 0.20) / 4)
    fat = int((tdee * 0.25) / 9)
    
    # [추가 영양소 권장 상한선/목표량 (한국인 영양소 섭취기준 - 시니어 참조)]
    # 나트륨: 2000mg 이하 (혈압 관리)
    # 당류: 50g 미만 (전체 에너지의 10~20% 제한)
    # 콜레스테롤: 300mg 이하
    # 칼슘: 700mg (골다공증 예방)
    
    return {
        "calories": tdee,
        "carbs": carbs,
        "protein": protein,
        "fat": fat,
        "sugar": 50,       # g
        "sodium": 2000,    # mg
        "cholesterol": 300,# mg
        "calcium": 700     # mg
    }

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
st.title("🐯 든든 타이거 (Cloud 정밀 분석)")

tab1, tab2, tab3, tab4 = st.tabs(["🐯 인사 나누기", "📸 식단 기록/분석", "📊 건강 보고서", "💬 영양 상담소"])

# 전역 변수 초기화
if 'user_info' not in st.session_state:
    st.session_state.user_info = {"nickname": "김건강", "age": 65, "gender": "남성", "height": 170, "weight": 60}

# ---------------------------------------------------------
# [탭 1] 인사 및 정보 입력
# ---------------------------------------------------------
with tab1:
    st.subheader("어르신, 기본 정보를 알려주세요!")
    
    col1, col2 = st.columns(2)
    with col1:
        nickname = st.text_input("닉네임(이름)", st.session_state.user_info["nickname"])
        age = st.number_input("나이 (세)", 0, 120, st.session_state.user_info["age"])
    with col2:
        gender = st.selectbox("성별", ["남성", "여성"], index=0 if st.session_state.user_info["gender"]=="남성" else 1)
    
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
        
        if bmi < 18.5: status, color = "저체중", "blue"
        elif bmi < 23: status, color = "정상", "green"
        elif bmi < 25: status, color = "과체중", "orange"
        else: status, color = "비만", "red"
            
        st.info(f"📏 BMI: **{bmi:.1f}** ({status}) | 💪 하루 권장 칼로리: **{needs['calories']} kcal**")
        with st.expander("👀 상세 권장 섭취량 보기"):
            st.write(f"- 탄수화물: {needs['carbs']}g / 단백질: {needs['protein']}g / 지방: {needs['fat']}g")
            st.write(f"- 당류: {needs['sugar']}g 이하 / 나트륨: {needs['sodium']}mg 이하")
            st.write(f"- 콜레스테롤: {needs['cholesterol']}mg 이하 / 칼슘: {needs['calcium']}mg 권장")
    else:
        bmi = 0
        status = "정보 없음"
        needs = calculate_needs(65, "남성", 170, 60) # 기본값

    goals = st.multiselect("건강 목표", ["체중 감량", "근육 유지", "혈당 관리", "혈압 관리", "뼈 건강"], ["혈당 관리"])
    
    if st.button("설정 저장 및 인사 👋"):
        prompt = f"""
        당신은 시니어 헬스케어 마스코트 '든든 타이거'입니다.
        사용자: {nickname}, {age}세, {gender}, BMI {bmi:.1f}({status}).
        목표: {', '.join(goals)}.
        
        환영 인사와 함께, 사용자의 목표에 맞춰 특히 주의해야 할 영양소(예: 혈압이면 나트륨 등)를 언급하며 격려해주세요.
        """
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
                st.caption("✅ 사용자 정보 업데이트 완료")
        except Exception as e:
            st.error(f"오류: {e}")

# ---------------------------------------------------------
# [탭 2] 식단 기록 및 분석 (정밀 분석 프롬프트)
# ---------------------------------------------------------
with tab2:
    st.subheader("📸 식사를 기록하고 분석해요")
    
    col_date, col_meal = st.columns(2)
    with col_date:
        record_date = st.date_input("식사 날짜", datetime.now())
    with col_meal:
        meal_type = st.selectbox("어떤 식사인가요?", ["아침", "점심", "저녁", "간식"])

    uploaded_file = st.file_uploader("음식 사진 업로드", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        st.image(uploaded_file, width=300)
        
        if st.button("정밀 분석 및 저장 💾"):
            with st.spinner("나트륨, 당류, 비타민까지 꼼꼼히 분석 중입니다..."):
                try:
                    img = PIL.Image.open(uploaded_file)
                    safety_settings = {HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE}
                    
                    # [핵심] 추가 영양소 요청 프롬프트
                    system_prompt = f"""
                    당신은 임상영양사 '든든 타이거'입니다. 사진 속 음식을 정밀 분석하세요.
                    
                    [필수 요청 사항]
                    반드시 아래 **JSON 형식**으로만 응답해야 합니다.
                    값은 추정치(정수)로 입력하세요.
                    
                    {{
                        "food_name": "음식 이름",
                        "calories": 000,
                        "carbs": 00,        // 탄수화물 (g)
                        "protein": 00,      // 단백질 (g)
                        "fat": 00,          // 지방 (g)
                        "sugar": 00,        // 당류 (g)
                        "sodium": 000,      // 나트륨 (mg) - 국물 포함 여부 고려
                        "cholesterol": 000, // 콜레스테롤 (mg)
                        "calcium": 000,     // 칼슘 (mg)
                        "vitamin_info": "비타민 C, D 등 풍부한 영양소와 효능 요약 (한 문장)",
                        "analysis": "종합 영양 평가 (3문장 이내)",
                        "tips": "시니어를 위한 섭취 팁 1가지"
                    }}
                    """
                    
                    res = model.generate_content([system_prompt, img], safety_settings=safety_settings)
                    data = parse_ai_json(res.text)
                    
                    if data:
                        st.divider()
                        st.markdown(f"### 🍱 {data['food_name']}")
                        
                        # 3단 구성 표시
                        c1, c2, c3 = st.columns(3)
                        c1.metric("🔥 칼로리", f"{data['calories']} kcal")
                        c2.metric("🍚 탄수화물", f"{data['carbs']} g")
                        c3.metric("🥩 단백질", f"{data['protein']} g")
                        
                        c4, c5, c6 = st.columns(3)
                        c4.metric("🧈 지방", f"{data['fat']} g")
                        c5.metric("🍭 당류", f"{data['sugar']} g")
                        c6.metric("🧂 나트륨", f"{data['sodium']} mg") # 나트륨 중요!
                        
                        c7, c8 = st.columns(2)
                        c7.metric("🥚 콜레스테롤", f"{data['cholesterol']} mg")
                        c8.metric("🦴 칼슘", f"{data['calcium']} mg")
                        
                        st.info(f"💊 **비타민/미네랄:** {data['vitamin_info']}")
                        st.success(f"💡 **타이거 팁:** {data['tips']}")
                        
                        # DB 저장
                        if db:
                            date_str = record_date.strftime("%Y-%m-%d")
                            log_data = {
                                "date": date_str,
                                "datetime": datetime.combine(record_date, datetime.now().time()),
                                "meal_type": meal_type,
                                "food_name": data['food_name'],
                                "calories": data['calories'],
                                "carbs": data['carbs'],
                                "protein": data['protein'],
                                "fat": data['fat'],
                                "sugar": data.get('sugar', 0),
                                "sodium": data.get('sodium', 0),
                                "cholesterol": data.get('cholesterol', 0),
                                "calcium": data.get('calcium', 0),
                                "vitamin_info": data.get('vitamin_info', ''),
                                "timestamp": datetime.now()
                            }
                            db.collection('users').document(nickname).collection('diet_logs').add(log_data)
                            st.toast("상세 영양 정보가 저장되었습니다!", icon="✅")
                            
                    else:
                        st.error("데이터 분석 실패. 다시 시도해주세요.")

                except Exception as e:
                    st.error(f"오류 발생: {e}")

# ---------------------------------------------------------
# [탭 3] 건강 보고서 (그래프 분리)
# ---------------------------------------------------------
with tab3:
    st.subheader("📊 호랑이 정밀 건강 보고서")
    report_type = st.radio("보고서 종류", ["일간 정밀 분석", "기간별 추이 (7일)"], horizontal=True)
    
    if db:
        docs_ref = db.collection('users').document(nickname).collection('diet_logs')
        
        # 권장량 가져오기
        my_needs = calculate_needs(st.session_state.user_info['age'], 
                                    st.session_state.user_info['gender'], 
                                    st.session_state.user_info['height'], 
                                    st.session_state.user_info['weight'])

        if report_type == "일간 정밀 분석":
            report_date = st.date_input("날짜 선택", datetime.now())
            date_str = report_date.strftime("%Y-%m-%d")
            
            query = docs_ref.where("date", "==", date_str).stream()
            daily_logs = [doc.to_dict() for doc in query]
            
            if daily_logs:
                df = pd.DataFrame(daily_logs)
                
                # --- 섹션 1: 주요 영양소 (g 단위) ---
                st.markdown("#### 1️⃣ 주요 영양소 균형 (단위: g)")
                
                # 합계 계산 (없으면 0 처리)
                total_carbs = df['carbs'].sum()
                total_prot = df['protein'].sum()
                total_fat = df['fat'].sum()
                total_sugar = df.get('sugar', pd.Series([0])).sum() # 컬럼 없을 때 대비
                
                chart_data_g = pd.DataFrame({
                    "영양소": ["탄수화물", "탄수화물", "단백질", "단백질", "지방", "지방", "당류", "당류"],
                    "구분": ["섭취량", "권장량", "섭취량", "권장량", "섭취량", "권장량", "섭취량", "권장량"],
                    "값(g)": [total_carbs, my_needs['carbs'], 
                              total_prot, my_needs['protein'], 
                              total_fat, my_needs['fat'],
                              total_sugar, my_needs['sugar']]
                })
                
                c1 = alt.Chart(chart_data_g).mark_bar().encode(
                    x='값(g)', y='영양소', color='구분', tooltip=['영양소', '구분', '값(g)']
                )
                st.altair_chart(c1, use_container_width=True)

                # --- 섹션 2: 주의해야 할 영양소 (mg 단위) ---
                st.markdown("#### 2️⃣ 관리 영양소 (단위: mg)")
                st.caption("나트륨과 콜레스테롤은 적게, 칼슘은 충분히 드시는 게 좋습니다.")
                
                total_sodium = df.get('sodium', pd.Series([0])).sum()
                total_chol = df.get('cholesterol', pd.Series([0])).sum()
                total_calcium = df.get('calcium', pd.Series([0])).sum()
                
                chart_data_mg = pd.DataFrame({
                    "영양소": ["나트륨", "나트륨", "콜레스테롤", "콜레스테롤", "칼슘", "칼슘"],
                    "구분": ["섭취량", "권장상한", "섭취량", "권장상한", "섭취량", "목표량"],
                    "값(mg)": [total_sodium, my_needs['sodium'], 
                               total_chol, my_needs['cholesterol'], 
                               total_calcium, my_needs['calcium']]
                })
                
                # 나트륨 경고색 표시 로직 (너무 높으면 빨강)
                c2 = alt.Chart(chart_data_mg).mark_bar().encode(
                    x='값(mg)', y='영양소', color=alt.Color('구분', scale=alt.Scale(scheme='set2')),
                    tooltip=['영양소', '구분', '값(mg)']
                )
                st.altair_chart(c2, use_container_width=True)
                
                # 상세 팁
                if total_sodium > my_needs['sodium']:
                    st.error(f"🚨 나트륨 섭취가 높습니다! (현재: {total_sodium}mg / 권장: {my_needs['sodium']}mg)")
                if total_sugar > my_needs['sugar']:
                    st.warning(f"⚠️ 당류 섭취를 조금 줄여보세요. (현재: {total_sugar}g)")
                
                st.markdown("#### 📋 섭취 음식 목록")
                st.dataframe(df[['meal_type', 'food_name', 'calories', 'sodium', 'sugar', 'vitamin_info']])
                
            else:
                st.info("기록된 데이터가 없습니다.")

        else: # 기간별 (최근 7일)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            all_logs = docs_ref.stream()
            
            period_data = []
            for doc in all_logs:
                d = doc.to_dict()
                if start_date.strftime("%Y-%m-%d") <= d['date'] <= end_date.strftime("%Y-%m-%d"):
                    period_data.append(d)
            
            if period_data:
                df_period = pd.DataFrame(period_data)
                # 날짜별 나트륨/당류 합계
                daily_stats = df_period.groupby('date')[['calories', 'sodium', 'sugar']].sum().reset_index()
                
                st.markdown("### 📈 건강 지표 추이 (나트륨/당류)")
                
                # 이중축 그래프 대신 탭으로 분리하여 깔끔하게
                tab_g1, tab_g2 = st.tabs(["🧂 나트륨 추이", "🍭 당류 추이"])
                
                with tab_g1:
                    line_na = alt.Chart(daily_stats).mark_line(point=True, color='red').encode(
                        x='date', y='sodium', tooltip=['date', 'sodium']
                    ).properties(title="일별 나트륨 섭취량 (mg)")
                    st.altair_chart(line_na, use_container_width=True)
                
                with tab_g2:
                    line_su = alt.Chart(daily_stats).mark_line(point=True, color='orange').encode(
                        x='date', y='sugar', tooltip=['date', 'sugar']
                    ).properties(title="일별 당류 섭취량 (g)")
                    st.altair_chart(line_su, use_container_width=True)
                    
            else:
                st.info("최근 7일간 기록이 없습니다.")

# ---------------------------------------------------------
# [탭 4] 영양 상담소
# ---------------------------------------------------------
with tab4:
    st.subheader("💬 무엇이든 물어보세요")
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])

    if prompt := st.chat_input("예: 칼슘이 부족하다는데 우유 말고 뭐가 좋아?"):
        st.chat_message("user").markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "text": prompt})

        with st.chat_message("model"):
            with st.spinner("생각 중..."):
                try:
                    today_date = datetime.now().strftime("%Y년 %m월 %d일")
                    
                    chat_system_prompt = f"""
                    당신은 임상영양사 '든든 타이거'입니다. 사용자: {nickname} 어르신.
                    현재: {today_date}.
                    질문에 대해 나트륨, 당류, 비타민 등 구체적인 영양소를 근거로 들어 전문적으로 답변하세요.
                    """
                    
                    full_prompt = chat_system_prompt + "\n\n[이전 대화]\n"
                    for msg in st.session_state.chat_history:
                        speaker = "어르신" if msg["role"] == "user" else "타이거"
                        full_prompt += f"{speaker}: {msg['text']}\n"
                    
                    full_prompt += f"\n타이거(답변):"
                    
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "model", "text": response.text})
                    
                except Exception as e:
                    st.error(f"오류: {e}")