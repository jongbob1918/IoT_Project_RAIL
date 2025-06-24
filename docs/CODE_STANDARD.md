# 목차
## 1. C/C++ 기반 (아두이노)
1-1. 파일 및 폴더 구조 규칙

1-2. 이름 규칙(Naming Convention)

1-3. 들여쓰기 / 중괄호 / 주석

1-4. 모듈/함수 구조 및 길이 규칙

## 2. 파이썬 (서버/ GUI)
2-1. 파일 및 폴더 구조 규칙

2-2. 이름 규칙(Naming Convention)

2-3. 들여쓰기 / 중괄호 / 주석

2-4. 모듈/함수 구조 및 길이 규칙

## 3. Git 규칙 
3-1. 작업 공간 (브랜치)

3-2. 커밋 메세지 규칙

--- 

## 1. C/C++ 기반 (아두이노)
### 1-1. 파일 및 폴더 구조 규칙


```
 .ino 확장자 사용 (컴파일 시 자동 병합됨)
📁 firmware/            // C++ 기반 아두이노 관리 폴더
├── main.ino              // 진입점, setup() / loop()만 존재
├── config.h              // 핀 번호, 상수 정의
├── 📁 module1/           // 모듈 폴더 (예시)
│   ├── module1_a.ino
│   └── module1_b.ino   
├── 📁 module2/
│   ├── module2_a.ino
│   └── module2_b.ino       
└── module3.ino     
```

### 1-2. 이름 규칙(Naming Convention)
- 영어로 작명할 것

변수 : snake_case 

함수 : snake_case() 

상수 : UPPER_SNAKE_CASE

클래스 : PascalCase

파일 이름 : snake_case.ino

### 1-3. 들여쓰기 / 중괄호 / 주석
들여쓰기 : 4칸

중괄호  : 데이터 정의의 중괄호 = 같은 줄 작성

```
const int current_led[] = {A0, 2, 3, 4, 5, 6, 7}; // red + yellow LED
: 함수, 제어문 등 코드블럭의 중괄호 = 새 줄 작성

void setup()
{
    pinMode(LED_PIN, OUTPUT);
}
```

주석규칙 
- 한글로 설명할 것
- // 또는 /** */ 사용
- 변수, 상수 = 우측 // (라인 정렬 해줄 것)

```
const int current_led[] = {A0, 2, 3, 4, 5, 6, 7}; // red + yellow LED
const int led_g[] = {8, 9, 10};                   // green LED (call indicator)
const int btn[] = {11, 12, 13};                   // buttons
: 함수, 클래스 = 상단 //, /** */
: 되도록 한 줄로 // 쓸 것

/**
* 여러 줄 주석
*/
// ====== 버튼 입력 처리 + 호출 상태 LED ======
void handleButton() 
{
    for (int i = 0; i < 3; i++) 
    {
        bool current = digitalRead(btn[i]);
        if (prevBtn[i] == HIGH && current == LOW) 
        {
            call[i] = !call[i];  // 토글
        }
        prevBtn[i] = current;
        digitalWrite(led_g[i], call[i] ? HIGH : LOW);
    }
}
```

### 1-4. 모듈/함수 구조 및 길이 규칙
전체 코드를 파일(모듈)과 파일 안에서 함수로 나누는 것은 너무 복잡한 로직을 방지하기 위함

**모듈**

하나의 모듈(하나의 .ino파일, 하나의 .py파일)에는 하나의 역할만

**함수**

하나의 함수에는 하나의 기능만 (단일 책임 원칙)

40줄 이상 되면, 함수 분리하기


안 좋은 예시
```
void loop() {
  int temp = analogRead(A0);
  if (temp > 500) {
    digitalWrite(LED_PIN, HIGH);
    digitalWrite(FAN_PIN, HIGH);
  } else {
    digitalWrite(LED_PIN, LOW);
    digitalWrite(FAN_PIN, LOW);
  }

  int button = digitalRead(BUTTON_PIN);
  if (button == HIGH) {
    for (int i = 0; i < 3; i++) {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(100);
      digitalWrite(BUZZER_PIN, LOW);
      delay(100);
    }
  }

  delay(100);
}
```
문제점
- 한 함수에 여러 동작이 다 섞여 있음
- 어떤 동작이 어디에 위치해있는지 찾기가 어려움 = 유지보수가 어려
- 쓰인 기능 중 일부를 다른 파일에서 사용하기 어려움 = 재사용성이 떨어짐

좋은 예시
```
// ---------- loop() 함수 ----------
void loop() 
{
    func_a();
    func_b();
    func_c();
}

// ---------- 기능 별 함수 ----------
void func_a()
{
  ...
}


void func_b()
{
  ...
}


void func_c()
{
  ...
}
```
좋은 점
- loop 함수에서 전체 흐름을 관리
- 각 기능은 개별 함수로 분리


## 2. 파이썬 (서버/ GUI)
### 2-1. 파일 및 폴더 구조 규칙
하드웨어 핀 번호는 config.h / config.py 로 중앙관리

**server 폴더 : **

```
📁 server/               # 백엔드 로직 (Flask, FastAPI, 또는 단순 DB 처리)
├── app.py                 # 서버 진입점
├── 📁 database/           # DB 연결 및 쿼리
├── 📁 models/             # DB 모델 정의 (예: 사용자, 로그 등)
├── 📁 service/            # 비즈니스 로직 (수익률 계산 등)
└── config.py              # 설정 (DB, 포트 등)
📁 gui/                  # GUI
├── main_window.py         # PyQt 진입점
├── 📁 ui/                 # ui 파일 
│   ├── dashboard.ui                
│   ├── storage_quantity.ui
│   ├── expiration_date_control.ui
│   ├── device_control.ui
│   └── access_control.ui
├── 📁 views/              # ui 파일을 작동하게 만드는 파일 
│   ├── dashboard_view.py                
│   ├── storage_quantity_view.py
│   ├── expiration_date_control_view.py
│   ├── device_control_view.py
│   └── access_control_view.py
├── 📁 components/         # 공통으로 사용되는 ui 요소
│   ├── button.py            # 버튼 (예시)
│   ├── loading_bar.py       # 로딩바 (예시)
│   ...  
└── 📁 resources/          # 이미지나, 아이콘 등의 정적 리소스
    ├── 📁 icons/            # 아이콘 폴더 (예시)
    ├── 📁 images/           # 이미지 폴더 (예시)
    ├── 📁 styles/           # qss 폴더 (예시)
    └── 📁 fonts/            # 폰트 폴더 (예시)
📁 controller/            # 시스템 간 데이터 흐름을 조정
├── __init__.py
├── 📁 arduino/             # 하드웨어(아두이노)와 통신
│   ├── serial_manager.py      # 예시
│   ├── motor_controller.py 
│   └── sensor_reader.py    
├── 📁 api/                 # 서버와의 통신
│   ├── access_api.py          # 출입 기록 저장 등 (예시)
│   ├── calculation_api.py     # 수익률 계산 요청 (예시)
│   └── config_api.py          # 서버 설정 관련 요청 등 (예시)
└── 📁 logic/               # 기능 별 로직
    ├── access_control.py      # 출입 제어 관련 처리 (예시)
    ├── device_status.py       # 장비 상태 판단 및 캐시 (예시)
    └── alert_handler.py       # 경고/알림 관련 처리 (예시)
```

### 2-2. 이름 규칙(Naming Convention)
- 영어로 작명할 것

변수 : snake_case

함수 : snake_case()

상수 : UPPER_SNAKE_CASE

클래스 : PascalCase

파일 이름 : snake_case.ino

### 2-3. 들여쓰기  / 주석
들여쓰기 : 4칸

주석규칙 
- 한글로 설명할 것
- 사용
- 변수, 상수 = 우측 (라인 정렬 해줄 것)

```
CURRENT_LED = [0, 2, 3, 4, 5, 6, 7]   # red + yellow LED
LED_G       = [8, 9, 10]             # green LED (call indicator)
BTN         = [11, 12, 13]           # buttons
```

함수, 클래스 = 상단에 주석
- 되도록 한 줄로 # 쓸 것
- 섹션 구분
```
# ===== 설명 ===== 가능 (C++과 유사)
```
```
# ===== 버튼 입력 처리 + 호출 상태 LED =====
def handle_button():
    for i in range(3):
        if prev_btn[i] and not current_btn[i]:
            call[i] = not call[i]  # 토글
```

### 2-4. 모듈/함수 구조 및 길이 규칙
전체 코드를  파일(모듈)과 파일 안에서 함수로 나누는 것은 너무 복잡한 로직을 방지하기 위함

**모듈**

하나의 모듈(하나의 .ino파일, 하나의 .py파일)에는 하나의 역할만

**함수**

하나의 함수에는 하나의 기능만 (단일 책임 원칙)

40줄 이상 되면, 함수 분리하기

## 3. GIT 규칙
### 3-1. 작업 공간 (브랜치)
브랜치는 목적에 따라 main + dev로 구분합니다.

main : 배포 또는 완성된 코드, 절대 직접 커밋 금지

dev : 모두가 작업하는 공용 개발 공간

- 모든 개발자는 dev에서 작업하고 커밋
- 충돌 방지를 위해 "하루 1회 pull & push 전 충돌 확인" 습관
- 본인이 작업할 파일이 팀원들이 현재 작업중인지 체킹할 것 [
실시간 작업내역 ]
- 프로세스 단위로 안정화된 dev → main으로 merge (릴리즈 개념)

### 3-2. 커밋 메시지 규칙
목적은 의도를 명확히 남기고, 변경 기록을 추적 가능하게 만드는 것.

[work directory] 한글 설명으로 주석 남기기

**디렉토리별 설명**

[firmware] : 아두이노 코드 변경

[gui] : GUI 관련 변경

[server] : 백엔드 관련 변경

[controller] : 데이터 흐름 변경

