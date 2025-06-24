# server/utils/multi_tcp_handler.py
import logging
from typing import Dict, Any, Callable, List

from .tcp_handler import TCPHandler

logger = logging.getLogger(__name__)

# ==== 다중 포트 TCP 핸들러 클래스 ====
class MultiTCPHandler:
    # ==== 다중 TCP 핸들러 초기화 ====
    def __init__(self, devices_config: Dict[str, Dict[str, Any]]):
        """
        디바이스별 별도 포트를 사용하는 TCP 핸들러를 초기화합니다.
        
        Args:
            devices_config: 디바이스별 설정 {디바이스ID: {host, port}}
        """
        self.handlers = {}
        self.config = devices_config
        
        # 디바이스별 TCP 핸들러 생성
        for device_id, config in devices_config.items():
            host = config.get('host', '192.168.0.10')
            port = config.get('port', 9000)
            
            handler = TCPHandler(host=host, port=port)
            self.handlers[device_id] = handler
            
            logger.info(f"디바이스 {device_id} 핸들러 생성: {host}:{port}")
    
    # ==== 모든 핸들러 시작 ====
    def start(self) -> bool:
        """모든 TCP 핸들러를 시작합니다."""
        success = True
        
        for device_id, handler in self.handlers.items():
            if not handler.start():
                logger.error(f"디바이스 {device_id} 핸들러 시작 실패")
                success = False
            else:
                logger.info(f"디바이스 {device_id} 핸들러 시작 성공")
        
        return success
    
    # ==== 모든 핸들러 종료 ====
    def stop(self):
        """모든 TCP 핸들러를 종료합니다."""
        for device_id, handler in self.handlers.items():
            try:
                handler.stop()
                logger.info(f"디바이스 {device_id} 핸들러 종료 성공")
            except Exception as e:
                logger.error(f"디바이스 {device_id} 핸들러 종료 실패: {str(e)}")
    
    # ==== 디바이스 핸들러 등록 ====
    def register_device_handler(self, device_id: str, message_type: str, handler: Callable):
        """디바이스별 메시지 타입 핸들러를 등록합니다."""
        if device_id in self.handlers:
            self.handlers[device_id].register_device_handler(device_id, message_type, handler)
            logger.debug(f"디바이스 {device_id}, 타입 {message_type} 핸들러 등록")
        else:
            logger.error(f"등록되지 않은 디바이스 ID: {device_id}")
    
    # ==== 메시지 전송 ====
    def send_message(self, device_id: str, command: str) -> bool:
        """지정된 디바이스에 명령 메시지를 전송합니다."""
        if device_id in self.handlers:
            return self.handlers[device_id].send_message(device_id, command)
        else:
            logger.error(f"등록되지 않은 디바이스 ID: {device_id}")
            return False
    
    # ==== 연결된 디바이스 목록 ====
    def get_connected_devices(self) -> List[str]:
        """현재 연결된 모든 디바이스 ID 목록을 반환합니다."""
        devices = []
        
        for device_id, handler in self.handlers.items():
            if handler.is_device_connected(device_id):
                devices.append(device_id)
        
        return devices