import random
from typing import Dict, Any
from .base_simulator import BaseSimulator

class EnvironmentSimulator(BaseSimulator):
    """창고 환경 제어 시뮬레이터
    
    기능:
    - 온도/습도 센서 시뮬레이션
    - 팬 제어 상태 관리
    - 환경 변화 시뮬레이션
    """
    
    def __init__(self, device_id: str = "hs_ab", **kwargs):
        """환경 제어 시뮬레이터 초기화
        
        Args:
            device_id (str): 장치 ID
        """
        super().__init__(**kwargs)
        self.device_id = device_id
        
        # 창고별 초기 설정
        self.warehouses = {
            "A": {"temp": -20.0, "target_temp": -20.0, "fan_mode": "off", "fan_speed": 0},
            "B": {"temp": 5.0, "target_temp": 5.0, "fan_mode": "off", "fan_speed": 0}
        }
        
        # 온도 변화 시뮬레이션을 위한 설정
        self.temp_change_rate = 0.5  # 분당 최대 온도 변화
        
    def handle_message(self, message: Dict[str, Any]):
        """서버 메시지 처리
        
        Args:
            message (Dict[str, Any]): 수신된 메시지
        """
        if message.get("tp") != "cmd":
            return
            
        cmd = message.get("cmd")
        if cmd == "fan":
            self._handle_fan_control(message)
            
    def _handle_fan_control(self, message: Dict[str, Any]):
        """팬 제어 명령 처리
        
        Args:
            message (Dict[str, Any]): 팬 제어 명령
        """
        warehouse = message.get("val", {}).get("wh")
        mode = message.get("val", {}).get("md")
        speed = message.get("val", {}).get("sp", 0)
        
        if warehouse in self.warehouses:
            self.warehouses[warehouse]["fan_mode"] = mode
            self.warehouses[warehouse]["fan_speed"] = speed
            self._send_response("fan", "ok")
        else:
            self._send_response("fan", "error")
            
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
        # 각 창고의 온도 변화 시뮬레이션
        for wh_id, warehouse in self.warehouses.items():
            # 팬 동작에 따른 온도 변화
            if warehouse["fan_mode"] != "off":
                target = warehouse["target_temp"]
                current = warehouse["temp"]
                speed_factor = warehouse["fan_speed"] / 3.0  # 팬 속도에 따른 효율
                
                if warehouse["fan_mode"] == "cool" and current > target:
                    change = -self.temp_change_rate * speed_factor
                elif warehouse["fan_mode"] == "heat" and current < target:
                    change = self.temp_change_rate * speed_factor
                else:
                    change = 0
            else:
                # 자연 온도 변화 (외부 요인)
                change = random.uniform(-0.2, 0.2)
                
            # 온도 업데이트
            warehouse["temp"] = round(warehouse["temp"] + change, 1)
            
        # 온도 상태 이벤트 전송
        status_data = {
            wh_id: {
                "t": warehouse["temp"],
                "st": self._get_temperature_status(wh_id, warehouse["temp"])
            }
            for wh_id, warehouse in self.warehouses.items()
        }
        
        self._send_event("tmp", status_data)
        
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
        
    def _get_temperature_status(self, warehouse_id: str, temperature: float) -> str:
        """온도에 따른 상태 판단
        
        Args:
            warehouse_id (str): 창고 ID
            temperature (float): 현재 온도
            
        Returns:
            str: 상태 (norm/warn/dang)
        """
        # 창고별 온도 범위 정의
        ranges = {
            "A": {"norm": (-25, -15), "warn": (-30, -10)},  # 냉동
            "B": {"norm": (2, 8), "warn": (0, 10)}          # 냉장
        }
        
        range_info = ranges.get(warehouse_id)
        if not range_info:
            return "warn"
            
        if range_info["norm"][0] <= temperature <= range_info["norm"][1]:
            return "norm"
        elif range_info["warn"][0] <= temperature <= range_info["warn"][1]:
            return "warn"
        else:
            return "dang" 