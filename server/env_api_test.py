#!/usr/bin/env python3
"""
환경 제어 시스템 API 테스트 도구
HTTP API를 통해 환경 제어 시스템을 테스트합니다.
"""

import requests
import json
import time
import sys
import argparse

# 기본 서버 정보
DEFAULT_HOST = "127.0.0.1"  # 또는 실제 서버 IP
DEFAULT_PORT = 8000

def send_temperature_command(warehouse, temperature, host=DEFAULT_HOST, port=DEFAULT_PORT):
    """환경 제어 시스템에 온도 설정 명령을 전송합니다."""
    url = f"http://{host}:{port}/api/environment/temperature"
    
    # API 요청 데이터
    payload = {
        "warehouse": warehouse,
        "temperature": temperature
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print(f"API 요청: {url}")
        print(f"데이터: {json.dumps(payload, indent=2)}")
        
        # API 호출
        response = requests.post(url, json=payload, headers=headers)
        
        # 응답 출력
        print(f"상태 코드: {response.status_code}")
        print(f"응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        return response.status_code == 200
    
    except Exception as e:
        print(f"API 요청 오류: {e}")
        return False

def run_env_test_sequence(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """환경 제어 시스템 테스트 시퀀스 실행"""
    test_cases = [
        {"warehouse": "A", "temperature": -20},  # A 창고 목표 온도 -20도 설정
        {"warehouse": "B", "temperature": 5},    # B 창고 목표 온도 5도 설정
        {"warehouse": "C", "temperature": 22},   # C 창고 목표 온도 22도 설정
        {"warehouse": "X", "temperature": 34}    # 에러 테스트 (잘못된 창고 ID)
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\n테스트 케이스 {i+1}: {test['warehouse']} 창고 {test['temperature']}도 설정")
        send_temperature_command(test["warehouse"], test["temperature"], host, port)
        time.sleep(1)  # 요청 간 딜레이

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="환경 제어 시스템 API 테스트")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"서버 호스트 (기본값: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"서버 포트 (기본값: {DEFAULT_PORT})")
    parser.add_argument("--warehouse", help="단일 테스트용 창고 ID (A, B, C)")
    parser.add_argument("--temperature", type=float, help="단일 테스트용 온도 값")
    
    args = parser.parse_args()
    
    # 단일 명령 테스트 또는
    if args.warehouse and args.temperature is not None:
        print(f"\n{args.warehouse} 창고 온도를 {args.temperature}도로 설정 요청")
        send_temperature_command(args.warehouse, args.temperature, args.host, args.port)
    else:
        # 전체 테스트 시퀀스 실행
        print(f"\n환경 제어 시스템 API 테스트 시퀀스 시작 ({args.host}:{args.port})")
        run_env_test_sequence(args.host, args.port)

if __name__ == "__main__":
    main() 