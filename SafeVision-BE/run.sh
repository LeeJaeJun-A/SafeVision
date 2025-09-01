#!/bin/bash

# Smart Safety FastAPI 서버 실행 스크립트

echo "Smart Safety 서버를 시작합니다..."

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "가상환경을 활성화합니다..."
    source venv/bin/activate
fi

# 의존성 설치 확인
echo "의존성을 확인합니다..."
pip install -r requirements.txt

# 서버 실행
echo "FastAPI 서버를 시작합니다..."
echo "서버 주소: http://localhost:8000"
echo "API 문서: http://localhost:8000/docs"
echo "중지하려면 Ctrl+C를 누르세요."

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
