"""
TCP 클라이언트 테스트 도구
하드웨어 장치와의 통신을 시뮬레이션하기 위한 테스트 클라이언트
"""
import socket
import sys
import time
import json
from config import TCP_PORT, SERVER_HOST

def test_tcp_connection(host=SERVER_HOST, port=TCP_PORT):
    """서버와의 TCP 연결을 테스트합니다."""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((host, port))
        print(f"서버 {host}:{port}에 연결되었습니다.")
        
        # 테스트 메시지 전송
        test_message = {
            "type": "test",
            "message": "테스트 메시지",
            "timestamp": time.time()
        }
        client.sendall((json.dumps(test_message) + "\n").encode())
        
        # 응답 수신
        response = client.recv(1024)
        print(f"서버 응답: {response.decode()}")
        
        return True
    except Exception as e:
        print(f"연결 오류: {e}")
        return False
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) > 2:
        # 명령줄 인수로 호스트와 포트 지정
        host = sys.argv[1]
        port = int(sys.argv[2])
        test_tcp_connection(host, port)
    else:
        # 기본값 사용
        test_tcp_connection()