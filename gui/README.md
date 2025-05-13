# RAIL GUI 애플리케이션

## 개요
RAIL GUI 애플리케이션은 물류 관리 시스템의 관리자 인터페이스입니다. PyQt6를 사용하여 개발되었습니다.

## 필요한 패키지 설치
다음 명령어로 필요한 패키지를 설치할 수 있습니다:
```
pip install -r requirements.txt
```

## 실행 방법
1. 서버 먼저 실행:
```
cd server
python main.py
```

2. GUI 애플리케이션 실행:
```
cd gui
python main_window.py
```

## UI 파일 로드 방식
모든 모듈은 PyQt6의 uic 방식으로 통일되었습니다:
```python
from PyQt6 import uic
uic.loadUi("ui/파일경로.ui", self)
```

## 디렉토리 구조
- `ui/` - UI 파일 디렉토리
- `modules/` - 각 화면 별 모듈 파일
- `main_window.py` - 메인 애플리케이션 진입점 