from abc import ABC, abstractmethod
import logging
from typing import Dict, Any

class BaseController(ABC):
    """모든 컨트롤러의 기본 클래스
    TCP 핸들러와의 인터페이스, 웹소켓 통신, 데이터베이스 접근 등을 처리합니다.
    """
    def __init__(self, tcp_handler, socketio=None, db_helper=None):
        self.tcp_handler = tcp_handler
        self.socketio = socketio
        self.db_helper = db_helper
        self.logger = logging.getLogger(self.__class__.__module__)
        self.register_handlers()
        self.logger.info(f"{self.__class__.__name__} 초기화 완료")

    @abstractmethod
    def register_handlers(self):
        """각 컨트롤러가 구현해야 하는 핸들러 등록 메서드"""
        pass

    def handle_event(self, message_data: Dict[str, Any]):
        """이벤트 메시지 처리의 공통 진입점"""
        if 'content' in message_data:
            self.process_event(message_data['content'])

    @abstractmethod
    def process_event(self, content: str):
        """각 컨트롤러별 이벤트 처리 로직"""
        pass

    def handle_response(self, message_data: Dict[str, Any]):
        """응답 메시지 처리의 공통 진입점"""
        if 'content' in message_data:
            self.process_response(message_data['content'])

    def process_response(self, content: str):
        """응답 메시지 처리 로직 (기본 구현)"""
        self.logger.debug(f"응답 수신: {content}")

    def emit_socketio_event(self, event_name: str, data: Dict[str, Any]):
        """WebSocket 이벤트를 발송합니다."""
        if not self.socketio:
            self.logger.warning(f"Socket.IO 없음 - 이벤트 발송 불가: {event_name}")
            return
        try:
            event_data = {
                "type": "event",
                "category": self.__class__.__name__.lower().replace('controller', ''),
                "action": event_name,
                "payload": data
            }
            self.socketio.emit("event", event_data, namespace='/ws')
        except Exception as e:
            self.logger.error(f"Socket.IO 이벤트 발송 오류: {str(e)}")
