# db/db_manager.py
import os
import sys
import logging
from typing import Dict, Any, Optional  # 타입 힌트 임포트 추가

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger(__name__)

class DBManager:
    """DB 관리자 클래스 - 중앙 관리를 위한 도우미 클래스"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_connection=None, warehouse_repo=None):
        """초기화"""
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # 설정 직접 사용
        self.host = DB_HOST
        self.port = DB_PORT
        self.user = DB_USER
        self.password = DB_PASSWORD
        self.database = DB_NAME
        
        # 연결 및 저장소 설정
        self.db = db_connection
        self.warehouse_repo = warehouse_repo
        self.connected = self.db is not None and hasattr(self.db, 'connected') and self.db.connected
        
        self._initialized = True
    
    def get_connection_status(self) -> Dict[str, Any]:
        """연결 상태 정보 반환"""
        status = {
            "connected": self.connected,
            "host": "localhost",
            "database": "rail_db",
            "user": "root"
        }
        
        # DB 연결 객체에서 안전하게 정보 추출
        if self.db and hasattr(self.db, 'get_connection_status'):
            # DBConnection 객체가 자체 상태 메서드를 가진 경우
            db_status = self.db.get_connection_status()
            status.update(db_status)
        elif self.db:
            # 상태 메서드가 없는 경우 안전하게 속성 접근
            if hasattr(self.db, 'config'):
                cfg = self.db.config
                status["host"] = getattr(cfg, 'host', status["host"])
                status["database"] = getattr(cfg, 'database', status["database"])
                status["user"] = getattr(cfg, 'user', status["user"])
        
        return status
    
    def get_warehouse_temp_ranges(self) -> Dict[str, Dict[str, float]]:
        """창고별 온도 범위 조회"""
        if not self.connected or not self.warehouse_repo:
            # 기본 설정값 반환
            return {
                "A": {"temp_min": -30, "temp_max": -18, "type": "freezer"},
                "B": {"temp_min": 0, "temp_max": 10, "type": "refrigerator"},
                "C": {"temp_min": 15, "temp_max": 25, "type": "room_temp"}
            }
        
        # warehouse_repo를 통해 데이터 가져오기
        return self.warehouse_repo.get_temperature_ranges()
    
    def get_warehouse_target_temps(self) -> Dict[str, float]:
        """창고별 목표 온도 설정값 조회"""
        if not self.connected or not self.warehouse_repo:
            # 기본 설정값 반환
            return {"A": -22, "B": 5, "C": 20}
        
        # 각 창고별 목표 온도 조회
        temps = {}
        if hasattr(self.warehouse_repo, 'get_all'):
            warehouses = self.warehouse_repo.get_all()
            
            for wh in warehouses:
                wh_id = wh.get('id') if isinstance(wh, dict) else getattr(wh, 'id', '')
                if hasattr(self.warehouse_repo, 'get_target_temperature'):
                    target_temp = self.warehouse_repo.get_target_temperature(wh_id)
                    if target_temp is not None:
                        temps[wh_id] = target_temp
        
        return temps if temps else {"A": -22, "B": 5, "C": 20}
    
    def get_warehouse_temp_settings(self) -> Dict[str, Dict[str, Any]]:
        """창고별 온도 설정 조회"""
        if not self.connected or not self.warehouse_repo:
            # 기본 설정값 반환
            return {
                "A": {"type": "freezer", "temp_min": -30, "temp_max": -18, "target_temp": -22},
                "B": {"type": "refrigerator", "temp_min": 0, "temp_max": 10, "target_temp": 5},
                "C": {"type": "room_temp", "temp_min": 15, "temp_max": 25, "target_temp": 20}
            }
        
        if hasattr(self.warehouse_repo, 'get_warehouse_temp_settings'):
            return self.warehouse_repo.get_warehouse_temp_settings()
        return {}
    
    def update_target_temperature(self, warehouse_id: str, target_temp: float) -> bool:
        """창고 목표 온도 설정 업데이트"""
        if not self.connected or not self.warehouse_repo:
            logger.warning("DB 연결 없음 - 온도 설정 업데이트 무시됨")
            return False
        
        if hasattr(self.warehouse_repo, 'save_target_temperature'):
            return self.warehouse_repo.save_target_temperature(warehouse_id, target_temp)
        return False

# 초기 인스턴스 (실제로는 db/__init__.py에서 초기화)
db_manager = DBManager()