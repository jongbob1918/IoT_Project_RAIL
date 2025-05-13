# server/db/db_manager.py
import os
import logging
from typing import Optional, Dict, List, Any, Tuple

# MySQL 관련 라이브러리
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    logging.warning("MySQL 라이브러리를 가져올 수 없습니다. 'pip install mysql-connector-python pymysql' 명령어로 설치하세요.")
    MYSQL_AVAILABLE = False

# config.py에서 설정 가져오기 시도
try:
    from config import CONFIG, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    logging.warning("config.py에서 설정을 가져올 수 없습니다. 환경 변수를 사용합니다.")

# 로거 설정
logger = logging.getLogger(__name__)

class DBManager:
    """
    데이터베이스 연결 관리 클래스
    
    이 클래스는 데이터베이스 연결을 관리하고 DB 연결이 없을 때
    임시 데이터를 제공하는 역할을 합니다.
    """
    
    _instance = None
    
    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """초기화 (싱글톤이므로 한 번만 실행)"""
        if self._initialized:
            return
            
        # 데이터베이스 연결 정보 (config.py 또는 환경 변수 사용)
        if USE_CONFIG:
            self.host = DB_HOST
            self.port = DB_PORT
            self.user = DB_USER
            self.password = DB_PASSWORD
            self.database = DB_NAME
            logger.info("config.py에서 데이터베이스 설정을 로드했습니다.")
        else:
            self.host = os.getenv("DB_HOST", "localhost")
            self.port = os.getenv("DB_PORT", "3306")
            self.user = os.getenv("DB_USER", "root")
            self.password = os.getenv("DB_PASSWORD", "0000")
            self.database = os.getenv("DB_NAME", "rail_db")
            logger.info("환경 변수에서 데이터베이스 설정을 로드했습니다.")
        
        # 데이터베이스 연결 객체
        self.connection = None
        self.connected = False
        
        # 가상 데이터 (DB 연결 실패 시 사용)
        self.mock_data = {}
        self._initialize_mock_data()
        
        # 데이터베이스 연결 시도
        if MYSQL_AVAILABLE:
            self.connect()
        else:
            logger.warning("MySQL 라이브러리가 설치되어 있지 않아 가상 데이터를 사용합니다.")
        
        self._initialized = True
        
    def _initialize_mock_data(self):
        """가상 데이터 초기화"""
        # 창고별 선반 데이터
        shelves = {
            'A': ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08'],
            'B': ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08'],
            'C': ['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08'],
            'D': ['D01', 'D02', 'D03', 'D04', 'D05', 'D06', 'D07', 'D08']
        }
        
        # 임의의 빈 선반 설정
        empty_shelves = {
            'A': ['A03', 'A07', 'A08'],
            'B': ['B04', 'B07', 'B08'],
            'C': ['C02', 'C06', 'C08'],
            'D': ['D01', 'D03', 'D05', 'D07']
        }
        
        self.mock_data['shelves'] = shelves
        self.mock_data['empty_shelves'] = empty_shelves
    
    def connect(self) -> bool:
        """데이터베이스 연결"""
        # MySQL이 설치되어 있지 않은 경우
        if not MYSQL_AVAILABLE:
            logger.warning("MySQL 라이브러리가 설치되어 있지 않습니다.")
            self.connected = False
            return False
            
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            
            if self.connection.is_connected():
                logger.info(f"MySQL 데이터베이스 '{self.database}'에 연결되었습니다.")
                self.connected = True
                return True
            else:
                logger.error("MySQL 데이터베이스 연결 실패")
                self.connected = False
                return False
                
        except Exception as e:
            logger.error(f"데이터베이스 연결 오류: {str(e)}")
            self.connection = None
            self.connected = False
            return False
    
    def ensure_connection(self) -> bool:
        """연결 확인 및 필요 시 재연결"""
        if not MYSQL_AVAILABLE:
            return False
            
        if not self.connection or not hasattr(self.connection, 'is_connected') or not self.connection.is_connected():
            return self.connect()
        return True
    
    def execute_query(self, query: str, params: Tuple = None) -> Optional[List[Tuple]]:
        """SELECT 쿼리 실행"""
        if not self.ensure_connection():
            logger.warning("DB 연결 없음 - 쿼리 실행 불가")
            return None
            
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"쿼리 실행 실패: {str(e)}")
            logger.error(f"쿼리: {query}, 파라미터: {params}")
            return None
    
    def execute_update(self, query: str, params: Tuple = None) -> bool:
        """INSERT/UPDATE/DELETE 쿼리 실행"""
        if not self.ensure_connection():
            logger.warning("DB 연결 없음 - 업데이트 실행 불가")
            return False
            
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows > 0
        except Exception as e:
            logger.error(f"업데이트 실행 실패: {str(e)}")
            logger.error(f"쿼리: {query}, 파라미터: {params}")
            return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """데이터베이스 연결 상태 반환"""
        status = {
            "connected": self.connected,
            "host": self.host,
            "database": self.database,
            "user": self.user
        }
        
        if self.connected and self.connection:
            try:
                cursor = self.connection.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                cursor.close()
                status["version"] = version[0] if version else "Unknown"
            except:
                status["version"] = "Error"
        
        return status
    
    # 가상 데이터 관련 메서드
    def get_empty_shelves(self, warehouse: str) -> List[str]:
        """지정된 창고의 빈 선반 목록 조회"""
        if not self.connected:
            # 가상 데이터 반환
            return self.mock_data['empty_shelves'].get(warehouse, [])
            
        query = """
            SELECT slot_id FROM warehouse_slot 
            WHERE warehouse_id = %s AND (status IS NULL OR status = 0)
            ORDER BY slot_id ASC
        """
        
        result = self.execute_query(query, (warehouse,))
        if result is None or len(result) == 0:
            # 쿼리 실패 또는 결과 없음 - 가상 데이터 반환
            return self.mock_data['empty_shelves'].get(warehouse, [])
        
        return [row[0] for row in result]

# 싱글톤 인스턴스
db_manager = DBManager()