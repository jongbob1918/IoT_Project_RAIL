# ===== 풀필먼트 시스템 설정 파일 =====
# ===== 시스템의 모든 설정을 중앙화하여 관리 =====
import os
from typing import Dict, Any
from pathlib import Path

# 기본 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent

# .env 파일 로드 (있는 경우)
try:
    from dotenv import load_dotenv
    ENV_PATH = BASE_DIR / '.env'
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
except ImportError:
    pass     # python-dotenv가 설치되지 않은 경우 무시

# ===== 서버 설정 =====
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# 데이터베이스 설정
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")  # 기본값 수정
DB_PASSWORD = os.getenv("DB_PASSWORD", "0000")  # 기본값 설정
DB_NAME = os.getenv("DB_NAME", "rail_db")  # rail_db로 통일
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ===== TCP 하드웨어 통신 설정 =====
TCP_PORT = int(os.getenv("TCP_PORT", "9000"))
HARDWARE_IP = {
    'sort_controller': os.getenv("SORT_CONTROLLER_IP", '192.168.0.101'),
    'env_controller': os.getenv("ENV_AB_CONTROLLER_IP", '192.168.0.102'),  # 환경 제어(A,B 창고)
    'env_cd_controller': os.getenv("ENV_CD_CONTROLLER_IP", '192.168.0.103'),  # 환경 제어(C,D 창고)
    'access_controller': os.getenv("ACCESS_CONTROLLER_IP", '192.168.0.104')
}

# ===== 멀티포트모드 TCP 하드웨어 통신 설정 =====
MULTI_PORT_MODE = os.getenv("MULTI_PORT_MODE", "False").lower() == "true"
TCP_PORTS = {
    'sort_controller': int(os.getenv("SORT_CONTROLLER_PORT", "9001")),
    'env_controller': int(os.getenv("ENV_CONTROLLER_PORT", "9002")),
    'access_controller': int(os.getenv("ACCESS_CONTROLLER_PORT", "9004"))
}


# ===== Socket.IO 설정 =====
SOCKETIO_PING_TIMEOUT = int(os.getenv("SOCKETIO_PING_TIMEOUT", "5"))
SOCKETIO_PING_INTERVAL = int(os.getenv("SOCKETIO_PING_INTERVAL", "25"))
SOCKETIO_ASYNC_MODE = os.getenv("SOCKETIO_ASYNC_MODE", "threading") 

# ===== 창고 환경 설정 =====
WAREHOUSES = {
    # A: 냉동 식품 창고 (-30°C ~ -18°C)
    "A": {"type": "freezer", "temp_min": -30, "temp_max": -18},
    # B: 냉장 식품 창고 (0°C ~ 10°C)
    "B": {"type": "refrigerator", "temp_min": 0, "temp_max": 10},
    # C: 상온 식품 창고 (15°C ~ 25°C)
    "C": {"type": "room_temp", "temp_min": 15, "temp_max": 25}
}

# ===== 로깅 설정 =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "server.log")
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", str(10 * 1024 * 1024)))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# ===== 시스템 모니터링 설정 =====
STATUS_CHECK_INTERVAL = int(os.getenv("STATUS_CHECK_INTERVAL", "10"))  # 상태 점검 주기(10초)

# ===== 모든 설정을 하나의 딕셔너리로 통합 =====
CONFIG = {
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
    "DB_NAME": DB_NAME,
    "DB_URL": DB_URL,
    "SERVER_HOST": SERVER_HOST,
    "SERVER_PORT": SERVER_PORT,
    "DEBUG": DEBUG,
    "TCP_PORT": TCP_PORT,
    "HARDWARE_IP": HARDWARE_IP,
    "MULTI_PORT_MODE": MULTI_PORT_MODE,
    "TCP_PORTS": TCP_PORTS,
    "SOCKETIO_PING_TIMEOUT": SOCKETIO_PING_TIMEOUT,
    "SOCKETIO_PING_INTERVAL": SOCKETIO_PING_INTERVAL,
    "SOCKETIO_ASYNC_MODE": SOCKETIO_ASYNC_MODE,
    "WAREHOUSES": WAREHOUSES,
    "LOG_LEVEL": LOG_LEVEL,
    "LOG_FILE": LOG_FILE,
    "LOG_MAX_SIZE": LOG_MAX_SIZE,
    "LOG_BACKUP_COUNT": LOG_BACKUP_COUNT,
    "STATUS_CHECK_INTERVAL": STATUS_CHECK_INTERVAL
}