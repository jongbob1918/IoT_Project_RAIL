import logging
logger = logging.getLogger(__name__)

# 편의성을 위해 주요 클래스와 함수를 패키지 레벨로 import
try:
    from .db_manager import DBManager, db_manager
    from .init_db import init_database
    MYSQL_AVAILABLE = True
except ImportError as e:
    # MySQL 라이브러리가 없을 경우 로깅하고 계속 진행
    logger.warning(f"MySQL 관련 모듈을 import할 수 없습니다. DB 기능이 제한될 수 있습니다. 오류: {e}")
    logger.warning("문제 해결을 위해 'pip install mysql-connector-python pymysql' 명령어로 필요한 패키지를 설치하세요.")
    
    # 더미 객체 제공
    class DummyDBManager:
        def __init__(self):
            self.connected = False
            
        def get_connection_status(self):
            return {"connected": False, "host": "localhost", "database": "none", "user": "none"}
            
        def get_empty_shelves(self, warehouse):
            shelves = {
                'A': ['A01', 'A02', 'A03', 'A04'],
                'B': ['B01', 'B02', 'B03', 'B04'],
                'C': ['C01', 'C02', 'C03', 'C04']
            }
            return shelves.get(warehouse, [])
    
    db_manager = DummyDBManager()
    
    # 더미 초기화 함수
    def init_database():
        logger.warning("MySQL 라이브러리가 설치되어 있지 않아 데이터베이스를 초기화할 수 없습니다.")
        return False
    
    MYSQL_AVAILABLE = False

# 버전 정보
__version__ = '1.0.0'

def init_database():
    """데이터베이스 초기화 함수"""
    try:
        # 기존 DB 모듈 초기화
        from .init_db import init_database as init_db_func
        init_result = init_db_func()
        
        # 추가 테이블 확인 및 생성
        create_tables_if_not_exist()
        
        return init_result
    except ImportError as e:
        logger.error(f"데이터베이스 초기화 모듈을 가져올 수 없습니다: {e}")
        return False

def create_tables_if_not_exist():
    """필요한 테이블이 없으면 생성합니다."""
    if not db_manager.connected:
        logger.warning("DB 연결 없음 - 테이블 생성 불가")
        return False
    
    try:
        # 기존 테이블 목록 조회
        query = "SHOW TABLES"
        result = db_manager.execute_query(query)
        
        if result:
            existing_tables = [row[0] for row in result]
            logger.debug(f"기존 테이블: {existing_tables}")
            
            # access_logs 테이블 확인 및 생성
            if 'access_logs' not in existing_tables:
                logger.info("access_logs 테이블이 없습니다. 생성합니다.")
                create_access_logs_table()
            
            # daily_access_stats 테이블 확인 및 생성
            if 'daily_access_stats' not in existing_tables:
                logger.info("daily_access_stats 테이블이 없습니다. 생성합니다.")
                create_daily_access_stats_table()
            
            return True
        else:
            logger.error("테이블 목록을 조회할 수 없습니다.")
            return False
    except Exception as e:
        logger.error(f"테이블 확인 중 오류: {str(e)}")
        return False

def create_access_logs_table():
    """access_logs 테이블을 생성합니다."""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS access_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            card_id VARCHAR(50),
            employee_name VARCHAR(100),
            access_type VARCHAR(20),
            timestamp DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        result = db_manager.execute_update(query)
        if result:
            logger.info("access_logs 테이블이 생성되었습니다.")
        return result
    except Exception as e:
        logger.error(f"access_logs 테이블 생성 중 오류: {str(e)}")
        return False

def create_daily_access_stats_table():
    """daily_access_stats 테이블을 생성합니다."""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS daily_access_stats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE,
            entries INT DEFAULT 0,
            exits INT DEFAULT 0,
            current_count INT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY (date)
        )
        """
        result = db_manager.execute_update(query)
        if result:
            logger.info("daily_access_stats 테이블이 생성되었습니다.")
        return result
    except Exception as e:
        logger.error(f"daily_access_stats 테이블 생성 중 오류: {str(e)}")
        return False

__all__ = ['db_manager', 'init_database', 'DBManager']