# server/utils/tcp_debug_helper.py
import logging
import sys

# 로깅 레벨을 DEBUG로 설정
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# 콘솔 핸들러 추가
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# TCP 핸들러 모듈에 대한 로깅 개선
tcp_logger = logging.getLogger('server.utils.tcp_handler')
tcp_logger.setLevel(logging.DEBUG)

# 원본 recv 메소드 패치 
import socket
original_recv = socket.socket.recv

def debug_recv(self, *args, **kwargs):
    data = original_recv(self, *args, **kwargs)
    if data:
        try:
            # 16진수로 변환
            hex_data = ' '.join([f'{b:02x}' for b in data])
            # 문자열로 변환 (디코딩 오류 처리)
            try:
                str_data = data.decode('utf-8', errors='replace')
            except:
                str_data = "[디코딩 불가]"
            
            # 원시 데이터 로깅
            tcp_logger.debug(f"데이터 수신: {len(data)} 바이트")
            tcp_logger.debug(f"HEX: {hex_data}")
            tcp_logger.debug(f"STR: {str_data}")
        except Exception as e:
            tcp_logger.error(f"데이터 디버깅 중 오류: {str(e)}")
    return data

# 소켓 recv 메소드 패치
socket.socket.recv = debug_recv
