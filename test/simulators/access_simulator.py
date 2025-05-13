import random
from typing import Dict, Any
from .base_simulator import BaseSimulator

class AccessSimulator(BaseSimulator):
    """출입 제어 시뮬레이터
    
    기능:
    - RFID 태그 인식 시뮬레이션
    - 출입문 제어 상태 관리
    """
    
    def __init__(self, device_id: str = "gt_01", **kwargs):
        """출입 제어 시뮬레이터 초기화
        
        Args:
            device_id (str): 장치 ID
        """
        super().__init__(**kwargs)
        self.device_id = device_id
        
        # 등록된 RFID 태그 목록
        self.registered_tags = [
            "E39368F5",   # 김민준 
            "E47291A3",   # 이서연 
            "E58213F7"    # 박지훈 
        ]
        
        # 출입문 상태
        self.door_status = "closed"  # closed/open
        
    def handle_message(self, message: Dict[str, Any]):
        """서버 메시지 처리
        
        Args:
            message (Dict[str, Any]): 수신된 메시지
        """
        if message.get("tp") != "cmd":
            return
            
        cmd = message.get("cmd")
        if cmd == "door":
            self._handle_door_control(message)
            
    def _handle_door_control(self, message: Dict[str, Any]):
        """출입문 제어 명령 처리
        
        Args:
            message (Dict[str, Any]): 출입문 제어 명령
        """
        action = message.get("act")
        
        if action == "open":
            self.door_status = "open"
            self._send_response("door", "ok")
            self.logger.info("출입문 열림")
        elif action == "close":
            self.door_status = "closed"
            self._send_response("door", "ok")
            self.logger.info("출입문 닫힘")
        else:
            self._send_response("door", "error")
            self.logger.warning(f"알 수 없는 출입문 명령: {action}")
            
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
        
    def update_state(self):
        """상태 업데이트 및 이벤트 발생"""
        # 랜덤하게 RFID 태그 인식 이벤트 발생 (30% 확률)
        if random.random() < 0.3:
            # 랜덤하게 RFID 태그 선택
            tag = random.choice(self.registered_tags)
            
            # RFID 태그 인식 이벤트 전송
            self._send_event("rf", {"uid": tag})
            self.logger.info(f"RFID 태그 인식: {tag}")
        
    def _send_event(self, event: str, data: Dict[str, Any]):
        """이벤트 메시지 전송
        
        Args:
            event (str): 이벤트 유형
            data (Dict[str, Any]): 이벤트 데이터
        """
        message = {
            "dev": self.device_id,
            "tp": "evt",
            "evt": event,
            "val": data,
            "ts": self.get_timestamp()
        }
        self.send_message(message)

    def _generate_rfid(self) -> str:
        """랜덤 RFID 태그 ID 생성"""
        return ''.join(random.choices('0123456789ABCDEF', k=8)) 