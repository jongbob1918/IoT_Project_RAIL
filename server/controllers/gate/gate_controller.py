# server/controllers/gate/gate_controller.py
import logging
import time
from typing import Dict, Any, List
from datetime import datetime
from utils.system import Controller
from .rfid_handler import RFIDHandler
from .access_manager import AccessManager
from utils.serial_handlers.gate_serial import GateSerialHandler

handler = GateSerialHandler(port='/dev/ttyUSB0')
handler.connect()
handler.send_mode_command(register_mode=False)


logger = logging.getLogger(__name__)

# ==== 출입 제어 컨트롤러 ====
class GateController(Controller):
    # ==== 출입 컨트롤러 초기화 ====
    def __init__(self, tcp_handler, socketio=None, db_helper=None):
        super().__init__(tcp_handler, socketio, db_helper)
        
        # 출입 관리자 생성
        self.access_manager = AccessManager(db_helper)
        
        # RFID 이벤트 핸들러 생성
        self.rfid_handler = RFIDHandler(self, tcp_handler)
        
        # 일일 출입 통계
        self.daily_stats = {
            "entries": 0,
            "exits": 0,
            "current_count": 0,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        
        # 최근 출입 로그 (최근 10개)
        self.recent_logs = []
        
        # 일일 통계 초기화
        self._initialize_daily_stats()
        
        logger.info("출입 제어 컨트롤러 초기화 완료")
    
    def register_handlers(self):
        # gt 디바이스의 이벤트/응답 핸들러 등록
        self.tcp_handler.register_device_handler("gt", "evt", self.handle_event)
        self.tcp_handler.register_device_handler("gt", "res", self.handle_response)
    
    def handle_event(self, message):
        """게이트 이벤트 처리"""
        if 'content' not in message and 'raw' not in message:
            logger.error("이벤트 메시지에 내용이 없음")
            return
            
        # raw 또는 content 키에서 메시지 가져오기
        content = message.get('raw', message.get('content', ''))
        
        # 로그 추가
        logger.debug(f"게이트 이벤트 수신: {content}")
        
        # 메시지 파싱
        device_id, msg_type, payload = parse_message(content)
        
        # 유효성 검증
        if not device_id or not msg_type or device_id != 'G':
            logger.warning(f"잘못된 이벤트 메시지: {content}")
            return
        
        # 이벤트 메시지가 아닌 경우 무시
        if msg_type != 'E':
            logger.warning(f"이벤트가 아닌 메시지: {content}")
            return
    
    def process_event(self, content: str):
        # 필요시 추가적인 이벤트 처리 로직 구현
        pass
    
    def handle_response(self, message_data: Dict[str, Any]):
        self.rfid_handler.handle_response(message_data)
    
    def process_response(self, content: str):
        # 필요시 추가적인 응답 처리 로직 구현
        pass
    
    # ==== 일일 통계 초기화 ====
    def _initialize_daily_stats(self):
        """일일 출입 통계를 초기화합니다."""
        if self.db_helper:
            try:
                # 오늘 날짜로 DB에서 통계 조회
                today = datetime.now().strftime("%Y-%m-%d")
                stats = self.db_helper.get_daily_access_stats(today)
                
                if stats:
                    self.daily_stats = stats
                    logger.info(f"일일 출입 통계 로드: 입장 {stats['entries']}명, 퇴장 {stats['exits']}명, 현재 {stats['current_count']}명")
                else:
                    # 새로운 날짜로 초기화
                    self.daily_stats = {
                        "entries": 0,
                        "exits": 0,
                        "current_count": 0,
                        "date": today
                    }
                    logger.info("새 일일 출입 통계 초기화")
            except Exception as e:
                logger.error(f"일일 통계 초기화 중 오류: {str(e)}")
    
    # ==== RFID 카드 인식 처리 ====
    def process_rfid(self, card_id: str) -> Dict[str, Any]:
        """RFID 카드 ID를 처리하고 접근 권한을 확인합니다."""
        logger.info(f"RFID 카드 인식: {card_id}")
        
        # 카드 ID 유효성 확인
        if not card_id or len(card_id) < 4:
            logger.warning(f"유효하지 않은 카드 ID: {card_id}")
            return {
                "access": False,
                "reason": "invalid_card"
            }
        
        # 출입 권한 확인
        access_result = self.access_manager.check_access(card_id)
        
        # 출입 결과에 따른 후속 처리
        if access_result["access"]:
            # 출입 기록 저장
            entry_type = access_result.get("entry_type", "entry")
            self._log_access(card_id, access_result.get("employee_name"), entry_type)
            
            # 일일 통계 업데이트
            if entry_type == "entry":
                self.daily_stats["entries"] += 1
                self.daily_stats["current_count"] += 1
            else:  # exit
                self.daily_stats["exits"] += 1
                self.daily_stats["current_count"] = max(0, self.daily_stats["current_count"] - 1)
            
            # 통계 DB 업데이트
            if self.db_helper:
                try:
                    self.db_helper.update_daily_access_stats(self.daily_stats)
                except Exception as e:
                    logger.error(f"일일 통계 업데이트 중 오류: {str(e)}")
            
            # Socket.IO 이벤트 발송
            self._emit_socketio_event(entry_type, {
                "card_id": card_id,
                "name": access_result.get("employee_name", "Unknown"),
                "time": datetime.now().strftime("%H:%M:%S"),
                "total_entries": self.daily_stats["entries"],
                "total_exits": self.daily_stats["exits"],
                "current_count": self.daily_stats["current_count"]
            })
        else:
            # 접근 거부 이벤트 발송
            self._emit_socketio_event("access_denied", {
                "card_id": card_id,
                "reason": access_result.get("reason", "unknown"),
                "time": datetime.now().strftime("%H:%M:%S")
            })
        
        return access_result
    
    # ==== 출입 기록 저장 ====
    def _log_access(self, card_id: str, name: str = None, entry_type: str = "entry"):
        """출입 이벤트를 로그에 기록하고 DB에 저장합니다."""
        timestamp = datetime.now()
        log_entry = {
            "card_id": card_id,
            "name": name if name else "Unknown",
            "time": timestamp.strftime("%H:%M:%S"),
            "type": entry_type,
            "timestamp": timestamp.isoformat()
        }
        
        # 로그에 기록
        logger.info(f"출입 기록: {card_id} ({name if name else 'Unknown'}) - {entry_type} at {timestamp.strftime('%H:%M:%S')}")
        
        # 최근 로그에 추가
        self.recent_logs.insert(0, log_entry)
        if len(self.recent_logs) > 10:
            self.recent_logs.pop()
        
        # DB에 저장
        if self.db_helper:
            try:
                self.db_helper.save_access_log(card_id, name, entry_type, timestamp)
            except Exception as e:
                logger.error(f"출입 로그 저장 중 오류: {str(e)}")
    
    # ==== 출입문 상태 변경 명령 전송 ====
    def set_gate_state(self, access: bool) -> bool:
        """출입문의 상태를 변경하는 명령을 전송합니다."""
        # 명령 구성
        command = {
            "dev": "gt",
            "tp": "cmd",
            "cmd": "ac",
            "act": "ap" if access else "dn"
        }
        
        # 명령 전송
        success = self.tcp_handler.send_message("gt", command)
        
        if success:
            logger.debug(f"출입문 상태 변경 명령 전송 성공: {'접근 허용' if access else '접근 거부'}")
        else:
            logger.error(f"출입문 상태 변경 명령 전송 실패")
        
        return success
    
    # ==== 날짜별 출입 기록 조회 ====
    def get_access_logs(self, date: str = None) -> Dict[str, Any]:
        """특정 날짜의 출입 기록을 조회합니다."""
        # 날짜 형식 검증
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return {
                    "status": "error",
                    "code": "E5001",
                    "message": "잘못된 날짜 형식 (YYYY-MM-DD 형식 필요)"
                }
        else:
            # 기본값은 오늘 날짜
            date = datetime.now().strftime("%Y-%m-%d")
        
        # DB 조회
        if self.db_helper:
            try:
                logs = self.db_helper.get_access_logs(date)
                stats = self.db_helper.get_daily_access_stats(date)
                
                if not stats:
                    stats = {
                        "entries": 0,
                        "exits": 0,
                        "current_count": 0,
                        "date": date
                    }
                
                return {
                    "status": "ok",
                    "date": date,
                    "total_entries": stats["entries"],
                    "total_exits": stats["exits"],
                    "current_count": stats["current_count"],
                    "logs": logs
                }
            except Exception as e:
                logger.error(f"출입 기록 조회 중 오류: {str(e)}")
                return {
                    "status": "error",
                    "code": "E5002",
                    "message": f"출입 기록 조회 실패: {str(e)}"
                }
        else:
            # DB 없이 최근 로그만 반환
            return {
                "status": "ok",
                "date": date,
                "total_entries": self.daily_stats["entries"],
                "total_exits": self.daily_stats["exits"],
                "current_count": self.daily_stats["current_count"],
                "logs": self.recent_logs
            }
    
    # ==== 현재 출입 상태 반환 ====
    def get_current_status(self) -> Dict[str, Any]:
        """현재 출입 상태 정보를 반환합니다."""
        return {
            "status": "ok",
            "date": self.daily_stats["date"],
            "total_entries": self.daily_stats["entries"],
            "total_exits": self.daily_stats["exits"],
            "current_count": self.daily_stats["current_count"],
            "recent_logs": self.recent_logs
        }
    
    # ==== Socket.IO 이벤트 발송 ====
    def _emit_socketio_event(self, event_type: str, data: dict):
        """Socket.IO를 통해 이벤트를 발송합니다."""
        if not self.socketio:
            logger.warning(f"Socket.IO 없음 - 이벤트 발송 불가: {event_type}")
            return
        
        try:
            # Flask-SocketIO 포맷으로 이벤트 발송
            self.socketio.emit("event", {
                "type": "event",
                "category": "access",
                "action": event_type,
                "payload": data,
                "timestamp": int(time.time())
            })
            logger.debug(f"Socket.IO 이벤트 발송: {event_type}")
        except Exception as e:
            logger.error(f"Socket.IO 이벤트 발송 오류: {str(e)}")