# db/db_connection.py
import logging
import os
import sys
from typing import Optional, Dict, List, Any, Tuple

# MySQL 라이브러리 임포트
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    logging.warning("MySQL 라이브러리를 가져올 수 없습니다. 'pip install mysql-connector-python' 명령어로 설치하세요.")
    MYSQL_AVAILABLE = False

# 상위 디렉토리를 import path에 추가 (config.py 접근용)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger(__name__)

class DBConnection:
    """데이터베이스 연결 관리 클래스"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(DBConnection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """초기화 (싱글톤이므로 한 번만 실행)"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 설정 직접 사용
        self.host = DB_HOST
        self.port = DB_PORT
        self.user = DB_USER
        self.password = DB_PASSWORD
        self.database = DB_NAME
        
        logger.info(f"데이터베이스 설정 로드: {self.host}:{self.port}/{self.database}")
        
        # DB 연결 초기화
        self.connection = None
        self.connected = False
        
        # MySQL 라이브러리 확인 및 연결
        if MYSQL_AVAILABLE:
            self.connect()
        else:
            logger.warning("MySQL 라이브러리가 설치되어 있지 않습니다.")
        
        self._initialized = True
        
    def connect(self) -> bool:
        """데이터베이스 연결"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.connected = True
            logger.info(f"데이터베이스 '{self.database}'에 연결됨")
            return True
        except Exception as e:
            self._handle_connection_error(e)
            self.connected = False
            return False

    def _handle_connection_error(self, error):
        """연결 오류 처리 및 상세 로깅"""
        error_str = str(error)
        if "Access denied" in error_str:
            logger.error("사용자 이름 또는 비밀번호가 잘못되었습니다.")
        elif "Unknown database" in error_str:
            logger.error(f"데이터베이스 '{self.database}'가 존재하지 않습니다.")
        elif "Can't connect to MySQL server" in error_str:
            logger.error(f"MySQL 서버({self.host}:{self.port})에 연결할 수 없습니다.")
        else:
            logger.error(f"데이터베이스 연결 오류: {error_str}")
        
    def ensure_connection(self) -> bool:
        """연결 확인 및 필요시 재연결"""
        if not MYSQL_AVAILABLE:
            return False
        
        try:
            # 연결 객체 없음
            if not self.connection:
                logger.debug("DB 연결 객체가 없음. 새로 연결합니다.")
                return self.connect()
            
            # 연결 끊김
            if not self.connection.is_connected():
                logger.debug("DB 연결이 끊어짐. 재연결합니다.")
                try:
                    self.connection.close()
                except:
                    pass
                return self.connect()
            
            return True
            
        except Exception as e:
            logger.error(f"DB 연결 확인 오류: {str(e)}")
            return self.connect()  # 오류 발생 시 재연결
    
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
            error_msg = f"쿼리 실행 실패: {str(e)}"
            logger.error(error_msg)
            logger.error(f"쿼리: {query}, 파라미터: {params}")
            # 원본 예외를 포함하여 새 예외 발생
            raise RuntimeError(error_msg) from e
    
    def execute_dict_query(self, query: str, params: Tuple = None) -> Optional[List[Dict]]:
        """SELECT 쿼리 실행 후 딕셔너리 리스트로 결과 반환"""
        if not self.ensure_connection():
            logger.warning("DB 연결 없음 - 쿼리 실행 불가")
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            error_msg = f"쿼리 실행 실패: {str(e)}"
            logger.error(error_msg)
            logger.error(f"쿼리: {query}, 파라미터: {params}")
            # 원본 예외를 포함하여 새 예외 발생
            raise RuntimeError(error_msg) from e
    
    def execute_update(self, query: str, params: Tuple = None) -> int:
        """INSERT/UPDATE/DELETE 쿼리 실행"""
        if not self.ensure_connection():
            logger.warning("DB 연결 없음 - 업데이트 실행 불가")
            return 0
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
        except Exception as e:
            error_msg = f"업데이트 실행 실패: {str(e)}"
            logger.error(error_msg)
            logger.error(f"쿼리: {query}, 파라미터: {params}")
            self.connection.rollback()
            # 원본 예외를 포함하여 새 예외 발생
            raise RuntimeError(error_msg) from e
    
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
    
    def close(self):
        """연결 종료"""
        if self.connection and self.connected:
            try:
                self.connection.close()
                logger.info("데이터베이스 연결 종료")
            except Exception as e:
                logger.error(f"데이터베이스 연결 종료 오류: {str(e)}")
        
        self.connected = False
        self.connection = None