""" 
IOT 시스템 통신 프로토콜 정의

기본 메시지 구조:
- 디바이스 ID (1바이트): 'S'(분류기), 'H'(창고환경), 'G'(입출입)
- 메시지 타입 (1바이트): 'E'(이벤트), 'C'(명령), 'R'(응답), 'X'(에러)
- 페이로드 (가변): 각 메시지별 데이터 ('\n'으로 종료)
"""

# 디바이스 식별자
DEVICE_SORTER = 'S'  # 분류기
DEVICE_WAREHOUSE = 'H'  # 창고환경
DEVICE_GATE = 'G'  # 입출입

# 메시지 타입
MSG_EVENT = 'E'  # 이벤트
MSG_COMMAND = 'C'  # 명령
MSG_RESPONSE = 'R'  # 응답
MSG_ERROR = 'X'  # 에러

# 공통 응답 코드
RESPONSE_OK = 'ok'  # 성공
ERROR_COMM = 'e1'   # 통신 오류
ERROR_SENSOR = 'e2'  # 센서 오류

# 분류기 이벤트
SORT_EVENT_IR = 'ir'        # IR 센서 (1=감지)
SORT_EVENT_BARCODE = 'bc'   # 바코드 인식
SORT_EVENT_SORTED = 'ss'    # 분류 완료
SORT_EVENT_AUTO_STOP = 'as' # 자동 정지

# 분류기 명령
SORT_CMD_START = 'st'      # 시작
SORT_CMD_STOP = 'sp'       # 정지
SORT_CMD_PAUSE = 'ps'      # 일시정지
SORT_CMD_SORT = 'so'       # 분류 (A~E)

# 분류 존 매핑
SORT_ZONE_MAP = {
    '1': 'A',  # 냉동
    '2': 'B',  # 냉장
    '3': 'C',  # 상온
    '0': 'E',  # 오류
    'A': 'A',
    'B': 'B',
    'C': 'C',
    'E': 'E'
}

# 메시지 생성 함수
def create_message(device, msg_type, payload):
    """통신 프로토콜에 맞는 메시지 생성"""
    return f"{device}{msg_type}{payload}\n"

# 메시지 파싱 함수
def parse_message(message):
    """수신된 메시지 파싱"""
    if not message or len(message) < 2:
        return None, None, None
        
    # 줄바꿈 제거
    message = message.strip()
    
    device = message[0]
    msg_type = message[1]
    payload = message[2:] if len(message) > 2 else ""
    
    return device, msg_type, payload

# 바코드 파싱 함수
def parse_barcode(barcode):
    """바코드 파싱: 1자리(구역) + 2자리(물품번호) + 6자리(유통기한)"""
    if not barcode or len(barcode) < 9:
        return None
        
    category_code = barcode[0]
    item_code = barcode[1:3]
    expiry_code = barcode[3:9]  # YYMMDD
    
    # 분류 존 결정
    category = SORT_ZONE_MAP.get(category_code, 'E')
    
    # 유통기한 변환
    try:
        year = f"20{expiry_code[0:2]}"
        month = expiry_code[2:4]
        day = expiry_code[4:6]
        expiry_date = f"{year}-{month}-{day}"
    except:
        expiry_date = None
        
    return {
        'barcode': barcode,
        'category': category,
        'item_code': item_code,
        'expiry_date': expiry_date
    }