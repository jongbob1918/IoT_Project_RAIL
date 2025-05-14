# server/db/db_manager.py
import os
import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta

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
    
    이 클래스는 데이터베이스 연결을 관리하고 쿼리를 실행하는 역할을 합니다.
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
            self.password = os.getenv("DB_PASSWORD", " ")
            self.database = os.getenv("DB_NAME", "rail_db")
            logger.info("환경 변수에서 데이터베이스 설정을 로드했습니다.")
        
        # 데이터베이스 연결 객체
        self.connection = None
        self.connected = False
        
        # 데이터베이스 연결 시도
        if MYSQL_AVAILABLE:
            self.connect()
        else:
            logger.warning("MySQL 라이브러리가 설치되어 있지 않습니다.")
        
        self._initialized = True
    
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
    
    def get_access_logs(self, limit=20, offset=0, start_date=None, end_date=None) -> List[Dict]:
        """출입 로그 목록을 조회합니다."""
        if self.connected:
            try:
                query = """
                    SELECT 
                        id, card_id, employee_name, access_type, 
                        timestamp, created_at 
                    FROM access_logs 
                    WHERE 1=1
                """
                
                params = []
                
                # 날짜 필터링 조건 추가
                if start_date:
                    query += " AND DATE(timestamp) >= %s"
                    params.append(start_date)
                
                if end_date:
                    query += " AND DATE(timestamp) <= %s"
                    params.append(end_date)
                
                # 정렬 및 페이징
                query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                result = self.execute_query(query, tuple(params))
                
                if result:
                    logs = []
                    for row in result:
                        logs.append({
                            "id": row[0],
                            "card_id": row[1],
                            "name": row[2],
                            "access_type": row[3],
                            "timestamp": row[4].isoformat() if hasattr(row[4], 'isoformat') else str(row[4]),
                            "created_at": row[5].isoformat() if hasattr(row[5], 'isoformat') else str(row[5])
                        })
                    return logs
                return []
            except Exception as e:
                logger.error(f"출입 로그 조회 오류: {str(e)}")
                return []
        
        # DB 연결이 없는 경우 빈 리스트 반환
        return []
    
    def get_warehouse_status(self, warehouse_id: str = None) -> Dict[str, Any]:
        """창고 상태 정보 조회"""
        if self.connected:
            try:
                query = """
                    SELECT 
                        w.id, 
                        w.warehouse_type,
                        w.capacity,
                        w.used_capacity,
                        COUNT(p.id) as item_count
                    FROM warehouse w
                    LEFT JOIN product_item p ON w.id = p.warehouse_id
                """
                
                if warehouse_id:
                    query += " WHERE w.id = %s"
                    query += " GROUP BY w.id"
                    result = self.execute_query(query, (warehouse_id,))
                else:
                    query += " GROUP BY w.id"
                    result = self.execute_query(query)
                
                if result:
                    if warehouse_id:
                        row = result[0]
                        return {
                            'warehouse_id': row[0],
                            'type': row[1],
                            'total_capacity': row[2],
                            'used_capacity': row[3],
                            'item_count': row[4]
                        }
                    else:
                        warehouses = {}
                        for row in result:
                            wh_id = row[0]
                            warehouses[wh_id] = {
                                'type': row[1],
                                'total_capacity': row[2],
                                'used_capacity': row[3],
                                'item_count': row[4]
                            }
                        return warehouses
            except Exception as e:
                logger.error(f"창고 상태 쿼리 오류: {str(e)}")
        
        # DB 연결이 없는 경우 빈 사전 반환
        return {}

    # 온도 로그 저장 메서드 추가
    def insert_temperature_log(self, warehouse_id: str, temperature: float) -> bool:
        """온도 로그를 데이터베이스에 저장합니다."""
        # 유효한 창고 ID 확인 (A, B, C만 허용)
        if warehouse_id not in ['A', 'B', 'C']:
            logger.warning(f"유효하지 않은 창고 ID: {warehouse_id}")
            return False
            
        if not self.ensure_connection():
            logger.warning(f"DB 연결 없음 - 온도 로그 저장 불가 (창고: {warehouse_id}, 온도: {temperature}°C)")
            return False
            
        try:
            # 해당 창고의 온도 범위 확인
            query = "SELECT min_temp, max_temp FROM warehouse WHERE id = %s"
            result = self.execute_query(query, (warehouse_id,))
            
            if result and len(result) > 0:
                min_temp, max_temp = result[0]
                
                # 온도가 범위를 벗어난 경우에만 temp_warning_logs에 저장
                if temperature < min_temp or temperature > max_temp:
                    status = "high" if temperature > max_temp else "low"
                    query = """
                        INSERT INTO temp_warning_logs 
                        (warehouse_id, temperature, status, dttm) 
                        VALUES (%s, %s, %s, NOW())
                    """
                    self.execute_update(query, (warehouse_id, temperature, status))
                    logger.warning(f"비정상 온도 감지: 창고 {warehouse_id}, 온도 {temperature}°C ({status})")
                    
                    # 경고 상태일 때만 로그에 기록
                    logger.debug(f"온도 로그 저장: 창고 {warehouse_id}, 온도 {temperature}°C")
                else:
                    # 정상 범위 온도는 로그에 기록하지 않고 디버그 메시지만 출력
                    logger.debug(f"정상 온도 감지: 창고 {warehouse_id}, 온도 {temperature}°C (로그 저장 안함)")
            else:
                # 데이터베이스에서 온도 범위를 가져올 수 없는 경우
                logger.debug(f"온도 범위 정보 없음: 창고 {warehouse_id}, 온도 {temperature}°C")
            
            return True
            
        except Exception as e:
            logger.error(f"온도 로그 저장 오류: {str(e)}")
            return False

    # 일일 출입 통계 조회 메서드 추가
    def get_daily_access_stats(self, date: str) -> Dict[str, Any]:
        """특정 날짜의 출입 통계를 조회합니다."""
        if not self.ensure_connection():
            logger.warning(f"DB 연결 없음 - 일일 출입 통계 조회 불가")
            return None
            
        try:
            query = """
                SELECT entries, exits, current_count 
                FROM daily_access_stats 
                WHERE date = %s
            """
            result = self.execute_query(query, (date,))
            
            if result and len(result) > 0:
                row = result[0]
                return {
                    "date": date,
                    "entries": row[0],
                    "exits": row[1],
                    "current_count": row[2]
                }
            else:
                # 데이터가 없으면 None 반환
                return None
                
        except Exception as e:
            logger.error(f"일일 출입 통계 조회 오류: {str(e)}")
            return None
    
    # 일일 출입 통계 업데이트 메서드 추가
    def update_daily_access_stats(self, stats: Dict[str, Any]) -> bool:
        """일일 출입 통계를 업데이트합니다."""
        if not self.ensure_connection():
            logger.warning(f"DB 연결 없음 - 일일 출입 통계 업데이트 불가")
            return False
            
        try:
            date = stats.get("date")
            entries = stats.get("entries", 0)
            exits = stats.get("exits", 0)
            current_count = stats.get("current_count", 0)
            
            # 기존 데이터가 있는지 확인
            check_query = "SELECT id FROM daily_access_stats WHERE date = %s"
            result = self.execute_query(check_query, (date,))
            
            if result and len(result) > 0:
                # 업데이트
                query = """
                    UPDATE daily_access_stats 
                    SET entries = %s, exits = %s, current_count = %s 
                    WHERE date = %s
                """
                self.execute_update(query, (entries, exits, current_count, date))
            else:
                # 새로 삽입
                query = """
                    INSERT INTO daily_access_stats 
                    (date, entries, exits, current_count) 
                    VALUES (%s, %s, %s, %s)
                """
                self.execute_update(query, (date, entries, exits, current_count))
            
            logger.debug(f"일일 출입 통계 업데이트: {date}, 입장 {entries}명, 퇴장 {exits}명, 현재 {current_count}명")
            return True
            
        except Exception as e:
            logger.error(f"일일 출입 통계 업데이트 오류: {str(e)}")
            return False
    
    # 출입 로그 저장 메서드 추가
    def save_access_log(self, card_id: str, name: str, entry_type: str, timestamp: datetime) -> bool:
        """출입 로그를 저장합니다."""
        if not self.ensure_connection():
            logger.warning(f"DB 연결 없음 - 출입 로그 저장 불가")
            return False
            
        try:
            query = """
                INSERT INTO access_logs 
                (card_id, employee_name, access_type, timestamp) 
                VALUES (%s, %s, %s, %s)
            """
            self.execute_update(query, (card_id, name, entry_type, timestamp))
            
            logger.debug(f"출입 로그 저장: {card_id} ({name}) - {entry_type}")
            return True
            
        except Exception as e:
            logger.error(f"출입 로그 저장 오류: {str(e)}")
            return False

    # 유통기한 만료 물품 처리 로그 저장
    def save_expiry_process_log(self, log_entry: Dict[str, Any]) -> bool:
        """유통기한 만료 물품 처리 로그를 저장합니다."""
        if not self.ensure_connection():
            logger.warning(f"DB 연결 없음 - 유통기한 처리 로그 저장 불가")
            return False
            
        try:
            item_id = log_entry.get("item_id")
            action = log_entry.get("action")
            description = log_entry.get("description")
            timestamp = log_entry.get("timestamp")
            
            query = """
                INSERT INTO expiry_process_logs 
                (item_id, action, description, processed_at) 
                VALUES (%s, %s, %s, %s)
            """
            self.execute_update(query, (item_id, action, description, timestamp))
            
            logger.debug(f"유통기한 처리 로그 저장: {item_id} ({action})")
            return True
            
        except Exception as e:
            logger.error(f"유통기한 처리 로그 저장 오류: {str(e)}")
            return False
            
    # 유통기한 만료 물품 조회
    def get_expired_items(self) -> List[Dict]:
        """
        유통기한이 만료된 물품 목록을 조회합니다.
        
        Returns:
            List[Dict]: 유통기한 만료 물품 목록
        """
        if not self.ensure_connection():
            logger.warning("DB 연결 없음 - 유통기한 만료 물품 조회 불가")
            return []
            
        try:
            # 오늘 날짜 기준으로 유통기한이 지난 물품 조회
            today = datetime.now().date().isoformat()
            
            query = """
                SELECT i.id, i.barcode, i.product_name, i.exp, i.quantity, i.entry_date, 
                       w.id as warehouse_id, i.shelf_id
                FROM inventory i
                JOIN warehouse w ON i.warehouse_id = w.id
                WHERE i.exp < %s
                ORDER BY i.exp ASC
            """
            result = self.execute_query(query, (today,))
            
            items = []
            if result:
                for row in result:
                    # 유통기한과 오늘 날짜의 차이 계산
                    exp_date = datetime.strptime(row[3], "%Y-%m-%d").date()
                    today_date = datetime.now().date()
                    days_remaining = (exp_date - today_date).days
                    
                    item = {
                        "id": row[0],
                        "barcode": row[1],
                        "product_name": row[2],
                        "exp": row[3],
                        "quantity": row[4],
                        "entry_date": row[5],
                        "warehouse_id": row[6],
                        "shelf_id": row[7],
                        "days_remaining": days_remaining,
                        "status": "expired"
                    }
                    items.append(item)
                    
            logger.info(f"유통기한 만료 물품 {len(items)}건 조회 완료")
            return items
            
        except Exception as e:
            logger.error(f"유통기한 만료 물품 조회 오류: {str(e)}")
            return []
            
    # 유통기한 경고 물품 조회
    def get_expiry_alerts(self, days_threshold: int = 7) -> List[Dict]:
        """
        유통기한 경고 목록을 조회합니다.
        
        Args:
            days_threshold (int): 경고 기준 일수 (기본값: 7일)
            
        Returns:
            List[Dict]: 유통기한 경고 목록
        """
        if not self.ensure_connection():
            logger.warning("DB 연결 없음 - 유통기한 경고 물품 조회 불가")
            return []
            
        try:
            # 오늘 날짜 기준으로 지정된 일수 내에 유통기한이 만료되는 물품 조회
            today = datetime.now().date()
            future_date = (today + timedelta(days=days_threshold)).isoformat()
            
            query = """
                SELECT i.id, i.barcode, i.product_name, i.exp, i.quantity, i.entry_date, 
                       w.id as warehouse_id, i.shelf_id
                FROM inventory i
                JOIN warehouse w ON i.warehouse_id = w.id
                WHERE i.exp >= %s AND i.exp <= %s
                ORDER BY i.exp ASC
            """
            result = self.execute_query(query, (today.isoformat(), future_date))
            
            items = []
            if result:
                for row in result:
                    # 유통기한과 오늘 날짜의 차이 계산
                    exp_date = datetime.strptime(row[3], "%Y-%m-%d").date()
                    days_remaining = (exp_date - today).days
                    
                    # 상태 결정
                    status = "warning"
                    if days_remaining <= 3:
                        status = "danger"
                    elif days_remaining == 0:
                        status = "today"
                    
                    item = {
                        "id": row[0],
                        "barcode": row[1],
                        "product_name": row[2],
                        "exp": row[3],
                        "quantity": row[4],
                        "entry_date": row[5],
                        "warehouse_id": row[6],
                        "shelf_id": row[7],
                        "days_remaining": days_remaining,
                        "status": status
                    }
                    items.append(item)
                    
            logger.info(f"유통기한 경고 물품 {len(items)}건 조회 완료 (기준일: {days_threshold}일)")
            return items
            
        except Exception as e:
            logger.error(f"유통기한 경고 물품 조회 오류: {str(e)}")
            return []
            
    # 특정 아이템 조회
    def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        """
        특정 ID의 물품 정보를 조회합니다.
        
        Args:
            item_id (str): 물품 ID
            
        Returns:
            Optional[Dict]: 물품 정보 또는 None
        """
        if not self.ensure_connection():
            logger.warning(f"DB 연결 없음 - 물품 조회 불가 (ID: {item_id})")
            return None
            
        try:
            query = """
                SELECT i.id, i.barcode, i.product_name, i.exp, i.quantity, i.entry_date, 
                       w.id as warehouse_id, i.shelf_id
                FROM inventory i
                JOIN warehouse w ON i.warehouse_id = w.id
                WHERE i.id = %s
            """
            result = self.execute_query(query, (item_id,))
            
            if result and len(result) > 0:
                row = result[0]
                
                # 유통기한과 오늘 날짜의 차이 계산
                exp_date = datetime.strptime(row[3], "%Y-%m-%d").date()
                today_date = datetime.now().date()
                days_remaining = (exp_date - today_date).days
                
                # 상태 결정
                status = "normal"
                if days_remaining < 0:
                    status = "expired"
                elif days_remaining <= 3:
                    status = "danger"
                elif days_remaining <= 7:
                    status = "warning"
                
                return {
                    "id": row[0],
                    "barcode": row[1],
                    "product_name": row[2],
                    "exp": row[3],
                    "quantity": row[4],
                    "entry_date": row[5],
                    "warehouse_id": row[6],
                    "shelf_id": row[7],
                    "days_remaining": days_remaining,
                    "status": status
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"물품 조회 오류: {str(e)}")
            return None

# 싱글톤 인스턴스
db_manager = DBManager()