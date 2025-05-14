import logging
from typing import Dict, Any
from datetime import datetime
import time
from config import CONFIG

logger = logging.getLogger(__name__)

class EnvController:
    """환경 컨트롤러 - 통합 통신 프로토콜 적용"""
    
    # 상태 상수
    NORMAL = "normal"
    WARNING = "warning"
    
    # 팬 모드 상수
    FAN_OFF = "off"
    FAN_COOLING = "cool"
    FAN_HEATING = "heat"
    
    def __init__(self, tcp_handler, socketio=None, db_helper=None):
        """컨트롤러 초기화"""
        self.tcp_handler = tcp_handler
        self.socketio = socketio
        self.db_helper = db_helper
        
        # 창고 설정 초기화
        self.warehouses = list(CONFIG["WAREHOUSES"].keys())
        
        # 창고별 상태 데이터
        self.warehouse_data = {}
        for wh in self.warehouses:
            temp_min = CONFIG["WAREHOUSES"][wh]["temp_min"]
            temp_max = CONFIG["WAREHOUSES"][wh]["temp_max"]
            
            self.warehouse_data[wh] = {
                "temp": None,
                "target_temp": (temp_min + temp_max) / 2,
                "temp_range": (temp_min, temp_max),
                "state": self.NORMAL,
                "fan_mode": self.FAN_OFF,
                "fan_speed": 0,
                "warning": False
            }
        
        # 이벤트 핸들러 등록 - 새로운 방식과 이전 방식 모두 지원
        # 원본 프로토콜 형식으로 등록 (E, C, R, X)
        tcp_handler.register_device_handler('H', 'E', self.process_event)
        tcp_handler.register_device_handler('H', 'C', self.process_command)
        tcp_handler.register_device_handler('H', 'R', self.process_response)
        tcp_handler.register_device_handler('H', 'X', self.process_error)
        
        # 매핑된 디바이스 ID로도 등록 (이중 등록)
        tcp_handler.register_device_handler('env_controller', 'E', self.process_event)
        tcp_handler.register_device_handler('env_controller', 'C', self.process_command)
        tcp_handler.register_device_handler('env_controller', 'R', self.process_response)
        tcp_handler.register_device_handler('env_controller', 'X', self.process_error)
        
        # 이전 방식 호환성 유지 (deprecated)
        tcp_handler.register_device_handler('env_controller', 'evt', self.process_event)
        tcp_handler.register_device_handler('env_controller', 'res', self.process_response)
        tcp_handler.register_device_handler('env_controller', 'err', self.process_error)
        
        def set_temperature(self, warehouse, temperature):
            """특정 창고의 온도를 설정합니다.
            
            Args:
                warehouse: 창고 ID (A, B, C)
                temperature: 설정할 온도 값 (정수)
                
            Returns:
                dict: 성공/실패 상태와 메시지를 포함한 응답
            """
            # 창고 존재 확인
            if warehouse not in self.warehouse_data:
                logger.error(f"존재하지 않는 창고: {warehouse}")
                return {"status": "error", "message": f"존재하지 않는 창고: {warehouse}"}
                
            # 온도 값을 정수로 변환 (API는 정수로 받음)
            try:
                temperature = int(temperature)
            except (ValueError, TypeError):
                logger.error(f"온도를 정수로 변환할 수 없음: {temperature}")
                return {"status": "error", "message": f"온도를 정수로 변환할 수 없음: {temperature}"}
                
            # 유효 범위 확인
            min_temp, max_temp = self.warehouse_data[warehouse]["temp_range"]
            if temperature < min_temp or temperature > max_temp:
                logger.error(f"유효하지 않은 온도: {temperature}. 범위는 {min_temp}~{max_temp}입니다.")
                return {"status": "error", "message": f"유효하지 않은 온도: {temperature}. 범위는 {min_temp}~{max_temp}입니다."}
            
            # set_target_temperature 메서드 호출
            result = self.set_target_temperature(warehouse, temperature)
            
            # 결과 그대로 반환
            return result

    def process_event(self, message_data):
        """이벤트 메시지 처리 - 'E' 타입 메시지"""
        if 'content' not in message_data:
            return
            
        content = message_data['content']
        logger.debug(f"환경 제어 이벤트 수신: {content}")
        
        # 원본 콘텐츠 저장
        original_content = content
        
        # 표준화된 파싱 - 프리픽스 제거 처리
        # HE 프리픽스 제거 (있는 경우)
        if content.startswith('HE'):
            content = content[2:]
        
        # 이벤트 타입별 처리
        if content.startswith('tp'):
            # 온도 데이터 - 'tp-18.5;4.2;21.3'
            temp_data = content[2:]
            self._process_temperature_data(temp_data)
            return True
            
        elif content.startswith('w') and len(content) >= 2:
            # 경고 상태 - 'wA1', 'wB0'
            warehouse = content[1:2]
            status = content[2:3] == '1' if len(content) >= 3 else False
            
            if warehouse in ['A', 'B', 'C']:
                self._set_warning_status(warehouse, status)
                return True
                
        elif content[0:1] in ['A', 'B', 'C'] and len(content) >= 2:
            # 팬 상태 - 'AC2', 'B0', 'CH1'
            warehouse = content[0:1]
            fan_status = content[1:]
            self._set_fan_status(warehouse, fan_status)
            return True
        
        # 이 외의 경우 로그로 기록
        logger.debug(f"처리되지 않은 이벤트: {original_content}")
        return False
    
    def process_command(self, message_data):
        """명령 메시지 처리 - 'C' 타입 메시지"""
        if 'content' not in message_data:
            return
            
        content = message_data['content']
        logger.debug(f"환경 제어 명령 수신: {content}")
        
        # 원본 콘텐츠 저장
        original_content = content
        
        # HC 프리픽스 제거 (있는 경우)
        if content.startswith('HC'):
            content = content[2:]
        
        # 명령 타입별 처리
        if content.startswith('f') and len(content) >= 3:
            # 팬 제어 - 'fA1', 'fB2', 'fC0'
            warehouse = content[1:2]
            status = content[2:]
            
            if warehouse in ['A', 'B', 'C']:
                self._set_fan_status(warehouse, status)
                logger.info(f"팬 제어 명령 수행: 창고 {warehouse}, 상태 {status}")
                return True
        
        elif content.startswith('p') and len(content) >= 2:
            # 온도 설정 - 'pA-20', 'pB5', 'pC22'
            warehouse = content[1:2]
            temp_str = content[2:]
            
            try:
                temperature = float(temp_str)
                
                if warehouse in ['A', 'B', 'C']:
                    result = self.set_target_temperature(warehouse, temperature)
                    if result["status"] == "ok":
                        logger.info(f"온도 설정 성공: 창고 {warehouse}, 온도 {temperature}°C")
                    else:
                        logger.warning(f"온도 설정 실패: {result['message']}")
                    return True
            except ValueError:
                logger.warning(f"잘못된 온도 값: {temp_str}")
                return False
        
        # 모든 팬 정지 명령
        elif content.startswith('0') and len(content) >= 2:
            # 모든 팬 정지 - '00'
            for wh in self.warehouses:
                self._set_fan_status(wh, "00")
            logger.info("모든 팬 정지 명령 수행")
            return True
        
        # 이 외의 경우 로그로 기록
        logger.debug(f"처리되지 않은 명령: {original_content}")
        return False
    
    def process_response(self, message_data):
        """응답 메시지 처리 - 'R' 타입 메시지"""
        if 'content' in message_data:
            content = message_data['content']
            logger.info(f"환경 제어 응답: {content}")
            return True
        return False
    
    def process_error(self, message_data):
        """오류 메시지 처리 - 'X' 타입 메시지"""
        if 'content' in message_data:
            content = message_data['content']
            error_code = content
            
            if content.startswith('e'):
                error_code = content  # 'e1', 'e2' 등
            
            logger.error(f"환경 제어 오류: {error_code}")
            
            # 소켓 이벤트 발송
            self._emit_event("env_error", {
                "error_code": error_code,
                "message": f"환경 제어 오류: {error_code}"
            })
            return True
        return False
    
    def _process_temperature_data(self, temp_data):
        """온도 데이터 처리"""
        if not temp_data:
            return
            
        try:
            # 세미콜론으로 구분된 온도 값 파싱
            temps = temp_data.split(';')
            warehouses = ['A', 'B', 'C']
            
            for i, temp_str in enumerate(temps):
                if i >= len(warehouses):
                    break
                    
                try:
                    temp = float(temp_str.strip())
                    warehouse = warehouses[i]
                    
                    # 이전 값과 다를 때만 업데이트
                    if self.warehouse_data[warehouse]["temp"] != temp:
                        logger.debug(f"온도 업데이트: 창고 {warehouse}, {temp}°C")
                        self.warehouse_data[warehouse]["temp"] = temp
                        
                        # 경고 상태일 때 DB 로깅
                        if self.db_helper and self.warehouse_data[warehouse]["warning"]:
                            self.db_helper.insert_temperature_log(warehouse, temp)
                        
                        # 소켓 이벤트 발송
                        self._emit_event("temperature_update", {
                            "warehouse_id": warehouse,
                            "temperature": temp
                        })
                        
                except (ValueError, IndexError):
                    logger.warning(f"온도 변환 오류: '{temp_str}'")
        except Exception as e:
            logger.error(f"온도 데이터 처리 오류: {str(e)}")
    
    def _set_warning_status(self, warehouse, warning_status):
        """경고 상태 설정"""
        logger.debug(f"경고 상태 설정: 창고 {warehouse}, 상태 {warning_status}")
        
        if warehouse not in self.warehouse_data:
            logger.warning(f"알 수 없는 창고 ID: {warehouse}")
            return
            
        # 상태 업데이트
        self.warehouse_data[warehouse]["warning"] = warning_status
        self.warehouse_data[warehouse]["state"] = self.WARNING if warning_status else self.NORMAL
        
        # 경고 시 DB 기록
        if warning_status and self.db_helper:
            current_temp = self.warehouse_data[warehouse]["temp"]
            if current_temp is not None:
                self.db_helper.insert_temperature_log(warehouse, current_temp)
                logger.info(f"창고 {warehouse} 경고 상태 온도 로깅: {current_temp}°C")
        
        # 이벤트 발송
        self._emit_event("warehouse_warning", {
            "warehouse": warehouse,
            "warning": warning_status
        })
        logger.info(f"창고 {warehouse} 경고 상태 변경: {warning_status}")
    
    def _set_fan_status(self, warehouse, status_str):
        """팬 상태 설정"""
        if warehouse not in self.warehouse_data or not status_str:
            return
            
        try:
            # 모드 설정 (첫 번째 문자)
            mode_char = status_str[0]
            
            # 창고 A, B는 난방 모드를 지원하지 않음
            if warehouse in ['A', 'B'] and mode_char == 'H':
                mode_char = '0'  # 정지로 변경
            
            # 모드 결정
            if mode_char == 'C':
                fan_mode = self.FAN_COOLING
            elif mode_char == 'H' and warehouse == 'C':  # C 창고만 난방 지원
                fan_mode = self.FAN_HEATING
            else:  # '0', 'O' 또는 다른 문자
                fan_mode = self.FAN_OFF
            
            # 속도 설정 (두 번째 문자)
            try:
                speed = int(status_str[1]) if len(status_str) > 1 else 0
                # 유효한 범위로 제한 (0-3)
                speed = max(0, min(speed, 3))
                
                # 정지 모드면 속도는 0
                if fan_mode == self.FAN_OFF:
                    speed = 0
            except (ValueError, IndexError):
                speed = 0
            
            # 상태 업데이트
            self.warehouse_data[warehouse]["fan_mode"] = fan_mode
            self.warehouse_data[warehouse]["fan_speed"] = speed
            
            # 로그
            mode_str = "냉방" if fan_mode == self.FAN_COOLING else \
                       "난방" if fan_mode == self.FAN_HEATING else "정지"
            speed_str = "정지" if speed == 0 else f"속도 {speed}"
            logger.info(f"창고 {warehouse} 팬 상태 변경: {mode_str}, {speed_str}")
            
            # 이벤트 발송
            self._emit_event("fan_status_update", {
                "warehouse": warehouse,
                "mode": fan_mode,
                "speed": speed
            })
            
        except Exception as e:
            logger.error(f"팬 상태 처리 오류: {str(e)}")
    
    def set_target_temperature(self, warehouse, temperature):
        """목표 온도 설정"""
        if warehouse not in self.warehouse_data:
            return {
                "status": "error",
                "message": f"존재하지 않는 창고: {warehouse}"
            }
        
        # 유효 범위 확인
        min_temp, max_temp = self.warehouse_data[warehouse]["temp_range"]
        if temperature < min_temp or temperature > max_temp:
            return {
                "status": "error",
                "message": f"유효하지 않은 온도: {temperature}. 범위는 {min_temp}~{max_temp}입니다."
            }
        
        # 명령 전송 (정수로 변환)
        value = int(temperature)
        command = f"HCp{warehouse}{value}\n"
        
        if not self.tcp_handler.send_message("H", command):
            return {"status": "error", "message": "환경 제어 통신 오류"}
        
        # 내부 상태 업데이트
        self.warehouse_data[warehouse]["target_temp"] = temperature
        
        return {
            "status": "ok",
            "message": f"{warehouse} 창고 목표 온도를 {temperature}도로 설정했습니다."
        }
    
    def get_status(self):
        """모든 창고의 상태 반환"""
        warehouses = {}
        
        for wh in self.warehouses:
            warehouses[wh] = {
                "temp": self.warehouse_data[wh]["temp"],
                "target_temp": self.warehouse_data[wh]["target_temp"],
                "status": self.warehouse_data[wh]["state"],
                "fan_mode": self.warehouse_data[wh]["fan_mode"],
                "fan_speed": self.warehouse_data[wh]["fan_speed"],
                "warning": self.warehouse_data[wh]["warning"]
            }
        
        return {
            "status": "ok",
            "data": {
                "warehouses": warehouses,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def get_warehouse_status(self, warehouse):
        """특정 창고의 상태 반환"""
        if warehouse not in self.warehouse_data:
            return {"status": "error", "message": f"알 수 없는 창고: {warehouse}"}
        
        return {
            "status": "ok",
            "data": {
                "temp": self.warehouse_data[warehouse]["temp"],
                "target_temp": self.warehouse_data[warehouse]["target_temp"],
                "status": self.warehouse_data[warehouse]["state"],
                "fan_mode": self.warehouse_data[warehouse]["fan_mode"],
                "fan_speed": self.warehouse_data[warehouse]["fan_speed"],
                "warning": self.warehouse_data[warehouse]["warning"]
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _emit_event(self, event_name, data):
        """소켓 이벤트 발송"""
        if not self.socketio:
            return
        
        try:
            event_data = {
                "type": "event",
                "category": "environment",
                "action": event_name,
                "payload": data,
                "timestamp": int(time.time())
            }
            
            self.socketio.emit("event", event_data, namespace="/ws")
        except Exception as e:
            logger.error(f"이벤트 발송 오류: {str(e)}")