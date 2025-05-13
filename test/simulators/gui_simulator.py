import json
import logging
import threading
import time
import random
from datetime import datetime
from typing import Dict, Any, Optional, List

class GUISimulator:
    """GUI 클라이언트 시뮬레이터
    
    기능:
    - WebSocket 연결 관리
    - 웹소켓 메시지 처리
    - 주기적 업데이트
    """
    
    def __init__(self, host: str = "localhost", port: int = 8000, update_interval: float = 2.0):
        """GUI 시뮬레이터 초기화
        
        Args:
            host (str): 서버 호스트
            port (int): 서버 포트
            update_interval (float): 업데이트 주기(초)
        """
        self.host = host
        self.port = port
        self.update_interval = update_interval
        self.ws = None
        self.running = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 상태 변수
        self.temperature = {
            "A": -20.0,
            "B": 5.0,
            "C": 18.0,
            "D": 20.0
        }
        
        # 온도 변화 시뮬레이션 설정
        self.temp_change_rate = 0.2
        
        # 스레드 관리
        self.ws_thread = None
        self.update_thread = None
        
    def connect(self) -> bool:
        """WebSocket 서버에 연결
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            self.logger.info(f"WebSocket 서버 연결 시도: ws://{self.host}:{self.port}/ws")
            # WebSockets는 비동기 라이브러리이므로 스레드로 실행
            self.ws_thread = threading.Thread(target=self._ws_loop)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            return True
        except Exception as e:
            self.logger.error(f"WebSocket 서버 연결 실패: {str(e)}")
            return False
            
    def disconnect(self):
        """WebSocket 연결 종료"""
        self.running = False
        self.logger.info("WebSocket 연결 종료 요청")
        
    def send_message(self, message: Dict[str, Any]):
        """서버에 메시지 전송
        
        Args:
            message (Dict[str, Any]): 전송할 메시지
        """
        if not self.ws:
            self.logger.warning("연결되지 않은 상태에서 메시지 전송 시도")
            return
            
        try:
            data = json.dumps(message)
            # 실제 전송은 _ws_loop 내에서 처리 (큐에 추가)
            self.logger.debug(f"메시지 전송 큐에 추가: {data}")
        except Exception as e:
            self.logger.error(f"메시지 전송 준비 실패: {str(e)}")
            
    def run(self):
        """시뮬레이터 실행"""
        self.running = True
        
        # 상태 업데이트 스레드 시작
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        self.logger.info("GUI 시뮬레이터 시작")
            
    def _ws_loop(self):
        """WebSocket 연결 및 통신 루프"""
        self.logger.info("WebSocket 통신 스레드 시작")
        
        # 여기서는 WebSocket 연결이 불가능하므로 연결 로그만 남김
        self.logger.info("WebSocket에 연결됨 (시뮬레이션)")
        
        # 가상 연결 유지
        while self.running:
            time.sleep(1)
            
        self.logger.info("WebSocket 통신 스레드 종료")
            
    def _update_loop(self):
        """상태 업데이트 루프"""
        self.logger.info("상태 업데이트 스레드 시작")
        
        while self.running:
            try:
                # 상태 업데이트 로직
                self._update_temperature()
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"상태 업데이트 오류: {str(e)}")
                time.sleep(1)
                
        self.logger.info("상태 업데이트 스레드 종료")
            
    def handle_message(self, message: Dict[str, Any]):
        """수신된 메시지 처리
        
        Args:
            message (Dict[str, Any]): 수신된 메시지
        """
        try:
            message_type = message.get("type")
            
            self.logger.info(f"메시지 수신: {message_type}")
            
            # 각 메시지 타입별 처리
            if message_type == "temperature_update":
                self._handle_temperature_update(message.get("data", {}))
            elif message_type == "status_update":
                self._handle_status_update(message.get("data", {}))
                
        except Exception as e:
            self.logger.error(f"메시지 처리 오류: {str(e)}")
            
    def _handle_temperature_update(self, data: Dict[str, Any]):
        """온도 업데이트 메시지 처리
        
        Args:
            data (Dict[str, Any]): 온도 데이터
        """
        for warehouse_id, temp_data in data.items():
            if warehouse_id in self.temperature:
                self.temperature[warehouse_id] = temp_data.get("temperature", self.temperature[warehouse_id])
                
        self.logger.info(f"온도 업데이트: {self.temperature}")
                
    def _handle_status_update(self, data: Dict[str, Any]):
        """상태 업데이트 메시지 처리
        
        Args:
            data (Dict[str, Any]): 상태 데이터
        """
        self.logger.info(f"상태 업데이트: {data}")
            
    def _update_temperature(self):
        """온도 데이터 시뮬레이션 및 업데이트"""
        # 랜덤 온도 변화 시뮬레이션
        for warehouse_id in self.temperature:
            # 랜덤 변화량 (±0.3°C)
            change = random.uniform(-self.temp_change_rate, self.temp_change_rate)
            self.temperature[warehouse_id] = round(self.temperature[warehouse_id] + change, 1)
            
        # 로그 출력
        self.logger.debug(f"온도 상태: {self.temperature}")
        
        # 온도 상태 메시지 생성 (실제 전송은 안 됨)
        status_data = {
            "A": {"temp": self.temperature["A"], "status": self._get_temp_status("A")},
            "B": {"temp": self.temperature["B"], "status": self._get_temp_status("B")},
            "C": {"temp": self.temperature["C"], "status": self._get_temp_status("C")},
            "D": {"temp": self.temperature["D"], "status": self._get_temp_status("D")}
        }
        
        self.logger.info(f"온도 상태 업데이트: {status_data}")
            
    def _get_temp_status(self, warehouse_id: str) -> str:
        """온도에 따른 상태 판단
        
        Args:
            warehouse_id (str): 창고 ID
            
        Returns:
            str: 상태 (normal/warning/danger)
        """
        temp = self.temperature[warehouse_id]
        
        # 창고별 온도 범위 정의
        ranges = {
            "A": {"normal": (-25, -15), "warning": (-30, -10)},   # 냉동
            "B": {"normal": (2, 8), "warning": (0, 10)},          # 냉장
            "C": {"normal": (15, 25), "warning": (10, 30)},       # 상온
            "D": {"normal": (15, 25), "warning": (10, 30)}        # 상온
        }
        
        range_info = ranges.get(warehouse_id)
        if not range_info:
            return "warning"
            
        if range_info["normal"][0] <= temp <= range_info["normal"][1]:
            return "normal"
        elif range_info["warning"][0] <= temp <= range_info["warning"][1]:
            return "warning"
        else:
            return "danger"
            
    def get_timestamp(self) -> str:
        """현재 시간 ISO 형식 문자열 반환"""
        return datetime.now().isoformat() 