#!/usr/bin/env python3
"""
TCP 클라이언트 테스트 도구 - 환경 컨트롤러용
환경 제어 하드웨어와의 통신을 시뮬레이션하기 위한 테스트 클라이언트
"""
import socket
import sys
import time
import binascii
from config import TCP_PORT, HARDWARE_IP

def send_env_command(command, host=HARDWARE_IP.get('env_controller', '192.168.2.4'), port=TCP_PORT):
    """환경 제어 시스템에 명령을 전송합니다."""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"서버 {host}:{port}에 연결 시도...")
        client.connect((host, port))
        print(f"서버 {host}:{port}에 연결되었습니다.")
        
        # 명령에 \n이 없으면 추가
        if not command.endswith('\n'):
            command += '\n'
        
        # 명령 전송 (바이너리로 변환)
        binary_data = command.encode('utf-8')
        print(f"전송 명령: {command.strip()}")
        print(f"바이너리 데이터: {binascii.hexlify(binary_data).decode()}")
        
        client.sendall(binary_data)
        
        # 응답 대기 (5초 타임아웃)
        client.settimeout(5.0)
        try:
            response = client.recv(1024)
            print(f"바이너리 응답: {binascii.hexlify(response).decode()}")
            print(f"텍스트 응답: {response.decode('utf-8', errors='replace').strip()}")
        except socket.timeout:
            print("응답 대기 시간 초과")
        
        return True
    except Exception as e:
        print(f"연결 오류: {e}")
        return False
    finally:
        client.close()

def format_env_command(warehouse, temperature):
    """올바른 형식의 환경 제어 명령을 생성합니다."""
    # 형식: HCp[창고ID][온도값]
    # 예: HCpA-20, HCpB5, HCpC22
    temp_str = str(int(temperature))  # 정수로 변환
    command = f"HCp{warehouse}{temp_str}"
    return command

def run_env_test_sequence():
    """환경 제어 시스템 테스트 시퀀스 실행"""
    test_cases = [
        {"warehouse": "A", "temperature": -20},  # A 창고 목표 온도 -20도 설정
        {"warehouse": "B", "temperature": 5},    # B 창고 목표 온도 5도 설정
        {"warehouse": "C", "temperature": 22},   # C 창고 목표 온도 22도 설정
        {"warehouse": "X", "temperature": 34}    # 에러 테스트 (잘못된 창고 ID)
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\n테스트 케이스 {i+1}: {test['warehouse']} 창고 {test['temperature']}도 설정")
        command = format_env_command(test["warehouse"], test["temperature"])
        send_env_command(command)
        time.sleep(2)  # 명령 간 딜레이

def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        if len(sys.argv) >= 3 and sys.argv[1] == '--warehouse' and sys.argv[3] == '--temperature':
            # 창고 및 온도 지정 방식
            warehouse = sys.argv[2]
            temperature = float(sys.argv[4])
            command = format_env_command(warehouse, temperature)
        else:
            # 직접 명령 지정 방식
            command = sys.argv[1]
        
        print(f"\n명령 전송: {command}")
        send_env_command(command)
    else:
        # 전체 테스트 시퀀스 실행
        print("\n환경 제어 시스템 테스트 시퀀스 시작")
        run_env_test_sequence()

if __name__ == "__main__":
    main() 