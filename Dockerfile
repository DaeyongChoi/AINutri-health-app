# 1. 파이썬 3.11 버전을 설치해라
FROM python:3.11-slim

# 2. 작업 폴더를 만들어라
WORKDIR /app

# 3. 내 컴퓨터에 있는 파일들을 다 복사해라
COPY . .

# 4. 필요한 부품(라이브러리)을 설치해라
RUN pip install -r requirements.txt

# 5. 서버 포트(8080)를 열어둬라
EXPOSE 8080

# 6. [중요] 앱을 실행해라 (Streamlit 실행 명령어)
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]