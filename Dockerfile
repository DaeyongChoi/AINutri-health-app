# 1. 파이썬 3.11 슬림 버전 (가볍고 빠름)
FROM python:3.11-slim

# 2. 작업 폴더 생성
WORKDIR /app

# 3. 모든 파일 복사
COPY . .

# 4. 라이브러리 설치
RUN pip install -r requirements.txt

# 5. 포트 개방
EXPOSE 8080

# 6. [최종 실행 명령어]
# - fileWatcherType=none: 불필요한 감시 꺼서 성능 최적화
# - enableXsrfProtection=false: 사진 업로드 에러 방지 (필수)
# - (enableCORS=false 옵션은 삭제하여 보안 강화)
CMD ["streamlit", "run", "app.py", \
    "--server.port=8080", \
    "--server.address=0.0.0.0", \
    "--server.fileWatcherType=none", \
    "--server.enableXsrfProtection=false"]