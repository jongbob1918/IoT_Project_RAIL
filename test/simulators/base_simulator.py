import json
import logging
import socket
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

class BaseSimulator:
    """모든 시뮬레이터의 기본 클래스
    
    공통 기능:
    - TCP 연결 관리
    - JSON 메시지 처리
    - 로깅
    - 주기적 상태 업데이트
    """
    
    def __init__(self, host: str = "localhost", port: int = 9000, update_interval: float = 5.0):
        """시뮬레이터 초기화
        
        Args:
            host (str): 서버 호스트
            port (int): 서버 포트
            update_interval (float): 상태 업데이트 주기(초)
        """
        self.host = host
        self.port = port
        self.update_interval = update_interval
        self.socket = None
        self.running = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 스레드
        self.receive_thread = None
        self.update_thread = None
        
    def connect(self) -> bool:
        """서버에 TCP 연결
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.logger.info(f"서버 연결 성공: {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"서버 연결 실패: {str(e)}")
            return False
            
    def disconnect(self):
        """서버 연결 종료"""
        if self.socket:
            try:
                self.socket.close()
                self.logger.info("서버 연결 종료")
            except Exception as e:
                self.logger.error(f"연결 종료 중 오류: {str(e)}")
                
    def send_message(self, message: Dict[str, Any]) -> bool:
        """서버에 메시지 전송
        
        Args:
            message (Dict[str, Any]): 전송할 메시지
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.socket:
            self.logger.error("연결되지 않은 상태에서 메시지 전송 시도")
            return False
            
        try:
            data = json.dumps(message)
            self.socket.sendall(f"{data}\n".encode())
            self.logger.debug(f"메시지 전송: {data}")
            return True
        except Exception as e:
            self.logger.error(f"메시지 전송 실패: {str(e)}")
            return False
            
    def receive_message(self) -> Optional[Dict[str, Any]]:
        """서버로부터 메시지 수신
        
        Returns:
            Optional[Dict[str, Any]]: 수신된 메시지
        """
        if not self.socket:
            self.logger.error("연결되지 않은 상태에서 메시지 수신 시도")
            return None
            
        try:
            # 줄바꿈까지 읽기
            buffer = b""
            while True:
                chunk = self.socket.recv(1)
                if not chunk:
                    return None
                    
                buffer += chunk
                if chunk == b'\n':
                    break
                    
            # JSON 파싱
            message = json.loads(buffer.decode().strip())
            self.logger.debug(f"메시지 수신: {message}")
            return message
        except Exception as e:
            self.logger.error(f"메시지 수신 실패: {str(e)}")
            return None
            
    def run(self):
        """시뮬레이터 실행"""
        self.running = True
        
        # 메시지 수신 스레드 시작
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        # 상태 업데이트 스레드 시작
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        self.logger.info(f"{self.__class__.__name__} 시작")
            
    def _receive_loop(self):
        """메시지 수신 루프"""
        while self.running:
            try:
                message = self.receive_message()
                if message:
                    self.handle_message(message)
                time.sleep(0.1)  # CPU 사용량 조절
            except Exception as e:
                self.logger.error(f"메시지 수신 루프 오류: {str(e)}")
                time.sleep(1)  # 오류 시 잠시 대기
                
    def _update_loop(self):
        """상태 업데이트 루프"""
        while self.running:
            try:
                self.update_state()
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"상태 업데이트 루프 오류: {str(e)}")
                time.sleep(1)  # 오류 시 잠시 대기
            
    def handle_message(self, message: Dict[str, Any]):
        """수신된 메시지 처리 (하위 클래스에서 구현)
        
        Args:
            message (Dict[str, Any]): 수신된 메시지
        """
        raise NotImplementedError
        
    def update_state(self):
        """상태 업데이트 (하위 클래스에서 구현)"""
        raise NotImplementedError
        
    def get_timestamp(self) -> str:
        """현재 시간 ISO 형식 문자열 반환"""
        return datetime.now().isoformat() 