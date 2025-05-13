import os
import logging
from logging.handlers import RotatingFileHandler
from config import LOG_LEVEL, LOG_FILE, LOG_MAX_SIZE, LOG_BACKUP_COUNT

# ==== 로거거를 설정하고 반환. 동일한 이름의 로거가 이미 설정되어 있다면 중복 설정방지 ====
def setup_logger(name: str = 'server') -> logging.Logger:
    
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