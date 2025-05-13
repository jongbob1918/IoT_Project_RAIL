# server/controllers/gate/rfid_handler.py
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ==== RFID 이벤트 처리 클래스 ====
class RFIDHandler:
    # ==== 이벤트 핸들러 초기화 ====
    def __init__(self, controller, tcp_handler):
        self.controller = controller
        self.tcp_handler = tcp_handler
        
        # 핸들러 맵 초기화 - 이벤트 타입별 처리 메소드 매핑
        self.event_handlers = {
            "rfid": self._handle_rfid_event,
            "dr": self._handle_door_event,
            "st": self._handle_status_event
        }
        
        # 응답 핸들러 맵
        self.response_handlers = {
            "ok": self._handle_ok_response,
            "er": self._handle_error_response
        }
        
        logger.info("RFID 이벤트 핸들러 초기화 완료")
    
    # ==== 이벤트 메시지 처리 ====
    def handle_event(self, message: Dict[str, Any]):
        """이벤트 메시지를 핸들러 맵을 사용하여 처리합니다."""
        try:
            if 'evt' not in message or 'val' not in message:
                logger.warning(f"잘못된 이벤트 메시지 형식: {json.dumps(message)}")
                return
            
            event_type = message['evt']
            values = message['val']
            
            # 핸들러 맵에서 처리 메소드 검색 및 실행
            if event_type in self.event_handlers:
                self.event_handlers[event_type](values)
            else:
                logger.warning(f"알 수 없는 이벤트 타입: {event_type}")
        
        except Exception as e:
            logger.error(f"RFID 이벤트 처리 중 오류: {str(e)}")
    
    # ==== 응답 메시지 처리 ====
    def handle_response(self, message: Dict[str, Any]):
        """응답 메시지를 핸들러 맵을 사용하여 처리합니다."""
        try:
            if 'res' not in message:
                logger.warning(f"잘못된 응답 메시지 형식: {json.dumps(message)}")
                return
            
            response_type = message['res']
            values = message.get('val', {})
            
            # 핸들러 맵에서 처리 메소드 검색 및 실행
            if response_type in self.response_handlers:
                self.response_handlers[response_type](values)
            else:
                logger.warning(f"알 수 없는 응답 타입: {response_type}")
        
        except Exception as e:
            logger.error(f"RFID 응답 처리 중 오류: {str(e)}")
    
    # ==== RFID 이벤트 처리 ====
    def _handle_rfid_event(self, values: Dict[str, Any]):
        """RFID 태그 인식 이벤트를 처리합니다."""
        if 'uid' not in values:
            logger.warning("UID 값이 없는 RFID 이벤트")
            return
        
        card_id = values['uid']
        logger.info(f"RFID 카드 인식: {card_id}")
        
        # 컨트롤러를 통해 카드 ID 처리
        access_result = self.controller.process_rfid(card_id)
        
        # 출입문 제어 명령 전송
        if access_result:
            self.controller.set_gate_state(access_result["access"])
    
    # ==== 문 상태 이벤트 처리 ====
    def _handle_door_event(self, values: Dict[str, Any]):
        """문 상태 변경 이벤트를 처리합니다."""
        if 'st' not in values:
            logger.warning("상태 값이 없는 문 이벤트")
            return
        
        state = values['st']
        logger.debug(f"문 상태 변경: {state}")
        
        # 필요한 경우 추가 처리 구현
    
    # ==== 상태 이벤트 처리 ====
    def _handle_status_event(self, values: Dict[str, Any]):
        """상태 변경 이벤트를 처리합니다."""
        if 'st' not in values:
            logger.warning("상태 값이 없는 상태 이벤트")
            return
        
        state = values['st']
        logger.debug(f"게이트 컨트롤러 상태 변경: {state}")
        
        # 필요한 경우 추가 처리 구현
    
    # ==== 성공 응답 처리 ====
    def _handle_ok_response(self, values: Dict[str, Any]):
        """성공 응답을 처리합니다."""
        if 'st' in values:
            state = values['st']
            logger.debug(f"게이트 컨트롤러 성공 응답: {state}")
            
            # 필요한 경우 추가 처리 구현
    
    # ==== 오류 응답 처리 ====
    def _handle_error_response(self, values: Dict[str, Any]):
        """오류 응답을 처리합니다."""
        error_code = values.get('c', 'unknown')
        error_message = values.get('m', '알 수 없는 오류')
        
        logger.error(f"게이트 컨트롤러 오류 응답: {error_code}, {error_message}")
        
        # 웹소켓 이벤트 발송
        self.controller._emit_socketio_event("gate_error", {
            "error_code": error_code,
            "error_message": error_message
        })