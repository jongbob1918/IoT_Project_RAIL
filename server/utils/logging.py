import os
import time
from logging.handlers import RotatingFileHandler
from config import LOG_LEVEL, LOG_FILE, LOG_MAX_SIZE, LOG_BACKUP_COUNT
import logging
logging.basicConfig(
    level=logging.DEBUG,  # INFO에서 DEBUG로 변경
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# ==== 로거 설정 함수 (기존 코드 유지) ====
def setup_logger(name: str = 'server') -> logging.Logger:
    """로거를 설정하고 반환합니다."""
    
    # 로거 인스턴스 생성 및 레벨 설정
    logger = logging.getLogger(name)
    
    # 문자열 로그 레벨을 로깅 상수로 변환
    log_level = getattr(logging, LOG_LEVEL.upper())
    logger.setLevel(log_level)

    # 이미 핸들러가 설정되어 있다면 중복 추가 방지
    if logger.handlers:
        return logger

    # logs 디렉토리 경로 설정
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # config에서 파일명을 가져오되, 이름별 구분이 필요하면 접두사 사용
    if name == 'server':
        log_filename = LOG_FILE  # config에 정의된 기본 로그 파일명
    else:
        # 다른 이름의 로거는 이름을 접두사로 추가
        log_filename = f"{name}_{LOG_FILE}"
    
    log_path = os.path.join(log_dir, log_filename)

    # config에서 정의한 값으로 회전 로그 설정
    file_handler = RotatingFileHandler(
        log_path, 
        maxBytes=LOG_MAX_SIZE, 
        backupCount=LOG_BACKUP_COUNT
    )
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 콘솔 출력 핸들러 추가 (개발 중 로그 확인 용이)
    if os.getenv('DEBUG', 'False').lower() == 'true':
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


# ==== 새로운 유틸리티 함수들 ====

def emit_event(socketio, event_name, data):
    """소켓 이벤트를 발송합니다.
    
    Args:
        socketio: SocketIO 인스턴스
        event_name: 이벤트 이름
        data: 이벤트 데이터
        
    Returns:
        bool: 발송 성공 여부
    """
    if not socketio:
        return False
        
    try:
        event_data = {
            "type": "event",
            "name": event_name,
            "data": data,
            "timestamp": int(time.time())
        }
        
        socketio.emit(event_name, event_data)
        return True
    except Exception as e:
        logger = logging.getLogger('utils')
        logger.error(f"이벤트 발송 오류: {str(e)}")
        return False


def send_command(tcp_handler, device, command):
    """장치에 명령을 전송합니다.
    
    Args:
        tcp_handler: TCP 통신 핸들러
        device: 장치 식별자 
        command: 전송할 명령어
        
    Returns:
        bool: 전송 성공 여부
    """
    if not tcp_handler:
        return False
        
    try:
        success = tcp_handler.send_message(device, command)
        if not success:
            logger = logging.getLogger('utils')
            logger.error(f"명령 전송 실패: {device}, {command}")
        return success
    except Exception as e:
        logger = logging.getLogger('utils')
        logger.error(f"명령 전송 오류: {str(e)}")
        return False


def parse_data(data_str, separator=';'):
    """데이터 문자열을 파싱합니다.
    
    Args:
        data_str: 파싱할 데이터 문자열
        separator: 구분자 (기본값: ';')
        
    Returns:
        list: 파싱된 데이터 목록
    """
    if not data_str:
        return []
        
    try:
        return [item.strip() for item in data_str.split(separator)]
    except Exception as e:
        logger = logging.getLogger('utils')
        logger.error(f"데이터 파싱 오류: {str(e)}")
        return []


def get_system_info():
    """시스템 기본 정보를 반환합니다.
    
    Returns:
        dict: 시스템 정보
    """
    import platform
    import psutil
    
    try:
        return {
            "os": platform.platform(),
            "python": platform.python_version(),
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent
        }
    except Exception as e:
        logger = logging.getLogger('utils')
        logger.error(f"시스템 정보 조회 오류: {str(e)}")
        return {}