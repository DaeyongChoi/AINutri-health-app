import google.generativeai as genai
import os

# 1. 먼저 터미널에서 아래 코드를 복사하여 API 키 등록 (터미널 껐다 켰으면 다시 해야 함)
# $env:GOOGLE_API_KEY="여기에_API_키_붙여넣기"

# API 키가 환경변수에 있는지 확인
if "GOOGLE_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    
    print("\n🔍 내 API 키로 사용 가능한 모델 목록:")
    print("-" * 50)
    
    # 모델 목록 가져오기
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            # 보기 편하게 'models/' 부분은 떼고 출력
            clean_name = m.name.replace("models/", "")
            print(f"👉 {clean_name}")
            
    print("-" * 50)
    print("위 목록에 있는 이름 중 하나를 app.py에 적으시면 됩니다.")
    
else:
    print("⚠️ 에러: 터미널에 API 키가 설정되지 않았습니다.")
    print("먼저 $env:GOOGLE_API_KEY='내_키' 명령어로 키를 등록해주세요.")