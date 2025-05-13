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
            # 바이너리 데이터 판별 (WebSocket 프레임은 대부분 0x80-0xFF 범위의 바이트로 시작)
            is_probably_binary = len(data) > 0 and (data[0] & 0x80) != 0
            
            # WebSocket/바이너리 데이터는 간단하게만 로깅
            if is_probably_binary:
                tcp_logger.debug(f"바이너리 데이터 수신: {len(data)} 바이트")
                return data
                
            # 문자열로 변환 시도
            try:
                str_data = data.decode('utf-8', errors='replace')
                
                # ASCII 출력 가능 문자 비율 확인
                printable_chars = sum(1 for c in str_data if c.isprintable())
                if printable_chars / len(str_data) < 0.7:  # 70% 미만이 출력 가능한 문자면 바이너리 데이터로 간주
                    tcp_logger.debug(f"바이너리 데이터 수신: {len(data)} 바이트")
                    return data
                
                # 일반 텍스트 데이터 처리
                tcp_logger.debug(f"데이터 수신: {len(data)} 바이트")
                
                # 16진수 변환 (최대 50바이트까지만 출력)
                if len(data) > 50:
                    hex_data = ' '.join([f'{b:02x}' for b in data[:50]]) + '...'
                else:
                    hex_data = ' '.join([f'{b:02x}' for b in data])
                
                # 문자열 출력 (최대 100자까지만)
                if len(str_data) > 100:
                    log_str = str_data[:100] + '...'
                else:
                    log_str = str_data
                
                tcp_logger.debug(f"HEX: {hex_data}")
                tcp_logger.debug(f"STR: {log_str}")
                
            except:
                tcp_logger.debug(f"디코딩 불가능한 데이터: {len(data)} 바이트")
                
        except Exception as e:
            tcp_logger.error(f"데이터 디버깅 중 오류: {str(e)}")
    return data

# 소켓 recv 메소드 패치
socket.socket.recv = debug_recv
