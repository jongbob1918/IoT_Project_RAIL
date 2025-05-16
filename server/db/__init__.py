# db/__init__.py
import logging
from typing import Dict, Any, Optional, List, Tuple, Union

# 로깅 설정
logger = logging.getLogger(__name__)

# 필요한 모듈 임포트
try:
    from .config import DBConfig
    from .db_connection import DBConnection
    from .repository import (
        BaseRepository, WarehouseRepository, ProductRepository, 
        ProductItemRepository, EmployeeRepository, AccessLogRepository, 
        WarningLogRepository
    )
    from .migration import DatabaseMigration
    
    # 데이터베이스 초기화 함수
    def init_database(config_module=None) -> bool:
        """데이터베이스 초기화
        
        Args:
            config_module: 설정 모듈 (None인 경우 환경 변수 사용)
            
        Returns:
            bool: 초기화 성공 여부
        """
        try:
            # 설정 로드
            if config_module:
                config = DBConfig.from_config_file(config_module)
            else:
                config = DBConfig.from_config_file()
                
            # 마이그레이션 실행
            migration = DatabaseMigration(config)
            return migration.init_database()
        except Exception as e:
            logger.error(f"데이터베이스 초기화 중 오류: {str(e)}")
            return False
    
    # 싱글톤 DB 연결 인스턴스
    db_connection = DBConnection()
    
    # 주요 리포지토리 인스턴스
    warehouse_repo = WarehouseRepository(db_connection)
    product_repo = ProductRepository(db_connection)
    product_item_repo = ProductItemRepository(db_connection)
    employee_repo = EmployeeRepository(db_connection)
    access_log_repo = AccessLogRepository(db_connection)
    warning_log_repo = WarningLogRepository(db_connection)
    
    # DB 관리자 인스턴스 (설정 조회용)
    class DBManager:
        """DB 관리자 클래스 - 중앙 관리를 위한 도우미 클래스"""
        
        def __init__(self, db_conn=None, warehouse_repository=None):
            self.db = db_conn or db_connection
            self.warehouse_repo = warehouse_repository or warehouse_repo
            self.connected = self.db.connected
        
        def get_warehouse_temp_settings(self) -> Dict[str, Dict[str, Any]]:
            """창고별 온도 설정 조회"""
            if not self.connected:
                return {}
            return self.warehouse_repo.get_warehouse_temp_settings()
        
        def update_target_temperature(self, warehouse_id: str, target_temp: float) -> bool:
            """창고 목표 온도 설정 업데이트"""
            if not self.connected:
                return False
            return self.warehouse_repo.save_target_temperature(warehouse_id, target_temp)
    
    # DB 관리자 싱글톤 인스턴스
    db_manager = DBManager()
    
    # 버전 정보
    __version__ = '1.0.0'
    
    # 모듈 외부에서 접근 가능한 심볼 정의
    __all__ = [
        'DBConfig', 'DBConnection', 'DatabaseMigration',
        'init_database', 'db_connection', 'db_manager',
        'warehouse_repo', 'product_repo', 'product_item_repo', 
        'employee_repo', 'access_log_repo', 'warning_log_repo'
    ]
    
# 예외 처리 블록 - MySQL 라이브러리 미설치 시
except ImportError as e:
    logger.error(f"DB 모듈 가져오기 오류: {str(e)}")
    
    # 더미 클래스 및 함수 정의 (최소 기능 제공)
    class DummyDBConnection:
        """더미 데이터베이스 연결 클래스"""
        
        def __init__(self):
            self.connected = False
        
        def get_connection_status(self):
            return {"connected": False, "host": "localhost", "database": "none", "user": "none"}
        
        def execute_query(self, query, params=None):
            logger.warning(f"DB 연결 없음 - 쿼리 무시됨: {query}")
            return None
        
        def execute_dict_query(self, query, params=None):
            logger.warning(f"DB 연결 없음 - 쿼리 무시됨: {query}")
            return None
        
        def execute_update(self, query, params=None):
            logger.warning(f"DB 연결 없음 - 업데이트 무시됨: {query}")
            return 0
    
    # 더미 리포지토리 클래스
    class DummyRepository:
        """더미 리포지토리 클래스"""
        
        def __init__(self, db_connection=None):
            pass
        
        def get_all(self):
            return []
        
        def get_by_id(self, id_value):
            return None
    
    # 더미 DB 관리자 클래스
    class DummyDBManager:
        """더미 DB 관리자 클래스"""
        
        def __init__(self):
            self.connected = False
        
        def get_warehouse_temp_settings(self):
            # 기본 설정값 반환
            return {
                "A": {"type": "freezer", "temp_min": -30, "temp_max": -18, "target_temp": -22},
                "B": {"type": "refrigerator", "temp_min": 0, "temp_max": 10, "target_temp": 5},
                "C": {"type": "room_temp", "temp_min": 15, "temp_max": 25, "target_temp": 20}
            }
        
        def update_target_temperature(self, warehouse_id, target_temp):
            logger.warning("DB 연결 없음 - 온도 설정 업데이트 무시됨")
            return False
    
    # 더미 초기화 함수
    def init_database(config_module=None):
        logger.warning("MySQL 라이브러리가 설치되어 있지 않아 데이터베이스를 초기화할 수 없습니다.")
        logger.warning("'pip install mysql-connector-python' 명령어로 필요한 패키지를 설치하세요.")
        return False
    
    # 더미 인스턴스 생성
    db_connection = DummyDBConnection()
    warehouse_repo = DummyRepository()
    product_repo = DummyRepository()
    product_item_repo = DummyRepository()
    employee_repo = DummyRepository()
    access_log_repo = DummyRepository()
    warning_log_repo = DummyRepository()
    db_manager = DummyDBManager()
    
    # 버전 정보
    __version__ = '1.0.0'
    
    # 모듈 외부에서 접근 가능한 심볼 정의 (더미 모드용 제한적 목록)
    __all__ = [
        'init_database', 'db_connection', 'db_manager',
        'warehouse_repo', 'product_repo', 'product_item_repo', 
        'employee_repo', 'access_log_repo', 'warning_log_repo'
    ]