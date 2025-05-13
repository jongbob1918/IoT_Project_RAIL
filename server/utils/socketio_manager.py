# server/utils/socketio_manager.py
import logging
import time
from typing import Dict, Any
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

class SocketIOManager:
    """Socket.IO 이벤트 관리 클래스"""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        logger.info("Socket.IO 매니저 초기화 완료")
    
    def emit_event(self, category: str, action: str, payload: Dict[str, Any]):
        """Socket.IO 이벤트 발송
        
        Args:
            category: 이벤트 카테고리 (sorter, environment, inventory 등)
            action: 세부 동작 (status_update, alarm 등)
            payload: 전송할 데이터
        """
        if not self.socketio:
            logger.warning(f"Socket.IO 인스턴스 없음 - 이벤트 발송 불가: {category}/{action}")
            return False
        
        try:
            # GUI 통신 사양에 맞는 이벤트 형식
            event_data = {
                "type": "event",
                "category": category,
                "action": action,
                "payload": payload,
                "timestamp": int(time.time())
            }
            
            self.socketio.emit("event", event_data)
            logger.debug(f"Socket.IO 이벤트 발송: {category}/{action}")
            return True
        except Exception as e:
            logger.error(f"Socket.IO 이벤트 발송 오류: {str(e)}")
            return False
    
    def emit_error(self, category: str, action: str, code: str, message: str, details: str = None):
        """Socket.IO 오류 이벤트 발송
        
        Args:
            category: 오류 카테고리
            action: 오류 발생 동작
            code: 오류 코드
            message: 오류 메시지
            details: 상세 오류 정보 (선택)
        """
        payload = {
            "code": code,
            "message": message
        }
        
        if details:
            payload["details"] = details
        
        event_data = {
            "type": "error",
            "category": category,
            "action": action,
            "payload": payload,
            "timestamp": int(time.time())
        }
        
        try:
            self.socketio.emit("event", event_data)
            logger.debug(f"Socket.IO 오류 이벤트 발송: {category}/{action} - {code}")
            return True
        except Exception as e:
            logger.error(f"Socket.IO 오류 이벤트 발송 실패: {str(e)}")
            return False