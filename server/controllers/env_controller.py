import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import time
from config import CONFIG
from utils.protocol import create_message, parse_message, DEVICE_WAREHOUSE, MSG_COMMAND


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
    
    def __init__(self, tcp_handler, socketio=None, db_helper=None, warning_log_repo=None):
        """컨트롤러 초기화
        
        Args:
            tcp_handler: TCP 통신 핸들러
            socketio: Socket.IO 객체 (실시간 이벤트용)
            db_helper: DB 관리자 (온도 설정 저장용)
            warning_log_repo: 경고 로그 리포지토리 (온도 경고 로깅용)
        """
        self.tcp_handler = tcp_handler
        self.socketio = socketio
        self.db_helper = db_helper
        self.warning_log_repo = warning_log_repo
        
        # 창고 설정 초기화
        self.warehouses = list(CONFIG.get("WAREHOUSES", {}).keys() if CONFIG else [])
        
        # 창고별 상태 데이터 기본값 설정
        self.warehouse_data = {}
        for wh in self.warehouses:
            # 기본값 설정
            self.warehouse_data[wh] = {
                "temp": None,
                "target_temp": None,
                "temp_range": (None, None),
                "state": self.NORMAL,
                "fan_mode": self.FAN_OFF,
                "fan_speed": 0,
                "warning": False,
                "type": None
            }
    
        # DB에서 설정 로드 (기본값 업데이트)
        self._load_warehouse_settings()
        
        
    def _set_default_warehouse_settings(self):
        """기본 창고 설정 적용"""
        defaults = {
            "A": {"temp_range": (-30, -18), "target_temp": -22, "type": "freezer"},
            "B": {"temp_range": (0, 10), "target_temp": 5, "type": "refrigerator"},
            "C": {"temp_range": (15, 25), "target_temp": 20, "type": "room_temp"}
        }
        
        for wh_id, setting in defaults.items():
            if wh_id in self.warehouse_data:
                self.warehouse_data[wh_id]["temp_range"] = setting["temp_range"]
                self.warehouse_data[wh_id]["target_temp"] = setting["target_temp"]
                self.warehouse_data[wh_id]["type"] = setting["type"]
    
    def set_target_temperature(self, warehouse: str, temperature: float) -> Dict[str, Any]:
        """목표 온도 설정
        
        Args:
            warehouse: 창고 ID ('A', 'B', 'C')
            temperature: 설정할 온도
            
        Returns:
            Dict: 결과 정보가 포함된 딕셔너리
                {
                    "status": "ok" | "error",
                    "message": "성공/오류 메시지",
                    "data": {...}  # 선택적 추가 데이터
                }
        """
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
        
        # DB에 저장
        self._save_temperature_to_db(warehouse, temperature)
        
        return {
            "status": "ok",
            "message": f"{warehouse} 창고 목표 온도를 {temperature}도로 설정했습니다.",
            "data": {
                "warehouse": warehouse,
                "temperature": temperature,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def _load_warehouse_settings(self):
        """DB에서 창고 설정 로드 또는 CONFIG 사용"""
        try:
            # DB에서 설정 가져오기 시도
            if self.db_helper and hasattr(self.db_helper, 'get_warehouse_temp_settings'):
                settings = self.db_helper.get_warehouse_temp_settings()
                if settings:
                    # 설정 적용
                    for wh_id, setting in settings.items():
                        if wh_id in self.warehouse_data:
                            temp_min = setting.get("temp_min")
                            temp_max = setting.get("temp_max")
                            target_temp = setting.get("target_temp") or setting.get("default_target")
                            wh_type = setting.get("type")
                            
                            self.warehouse_data[wh_id]["temp_range"] = (temp_min, temp_max)
                            self.warehouse_data[wh_id]["target_temp"] = target_temp
                            self.warehouse_data[wh_id]["type"] = wh_type
                            
                    logger.info("DB에서 창고 설정 로드 완료")
                    return True
            
            # DB 로드 실패 시 CONFIG 사용
            if CONFIG and 'WAREHOUSES' in CONFIG:
                warehouses = CONFIG['WAREHOUSES']
                for wh_id, setting in warehouses.items():
                    if wh_id in self.warehouse_data:
                        temp_min = setting.get("temp_min")
                        temp_max = setting.get("temp_max")
                        target_temp = setting.get("default_target") or setting.get("target_temp")
                        wh_type = setting.get("type")
                        
                        self.warehouse_data[wh_id]["temp_range"] = (temp_min, temp_max)
                        self.warehouse_data[wh_id]["target_temp"] = target_temp
                        self.warehouse_data[wh_id]["type"] = wh_type
                
                logger.info("CONFIG에서 창고 설정 로드 완료")
                return True
        except Exception as e:
            logger.error(f"창고 설정 로드 오류: {str(e)}")
        
        # 모든 시도 실패 시 기본값 사용
        self._set_default_warehouse_settings()
        return False
    
    def _save_temperature_to_db(self, warehouse: str, temperature: float) -> bool:
        """DB에 온도 설정 저장 (내부 메서드)
        
        여러 종류의 DB 도우미(db_helper)를 지원하기 위한 래퍼 메서드
        """
        if not self.db_helper:
            logger.warning("DB 도우미가 설정되지 않아 온도 설정을 저장할 수 없습니다.")
            return False
            
        # DBManager 클래스를 사용하는 경우
        if hasattr(self.db_helper, 'update_target_temperature'):
            return self.db_helper.update_target_temperature(warehouse, temperature)
        
        # WarehouseRepository를 직접 사용하는 경우
        elif hasattr(self.db_helper, 'save_target_temperature'):
            return self.db_helper.save_target_temperature(warehouse, temperature)
            
        # WarehouseRepository를 속성으로 가진 객체인 경우
        elif hasattr(self.db_helper, 'warehouse_repo'):
            return self.db_helper.warehouse_repo.save_target_temperature(warehouse, temperature)
            
        logger.warning("적절한 온도 저장 메서드를 찾을 수 없습니다.")
        return False

    # 이벤트 처리 함수
    def process_event(self, message: Dict[str, Any]) -> bool:
        """이벤트 처리 로직"""
        if 'content' not in message and 'raw' not in message:
            logger.error("이벤트 메시지에 내용이 없음")
            return False
                
        # raw 또는 content 키에서 메시지 가져오기
        content = message.get('raw', message.get('content', ''))
        
        # 로그 추가
        logger.debug(f"환경 이벤트 수신: {content}")
        
        # 직접 'tp-'로 시작하는 메시지 처리 (프로토콜 파싱 우회)
        if content.startswith('tp-'):
            self._process_temperature_data(content[3:])  # 'tp-' 제거
            return True
        
        # 표준 프로토콜 메시지 파싱
        device_id, msg_type, payload = parse_message(content)
        
        # 유효성 검증
        if not device_id or not msg_type or device_id != 'H':
            logger.warning(f"잘못된 이벤트 메시지: {content}")
            return False
        
        # 이벤트 메시지가 아닌 경우 무시
        if msg_type != 'E':
            logger.warning(f"이벤트가 아닌 메시지: {content}")
            return False
        
        # 이벤트 타입별 처리
        if payload.startswith('tp'):
            # 온도 데이터 - 'tp-18.5;4.2;21.3'
            temp_data = payload[2:]
            self._process_temperature_data(temp_data)
            return True
        elif payload.startswith('wA'):
            # A 창고 경고 - 'wA1' (1=경고, 0=정상)
            warning_status = payload[2:] == '1'
            self._set_warning_status('A', warning_status)
            return True
        elif payload.startswith('wB'):
            # B 창고 경고
            warning_status = payload[2:] == '1'
            self._set_warning_status('B', warning_status)
            return True
        elif payload.startswith('wC'):
            # C 창고 경고
            warning_status = payload[2:] == '1'
            self._set_warning_status('C', warning_status)
            return True
        elif payload.startswith('A'):
            # A 창고 온도제어상태 - 'AC2' (C=냉방, H=난방, 0-3=속도)
            self._set_fan_status('A', payload[1:])
            return True
        elif payload.startswith('B'):
            # B 창고 온도제어상태
            self._set_fan_status('B', payload[1:])
            return True
        elif payload.startswith('C'):
            # C 창고 온도제어상태
            self._set_fan_status('C', payload[1:])
            return True
        
        # 처리되지 않은 이벤트
        logger.warning(f"처리되지 않은 환경 이벤트: {payload}")
        return False
    
    def process_command(self, message_data: Dict[str, Any]) -> bool:
        """명령 메시지 처리 - 'C' 타입 메시지"""
        if 'content' not in message_data:
            return False
            
        content = message_data['content']
        logger.debug(f"환경 제어 명령 수신: {content}")
        
        # 원본 콘텐츠 저장
        original_content = content
        
        # HC 프리픽스 제거 (있는 경우)
        if content.startswith('HC'):
            content = content[2:]
        
        # 명령 유형 파싱
        if content.startswith('p'):
            # 목표 온도 설정
            warehouse_id = content[1:2]  # 'pA-20' -> 'A'
            temp_str = content[2:]       # 'pA-20' -> '-20'
            
            try:
                temp = float(temp_str)
                logger.info(f"목표 온도 설정 명령: 창고 {warehouse_id}, 온도 {temp}°C")
                
                # 내부 상태 업데이트
                if warehouse_id in self.warehouse_data:
                    self.warehouse_data[warehouse_id]["target_temp"] = temp
                    
                    # DB에 저장
                    self._save_temperature_to_db(warehouse_id, temp)
                
                # 응답은 하드웨어가 보낼 것임
                return True
            except ValueError:
                logger.error(f"잘못된 온도 값: {temp_str}")
        
        return False
    
    def process_response(self, message_data: Dict[str, Any]) -> bool:
        """응답 메시지 처리 - 'R' 타입 메시지"""
        if 'content' in message_data:
            content = message_data['content']
            logger.info(f"환경 제어 응답: {content}")
            return True
        return False
    
    def process_error(self, message_data: Dict[str, Any]) -> bool:
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
    
    def _process_temperature_data(self, temp_data: str) -> None:
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
                        if self.warehouse_data[warehouse]["warning"]:
                            self._log_temperature_warning(warehouse, temp, "warning")
                        
                        # 소켓 이벤트 발송
                        self._emit_event("temperature_update", {
                            "warehouse_id": warehouse,
                            "temperature": temp
                        })
                        
                except (ValueError, IndexError):
                    logger.warning(f"온도 변환 오류: '{temp_str}'")
        except Exception as e:
            logger.error(f"온도 데이터 처리 오류: {str(e)}")
    
    def _log_temperature_warning(self, warehouse: str, temperature: float, status: str) -> bool:
        """온도 경고 로그 저장 (내부 메서드)
        
        여러 종류의 로깅 객체를 지원하기 위한 래퍼 메서드
        """
        # 경고 로그 리포지토리가 직접 전달된 경우
        if self.warning_log_repo:
            return self.warning_log_repo.log_temperature_warning(warehouse, temperature, status)
            
        # db_helper에 log_temperature_warning 메서드가 있는 경우
        if self.db_helper and hasattr(self.db_helper, 'log_temperature_warning'):
            return self.db_helper.log_temperature_warning(warehouse, temperature, status)
            
        # db_helper가 warning_log_repo 속성을 가진 경우 (DBManager)
        if self.db_helper and hasattr(self.db_helper, 'warning_log_repo'):
            return self.db_helper.warning_log_repo.log_temperature_warning(warehouse, temperature, status)
            
        logger.warning(f"온도 경고 로그를 저장할 적절한 메서드를 찾을 수 없습니다. (창고: {warehouse})")
        return False
        
    def _set_warning_status(self, warehouse: str, warning_status: bool) -> None:
        """경고 상태 설정"""
        logger.debug(f"경고 상태 설정: 창고 {warehouse}, 상태 {warning_status}")
        
        if warehouse not in self.warehouse_data:
            logger.warning(f"알 수 없는 창고 ID: {warehouse}")
            return
            
        # 상태 업데이트
        self.warehouse_data[warehouse]["warning"] = warning_status
        self.warehouse_data[warehouse]["state"] = self.WARNING if warning_status else self.NORMAL
        
        # 경고 시 DB 기록
        if warning_status:
            current_temp = self.warehouse_data[warehouse]["temp"]
            if current_temp is not None:
                self._log_temperature_warning(warehouse, current_temp, "warning")
                logger.info(f"창고 {warehouse} 경고 상태 온도 로깅: {current_temp}°C")
        
        # 이벤트 발송
        self._emit_event("warehouse_warning", {
            "warehouse": warehouse,
            "warning": warning_status
        })
        logger.info(f"창고 {warehouse} 경고 상태 변경: {warning_status}")
    
    def _set_fan_status(self, warehouse: str, status_str: str) -> None:
        """팬 상태 설정"""
        if warehouse not in self.warehouse_data or not status_str:
            return
            
        try:
            # 모드 설정 (첫 번째 문자)
            mode_char = status_str[0]
            
            # 모드 결정
            if mode_char == 'C':
                fan_mode = self.FAN_COOLING
            elif mode_char == 'H':
                # C 창고만 난방 지원 (A, B는 난방모드 무시)
                if warehouse == 'C':
                    fan_mode = self.FAN_HEATING
                else:
                    fan_mode = self.FAN_OFF
            else:  # '0', 'O' 또는 다른 문자
                fan_mode = self.FAN_OFF
            
            # 속도 설정 (두 번째 문자)
            try:
                speed = int(status_str[1]) if len(status_str) > 1 else 0
                # 유효한 범위로 제한 (0-3)
                speed = max(0, min(speed, 3))
                
                # 모드가 FAN_OFF면 속도도 0으로 설정
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
    
    def get_status(self) -> Dict[str, Any]:
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
    
    def get_warehouse_status(self, warehouse: str) -> Dict[str, Any]:
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
    
    def _emit_event(self, event_name: str, data: Dict[str, Any]) -> None:
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
            
    def get_warnings(self) -> List[Dict[str, Any]]:
        """현재 경고 상태인 창고 목록 반환"""
        warnings = []
        
        for warehouse_id, data in self.warehouse_data.items():
            if data["warning"]:
                warnings.append({
                    "warehouse_id": warehouse_id,
                    "temperature": data["temp"],
                    "target_temp": data["target_temp"],
                    "temp_range": data["temp_range"]
                })
                
        return warnings