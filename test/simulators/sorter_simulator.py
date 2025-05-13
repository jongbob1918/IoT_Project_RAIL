import random
from typing import Dict, Any
from .base_simulator import BaseSimulator

class SorterSimulator(BaseSimulator):
    """물류 분류기 시뮬레이터
    
    기능:
    - 바코드 스캔 시뮬레이션
    - 컨베이어 벨트 상태 관리
    - 분류 동작 시뮬레이션
    """
    
    def __init__(self, device_id: str = "sr_01", **kwargs):
        """분류기 시뮬레이터 초기화
        
        Args:
            device_id (str): 장치 ID
        """
        super().__init__(**kwargs)
        self.device_id = device_id
        self.running_status = "stopped"  # running/stopped/emergency
        self.conveyor_status = "idle"    # idle/running/error
        self.items_processed = 0
        self.items_waiting = 0
        
    def handle_message(self, message: Dict[str, Any]):
        """서버 메시지 처리
        
        Args:
            message (Dict[str, Any]): 수신된 메시지
        """
        if message.get("tp") != "cmd":
            return
            
        cmd = message.get("cmd")
        if cmd == "start":
            self._handle_start()
        elif cmd == "stop":
            self._handle_stop()
        elif cmd == "emergency":
            self._handle_emergency()
            
    def _handle_start(self):
        """분류 작업 시작 처리"""
        self.running_status = "running"
        self.conveyor_status = "running"
        self._send_response("start", "ok")
        
    def _handle_stop(self):
        """분류 작업 중지 처리"""
        self.running_status = "stopped"
        self.conveyor_status = "idle"
        self._send_response("stop", "ok")
        
    def _handle_emergency(self):
        """비상 정지 처리"""
        self.running_status = "emergency"
        self.conveyor_status = "idle"
        self._send_response("emergency", "ok")
        
    def _send_response(self, cmd: str, status: str):
        """응답 메시지 전송
        
        Args:
            cmd (str): 명령어
            status (str): 상태
        """
        message = {
            "dev": self.device_id,
            "tp": "res",
            "cmd": cmd,
            "res": status,
            "ts": self.get_timestamp()
        }
        self.send_message(message)
        
    def _send_event(self, event: str, value: Dict[str, Any]):
        """이벤트 메시지 전송
        
        Args:
            event (str): 이벤트 종류
            value (Dict[str, Any]): 이벤트 데이터
        """
        message = {
            "dev": self.device_id,
            "tp": "evt",
            "evt": event,
            "val": value,
            "ts": self.get_timestamp()
        }
        self.send_message(message)
        
    def update_state(self):
        """상태 업데이트 및 이벤트 발생"""
        if self.running_status != "running":
            return
            
        # 랜덤하게 바코드 스캔 이벤트 발생
        if random.random() < 0.3:  # 30% 확률
            barcode = self._generate_barcode()
            self._send_event("scan", {
                "code": barcode,
                "status": "success"
            })
            self.items_processed += 1
            
        # 랜덤하게 대기 물품 수 변경
        self.items_waiting = max(0, self.items_waiting + random.randint(-1, 2))
        
        # 상태 이벤트 전송
        self._send_event("status", {
            "running": self.running_status == "running",
            "conveyor": self.conveyor_status,
            "processed": self.items_processed,
            "waiting": self.items_waiting
        })
        
    def _generate_barcode(self) -> str:
        """랜덤 바코드 생성"""
        # 바코드 형식: YYMMDDNNNNN (연월일 + 5자리 일련번호)
        date = f"{random.randint(23, 25):02d}{random.randint(1, 12):02d}{random.randint(1, 28):02d}"
        serial = f"{random.randint(0, 99999):05d}"
        return date + serial 