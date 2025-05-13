import logging
logger = logging.getLogger(__name__)

# 편의성을 위해 주요 클래스와 함수를 패키지 레벨로 import
try:
    from .db_manager import DBManager
    db_manager = DBManager()  # 싱글톤 인스턴스 생성
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