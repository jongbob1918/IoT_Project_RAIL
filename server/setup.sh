#!/bin/bash
# 서버 설정 스크립트

# 필요한 Python 패키지 설치
echo "필요한 패키지를 설치합니다..."
pip install -r ../requirements.txt

# MySQL 데이터베이스 초기화 (필요한 경우)
echo "데이터베이스 설정을 확인하세요..."
cd $(dirname "$0")
python -c "from db.init_db import init_database; init_database()"

echo "서버 설정이 완료되었습니다. 이제 main.py를 실행하여 서버를 시작할 수 있습니다."