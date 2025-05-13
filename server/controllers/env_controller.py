# server/controllers/env_controller.py
import logging
from typing import Dict, Any, Tuple
from enum import Enum
from datetime import datetime
import time
from config import CONFIG
from controllers.base_controller import BaseController

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
class EnvController(BaseController):
    # ==== 환경 컨트롤러 초기화 ====
    def __init__(self, tcp_handler, socketio=None, db_helper=None):
        super().__init__(tcp_handler, socketio, db_helper)
        self.warehouses = list(CONFIG["WAREHOUSES"].keys())
        self.warehouse_temps = {wh: None for wh in self.warehouses}
        self.target_temps = {
            wh: (CONFIG["WAREHOUSES"][wh]["temp_min"] + CONFIG["WAREHOUSES"][wh]["temp_max"]) / 2
            for wh in self.warehouses
        }
        self.env_states = {wh: EnvState.NORMAL for wh in self.warehouses}
        self.fan_status = {wh: {"mode": FanMode.OFF, "speed": 0} for wh in self.warehouses}
        self.warning_status = {wh: False for wh in self.warehouses}
        self.temp_ranges = {
            wh: (CONFIG["WAREHOUSES"][wh]["temp_min"], CONFIG["WAREHOUSES"][wh]["temp_max"])
            for wh in self.warehouses
        }
        self.register_handlers()
        logger.info("환경 컨트롤러 초기화 완료")

    def register_handlers(self):
        # TCP 핸들러에 이벤트 핸들러 등록
        self.tcp_handler.register_device_handler('env_controller', 'evt', self.handle_event)
        self.tcp_handler.register_device_handler('env_controller', 'res', self.handle_response)

    # ==== 이벤트 처리 ====
    def handle_event(self, message_data):
        """TCP 핸들러로부터 이벤트 수신 시 호출되는 메서드"""
        if 'content' in message_data:
            self.process_event(message_data['content'])

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
        
        # 온도 데이터 DB 저장 (경고 상태일 때만)
        if self.db_helper and self.warning_status[warehouse]:
            try:
                self.db_helper.insert_temperature_log(warehouse, temp)
                logger.debug(f"경고 상태 - 창고 {warehouse} 온도 로그 저장: {temp}°C")
            except Exception as e:
                logger.error(f"온도 로그 저장 오류: {str(e)}")
        
        # 목표 온도와의 차이 계산 (정보 제공용)
        target_temp = self.target_temps[warehouse]
        temp_diff = target_temp - temp
        
        # 온도 차이가 너무 크면 경고 상태로 설정 (자동 제어는 하지 않음)
        # 실제 제어는 펌웨어에서 수행
        if abs(temp_diff) > 5.0 and self.env_states[warehouse] != EnvState.WARNING:
            logger.warning(f"창고 {warehouse} 온도 차이 큼: 목표={target_temp}, 현재={temp}, 차이={temp_diff}")
        
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
        """특정 창고의 목표 온도를 설정합니다.
        
        형식:
        - HCpA-20 -> A 창고 목표 온도 -20도 설정
        - HCpB5  -> B 창고 목표 온도 5도 설정
        - HCpC22 -> C 창고 목표 온도 22도 설정
        """
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
                self.process_event(content)
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
    
    # process_event 메서드 수정
    def process_event(self, content: str):
        # 온도 이벤트: HEtp-19.1;4.2;19.3 (하우스 → 서버)
        if content.startswith('HEtp'):
            # 'HEtp' 다음의 모든 데이터 전달
            self._handle_temperature_event(content[4:])
            return
        # 온도 이벤트 (단축형): tp-19.1;4.2;19.3
        elif content.startswith('tp'):
            # 디버그 로그 추가
            logger.debug(f"단축형 온도 이벤트 수신: {content}")
            # 'tp' 다음의 모든 데이터 전달 (마이너스 부호 포함)
            temp_data = content[2:]
            logger.debug(f"온도 데이터 추출: {temp_data}")
            self._handle_temperature_event(temp_data)
            return
        
                
        # 팬 상태 이벤트: HEAC2, HEBC2, HECH1 (하우스 → 서버)
        if content.startswith('HE') and len(content) >= 4:
            warehouse = content[2:3]
            if warehouse in ['A', 'B', 'C']:
                fan_status = content[3:] if len(content) > 3 else ""
                self._handle_fan_status_event(warehouse, fan_status)
                return
                
        # 응답 메시지: HRok (성공), HXe1 (오류)
        if content.startswith('HR') or content.startswith('HX'):
            logger.info(f"환경 제어 응답 수신: {content}")
            return
        
        self.logger.warning(f"알 수 없는 이벤트 형식: {content}")
    
    # _handle_temperature_event 메서드 수정
    def _handle_temperature_event(self, content: str):
        """온도 이벤트를 처리합니다.
        
        형식: 
        - -18.5;4.2;21.3 -> A(-18.5), B(4.2), C(21.3) 창고 온도
        """
        try:
            # 값이 없으면 처리 중단
            if not content:
                logger.warning("온도 데이터 없음")
                return
            
            logger.debug(f"온도 이벤트 처리 시작: {content}")
            
            # 세미콜론으로 구분된 온도 값들 파싱
            temps = content.split(';')
            logger.debug(f"파싱된 온도 값: {temps}")
            
            # 각 창고별 온도 할당 (창고 순서는 A, B, C 순으로 가정)
            warehouses = ['A', 'B', 'C']
            
            for i, temp_str in enumerate(temps):
                if i >= len(warehouses):
                    break
                    
                try:
                    # 온도 문자열 정리 (공백 제거)
                    temp_str = temp_str.strip()
                    logger.debug(f"창고 {warehouses[i]} 온도 문자열: '{temp_str}'")
                    
                    # 온도 파싱
                    try:
                        temp = float(temp_str)
                        warehouse = warehouses[i]

                        # 온도 업데이트
                        self.update_temperature(warehouse, temp)
                        logger.debug(f"창고 {warehouse} 온도 업데이트: {temp}°C")
                    except ValueError as ve:
                        logger.warning(f"온도 변환 오류 ('{temp_str}'): {ve}")
                        continue
                
                except Exception as e:
                    logger.warning(f"온도 처리 개별 오류: {e}, 값: '{temp_str}'")
        except Exception as e:
            logger.error(f"온도 이벤트 처리 오류: {str(e)}")
            logger.error(f"원인 데이터: {content}")
    
    # ==== 경고 이벤트 처리 ====
    def _handle_warning_event(self, warehouse: str, warning_str: str):

        try:
            # 데이터 유효성 확인
            if warehouse not in self.warehouses:
                logger.warning(f"알 수 없는 창고 ID: {warehouse}")
                return
                
            # 경고 상태 파싱
            try:
                warning_state = int(warning_str) == 1
            except ValueError:
                logger.warning(f"잘못된 경고 상태 값: {warning_str}, 기본값 False 사용")
                warning_state = False
            
            # 내부 상태 업데이트
            self.warning_status[warehouse] = warning_state
            
            # 경고 상태에 따른 환경 상태 업데이트
            if warning_state:
                self.env_states[warehouse] = EnvState.WARNING
                logger.info(f"창고 {warehouse} 경고 발생")
                
                # 경고 상태를 DB에 기록 (있는 경우)
                if self.db_helper:
                    try:
                        # 현재 온도 가져오기
                        current_temp = self.warehouse_temps[warehouse]
                        if current_temp is not None:
                            # 경고 상황을 DB에 기록
                            self.db_helper.insert_temperature_log(warehouse, current_temp)
                            logger.info(f"창고 {warehouse} 경고 상태 DB 기록: 온도 {current_temp}°C")
                    except Exception as e:
                        logger.error(f"경고 상태 DB 기록 오류: {str(e)}")
            else:
                self.env_states[warehouse] = EnvState.NORMAL
                logger.info(f"창고 {warehouse} 경고 해제")
            
            # 소켓 이벤트 발송
            self._emit_socketio_event("warehouse_warning", {
                "warehouse": warehouse,
                "warning": warning_state
            })
            
        except Exception as e:
            logger.error(f"경고 이벤트 처리 오류: {str(e)}")
            logger.error(f"창고: {warehouse}, 값: {warning_str}")
    
    # ==== 팬 상태 이벤트 처리 ====
    def _handle_fan_status_event(self, warehouse: str, status_str: str):
        try:
            if not status_str or len(status_str) < 1:
                logger.warning(f"잘못된 팬 상태 형식: {status_str}")
                return
            
            # 첫 문자: 모드(C=냉방, H=난방, 0=정지)
            mode_char = status_str[0]
            
            # 창고별 모드 제약조건 검증
            if warehouse in ['A', 'B'] and mode_char == 'H':
                logger.warning(f"창고 {warehouse}는 난방을 지원하지않음")
                # 기본값으로 냉방 모드 설정
                mode_char = '0'
            
            # 모드 설정
            if mode_char == 'C':
                fan_mode = FanMode.COOLING
            elif mode_char == 'H' and warehouse == 'C':  # C 창고만 난방 가능
                fan_mode = FanMode.HEATING
            elif mode_char == '0' or mode_char == 'O':  # '0'이나 'O'는 정지 모드로 처리
                fan_mode = FanMode.OFF
            else:
                logger.warning(f"알 수 없는 팬 모드: {mode_char}, 기본값 OFF 사용")
                fan_mode = FanMode.OFF
            
            # 두 번째 문자: 속도(0-3)
            try:
                if len(status_str) > 1:
                    speed = int(status_str[1])
                else:
                    speed = 0
            except (ValueError, IndexError):
                speed = 0
                logger.warning(f"팬 속도 파싱 오류: {status_str}, 기본값 0 사용")
            
            # 유효한 속도 범위 확인
            if speed < 0 or speed > 3:
                logger.warning(f"유효하지 않은 팬 속도: {speed}, 범위 0-3")
                speed = 0
            
            # 정지 상태와 속도가 일치하는지 확인
            if fan_mode == FanMode.OFF and speed != 0:
                logger.warning(f"모드와 속도 불일치: 모드 정지인데 속도가 {speed}, 속도를 0으로 조정")
                speed = 0
            
            # 상태 업데이트
            self.fan_status[warehouse] = {
                "mode": fan_mode,
                "speed": speed
            }
            
            # 로그 출력
            mode_str = "냉방" if fan_mode == FanMode.COOLING else ("난방" if fan_mode == FanMode.HEATING else "정지")
            speed_str = "정지" if speed == 0 else f"{['저속', '중속', '고속'][speed-1]} ({speed})"
            logger.info(f"창고 {warehouse} 팬 상태 변경: {mode_str} {speed_str}")
            
            # 상태 업데이트 이벤트 발송
            self._emit_status_update()
            
        except Exception as e:
            logger.error(f"팬 상태 처리 오류: {str(e)}")
            logger.error(f"원인 데이터: {warehouse}, {status_str}")
    
    # ==== Socket.IO 이벤트 발송 ====
    def _emit_socketio_event(self, event_name: str, data: dict):
        """WebSocket 이벤트를 발송합니다."""
        if not self.socketio:
            logger.warning(f"Socket.IO 없음 - 이벤트 발송 불가: {event_name}")
            return
        
        try:
            # 이벤트 포맷 구성
            standard_event = {
                "type": "event",
                "category": "environment",
                "action": event_name,
                "payload": data,
                "timestamp": int(time.time())
            }
            
            # '/ws' 네임스페이스로만 이벤트 발송
            self.socketio.emit("event", standard_event, namespace='/ws')
            logger.debug(f"Socket.IO 이벤트 발송: {event_name}")
        except Exception as e:
            logger.error(f"Socket.IO 이벤트 발송 오류: {str(e)}")
    
    # ==== 상태 업데이트 이벤트 발송 ====
    def _emit_status_update(self):
        self._emit_socketio_event("environment_update", self.get_status()["data"])

    def handle_response(self, message_data: Dict[str, Any]):
        super().handle_response(message_data)