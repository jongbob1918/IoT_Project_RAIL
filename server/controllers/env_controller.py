# server/controllers/env_controller.py
import logging
from typing import Dict, Any, Tuple
from enum import Enum
from datetime import datetime
import time

logger = logging.getLogger(__name__)

# ==== 환경 상태 열거형 ====
class EnvState(Enum):
    NORMAL = "normal"      # 정상 상태
    WARNING = "warning"    # 경고 상태
    DANGER = "danger"      # 위험 상태

# ==== 팬 모드 열거형 ====
class FanMode(Enum):
    OFF = "off"        # 정지
    COOLING = "cool"   # 냉방
    HEATING = "heat"   # 난방

# ==== 환경 컨트롤러 ====
class EnvController:
    # ==== 환경 컨트롤러 초기화 ====
    def __init__(self, tcp_handler, socketio=None, db_helper=None):
        self.tcp_handler = tcp_handler
        self.socketio = socketio
        self.db_helper = db_helper
        
        # 지원되는 창고 목록
        self.warehouses = ["A", "B", "C"]
        
        # 창고별 현재 측정 온도
        self.warehouse_temps = {
            "A": None,  # 냉동
            "B": None,  # 냉장
            "C": None   # 상온
        }
        
        # 창고별 목표 온도 설정
        self.target_temps = {
            "A": -24,   # 냉동 창고 목표 온도 기본값
            "B": 4.0,   # 냉장 창고 목표 온도 기본값
            "C": 20.0   # 상온 창고 목표 온도 기본값
        }
        
        # 창고별 환경 상태 (펌웨어에서 받은 값)
        self.env_states = {
            "A": EnvState.NORMAL,
            "B": EnvState.NORMAL,
            "C": EnvState.NORMAL
        }
        
        # 창고별 팬 상태 (펌웨어에서 받은 값)
        self.fan_status = {
            "A": {"mode": FanMode.OFF, "speed": 0},
            "B": {"mode": FanMode.OFF, "speed": 0},
            "C": {"mode": FanMode.OFF, "speed": 0}
        }
        
        # 창고별 경고 상태
        self.warning_status = {
            "A": False,
            "B": False,
            "C": False
        }
        
        # 창고별 온도 범위
        self.temp_ranges = {
            "A": (-30, -18),  # 냉동
            "B": (0, 10),     # 냉장
            "C": (15, 25)     # 상온
        }
        
        logger.info("환경 컨트롤러 초기화 완료")
    
    # ==== 온도 범위 반환 ====
    def get_temperature_range(self, warehouse: str) -> Tuple[int, int]:
        """특정 창고의 온도 범위를 반환합니다."""
        if warehouse in self.temp_ranges:
            return self.temp_ranges[warehouse]
        return (0, 0)  # 기본값
    
    # ==== 온도 업데이트 ====
    def update_temperature(self, warehouse: str, temp: float) -> Dict[str, Any]:
        """특정 창고의 온도를 업데이트하고 새 상태를 반환합니다."""
        if warehouse not in self.warehouse_temps:
            logger.warning(f"알 수 없는 창고 ID: {warehouse}")
            return {}
        
        prev_temp = self.warehouse_temps[warehouse]
        self.warehouse_temps[warehouse] = temp
        
        # 온도 변경 로그
        if prev_temp != temp:
            logger.debug(f"창고 {warehouse} 온도 변경: {prev_temp} → {temp}")
        
        # 온도 데이터 DB 저장 (필요한 경우)
        if self.db_helper:
            try:
                self.db_helper.insert_temperature_log(warehouse, temp)
            except Exception as e:
                logger.error(f"온도 로그 저장 오류: {str(e)}")
        
        # 상태 업데이트 이벤트 발송
        self._emit_status_update()
        
        return {
            "warehouse": warehouse,
            "temp": temp,
            "target_temp": self.target_temps[warehouse],
            "state": self.env_states[warehouse].value,
            "fan_mode": self.fan_status[warehouse]["mode"].value,
            "fan_speed": self.fan_status[warehouse]["speed"]
        }
    
    # ==== 목표 온도 설정 ====
    def set_target_temperature(self, warehouse: str, temperature: float) -> dict:
        """특정 창고의 목표 온도를 설정합니다."""
        if warehouse not in self.warehouses:
            return {
                "status": "error",
                "code": "E4001",
                "message": f"존재하지 않는 창고: {warehouse}",
                "auto_dismiss": 1000
            }
        
        # 유효 범위 확인
        min_temp, max_temp = self.get_temperature_range(warehouse)
        if temperature < min_temp or temperature > max_temp:
            return {
                "status": "error",
                "code": "E4002",
                "message": f"유효하지 않은 온도 값: {temperature}. 범위는 {min_temp}~{max_temp}입니다.",
                "auto_dismiss": 1000
            }
        
        # 온도 설정 명령 전송
        # HCpA-20\n - 하우스(H) 명령(C) 온도설정(p) A창고(A) -20도(-20)
        value = int(temperature)  # 정수로 변환 (소수점 버림)
        command = f"HCp{warehouse}{value}\n"
        
        success = self.tcp_handler.send_message("env_controller", command)
        if not success:
            return {
                "status": "error",
                "code": "E4003",
                "message": "환경 제어 통신 오류",
                "auto_dismiss": 1000
            }
        
        # 내부 상태 업데이트
        self.target_temps[warehouse] = temperature
        
        # 상태 업데이트 이벤트 발송
        self._emit_status_update()
        
        return {
            "status": "ok",
            "warehouse": warehouse,
            "target_temperature": temperature,
            "message": f"{warehouse} 창고 목표 온도를 {temperature}도로 설정했습니다."
        }
    
    # ==== 현재 환경 상태 반환 ====
    def get_status(self) -> dict:
        """API 응답용 상태 정보를 반환합니다."""
        warehouses = {}
        
        for wh in self.warehouses:
            warehouses[wh] = {
                "temp": self.warehouse_temps[wh],
                "target_temp": self.target_temps[wh],
                "status": self.env_states[wh].value if self.env_states[wh] else None,
                "fan_mode": self.fan_status[wh]["mode"].value,
                "fan_speed": self.fan_status[wh]["speed"],
                "warning": self.warning_status[wh]
            }
        
        return {
            "status": "ok",
            "data": {
                "warehouses": warehouses,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    # ==== 특정 창고의 환경 상태 반환 ====
    def get_warehouse_status(self, warehouse: str) -> Dict[str, Any]:
        """특정 창고의 환경 상태를 반환합니다."""
        if warehouse not in self.warehouses:
            return {
                "status": "error",
                "code": "E4001",
                "message": f"알 수 없는 창고 ID: {warehouse}"
            }
        
        return {
            "status": "ok",
            "warehouse": warehouse,
            "data": {
                "temp": self.warehouse_temps[warehouse],
                "target_temp": self.target_temps[warehouse],
                "status": self.env_states[warehouse].value if self.env_states[warehouse] else None,
                "fan_mode": self.fan_status[warehouse]["mode"].value,
                "fan_speed": self.fan_status[warehouse]["speed"],
                "warning": self.warning_status[warehouse]
            },
            "timestamp": datetime.now().isoformat()
        }
    
    # ==== 환경 제어 명령 처리 ====
    def handle_message(self, message: dict):
        """TCP 메시지를 처리합니다."""
        try:
            # 메시지 타입 확인
            msg_type = message.get("type", "")
            content = message.get("content", "")
            
            if msg_type == "event":
                # 이벤트 처리
                self._handle_event(content)
            elif msg_type == "response":
                # 응답 처리
                logger.debug(f"환경 제어 응답: {content}")
            elif msg_type == "error":
                # 오류 처리
                logger.error(f"환경 제어 오류: {content}")
                if self.socketio:
                    self.socketio.emit("environment_error", {
                        "error_code": content,
                        "error_message": f"환경 제어 오류: {content}"
                    })
        except Exception as e:
            logger.error(f"메시지 처리 오류: {str(e)}")
    
    # ==== 이벤트 처리 ====
    def _handle_event(self, content: str):
        """이벤트 메시지를 처리합니다."""
        try:
            # 이벤트 타입 확인
            if content.startswith('tp'):
                # 온도 이벤트
                self._handle_temperature_event(content)
            elif content.startswith('w') and len(content) >= 3:
                # 경고 이벤트
                warehouse = content[1]
                self._handle_warning_event(warehouse, content[2:])
            elif (content.startswith('A') or content.startswith('B') or content.startswith('C')) and len(content) >= 2:
                # 팬 상태 이벤트
                warehouse = content[0]
                self._handle_fan_status_event(warehouse, content[1:])
            else:
                logger.warning(f"알 수 없는 이벤트: {content}")
        except Exception as e:
            logger.error(f"이벤트 처리 오류: {str(e)}")
    
    # ==== 온도 이벤트 처리 ====
    def _handle_temperature_event(self, content: str):
        """온도 이벤트를 처리합니다."""
        # 값 추출 (tp-18.5;4.2;21.3 - 세미콜론으로 구분된 3개의 온도)
        if len(content) < 3:
            logger.warning(f"잘못된 온도 이벤트 형식: {content}")
            return
        
        # 온도 값 추출 (tp- 이후의 값)
        temp_data = content[2:]
        
        # 세미콜론으로 구분된 온도 값들 파싱
        temps = temp_data.split(';')
        
        # 각 창고별 온도 할당 (창고 순서는 A, B, C 순으로 가정)
        warehouses = ['A', 'B', 'C']
        
        for i, temp_str in enumerate(temps):
            if i >= len(warehouses):
                break
                
            try:
                temp = float(temp_str)
                warehouse = warehouses[i]
                
                # 온도 업데이트
                self.update_temperature(warehouse, temp)
            
            except ValueError:
                logger.warning(f"잘못된 온도 값 형식: {temp_str}")
    
    # ==== 경고 이벤트 처리 ====
    def _handle_warning_event(self, warehouse: str, warning_str: str):
        """창고 경고 이벤트를 처리합니다."""
        try:
            warning_state = int(warning_str) == 1
            
            # 내부 상태 업데이트
            self.warning_status[warehouse] = warning_state
            
            # 경고 상태에 따른 환경 상태 업데이트
            if warning_state:
                self.env_states[warehouse] = EnvState.WARNING
            else:
                self.env_states[warehouse] = EnvState.NORMAL
            
            # 소켓 이벤트 발송
            self._emit_socketio_event("warehouse_warning", {
                "warehouse": warehouse,
                "warning": warning_state
            })
            
        except ValueError:
            logger.warning(f"잘못된 경고 상태 값: {warning_str}")
    
    # ==== 팬 상태 이벤트 처리 ====
    def _handle_fan_status_event(self, warehouse: str, status_str: str):
        """팬 상태 이벤트를 처리합니다."""
        try:
            if len(status_str) < 2:
                logger.warning(f"잘못된 팬 상태 형식: {status_str}")
                return
            
            # 첫 문자: 모드(C=냉방, H=난방, 기타=OFF)
            mode_char = status_str[0]
            if mode_char == 'C':
                fan_mode = FanMode.COOLING
            elif mode_char == 'H':
                fan_mode = FanMode.HEATING
            else:
                fan_mode = FanMode.OFF
            
            # 두 번째 문자: 속도(0-3)
            speed = int(status_str[1])
            
            # 상태 업데이트
            self.fan_status[warehouse] = {
                "mode": fan_mode,
                "speed": speed
            }
            
            # 상태 업데이트 이벤트 발송
            self._emit_status_update()
            
        except (ValueError, IndexError):
            logger.warning(f"잘못된 팬 상태 값: {status_str}")
    
    # ==== Socket.IO 이벤트 발송 ====
    def _emit_socketio_event(self, event_name: str, data: dict):
        """WebSocket 이벤트를 발송합니다."""
        if not self.socketio:
            logger.warning(f"Socket.IO 없음 - 이벤트 발송 불가: {event_name}")
            return
        
        try:
            # 기본 네임스페이스와 /ws 네임스페이스 모두에 이벤트 발송
            standard_event = {
                "type": "event",
                "category": "environment",
                "action": event_name,
                "payload": data,
                "timestamp": int(time.time())
            }
            
            self.socketio.emit("event", standard_event)
            self.socketio.emit("event", standard_event, namespace='/ws')
            logger.debug(f"Socket.IO 이벤트 발송: {event_name}")
        except Exception as e:
            logger.error(f"Socket.IO 이벤트 발송 오류: {str(e)}")
    
    # ==== 상태 업데이트 이벤트 발송 ====
    def _emit_status_update(self):
        """환경 상태 업데이트 이벤트를 발송합니다."""
        self._emit_socketio_event("environment_update", self.get_status()["data"])