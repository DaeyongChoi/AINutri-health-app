import google.generativeai as genai

# ==========================================
# 아까 그 긴 API 키를 여기에 다시 붙여넣으세요!
# ==========================================
genai.configure(api_key="AIzaSyDCOazMzSe7Ws2Ceyd-g_GiqYXa3M9mVBE")

print("🔎 내 키로 주문 가능한 모델 목록을 조회합니다...")
print("-" * 30)

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"발견됨! 👉 {m.name}")
except Exception as e:
    print(f"에러 발생: {e}")

print("-" * 30)