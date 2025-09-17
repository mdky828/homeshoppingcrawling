# Python 3.11 slim 이미지를 사용합니다.
FROM python:3.11-slim

# 작업 디렉토리를 설정합니다.
WORKDIR /app

# requirements.txt를 복사하고 의존성을 설치합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드를 복사합니다.
COPY . .

# Cloud Run 서비스가 시작될 때 main.py를 실행합니다.
CMD ["python", "main.py"]
