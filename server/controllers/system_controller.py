"""
시스템 전체 상태를 관리하고 모니터링하는 컨트롤러
"""
import os
import psutil
import platform
import time
from datetime import datetime
from loguru import logger
from config import (
    WAREHOUSES, 
    STATUS_CHECK_INTERVAL,
    DB_HOST,
    DB_PORT,
    DB_NAME
)

# 서버 시작 시간 기록
SERVER_START_TIME = time.time()

def check_db_connection():
    """
    데이터베이스 연결 상태를 확인합니다.
    
    Returns:
        str: 연결 상태 (connected/disconnected)
    """
    try:
        from db.db_manager import db_manager
        status = db_manager.get_connection_status()
        return "connected" if status["connected"] else "disconnected"
    except Exception as e:
        logger.error(f"DB 연결 상태 확인 중 오류: {e}")
        return "disconnected"

def get_system_status():
    """
    전체 시스템 상태 정보를 수집하여 반환합니다.
    
    Returns:
        dict: 시스템 상태 정보를 포함하는 딕셔너리
    """
    try:
        # 시스템 기본 정보
        system_info = {
            "status": "online",
            "uptime_seconds": int(time.time() - SERVER_START_TIME),
            "server_time": datetime.now().isoformat(),
            "os": platform.platform(),
            "python_version": platform.python_version(),
        }
        
        # 시스템 리소스 정보
        resource_info = {
            "cpu_usage": psutil.cpu_percent(interval=0.1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
        }
        
        # 데이터베이스 연결 정보
        db_info = {
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME,
            "connection_status": check_db_connection(),
        }
        
        # 창고 환경 정보
        warehouse_info = get_warehouse_status()
        
        # 하드웨어 연결 상태
        hardware_info = get_hardware_connection_status()
        
        return {
            "system": system_info,
            "resources": resource_info,
            "database": db_info,
            "warehouses": warehouse_info,
            "hardware": hardware_info,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"시스템 상태 조회 중 오류 발생: {e}")
        return {
            "status": "error",
            "message": f"시스템 상태 조회 중 오류가 발생했습니다: {str(e)}"
        }

def get_warehouse_status():
    """
    각 창고의 현재 상태 정보를 수집합니다.
    
    Returns:
        dict: 창고별 상태 정보
    """
    status = {}
    for warehouse_id, config in WAREHOUSES.items():
        # 실제로는 센서 데이터나 DB에서 실시간 정보를 가져와야 함
        # 임시 데이터로 대체
        status[warehouse_id] = {
            "type": config["type"],
            "current_temp": (config["temp_min"] + config["temp_max"]) / 2,  # 임시 데이터
            "target_temp_min": config["temp_min"],
            "target_temp_max": config["temp_max"],
            "humidity": 50,  # 임시 데이터
            "status": "normal"
        }
    return status

def get_hardware_connection_status():
    """
    하드웨어 장치들의 연결 상태를 확인합니다.
    
    Returns:
        dict: 하드웨어별 연결 상태
    """
    # 실제로는 각 하드웨어의 연결 상태를 확인해야 함
    # 임시 데이터로 대체
    return {
        "sort_controller": {"status": "connected", "last_seen": datetime.now().isoformat()},
        "env_controller_ab": {"status": "connected", "last_seen": datetime.now().isoformat()},
        "env_controller_cd": {"status": "connected", "last_seen": datetime.now().isoformat()},
        "access_controller": {"status": "connected", "last_seen": datetime.now().isoformat()}
    }