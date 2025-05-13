#!/usr/bin/env python3
"""
간단한 TCP 명령 전송기 - 환경 제어기 테스트용
6초마다 명령어를 자동으로 전송합니다.
"""
import socket
import time
import sys

# 환경 제어기 정보
HOST = "192.168.2.4"  # 환경 제어기 IP
PORT = 9000  # TCP 포트

# 테스트할 명령어 목록
COMMANDS = [
    "HCpA-20\n",  # A 창고 목표 온도 -20도 설정
    "HCpB5\n",    # B 창고 목표 온도 5도 설정
    "HCpC22\n",   # C 창고 목표 온도 22도 설정
    "HCp34\n"     # 에러 테스트 (잘못된 창고 ID)
]

def send_command(cmd, host=HOST, port=PORT):
    """명령어를 TCP로 전송합니다."""
    try:
        # 소켓 생성 및 연결
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)  # 3초 타임아웃
        sock.connect((host, port))
        
        # 명령어 전송
        print(f"전송: {cmd.strip()}")
        sock.sendall(cmd.encode('utf-8'))
        
        # 응답 대기
        try:
            response = sock.recv(1024)
            print(f"응답: {response.decode('utf-8', errors='replace').strip()}")
        except socket.timeout:
            print("응답 없음 (타임아웃)")
        
        # 소켓 종료
        sock.close()
        return True
        
    except ConnectionRefusedError:
        print(f"연결 거부됨 - {host}:{port}가 열려있지 않음")
        return False
    except Exception as e:
        print(f"오류: {e}")
        return False

def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        # IP 주소가 명령줄 인수로 제공된 경우
        global HOST
        HOST = sys.argv[1]
        print(f"환경 제어기 IP: {HOST}")
    
    print(f"환경 제어기 {HOST}:{PORT}에 6초마다 명령 전송 시작...")
    
    # 명령어 순환 전송
    cmd_index = 0
    try:
        while True:
            # 다음 명령어 선택
            cmd = COMMANDS[cmd_index]
            cmd_index = (cmd_index + 1) % len(COMMANDS)
            
            # 명령어 전송
            send_command(cmd)
            
            # 6초 대기
            print("6초 대기 중...")
            time.sleep(6)
            
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")

if __name__ == "__main__":
    main() 