#!/usr/bin/env python3
"""
분류기 시뮬레이터
서버와의 통신을 테스트하기 위한 가상 분류기 장치

사용법:
python sorter_simulator.py [host] [port]

예시:
python sorter_simulator.py localhost 5000
"""

import socket
import time
import sys
import threading
import random
from datetime import datetime, timedelta

# 기본 설정
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 5000
BUFFER_SIZE = 1024

# 프로토콜 정의
DEVICE_ID = 'S'  # 분류기
MSG_EVENT = 'E'  # 이벤트
MSG_COMMAND = 'C'  # 명령
MSG_RESPONSE = 'R'  # 응답
MSG_ERROR = 'X'  # 에러

# 분류기 상태
running = False
ir_sensor_active = False
sorting_active = False

# 명령 및 이벤트 정의
EVT_IR = 'ir'
EVT_BARCODE = 'bc'
EVT_SORTED = 'ss'
CMD_START = 'st'
CMD_STOP = 'sp'
CMD_PAUSE = 'ps'
CMD_SORT = 'so'
RESP_OK = 'ok'
ERROR_COMM = 'e1'
ERROR_SENSOR = 'e2'

# 테스트용 바코드 목록
TEST_BARCODES = [
    "112230501",  # 1: 냉동, 12: 물품번호, 230501: 유통기한
    "223230610",  # 2: 냉장, 23: 물품번호, 230610: 유통기한 
    "334230715",  # 3: 상온, 34: 물품번호, 230715: 유통기한
    "045230820",  # 0: 에러, 45: 물품번호, 230820: 유통기한
]

def create_message(msg_type, payload):
    """프로토콜에 맞는 메시지 생성"""
    return f"{DEVICE_ID}{msg_type}{payload}\n"

def parse_message(message):
    """수신 메시지 파싱"""
    if len(message) < 2:
        return None, None
        
    msg_type = message[1]
    payload = message[2:].strip()
    
    return msg_type, payload

def send_message(sock, message):
    """소켓을 통해 메시지 전송"""
    try:
        sock.sendall(message.encode('utf-8'))
        print(f">> 송신: {message.strip()}")
        return True
    except Exception as e:
        print(f"전송 오류: {e}")
        return False

def connect_to_server(host, port):
    """서버에 TCP 연결"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
        print(f"서버 {host}:{port}에 연결됨")
        return sock
    except Exception as e:
        print(f"연결 실패: {e}")
        return None

def handle_command(sock, command):
    """서버로부터 받은 명령 처리"""
    global running, sorting_active
    
    msg_type, payload = parse_message(command)
    
    if msg_type != MSG_COMMAND:
        return
        
    cmd = payload[:2]
    args = payload[2:] if len(payload) > 2 else ""
    
    # 명령 처리
    if cmd == CMD_START:
        running = True
        print("분류기 시작됨")
        # 응답 전송
        response = create_message(MSG_RESPONSE, RESP_OK)
        send_message(sock, response)
        
    elif cmd == CMD_STOP:
        running = False
        print("분류기 정지됨")
        # 응답 전송
        response = create_message(MSG_RESPONSE, RESP_OK)
        send_message(sock, response)
        
    elif cmd == CMD_PAUSE:
        running = False
        print("분류기 일시정지됨")
        # 응답 전송
        response = create_message(MSG_RESPONSE, RESP_OK)
        send_message(sock, response)
        
    elif cmd == CMD_SORT:
        if not running:
            print(f"분류 명령 실패 - 분류기 정지 상태: {args}")
            error = create_message(MSG_ERROR, ERROR_COMM)
            send_message(sock, error)
            return
            
        zone = args if args else "E"
        print(f"분류 명령 수신 - 구역: {zone}")
        
        # 분류 완료 이벤트 전송 (1초 후)
        threading.Timer(1.0, send_sort_complete, args=[sock, zone]).start()
        
        # 응답 전송
        response = create_message(MSG_RESPONSE, RESP_OK)
        send_message(sock, response)
    
    else:
        print(f"알 수 없는 명령: {cmd}")
        # 오류 응답
        error = create_message(MSG_ERROR, ERROR_COMM)
        send_message(sock, error)

def send_ir_event(sock):
    """IR 센서 감지 이벤트 전송"""
    if not running:
        return
        
    event = create_message(MSG_EVENT, f"{EVT_IR}1")
    send_message(sock, event)
    print("IR 센서 이벤트 발송")
    
    # 1초 후 바코드 인식 이벤트 전송
    threading.Timer(1.0, send_barcode_event, args=[sock]).start()

def send_barcode_event(sock):
    """바코드 인식 이벤트 전송"""
    if not running:
        return
        
    # 랜덤 바코드 선택
    barcode = random.choice(TEST_BARCODES)
    event = create_message(MSG_EVENT, f"{EVT_BARCODE}{barcode}")
    send_message(sock, event)
    print(f"바코드 인식 이벤트 발송: {barcode}")

def send_sort_complete(sock, zone):
    """분류 완료 이벤트 전송"""
    if not running:
        return
        
    event = create_message(MSG_EVENT, f"{EVT_SORTED}{zone}")
    send_message(sock, event)
    print(f"분류 완료 이벤트 발송: {zone}")

def receive_messages(sock):
    """서버로부터 메시지 수신"""
    try:
        while True:
            data = sock.recv(BUFFER_SIZE)
            if not data:
                print("서버와의 연결이 종료됨")
                break
                
            messages = data.decode('utf-8').split('\n')
            for msg in messages:
                if msg:
                    print(f"<< 수신: {msg}")
                    handle_command(sock, msg)
    except Exception as e:
        print(f"수신 오류: {e}")
    finally:
        sock.close()
        print("연결 종료됨")

def simulate_flow(sock):
    """분류 작업 흐름 시뮬레이션"""
    global running
    
    try:
        while True:
            cmd = input("\n명령을 입력하세요 (start/stop/ir/bc/quit): ")
            
            if cmd == "quit":
                print("시뮬레이터 종료")
                break
                
            elif cmd == "start":
                # 분류기 시작 명령 (자체적으로)
                running = True
                print("분류기 시작됨")
                
            elif cmd == "stop":
                # 분류기 정지 명령 (자체적으로)
                running = False
                print("분류기 정지됨")
                
            elif cmd == "ir":
                # IR 센서 이벤트 트리거
                send_ir_event(sock)
                
            elif cmd == "bc":
                # 바코드 인식 이벤트 트리거
                send_barcode_event(sock)
                
            elif cmd.startswith("bc "):
                # 특정 바코드 전송
                barcode = cmd[3:]
                event = create_message(MSG_EVENT, f"{EVT_BARCODE}{barcode}")
                send_message(sock, event)
                print(f"바코드 인식 이벤트 발송: {barcode}")
                
            elif cmd == "auto":
                # 자동 모드: 5초마다 IR 센서 감지
                print("자동 모드 시작 (종료: Ctrl+C)")
                while running:
                    send_ir_event(sock)
                    time.sleep(5)
            
            elif cmd == "help":
                print("""
명령어 목록:
  start - 분류기 시작
  stop - 분류기 정지
  ir - IR 센서 이벤트 발생
  bc - 랜덤 바코드 이벤트 발생
  bc 123456789 - 특정 바코드 이벤트 발생
  auto - 자동 모드 (5초마다 작업 발생)
  quit - 종료
  help - 도움말
                """)
            else:
                print(f"알 수 없는 명령: {cmd} (help 입력으로 도움말 확인)")
                
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
    except Exception as e:
        print(f"시뮬레이션 오류: {e}")

def main():
    """메인 함수"""
    # 호스트, 포트 설정
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    # 서버 연결
    sock = connect_to_server(host, port)
    if not sock:
        print("프로그램 종료")
        return
    
    # 수신 스레드 시작
    receive_thread = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    receive_thread.start()
    
    # 시뮬레이션 시작
    print("\n=== 분류기 시뮬레이터 ===")
    print(f"연결: {host}:{port}")
    print("명령어를 입력하세요 (help 입력으로 도움말 확인)")
    
    simulate_flow(sock)
    
    # 소켓 닫기
    try:
        sock.close()
    except:
        pass
    
    print("프로그램 종료")

if __name__ == "__main__":
    main() 