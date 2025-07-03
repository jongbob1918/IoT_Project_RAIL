[![표지](https://github.com/user-attachments/assets/48721f79-2985-49a5-b865-95c53c58e082)](https://docs.google.com/presentation/d/1FzKztQ5YNb_TZpFh6WQ7UyEFaeflS6z4hu515bo7t1Q/edit?slide=id.p#slide=id.p)
[ㄴ 클릭시 PPT 이동](https://docs.google.com/presentation/d/1FzKztQ5YNb_TZpFh6WQ7UyEFaeflS6z4hu515bo7t1Q/edit?slide=id.p#slide=id.p)

## 주제 : 물류 자동화 시스템 
![예시 이미지](https://github.com/user-attachments/assets/03f315c8-1333-4b91-ac39-5488418d2069)

### 목차
**00** 팀 소개 <br/>
**01** 프로젝트 소개 <br/>
**02** 프로젝트 설계 <br/>
**03** 프로젝트 구현 <br/>
**04** 프로젝트 결과 <br/>
마무리 
# 00. 팀 소개

## 팀명 : RAIL
![로고](https://github.com/user-attachments/assets/8f8feda1-c146-4f99-8d42-3796149e6753)

**R**apid **A**utomated **I**ntegrated **L**ogistics <br/>
빠르고 자동화된 통합 물류관리 시스템
## 팀원 
| 이름 | 주요 역할 | 상세 |
|:---:|---|---|
| 최원호 (팀장) | **프로젝트 총괄**  | DB / 발표자료 / 시퀀스 다이어그램 |
| 김종명 (팀원) | **설계** | 통신 / SW,HW 아키텍쳐 / 서버 | 
| 김지연 (팀원) | **GUI**   | GUI / 발표자료 / 시퀀스 다이어그램 |
| 박효진 (팀원) | **시스템 통합**  | 창고, 보안 기술 구현 |
| 박태환 (팀원) | **기술 조사**  | 분류기 기술 구현 |

## 활용 기술
|분류|기술|
|---|---|
|**개발환경**|<img src="https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=white"/> <img src="https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=Ubuntu&logoColor=white"/> <img src="https://img.shields.io/badge/VSCode-007ACC?style=for-the-badge&logo=visualstudiocode&logoColor=white"/> |
|**언어**|<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=Python&logoColor=white"/> <img src="https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=cplusplus&logoColor=white"/> <img src="https://img.shields.io/badge/Arduino-00878F?style=for-the-badge&logo=arduino&logoColor=white"/>
|**UI**|<img src="https://img.shields.io/badge/PyQt5-28c745?style=for-the-badge&logo=PyQt5&logoColor=white"/>|
|**DBMS**| <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white"/>|
|**협업**|<img src="https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white"/> <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white"/> <img src="https://img.shields.io/badge/SLACK-4A154B?style=for-the-badge&logo=slack&logoColor=white"/> <img src="https://img.shields.io/badge/Confluence-172B4D?style=for-the-badge&logo=confluence&logoColor=white"/> <img src="https://img.shields.io/badge/JIRA-0052CC?style=for-the-badge&logo=jira&logoColor=white"/> |

## 일정관리
![일정](https://github.com/user-attachments/assets/b398133c-9083-461a-9600-5ef30027cfa5)

# 01. 프로젝트 소개
## 주제 선정 배경
![주제선정배경](https://github.com/user-attachments/assets/5ad439c4-b119-49da-a3a2-a7d28271f93d)

물류 자동화 시스템을 주제로 선정한 이유는 크게 3가지가 있습니다. <br/>
**첫 번째**는 온라인 쇼핑이 증가하고 오프라인 매장 수가 감소하면서 **전자상거래**가 증가하면서, 해당 주제에 수요가 증가했습니다. <br/>
**두 번째**는 쿠팡이나, 여러 소셜 커머스에서 시행하는 당일 배송으로 인해 **짧은 배송시간 수요**가 증가했습니다. <br/>
**세 번째**는 각종 기술, 로봇, IoT, 인공지능 등의 발달로 **물류 자동화 시스템의 접근성**이 높아졌습니다. <br/>
이로 인해 물류 자동화 시스템은 앞으로 고성장할 서비스로 판단되었고 사업성이 좋은 아이템으로 생각되어 해당 주제를 선정하게 되었습니다.

## 사용자 요구사항 (User Requirements)
| 번호 | 설명 |
|------|----------------|
| 1 | 물류센터의 **입고, 분류, 저장, 출고** 과정을 자동화하고 싶다. |
| 2 | 물품을 **식품과 비식품**으로 분류하고, 식품은 **온도별로 보관**하고 싶다. |
| 3 | 입고, 출고 및 보관 중인 재고를 **수치적으로 시각화**해서 한눈에 파악하고 싶다. |
| 4 | **많은 물품을 효율적으로 저장**하고, 보관 종류에 따라 **다른 창고에 분류 보관**하고 싶다. |
| 5 | 창고의 **온도는 자동으로 관리**되며, 필요 시 **온도 조절**이 가능해야 한다. |
| 6 | 물품의 **유통기한을 파악**하고, 물품마다 유통기한 상태를 관리하고 싶다. |
| 7 | 유통기한이 **5일 미만인 물품은 경고 알림**을 받고, **시각적으로 표시**하고 싶다. |
| 8 | **유통기한이 지난 식품**은 자동으로 **폐기물 처리장으로 분류**되며, **알림**을 받고 싶다. |
| 9 | 직원들의 **출입기록 확인 및 과거 기록 조회** 기능이 필요하다. |
| 10 | 물류센터 내부를 **실시간 영상으로 모니터링**하고 싶다. |

[ **요약** ]
![사용자 요구사항](https://github.com/user-attachments/assets/82bc95f1-165f-4cd8-bba9-3471a00a45e4)

저희는 정의한 사용자 요구사항을 크게 3가지로 구분 할 수 있었습니다. <br/>
'분류 / 재고,환경 관리 / 직원 출입 관리' 이렇게 3가지로 구분되었습니다.
## 프로젝트 설립
![프로젝트 설립](https://github.com/user-attachments/assets/1672b838-114b-47f0-944e-e036b8b76b69)

사용자 요구사항을 3가지를 각각의 역할에 맞게 정의하여 프로젝트를 설립하였습니다.

# 02. 프로젝트 설계
## System Requirements
| SR_ID | Category | Name | Description | Priority |
|-------|----------|------|-------------|----------|
| SR_01 | 분류 | 분류장치 원격 제어 기능 | 입고하는 물품들을 분류하는 장치를 원격으로 작동/정지함.<br>분류할 물품이 없을 때 일정 시간 경과 시 자동 종료됨. | R |
| SR_02 | 분류 | 물품 분류 기능 | 입고된 물품을 다음 기준에 따라 분류하고 해당 창고로 이동:<br>냉동, 냉장, 상온, 비식품, 오류물품(분류되지 않은 물품) | R |
| SR_03 | 분류 | 물품 정보 인식 기능 | 물품의 분류 정보, 판매자, 보관 온도, 유통기한을 인식 후 저장 | R |
| SR_04 | 분류 | 분류대 물품 개수 확인 기능 | 분류 위치별로 분류된 물품 개수를 집계하여 확인 | R |
| SR_05 | 분류 | 분류중 정지 방지 기능 | 입고 종료 시 분류중인 물품이 있으면 알림 표시되며 작동 유지<br>입고/분류중인 물품 없을 경우 종료 | R |
| SR_06 | 분류 | 비상 정지 기능 | 입고 중 비상 정지 버튼 누르면 컨베이어/분류기 즉시 정지<br>입고 수량 남아있어도 강제 정지 가능 | O |
| SR_07 | 분류 | 입고 상태 실시간 모니터링 기능 | 입고 시작/종료/알림 상태를 모니터에 실시간 반영 | R |
| SR_09 | 환경관리 | 보관창고 모니터링 기능 | 보관창고의 물품 리스트, 창고별 온도, 선반별 상태 모니터링 | R |
| SR_10 | 환경관리 | 온도 제어 기능 | 창고별 온도 기준 설정 및 자동 냉방/난방 장치 작동 | R |
| SR_11 | 환경관리 | 온도 실시간 모니터링 기능 | 보관창고 온도 원격 실시간 모니터링 | R |
| SR_12 | 환경관리 | 온도 이상 감지 및 알림 기능 | 온도가 설정값을 벗어나면 경고 및 알림 작동<br>설정값 범위로 복귀 시 경고 해제 | R |
| SR_13 | 입출입관리 | 출입증 확인 기능 | 등록된 출입증인지 확인<br>미등록 출입증이 3회 인식되면 경고 알림 발생 | O |
| SR_14 | 입출입관리 | 출입문 제어 기능 | 출입증의 허가 여부에 따라 출입문 자동 제어 | O |
| SR_15 | 입출입관리 | 출입 기록 관리 기능 | 출입 기록 저장 및 열람 기능 제공 | O |
| SR_16 | 재고관리 | 물품 입출고 실시간 확인 기능 | 물품의 입고량 및 출고량 실시간 확인 | R |
| SR_17 | 재고관리 | 유통기한 관리 기능 | 물품 유통기한 확인 및 경과 시 관리자 알림 전송 | O |
| SR_18 | 재고관리 | 유통기한 경과 물품 처리 기능 | 유통기한 경과 물품에 대한 알림 및 처리 | O |
| SR_19 | 재고관리 | 창고 재고량 표시 기능 | 창고의 현재 적재량 실시간 모니터링 | R |
| SR_20 | 재고관리 | 창고 선반 위치 지정 기능 | 창고 내 빈 선반 위치 자동 확인 후 지정 | R |

![System Requirements](https://github.com/user-attachments/assets/74ba4a5a-1550-420f-b804-ef82591d6623)

기능 리스트를 요약하면 크게 3가지로 나눌 수 있습니다. <br/>
물품의 분류를 담당하는 분류 기능(**컨베이어 벨트**) <br/>
물품의 재고 보관과, 온도 등의 환경을 담당하는 재고 환경 관리 기능(**창고**) <br/>
직원의 출입을 담당하는 출입 관리 기능(**보안**) <br/>
추가적으로 위 3가지 기능을 모니터링하고 제어하는 **GUI** 가 있겠습니다.

## HW 아키텍쳐 (Hardware Architecture)
![HW 아키텍쳐](https://github.com/user-attachments/assets/f69be87c-ffeb-4156-8f38-70de20bbb698)

## SW 아키텍쳐 (Software Architecture)
![SW 아키텍쳐](https://github.com/user-attachments/assets/a9810ca7-fd8e-40b0-a7cf-f6aad21054de)

## 상태 다이어그램 (State Diagram)
![상태 다이어그램](https://github.com/user-attachments/assets/f3619613-45f6-4e7a-953a-47ae282efaee)

## 시나리오 (Scenario)
<details>
<summary>SC_01 - 분류 작업 제어 시나리오 [클릭] </summary>

📌 트리거
- 관리자가 GUI에서 "분류시작", "분류종료", "일시정지" 버튼 클릭
- 컨베이어 벨트 입구 IR 센서에 물품 감지
- 10초간 물품 미감지

👥 참여자
- GUI
- API Server
- Service Layer
- TCP Handler
- Sort Controller (ESP32)

---

🟢 A. 분류 시작 시나리오

1. 시작 명령 발생  
   - 관리자가 GUI에서 "분류시작" 버튼 클릭  
   - GUI에서 REST API 요청 전송: `POST /api/inbound/start`

2. 시스템 상태 확인  
   - Service Layer는 현재 분류기 상태 확인  
     - 상태가 RUNNING일 경우  
       → WebSocket 메시지 전송:  
         `{"event_type": "info", "message": "이미 작동 중입니다", "auto_dismiss": 1000}`  
       → 요청 중단  
     - 상태가 PAUSED일 경우  
       → 일시정지에서 재개 작업 진행  
     - 상태가 STOPPED일 경우  
       → 정지에서 시작 작업 진행

3. 하드웨어 제어 명령 전송  
   - TCP Handler가 Sort Controller로 메시지 전송: `SCst\n`  
   - Sort Controller 작업:  
     - 컨베이어 벨트 모터 ON  
     - 바코드 스캐너 ON  
     - 센서 활성화  
     - 응답 전송: `SRok\n`

4. GUI 상태 업데이트  
   - 상태를 RUNNING으로 변경  
   - WebSocket 메시지 전송:  
     `{"event_type": "status_update", "status": "running"}`  
   - GUI 반영:  
     - 상태: 작동 중 (녹색)  
     - "분류시작" 버튼 비활성화  
     - "분류종료", "일시정지" 버튼 활성화

---

🔴 B. 분류 종료 시나리오

1. 종료 명령 발생  
   - GUI에서 "분류종료" 클릭 → `POST /api/inbound/stop`  
   - 또는 Sort Controller가 10초 미감지 감지 → `SEas\n`

2. 시스템 상태 확인  
   - 상태가 RUNNING 또는 PAUSED가 아닐 경우  
     → WebSocket 메시지 전송:  
       `{"event_type": "info", "message": "분류기가 작동 중이 아닙니다", "auto_dismiss": 1000}`  
     → 중단

3. 대기 물품 확인  
   - 대기 물품 수 > 0일 경우  
     → WebSocket 경고 메시지 전송:  
       `{"event_type": "warning", "message": "아직 처리 중인 물품이 있습니다", "auto_dismiss": 1000}`  
     → 종료 중단  
   - 대기 물품 없음 → 다음 단계 진행

4. 하드웨어 제어 명령 전송  
   - TCP Handler → Sort Controller: `SCsp\n`  
   - Sort Controller 작업:  
     - 컨베이어 벨트 모터 OFF  
     - 바코드 스캐너 OFF  
     - 센서 비활성화  
     - 응답 전송: `SRok\n`

5. GUI 상태 업데이트  
   - 상태를 STOPPED로 변경  
   - WebSocket 메시지 전송:  
     `{"event_type": "status_update", "status": "stopped"}`  
   - GUI 반영:  
     - 상태: 분류 종료 (회색)  
     - "분류시작" 버튼 활성화  
     - "분류종료", "일시정지" 버튼 비활성화

---

🟡 C. 일시정지 시나리오

1. 일시정지 명령 발생  
   - GUI에서 "일시정지" 버튼 클릭 → `POST /api/inbound/pause`

2. 시스템 상태 확인  
   - 상태가 RUNNING이 아닐 경우  
     → WebSocket 메시지 전송:  
       `{"event_type": "info", "message": "분류기가 작동 중이 아닙니다", "auto_dismiss": 1000}`  
     → 중단

3. 하드웨어 제어 명령 전송  
   - TCP Handler → Sort Controller: `SCps\n`  
   - Sort Controller 작업:  
     - 컨베이어 벨트 모터 OFF  
     - 스캐너 및 센서는 ON 상태 유지  
     - 응답 전송: `SRok\n`

4. GUI 상태 업데이트  
   - 상태를 PAUSED로 변경  
   - WebSocket 메시지 전송:  
     `{"event_type": "status_update", "status": "paused"}`  
   - GUI 반영:  
     - 상태: 일시정지 (노란색)  
     - "분류시작" 버튼 활성화 (재개 용도)  
     - "분류종료" 버튼 활성화  
     - "일시정지" 버튼 비활성화

</details>

<details>
<summary>SC_02 - 바코드 기반 자동 분류 시나리오 [클릭] </summary>

📌 트리거
- 컨베이어 벨트 입구 IR 센서에 물품 감지

👥 참여자
- Sort Controller (ESP32)
- TCP Handler
- Service Layer
- DB
- GUI

---

📦 1. 물품 감지 및 카운트 증가

- Sort Controller의 입구 IR 센서가 물품 감지  
- Sort Controller는 TCP 메시지를 TCP Handler로 전송  
  - 메시지에는 센서 ID(entry), 감지 상태(1=감지됨) 포함  
- TCP Handler는 메시지를 Service Layer로 전달  
- Service Layer는 입고 대기 물품 수를 1 증가시킴  
- Socket.IO를 통해 GUI에 업데이트된 카운트 전송  
- GUI는 다음과 같이 표시  
  - 대기 물품 수를 1로 업데이트  
  - 진행 표시줄 반영

---

🔍 2. 바코드 스캔 및 분류

- 물품이 ESP32-CAM 위치에 도달 → Sort Controller가 바코드 스캔 수행  
- 스캔된 바코드 정보를 TCP 메시지로 전송  
- TCP Handler → Service Layer로 메시지 전달  
- Service Layer는 바코드 파싱 수행:  
  - 보관 종류: 첫 1자리 (1: 냉동/A, 2: 냉장/B, 3: 상온/C)  
  - 물품 번호: 다음 2자리  
  - 유통기한: 다음 6자리 (YYMMDD 형식)  
- 물품 번호에 따라 창고 결정 (A/B/C)  
- DB에서 해당 창고의 빈 선반 위치 조회  
  - 가장 번호가 작은 선반 위치 할당  
- TCP Handler가 Sort Controller에 분류 명령 전송  
  - 분류 구역 정보 포함 (A/B/C/E)

---

⚙️ 3. 분류 실행 및 결과 처리

- Sort Controller는 명령 수신 → 서보모터 작동  
  - 지정된 구역으로 물품 밀어냄  
- 분류대 IR 센서가 물품 통과 감지  
- 감지 결과를 TCP 메시지로 전송 → Service Layer로 전달  
- Service Layer는 다음 작업 수행:  
  - 대기 물품 수 1 감소  
  - 처리된 물품 수 1 증가  
  - DB에 물품 정보 저장 (분류, 창고, 유통기한 등)  
- Socket.IO를 통해 GUI에 분류 결과 및 카운트 전송  
- GUI는 다음 항목 업데이트:  
  - 대기 수량  
  - 처리 수량  
  - 물품 로그에 새 항목 추가

---

🔀 선택 분기점

- 물품 분류:  
  - 물품 번호에 따라 A/B/C 창고 중 하나로 지정  
- 분류 감지:  
  - IR 센서 감지 성공 → 분류 완료  
  - 감지 실패 → 물품 분실 처리

---

❗ 예외 상황 - 바코드 오류

- Sort Controller가 바코드 인식 실패 시 오류 이벤트 전송  
- Service Layer는 오류 물품을 E 분류대로 이동 지시  
- GUI에 바코드 오류 알림 표시 (Socket.IO 메시지)


</details>

<details>
<summary>SC_03 - 창고 온습도 모니터링 및 제어 시나리오 [클릭] </summary>

📌 트리거
- 정기적(5초 간격) 환경 센서 측정
- 관리자 온도 기준치 변경 시

👥 참여자
- Env Controller
- TCP Handler
- Service Layer
- DB
- GUI

---

🌡️ 1. 창고별 상태 확인

- 기준치: 사용자가 고정된 범위 내에서 설정한 온도
- 고정된 범위:
  - 냉동 창고(A): -25℃ ~ -15℃
  - 냉장 창고(B): 0℃ ~ 10℃
  - 상온 창고(C): 15℃ ~ 25℃

- 기준치 설정 플로우:
  - GUI에서 기준치 설정 (고정 범위 내)
  - API Server → Service Layer → TCP Server → Env Controller로 기준치 전송

- 온도 측정 및 상태 판단 (Env Controller에서 5초 주기 실행):
  - 대기 모드: 기준치 ±2℃ 이내
  - 냉방 모드:
    - 1단계: 기준치 +2℃ 초과 ~ +4℃ 이내
    - 2단계: 기준치 +4℃ 초과 ~ +6℃ 이내
    - 3단계: 기준치 +6℃ 초과
  - 난방 모드:
    - 1단계: 기준치 -2℃ 미만 ~ -4℃ 이내
    - 2단계: 기준치 -4℃ 미만 ~ -6℃ 이내
    - 3단계: 기준치 -6℃ 미만
  - 경고 상태: 고정된 min/max 범위 벗어난 값

- 결과 전송:
  - Env Controller → TCP Handler → Service Layer → API Server → GUI
  - 포함 정보:
    - 창고 ID
    - 측정값
    - 온도 제어 단계
    - 정상/경고 상태
    - 시간

- 경고 상태인 경우:
  - DB의 `temp_warning_logs` 테이블에 기록 (창고 ID, 온도, 발생 시각)

---

🖥️ 2. GUI 표시

- 대시보드:
  - 창고 ID, 측정값, 상태 표시
  - 상태 색상:
    - 정상: 녹색
    - 경고: 빨간색

- 창고환경 페이지:
  - 창고 ID, 측정값, 온도 제어 단계, 상태 표시
  - 제어 단계 색상:
    - 냉방: 파란색
    - 난방: 빨간색
    - 정지: 회색
  - 상태 색상:
    - 정상: 초록색
    - 경고: 빨간색

---

💨 3. 팬 제어 명령 결정

- Env Controller는 온도 제어 단계에 따라 팬 속도 및 LED 상태 조절

- 냉방 모드:
  - 팬 작동 (단계별 세기 증가)
  - 파란색 LED ON
  - 빨간색 LED OFF

- 난방 모드:
  - A, B 창고: 팬 정지 + 모든 LED OFF
  - C 창고: 팬 작동 (단계별 세기 증가) + 빨간색 LED ON + 파란색 LED OFF

- 정지 모드:
  - 팬 정지 + 모든 LED OFF

- 처리 후 TCP Handler → Service Layer로 제어 단계 전송

---

🚨 4. 경고 상태 처리

- 경고 상태 발생 시:
  - Service Layer → Env Controller로 경고 명령 전송
  - Env Controller는 노란색 LED 깜빡임 및 부저 작동

- 정상 상태 복귀 시:
  - 경고 장치 비활성화 명령 전송 (LED 및 부저 OFF)

---

🔀 선택 분기점

- 온도 상태에 따라:
  - 정상 / 경고 / 위험 상태 → GUI 및 LED 표시, 팬 제어 방식 변경

- 팬 제어 모드:
  - 냉방: 파란 LED, 팬 작동
  - 난방: 빨간 LED, 팬 작동 (C 창고만)
  - 정지: 팬 OFF, 모든 LED OFF

---

❗ 예외 상황

- 센서 오류:
  - 측정값 비정상 시 이전 값 유지
  - 오류 상태 GUI 표시

- 통신 장애:
  - 10초 이상 데이터 미수신 시 장애 표시
  - 자동 재연결 시도


</details>

<details>
<summary>SC_04 - RFID 기반 출입 관리 시나리오 [클릭] </summary>



</details>

## 시퀀스 다이어그램 (Sequence Diagram)
<details>
<summary>SD_01 - 분류 작업 제어 시퀀스 다이어그램 [클릭] </summary>

![시퀀스 다이어그램 1](https://github.com/user-attachments/assets/61530605-87bb-4b0f-90f3-eb1f4adc8550)

</details>

<details>
<summary>SD_02 - 바코드 기반 자동 분류 시퀀스 다이어그램 [클릭] </summary>

![시퀀스 다이어그램 2](https://github.com/user-attachments/assets/f9a25752-9425-4728-a3be-6d1de394f7d7)

</details>

<details>
<summary>SD_03 - 창고 온습도 모니터링 및 제어 시퀀스 다이어그램 [클릭] </summary>

![시퀀스 다이어그램 3](https://github.com/user-attachments/assets/03a914da-d5ca-41f6-a2b6-2a195b824006)

</details>

<details>
<summary>SD_04 - RFID 기반 출입 관리 시나리오 [클릭] </summary>

[RFID 카드 등록]
![시퀀스 다이어그램 4](https://github.com/user-attachments/assets/25934229-0434-4082-beba-a4edc67492d5)

[등록된 RFID 카드 출입]
![시퀀스 다이어그램 4-2](https://github.com/user-attachments/assets/0dfbf2d4-9857-455e-b138-1b494b33372b)

</details>

## 구성도
![구성도](https://github.com/user-attachments/assets/ef878f25-e8d5-462d-b07b-2e252b989660)

구성도는 크게 **'분류 / 창고 / 보안'** 으로 나눌 수 있겠습니다. <br/> 
**분류**는 물품을 분류해주는 컨베이어 벨트 주변 부품들로 구성되어 있습니다.  <br/> 
- DC모터 : 컨베이어 벨트를 가동  <br/> 
- 전면 IR 센서 x1 : 물품이 벨트 위에 올려져있는지 감지 <br/> 
- esp캠 : QR코드를 스캔  <br/> 
- 서보 모터 : 물품을 분류  <br/>
- 물류대 IR 센서 x4: 해당 물류대 물품 진입 확인 <br/> 
  
**창고**는 재고관리와 환경관리를 위한 부품들로 구성되어 있습니다. <br/> 
- 온도계 : 창고 온도 측정 <br/> 
- DC 모터 (팬) : 창고 온도 관리 <br/> 
- 부저 : 온도 이상 시 알림 <br/> 
- LED : 온도 이상 표시 및 팬 가동중 표시 <br/> 
- OLED : 각 창고 모니터링 <br/> 

**보안**은 출입관리를 위한 부품들로 구성되어 있습니다. <br/> 
- RFID 센서 : 카드를 태그 <br/>
- LED : 카드 스캔 결과를 알림 <br/>

# 03. 프로젝트 구현
## 기구 구현
### [분류]
![분류 기구 구현 1](https://github.com/user-attachments/assets/23dfd2a1-5f67-4d9c-b1bb-47a1d94c6ecb)
![분류 기구 구현 2](https://github.com/user-attachments/assets/4d752eca-fe98-4509-aa7c-743ad57f723c)

### [창고]
![창고 기구 구현 1](https://github.com/user-attachments/assets/ebcaeac1-54a8-4fd9-a9b6-9a77d3dd77b7)
![창고 기구 구현 2](https://github.com/user-attachments/assets/996e25e0-bf97-4daa-8c83-ba98002c464b)

## GUI 구현
![GUI 구현 1](https://github.com/user-attachments/assets/2cf18369-3293-4d12-bb9b-0d01d1c11112)
![GUI 구현 2](https://github.com/user-attachments/assets/a443dddc-3308-41e0-abdf-73cda1f6a73f)
![GUI 구현 3](https://github.com/user-attachments/assets/517305b3-4521-440c-b598-a36d6c61d626)
![GUI 구현 4](https://github.com/user-attachments/assets/0f24a2a1-c8c7-4cc0-9b6f-70b4e7914676)
![GUI 구현 5](https://github.com/user-attachments/assets/da85d4d9-5982-48c4-a7ff-ad8575a9d716)
![GUI 구현 6](https://github.com/user-attachments/assets/b1163f35-0efc-4bd1-b58f-e0892f0a381d)
![GUI 구현 7](https://github.com/user-attachments/assets/b83ed652-242d-4b49-aa6a-02796af6b2a0)

# 04. 프로젝트 결과
## 테스트 영상
[![Video](https://github.com/user-attachments/assets/70b6aa95-32b6-4778-b198-629e9ff7317a)](https://youtu.be/XRiPvK90PW8)

## 최종 구현 결과
![최종구현결과](https://github.com/user-attachments/assets/0a1a8132-103f-426e-a4cc-0be829917902)

# 마무리
## 소감
| 이름 | 소감 |
|:---:|---|
| 최원호 | 프로젝트를 진행하며 설계의 중요성에 대해 깊이 고민하게 되었습니다. 우리가 일상 속에서 마주하는 단순해보이는 물건들도, 결국 사람의 피조물입니다. 그 안에는 안전과 성능을 보장하기 위해 치밀한 설계 과정이 있었음을 깨달았습니다. 프로젝트를 통해 단순히 기술이나 동작 자체에만 집착해서는 안되며, 그 이면에 담긴 설계의 섬세함과 철학을 이해하고 디자인하는 태도가 무엇보다 중요하다는 것을 배웠습니다.| 
| 김종명 | 하드웨어를 사용하는 프로젝트였던 만큼, 예상치 못한 여러 난관에 직면하게 되었습니다. 특히 일부 센서들의 성능 문제로 인해 처음 계획했던 설계를 대부분 수정해야 하는 상황도 발생했습니다. 또한 서버 측에서는 모듈화에 집착하면서 오히려 코드의 복잡도와 디버깅 난이도가 증가하는 문제를 경험했습니다 이와 같은 시행착오를 통해, 앞으로는 시스템의 특성과 상황에 따라 유연하게 설계하고 적절한 균형을 찾는 것이 중요하다는 점을 깊이 느꼈습니다. |
| 김지연 | 이번 프로젝트를 통해 처음으로 서버, GUI, 하드웨어가 유기적으로 통합된 시스템을 직접 설계하고 구현해보는 경험을 할 수 있었습니다. 특히 서버와 GUI, 서버와 컨트롤러 간의 통신에서 어떤 프로토콜을 선택할지, 실시간성을 보장하면서도 최소한의 데이터만 주고받을 수 있도록 인터페이스를 어떻게 설계할지에 대해 깊이 고민하며, 시스템 아키텍처에 대한 시야가 한층 넓어진 것을 느꼈습니다. 또한 각 모듈을 나눠 개발한 후 통합하는 과정에서 예상치 못한 오류와 복잡성이 나타났고, 그 과정에서 협업과 명확한 설계의 중요성을 더욱 실감하게 되었습니다. 단순히 동작하는 기능을 구현하는 것에서 나아가, 유지보수와 확장성을 고려한 구조적인 접근의 필요성을 절감할 수 있는 기회였습니다. | 
| 박효진 | 기능 테스트 과정에서 저가형 부품의 성능 한계를 경험하며 시스템을 두 차례 수정하였습니다. 시행착오를 통해 부품 선택의 중요성을 체감했고, 실전에서의 문제 해결 능력을 기를 수 있는 값진 경험이었습니다.| 
| 박태환 |  | 
