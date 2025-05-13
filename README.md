# iot-repo-3

## 폴더 별 역할
```
requirements.txt           : 필요 패키지 목록
.env                       : 시스템의 모든 설정을 중앙화

📁 docs : 설명 문서
ㄴ CODE_STANDARD.md : 코딩 스탠다드
ㄴ README.md

📁 firmware : C++ 기반 아두이노 관리 폴더 (ino 확장자)
ㄴ config.h                 : 핀 번호, MQTT 토픽, 상수 등 공통 설정 정의
ㄴ main.ino                 : 진입점. setup()과 loop()만 존재하며 직접 로직 없음
ㄴ 📁 modules               : 센서 및 액추에이터별 기능 구현 파일
   ㄴ barcode.ino           : 바코드 스캐너 제어 및 MQTT 전송
   ㄴ ir_sensor.ino         : 분류대 IR 센서 감지 처리
   ㄴ dc_motor.ino          : 컨베이어용 DC 모터 제어
   ㄴ temp_humidity.ino     : 온도/습도 센서 측정 및 전송
   ㄴ fan.ino               : 창고 팬 작동 및 자동 제어
   ㄴ rfid.ino              : 출입관리용 RFID 리더기 처리

📁 server   
ㄴ main.py       : 서버 진입점 (Flask + Socket.IO 통합)
ㄴ config.py                  : 설정 값 및 상수
ㄴ run_server.sh              : 서버 실행 스크립트
ㄴ setup.sh                   : 초기 설정 스크립트
ㄴ test_tcp_client.py         : 테스트용 TCP 클라이언트
ㄴ 📁 api : GUI ⇄ Server 간 HTTP 통신 폴더 
   ㄴ __init__.py             : 패키지 초기화
   ㄴ sort_api.py             : 분류기 API
   ㄴ inventory_api.py        : 재고 관리 API
   ㄴ env_api.py              : 환경 제어 API
   ㄴ access_api.py           : 출입 관리 API
   ㄴ expiry_api.py           : 유통기한 관리 API
ㄴ 📁 controllers : 디바이스 컨트롤러
   ㄴ  __init__.py            : 패키지 초기화
   ㄴ sort_controller.py      : 분류기 로직
   ㄴ inventory_controller.py : 재고 관리 로직
   ㄴ env_controller.py       : 환경 제어 로직
   ㄴ access_controller.py    : 출입 관리 로직
   ㄴ expiry_controoler.py    : 유통기한 관리 로직
ㄴ 📁 db : 데이터베이스 관련 모듈
   ㄴ  __init__.py            : 패키지 초기화
   ㄴ rail_db_backup.sql      : DB 파일
   ㄴ db_helper.py            : DB 접근 추상화 레이어
   ㄴ real_db.py              : MySQL 연결 및 쿼리
ㄴ 📁 utils : 유틸리티
   ㄴ  __init__.py            : 패키지 초기화
   ㄴ tcp_handler.py          : TCP 소켓 통신 관리
   ㄴ logging.py              : 로깅설정 및 로그 파일 관리

📁 gui : GUI 파일
ㄴ 📁 components  : 공통으로 사용되는 UI 요소
ㄴ 📁 resources : 이미지나, 아이콘 등의 정적 리소스
  ㄴ 📁 fonts : 폰트 폴더
  ㄴ 📁 icons : 아이콘 폴더
  ㄴ 📁 images : 이미지 폴더
  ㄴ 📁 styles : qss 폴더
ㄴ 📁 ui : pyqt designer로 만든 .ui 파일
ㄴ 📁 views : .ui파일을 작동하게 만드는 파일
ㄴ main_window.py : PyQt 진입점


📁 test : 테스트 코드 및 시나리오
ㄴ 📁 simulator: 가상 시뮬레이션
   ㄴ bacode_simulator.py  : 바코드 시뮬레이터
```