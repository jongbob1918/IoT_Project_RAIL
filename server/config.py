# server/config.py
import os
import logging
from typing import Dict, Any
from pathlib import Path

# 기본 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ===== 서버 설정 =====
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000
DEBUG = False

# ===== UDP 설정 =====
UDP_HOST = "0.0.0.0"  # 모든 인터페이스에서 수신
UDP_PORT = 9000

# 데이터베이스 설정
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "134679"
DB_NAME = "rail_db"
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ===== TCP 하드웨어 통신 설정 =====
TCP_PORT = 9000
HARDWARE_IP = {
    'sort_controller': '192.168.0.101',
    'env_ab_controller': '192.168.0.102', 
    'env_cd_controller': '192.168.0.103',
    'access_controller': '192.168.0.104'
}

# ===== 멀티포트모드 TCP 하드웨어 통신 설정 =====
MULTI_PORT_MODE = False
TCP_PORTS = {
    'sort_controller': 9001,
    'env_ab_controller': 9002,
    'env_cd_controller': 9003,
    'access_controller': 9004
}

# ===== Socket.IO 설정 =====
SOCKETIO_PING_TIMEOUT = 5
SOCKETIO_PING_INTERVAL = 25
SOCKETIO_ASYNC_MODE = "threading"

# ===== 창고 환경 설정 =====
DEFAULT_WAREHOUSES = {
    # A: 냉동 식품 창고 (-30°C ~ -18°C), 기본 목표 온도: -22°C
    "A": {"type": "freezer", "temp_min": -30, "temp_max": -18, "default_target": -22},
    # B: 냉장 식품 창고 (0°C ~ 10°C), 기본 목표 온도: 5°C
    "B": {"type": "refrigerator", "temp_min": 0, "temp_max": 10, "default_target": 5},
    # C: 상온 식품 창고 (15°C ~ 25°C), 기본 목표 온도: 20°C
    "C": {"type": "room_temp", "temp_min": 15, "temp_max": 25, "default_target": 20}
}

# db_manager 임포트 부분 제거하고 기본 창고 설정 직접 사용
def get_warehouse_config():
    # 기본값 반환
    return DEFAULT_WAREHOUSES

WAREHOUSES = get_warehouse_config()

# ===== 로깅 설정 =====
LOG_LEVEL = "INFO"
LOG_FILE = "server.log"
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# ===== 시스템 모니터링 설정 =====
STATUS_CHECK_INTERVAL = 5  # 상태 점검 주기(5초)

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