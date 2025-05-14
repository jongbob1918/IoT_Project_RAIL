import logging
from typing import Dict, Any
from datetime import datetime
import time
from config import CONFIG

logger = logging.getLogger(__name__)

class EnvController:
    """간소화된 환경 컨트롤러"""
    
    # 간단한 상태 상수
    NORMAL = "normal"
    WARNING = "warning"
    
    # 간단한 팬 모드 상수
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
        
        # 이벤트 핸들러 등록
        tcp_handler.register_device_handler('env_controller', 'evt', self.process_event)
        tcp_handler.register_device_handler('env_controller', 'res', self.process_response)
        
        logger.info("환경 컨트롤러 초기화 완료")
    
    def process_event(self, message_data):
        """모든 이벤트 처리 통합 메서드"""
        if 'content' not in message_data:
            return
            
        content = message_data['content']
        
        # 온도 데이터 처리
        if content.startswith('HEtp') or content.startswith('tp'):
            # 프리픽스 제거
            temp_data = content[4:] if content.startswith('HEtp') else content[2:]
            self._process_temperature_data(temp_data)
            return
            
        # 경고 상태 처리
        if content.startswith('HEw') and len(content) >= 4:
            warehouse = content[2:3]
            if warehouse in ['A', 'B', 'C']:
                warning_status = content[3:] == '1'
                self._set_warning_status(warehouse, warning_status)
                return
        
        # 팬 상태 이벤트 (프리픽스 형식 또는 짧은 형식)
        if (content.startswith('HE') and len(content) >= 4 and content[2:3] in ['A', 'B', 'C']) or \
           (len(content) >= 2 and content[0:1] in ['A', 'B', 'C']):
            
            # 팬 상태 추출
            if content.startswith('HE'):
                warehouse = content[2:3]
                fan_status = content[3:]
            else:
                warehouse = content[0:1]
                fan_status = content[1:]
                
            self._set_fan_status(warehouse, fan_status)
            return
        
        # 모든 팬 정지 명령
        if content.startswith('C0') and len(content) == 3:
            for wh in self.warehouses:
                self._set_fan_status(wh, "00")
            return
            
        # 기타 응답은 로그만 기록
        if content.startswith('HR') or content.startswith('HX'):
            logger.info(f"환경 제어 응답: {content}")
            return
            
        # 처리되지 않은 명령은 디버그 로그로만 기록
        logger.debug(f"처리되지 않은 이벤트: {content}")
    
    def process_response(self, message_data):
        """응답 처리 간소화"""
        if 'content' in message_data:
            logger.info(f"환경 제어 응답: {message_data['content']}")
    
    def _process_temperature_data(self, temp_data):
        """온도 데이터 처리"""
        if not temp_data:
            return
            
        try:
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
        if warehouse not in self.warehouse_data:
            return
            
        # 상태 업데이트
        self.warehouse_data[warehouse]["warning"] = warning_status
        self.warehouse_data[warehouse]["state"] = self.WARNING if warning_status else self.NORMAL
        
        # 경고 시 DB 기록
        if warning_status and self.db_helper:
            current_temp = self.warehouse_data[warehouse]["temp"]
            if current_temp is not None:
                self.db_helper.insert_temperature_log(warehouse, current_temp)
        
        # 이벤트 발송
        self._emit_event("warehouse_warning", {
            "warehouse": warehouse,
            "warning": warning_status
        })
    
    def _set_fan_status(self, warehouse, status_str):
        """팬 상태 설정"""
        if warehouse not in self.warehouse_data or not status_str:
            return
            
        try:
            # 모드 설정
            mode_char = status_str[0]
            
            # 창고 C만 난방 가능
            if warehouse in ['A', 'B'] and mode_char == 'H':
                mode_char = '0'
            
            # 모드 설정
            if mode_char == 'C':
                fan_mode = self.FAN_COOLING
            elif mode_char == 'H' and warehouse == 'C':
                fan_mode = self.FAN_HEATING
            else:
                fan_mode = self.FAN_OFF
            
            # 속도 설정 (0-3)
            try:
                speed = int(status_str[1]) if len(status_str) > 1 else 0
                # 유효한 범위로 제한
                speed = max(0, min(speed, 3))
                
                # 정지 모드면 속도는 0
                if fan_mode == self.FAN_OFF:
                    speed = 0
            except (ValueError, IndexError):
                speed = 0
            
            # 상태 업데이트
            self.warehouse_data[warehouse]["fan_mode"] = fan_mode
            self.warehouse_data[warehouse]["fan_speed"] = speed
            
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
        
        if not self.tcp_handler.send_message("env_controller", command):
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
        """이벤트 발송 메서드 통합"""
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