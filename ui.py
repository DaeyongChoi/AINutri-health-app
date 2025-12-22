# ui.py (식단 분석 탭 추가 버전)
import streamlit as st
import requests

st.set_page_config(page_title="든든 타이거", page_icon="🐯")

# 탭(Tap) 메뉴 만들기 (기능 나누기)
tab1, tab2 = st.tabs(["🐯 인사 나누기", "📸 식단 분석하기"])

# === [탭 1] 인사 기능 ===
with tab1:
    st.title("🐯 든든 타이거와 인사해요")
    st.image("https://cdn.pixabay.com/photo/2023/10/24/13/54/tiger-8338379_1280.png", width=150)
    
    with st.expander("내 정보 입력하기 (클릭)", expanded=True):
        nickname = st.text_input("닉네임", "김건강")
        height = st.slider("키", 140, 200, 170)
        weight = st.slider("몸무게", 40, 120, 65)
        goals = st.multiselect("목표", ["체중 감량", "근육", "혈당"], ["근육"])

    if st.button("호랑이야 안녕! 👋"):
        with st.spinner("생각 중..."):
            data = {"nickname": nickname, "height": height, "weight": weight, "goals": goals}
            res = requests.post("http://127.0.0.1:8000/api/v1/greeting", json=data)
            if res.status_code == 200:
                st.success(res.json()["message"])
            else:
                st.error("서버 연결 실패")

# === [탭 2] 식단 분석 기능 (핵심!) ===
with tab2:
    st.title("📸 오늘의 식사를 보여주세요")
    st.info("음식 사진을 올리면 호랑이가 영양소를 분석해드려요!")
    
    # 1. 파일 업로더 만들기
    uploaded_file = st.file_uploader("여기에 음식 사진을 올려주세요", type=["jpg", "png", "jpeg"])
    
    if uploaded_file is not None:
        # 올린 사진 미리보기
        st.image(uploaded_file, caption="맛있겠네요!", use_column_width=True)
        
        # 2. 서버로 보내서 분석하기
        if st.button("이 음식 분석해줘! 🥗"):
            with st.spinner("호랑이가 음식을 뚫어지게 보는 중... 👀"):
                # 이미지 파일을 서버로 전송하기 위한 포장
                files = {"file": uploaded_file.getvalue()}
                
                try:
                    res = requests.post("http://127.0.0.1:8000/api/v1/analyze_food", files=files)
                    
                    if res.status_code == 200:
                        st.success("분석 완료!")
                        st.write(res.json()["message"])
                    else:
                        st.error("분석 실패! 서버를 확인해주세요.")
                except Exception as e:
                    st.error(f"에러: {e}")