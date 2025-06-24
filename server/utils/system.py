import logging
import time
from datetime import datetime
import psutil

logger = logging.getLogger(__name__)

# 시스템 시작 시간
SYSTEM_START_TIME = time.time()

class Controller:
    """간소화된 통합 컨트롤러 기본 클래스"""
    
    def __init__(self, tcp_handler=None, socketio=None, db_helper=None):
        """컨트롤러 초기화"""
        self.tcp_handler = tcp_handler
        self.socketio = socketio
        self.db_helper = db_helper
        self.logger = logger
        
        if tcp_handler:
            self.register_handlers()
            
        logger.info(f"{self.__class__.__name__} 초기화 완료")
    
    def register_handlers(self):
        """각 컨트롤러별 이벤트 핸들러 등록 (기본 구현)"""
        pass
    
    def handle_event(self, message):
        """이벤트 메시지 처리"""
        if 'content' in message:
            self.process_event(message['content'])
    
    def process_event(self, content):
        """이벤트 처리 로직 (기본 구현)"""
        logger.debug(f"이벤트 수신: {content}")
    
    def handle_response(self, message):
        """응답 메시지 처리"""
        if 'content' in message:
            logger.debug(f"응답 수신: {message['content']}")
    
    def emit_event(self, event_name, data):
        """소켓 이벤트 발송"""
        if not self.socketio:
            return
            
        try:
            event_data = {
                "type": "event",
                "category": self.__class__.__name__.lower().replace('controller', ''),
                "action": event_name,
                "payload": data,
                "timestamp": int(time.time())
            }
            
            self.socketio.emit("event", event_data, namespace="/ws")
        except Exception as e:
            logger.error(f"이벤트 발송 오류: {str(e)}")


class SystemMonitor:
    """간소화된 시스템 모니터링"""
    
    def __init__(self, config=None):
        """시스템 모니터 초기화"""
        self.config = config or {}
        self.hardware_status = {}
        
    def get_system_status(self):
        """시스템 상태 정보 반환"""
        try:
            # 기본 시스템 정보
            status = {
                "status": "online",
                "uptime": int(time.time() - SYSTEM_START_TIME),
                "cpu_usage": psutil.cpu_percent(interval=0.1),
                "memory_usage": psutil.virtual_memory().percent,
                "timestamp": datetime.now().isoformat()
            }
            
            # DB 상태 (연결된 경우)
            if hasattr(self, 'db_helper') and self.db_helper:
                status["db_connected"] = self.db_helper.is_connected()
            
            # 하드웨어 상태
            status["hardware"] = self.hardware_status
            
            return status
            
        except Exception as e:
            logger.error(f"시스템 상태 조회 오류: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def update_hardware_status(self, device_id, status):
        """하드웨어 장치 상태 업데이트"""
        self.hardware_status[device_id] = {
            "status": status,
            "last_updated": datetime.now().isoformat()
        }
    
    def check_warehouse_status(self, warehouse_data):
        """창고 데이터 분석 및 경고 상태 확인"""
        results = {}
        
        for wh_id, data in warehouse_data.items():
            if "temp" in data and "target_temp" in data:
                temp = data["temp"]
                target = data["target_temp"]
                
                # 기본 상태는 정상으로 설정
                status = "normal"
                
                # 온도 차이가 5도 이상이면 경고
                if abs(temp - target) >= 5:
                    status = "warning"
                
                results[wh_id] = {
                    "status": status,
                    "temp": temp,
                    "target": target
                }
        
        return results