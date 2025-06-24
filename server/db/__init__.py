# db/__init__.py
import logging
from typing import Dict, Any, Optional, List, Tuple, Union

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    # DB 연결 클래스 임포트
    from .db_connection import DBConnection
    
    # 데이터베이스 초기화 함수
    def init_database() -> bool:
        """데이터베이스 초기화"""
        try:
            from .migration import DatabaseMigration
            migration = DatabaseMigration()
            return migration.init_database()
        except Exception as e:
            logger.error(f"데이터베이스 초기화 오류: {str(e)}")
            return False
    
    # 싱글톤 DB 연결 인스턴스 생성
    db_connection = DBConnection()
    
    # 리포지토리 및 마이그레이션 클래스 임포트
    from .repository import (
        BaseRepository, WarehouseRepository, ProductRepository, 
        ProductItemRepository, EmployeeRepository, AccessLogRepository, 
        WarningLogRepository
    )
    
    # 주요 리포지토리 인스턴스 생성
    warehouse_repo = WarehouseRepository(db_connection)
    product_repo = ProductRepository(db_connection)
    product_item_repo = ProductItemRepository(db_connection)
    employee_repo = EmployeeRepository(db_connection)
    access_log_repo = AccessLogRepository(db_connection)
    warning_log_repo = WarningLogRepository(db_connection)
    
    # DBManager 지연 임포트
    from .db_manager import DBManager
    
    # 새 DBManager 인스턴스 생성
    db_manager = DBManager(db_connection, warehouse_repo)
    
    # 외부 노출 심볼
    __all__ = [
        'DBConnection', 'init_database', 'db_connection', 'db_manager',
        'warehouse_repo', 'product_repo', 'product_item_repo', 
        'employee_repo', 'access_log_repo', 'warning_log_repo'
    ]
    
except ImportError as e:
    logger.error(f"DB 모듈 가져오기 오류: {str(e)}")
    
    # 더미 클래스 및 함수 정의 (최소 기능 제공)
    class DummyDBConnection:
        """더미 데이터베이스 연결 클래스"""
        def __init__(self):
            self.connected = False
            
        def connect(self):
            return False
            
        def execute_query(self, *args, **kwargs):
            return []
            
        def execute_dict_query(self, *args, **kwargs):
            return []
            
        def execute_update(self, *args, **kwargs):
            return 0
    
    # 더미 리포지토리 클래스
    class DummyRepository:
        """더미 리포지토리 클래스"""
        def __init__(self, *args, **kwargs):
            pass
            
        def get_all(self, *args, **kwargs):
            return []
            
        def get_by_id(self, *args, **kwargs):
            return None
    
    # 더미 초기화 함수
    def init_database(*args, **kwargs):
        return False
    
    # 더미 인스턴스 생성
    db_connection = DummyDBConnection()
    warehouse_repo = DummyRepository()
    product_repo = DummyRepository()
    product_item_repo = DummyRepository()
    employee_repo = DummyRepository()
    access_log_repo = DummyRepository()
    warning_log_repo = DummyRepository()
    
    # DBManager 가져오기 시도
    try:
        from .db_manager import DBManager
        db_manager = DBManager()
    except ImportError:
        # 가져오기 실패 시 더미 클래스 정의
        class DBManager:
            def __init__(self, *args, **kwargs):
                pass
        db_manager = DBManager()