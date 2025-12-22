# 1. 파이썬 3.11 버전 설치
FROM python:3.11-slim

# 2. 작업 폴더 생성
WORKDIR /app

# 3. 파일 복사
COPY . .

# 4. 라이브러리 설치
RUN pip install -r requirements.txt

# 5. 포트 개방
EXPOSE 8080

# 6. [중요 수정] Streamlit 실행 (보안 옵션 완화 및 파일 업로드 허용)
CMD ["streamlit", "run", "app.py", \
    "--server.port=8080", \
    "--server.address=0.0.0.0", \
    "--server.enableCORS=false", \
    "--server.enableXsrfProtection=false", \
    "--server.fileWatcherType=none"]