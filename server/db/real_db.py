import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager

# config.py에서 설정 가져오기 시도
try:
    from config import CONFIG
    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    import os
    CONFIG = {
        "DB_HOST": os.getenv("DB_HOST", "localhost"),
        "DB_PORT": int(os.getenv("DB_PORT", "3306")),
        "DB_USER": os.getenv("DB_USER", "root"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", "0000"),
        "DB_NAME": os.getenv("DB_NAME", "rail_db")
    }

class RealDB:
    """MySQL 데이터베이스 연결 및 쿼리 클래스
    
    실제 MySQL 데이터베이스와의 연결을 관리하고 쿼리를 실행하는 클래스입니다.
    DBHelper 클래스와 동일한 인터페이스를 제공합니다.
    """
    
    _instance = None
    
    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(RealDB, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """데이터베이스 연결 설정을 초기화합니다."""
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.logger = logging.getLogger(__name__)
        self.connection_params = {
            "host": CONFIG["DB_HOST"],
            "port": CONFIG["DB_PORT"],
            "user": CONFIG["DB_USER"],
            "password": CONFIG["DB_PASSWORD"],
            "db": CONFIG["DB_NAME"],
            "charset": "utf8mb4",
            "cursorclass": DictCursor
        }
        
        # 기본 연결 상태
        self.connected = False
        self.connection = None
        
        # 연결 시도
        try:
            with self.get_connection() as conn:
                self.connected = True
                self.logger.info(f"데이터베이스 '{CONFIG['DB_NAME']}'에 연결되었습니다.")
        except Exception as e:
            self.logger.error(f"데이터베이스 연결 실패: {str(e)}")
            self.connected = False
            
        self._initialized = True
        
    @contextmanager
    def get_connection(self):
        """데이터베이스 연결을 생성하고 관리하는 컨텍스트 매니저
        
        Yields:
            pymysql.Connection: 데이터베이스 연결 객체
        """
        connection = None
        try:
            connection = pymysql.connect(**self.connection_params)
            yield connection
        except pymysql.Error as e:
            self.logger.error(f"데이터베이스 연결 오류: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()
                
    @contextmanager
    def get_cursor(self, connection):
        """데이터베이스 커서를 생성하고 관리하는 컨텍스트 매니저
        
        Args:
            connection (pymysql.Connection): 데이터베이스 연결 객체
            
        Yields:
            pymysql.cursors.DictCursor: 데이터베이스 커서 객체
        """
        cursor = None
        try:
            cursor = connection.cursor()
            yield cursor
        finally:
            if cursor:
                cursor.close()
                
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """SELECT 쿼리를 실행하고 결과를 반환합니다.
        
        Args:
            query (str): SQL 쿼리문
            params (tuple, optional): 쿼리 파라미터
            
        Returns:
            List[Dict]: 쿼리 결과 목록
        """
        with self.get_connection() as conn:
            with self.get_cursor(conn) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
                
    def execute_update(self, query: str, params: tuple = None) -> int:
        """INSERT/UPDATE/DELETE 쿼리를 실행하고 영향받은 행 수를 반환합니다.
        
        Args:
            query (str): SQL 쿼리문
            params (tuple, optional): 쿼리 파라미터
            
        Returns:
            int: 영향받은 행 수
        """
        with self.get_connection() as conn:
            with self.get_cursor(conn) as cursor:
                affected_rows = cursor.execute(query, params)
                conn.commit()
                return affected_rows
                
    # ===== 재고 관련 메서드 =====
    def get_inventory(self, warehouse_id: Optional[str] = None) -> List[Dict]:
        """재고 목록을 조회합니다.
        
        Args:
            warehouse_id (Optional[str]): 창고 ID
            
        Returns:
            List[Dict]: 재고 목록
        """
        query = """
            SELECT * FROM inventory
            WHERE 1=1
        """
        params = []
        
        if warehouse_id:
            query += " AND warehouse_id = %s"
            params.append(warehouse_id)
            
        return self.execute_query(query, tuple(params))
        
    def add_inventory_item(self, item: Dict) -> bool:
        """새로운 재고 물품을 추가합니다.
        
        Args:
            item (Dict): 물품 정보
            
        Returns:
            bool: 추가 성공 여부
        """
        query = """
            INSERT INTO inventory (
                item_id, barcode, name, warehouse_id,
                shelf_id, expiry_date, status, entry_date
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        params = (
            item["item_id"], item["barcode"], item["name"],
            item["warehouse_id"], item["shelf_id"], item["expiry_date"],
            item["status"], datetime.now().isoformat()
        )
        
        try:
            self.execute_update(query, params)
            return True
        except Exception as e:
            self.logger.error(f"재고 추가 실패: {str(e)}")
            return False
            
    # ===== 환경 데이터 관련 메서드 =====
    def get_environment(self, warehouse_id: Optional[str] = None) -> Dict:
        """환경 데이터를 조회합니다.
        
        Args:
            warehouse_id (Optional[str]): 창고 ID
            
        Returns:
            Dict: 환경 데이터
        """
        query = """
            SELECT * FROM environment
            WHERE timestamp = (
                SELECT MAX(timestamp)
                FROM environment
                WHERE warehouse_id = %s
            )
        """
        
        if warehouse_id:
            result = self.execute_query(query, (warehouse_id,))
            return result[0] if result else None
        else:
            data = {}
            for wh in ["A", "B", "C", "D"]:
                result = self.execute_query(query, (wh,))
                if result:
                    data[wh] = result[0]
            return data
            
    def update_environment(self, warehouse_id: str, data: Dict) -> bool:
        """환경 데이터를 업데이트합니다.
        
        Args:
            warehouse_id (str): 창고 ID
            data (Dict): 환경 데이터
            
        Returns:
            bool: 업데이트 성공 여부
        """
        query = """
            INSERT INTO environment (
                warehouse_id, temperature, humidity,
                status, timestamp
            ) VALUES (
                %s, %s, %s, %s, %s
            )
        """
        params = (
            warehouse_id, data["temperature"], data["humidity"],
            data["status"], datetime.now().isoformat()
        )
        
        try:
            self.execute_update(query, params)
            return True
        except Exception as e:
            self.logger.error(f"환경 데이터 업데이트 실패: {str(e)}")
            return False
            
    # ===== 출입 기록 관련 메서드 =====
    def get_access_logs(self, date: Optional[str] = None) -> List[Dict]:
        """출입 기록을 조회합니다.
        
        Args:
            date (Optional[str]): 조회 날짜
            
        Returns:
            List[Dict]: 출입 기록 목록
        """
        query = """
            SELECT al.*, e.name, e.department
            FROM access_logs al
            JOIN employees e ON al.employee_id = e.id
            WHERE 1=1
        """
        params = []
        
        if date:
            query += " AND DATE(timestamp) = %s"
            params.append(date)
            
        query += " ORDER BY timestamp DESC"
        
        return self.execute_query(query, tuple(params))
        
    def add_access_log(self, employee_id: str, status: str) -> bool:
        """새로운 출입 기록을 추가합니다.
        
        Args:
            employee_id (str): 직원 ID
            status (str): 출입 상태 (entry/exit)
            
        Returns:
            bool: 추가 성공 여부
        """
        query = """
            INSERT INTO access_logs (
                employee_id, status, timestamp
            ) VALUES (
                %s, %s, %s
            )
        """
        params = (employee_id, status, datetime.now().isoformat())
        
        try:
            self.execute_update(query, params)
            return True
        except Exception as e:
            self.logger.error(f"출입 기록 추가 실패: {str(e)}")
            return False
            
    # ===== 오류 로그 관련 메서드 =====
    def log_error(self, error_code: str, description: str) -> None:
        """오류 로그를 기록합니다.
        
        Args:
            error_code (str): 오류 코드
            description (str): 오류 설명
        """
        query = """
            INSERT INTO error_logs (
                error_code, description, timestamp
            ) VALUES (
                %s, %s, %s
            )
        """
        params = (error_code, description, datetime.now().isoformat())
        
        try:
            self.execute_update(query, params)
        except Exception as e:
            self.logger.error(f"오류 로그 기록 실패: {str(e)}")

    # ==== DBManager와 호환되는 메서드 추가 ====
    def get_connection_status(self) -> Dict[str, Any]:
        """데이터베이스 연결 상태 반환"""
        status = {
            "connected": self.connected,
            "host": CONFIG["DB_HOST"],
            "database": CONFIG["DB_NAME"],
            "user": CONFIG["DB_USER"]
        }
        
        if self.connected:
            try:
                with self.get_connection() as conn:
                    with self.get_cursor(conn) as cursor:
                        cursor.execute("SELECT VERSION()")
                        version = cursor.fetchone()
                        status["version"] = version["VERSION()"] if version else "Unknown"
            except Exception as e:
                self.logger.error(f"버전 조회 실패: {str(e)}")
                status["version"] = "Error"
        
        return status 