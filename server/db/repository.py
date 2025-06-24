# db/repository.py
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta

from .db_connection import DBConnection

logger = logging.getLogger(__name__)

class BaseRepository:
    """기본 리포지토리 클래스"""
    
    def __init__(self, db_connection: Optional[DBConnection] = None):
        """초기화
        
        Args:
            db_connection: 데이터베이스 연결 객체. None인 경우 기본값 사용
        """
        self.db = db_connection or DBConnection()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def _log_error(self, message: str, error: Exception):
        """오류 로깅 헬퍼 메서드"""
        self.logger.error(f"{message}: {str(error)}")



class WarehouseRepository(BaseRepository):
    """창고 데이터 관리 리포지토리"""
    
    def get_all(self) -> List[Dict]:
        """모든 창고 정보 조회"""
        try:
            query = """
                SELECT id, warehouse_type, min_temp, max_temp, target_temp, 
                    capacity
                FROM warehouse
            """
            result = self.db.execute_dict_query(query)
            
            if not result:
                return []
                
            return result
        except Exception as e:
            self._log_error("창고 정보 조회 오류", e)
            return []
    def get_by_id(self, warehouse_id: str) -> Optional[Dict]:
        """ID로 창고 정보 조회"""
        try:
            query = """
                SELECT id, warehouse_type, min_temp, max_temp, target_temp,
                       capacity, used_capacity 
                FROM warehouse 
                WHERE id = %s
            """
            result = self.db.execute_dict_query(query, (warehouse_id,))
            
            if not result:
                return None
                
            return result[0]
        except Exception as e:
            self._log_error(f"창고 정보 조회 오류 (ID: {warehouse_id})", e)
            return None
    
    def get_temperature_ranges(self) -> Dict[str, Dict[str, float]]:
        """창고별 온도 범위 조회"""
        try:
            query = """
                SELECT id, min_temp, max_temp, target_temp 
                FROM warehouse
            """
            result = self.db.execute_query(query)
            
            if not result:
                return {}
                
            ranges = {}
            for row in result:
                warehouse_id, min_temp, max_temp, target_temp = row
                ranges[warehouse_id] = {
                    "min_temp": min_temp,
                    "max_temp": max_temp,
                    "target_temp": target_temp
                }
            return ranges
        except Exception as e:
            self._log_error("창고 온도 범위 조회 오류", e)
            return {}
    
    def update_capacity(self, warehouse_id: str, used_capacity: int) -> bool:
        """창고 사용 용량 업데이트"""
        try:
            query = "UPDATE warehouse SET used_capacity = %s WHERE id = %s"
            affected = self.db.execute_update(query, (used_capacity, warehouse_id))
            return affected > 0
        except Exception as e:
            self._log_error(f"창고 용량 업데이트 오류 (ID: {warehouse_id})", e)
            return False
    
    def log_temperature_warning(self, warehouse_id: str, temperature: float, status: str) -> bool:
        """온도 경고 로그 저장"""
        try:
            query = """
                INSERT INTO temp_warning_logs 
                (warehouse_id, temperature, status, dttm) 
                VALUES (%s, %s, %s, NOW())
            """
            affected = self.db.execute_update(query, (warehouse_id, temperature, status))
            return affected > 0
        except Exception as e:
            self._log_error(f"온도 경고 로그 저장 오류 (ID: {warehouse_id})", e)
            return False
    
    def get_target_temperature(self, warehouse_id: str) -> Optional[float]:
        """창고별 목표 온도 설정값 조회"""
        try:
            query = """
                SELECT target_temp
                FROM warehouse
                WHERE id = %s
            """
            result = self.db.execute_query(query, (warehouse_id,))
            
            if result and result[0] and result[0][0] is not None:
                return float(result[0][0])
                
            return None
        except Exception as e:
            self._log_error(f"목표 온도 조회 오류 (창고: {warehouse_id})", e)
            return None
    
    def save_target_temperature(self, warehouse_id: str, target_temp: float) -> bool:
        """창고별 목표 온도 설정값 저장"""
        try:
            query = """
                UPDATE warehouse
                SET target_temp = %s
                WHERE id = %s
            """
            affected = self.db.execute_update(query, (target_temp, warehouse_id))
            
            if affected > 0:
                self.logger.info(f"창고 '{warehouse_id}' 목표 온도가 {target_temp}°C로 업데이트 됨")
                return True
            else:
                self.logger.warning(f"창고 '{warehouse_id}' 목표 온도 업데이트 실패")
                return False
        except Exception as e:
            self._log_error(f"목표 온도 저장 오류 (창고: {warehouse_id})", e)
            return False
    
    def get_warehouse_temp_settings(self) -> Dict[str, Dict[str, Any]]:
        """창고별 온도 설정 조회 (범위 및 목표 온도)"""
        try:
            query = """
                SELECT id, warehouse_type, min_temp, max_temp, target_temp
                FROM warehouse
            """
            result = self.db.execute_dict_query(query)
            
            if not result:
                return {}
                
            settings = {}
            for row in result:
                warehouse_id = row['id']
                warehouse_type = row['warehouse_type']
                min_temp = row['min_temp']
                max_temp = row['max_temp']
                target_temp = row['target_temp']
                
                # 목표 온도가 None이면 범위의 중간값 사용
                if target_temp is None:
                    target_temp = (min_temp + max_temp) / 2
                    
                # 창고 유형이 없으면 ID로 추측
                if not warehouse_type:
                    if warehouse_id == 'A':
                        warehouse_type = 'freezer'
                    elif warehouse_id == 'B':
                        warehouse_type = 'refrigerator'
                    else:
                        warehouse_type = 'room_temp'
                
                settings[warehouse_id] = {
                    "type": warehouse_type,
                    "temp_min": min_temp,
                    "temp_max": max_temp,
                    "target_temp": target_temp
                }
            return settings
        except Exception as e:
            self._log_error("창고 온도 설정 조회 오류", e)
            return {}

class ProductRepository(BaseRepository):
    """제품 데이터 관리 리포지토리"""
    
    def get_all(self) -> List[Dict]:
        """모든 제품 정보 조회"""
        try:
            query = """
                SELECT id, name, category, price, warehouse_id
                FROM product
            """
            result = self.db.execute_dict_query(query)
            
            if not result:
                return []
                
            return result
        except Exception as e:
            self._log_error("제품 정보 조회 오류", e)
            return []
    
    def get_by_id(self, product_id: str) -> Optional[Dict]:
        """ID로 제품 정보 조회"""
        try:
            query = """
                SELECT id, name, category, price, warehouse_id
                FROM product
                WHERE id = %s
            """
            result = self.db.execute_dict_query(query, (product_id,))
            
            if not result:
                return None
                
            return result[0]
        except Exception as e:
            self._log_error(f"제품 정보 조회 오류 (ID: {product_id})", e)
            return None
    
    def get_by_category(self, category: str) -> List[Dict]:
        """카테고리로 제품 정보 조회"""
        try:
            query = """
                SELECT id, name, category, price, warehouse_id
                FROM product
                WHERE category = %s
            """
            result = self.db.execute_dict_query(query, (category,))
            
            if not result:
                return []
                
            return result
        except Exception as e:
            self._log_error(f"제품 정보 조회 오류 (카테고리: {category})", e)
            return []


class ProductItemRepository(BaseRepository):
    """제품 아이템 (개별 재고) 데이터 관리 리포지토리"""
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """모든 제품 아이템 정보 조회"""
        try:
            query = """
                SELECT pi.id, pi.warehouse_id, pi.product_id, pi.exp, pi.entry_time,
                       p.name, p.category
                FROM product_item pi
                JOIN product p ON pi.product_id = p.id
                ORDER BY pi.entry_time DESC
                LIMIT %s OFFSET %s
            """
            result = self.db.execute_dict_query(query, (limit, offset))
            
            if not result:
                return []
                
            return result
        except Exception as e:
            self._log_error("제품 아이템 정보 조회 오류", e)
            return []
    
    def get_by_id(self, item_id: str) -> Optional[Dict]:
        """ID로 제품 아이템 정보 조회"""
        try:
            query = """
                SELECT pi.id, pi.warehouse_id, pi.product_id, pi.exp, pi.entry_time,
                       p.name, p.category
                FROM product_item pi
                JOIN product p ON pi.product_id = p.id
                WHERE pi.id = %s
            """
            result = self.db.execute_dict_query(query, (item_id,))
            
            if not result:
                return None
                
            return result[0]
        except Exception as e:
            self._log_error(f"제품 아이템 정보 조회 오류 (ID: {item_id})", e)
            return None
    
    def get_by_warehouse(self, warehouse_id: str) -> List[Dict]:
        """창고별 제품 아이템 정보 조회"""
        try:
            query = """
                SELECT pi.id, pi.warehouse_id, pi.product_id, pi.exp, pi.entry_time,
                       p.name, p.category
                FROM product_item pi
                JOIN product p ON pi.product_id = p.id
                WHERE pi.warehouse_id = %s
                ORDER BY pi.exp ASC
            """
            result = self.db.execute_dict_query(query, (warehouse_id,))
            
            if not result:
                return []
                
            return result
        except Exception as e:
            self._log_error(f"제품 아이템 정보 조회 오류 (창고: {warehouse_id})", e)
            return []
    
    def get_expiring_items(self, days: int = 7) -> List[Dict]:
        """유통기한 임박 아이템 조회"""
        try:
            today = datetime.now().date()
            target_date = today + timedelta(days=days)
            
            query = """
                SELECT pi.id, pi.warehouse_id, pi.product_id, pi.exp, pi.entry_time,
                       p.name, p.category
                FROM product_item pi
                JOIN product p ON pi.product_id = p.id
                WHERE pi.exp <= %s AND pi.exp >= %s
                ORDER BY pi.exp ASC
            """
            result = self.db.execute_dict_query(query, (target_date, today))
            
            if not result:
                return []
                
            # 남은 일수 계산 추가
            for item in result:
                exp_date = item['exp']
                item['days_remaining'] = (exp_date - today).days
                
                # 상태 정보 추가
                days_remaining = item['days_remaining']
                if days_remaining <= 1:
                    item['status'] = 'danger'
                elif days_remaining <= 3:
                    item['status'] = 'warning'
                else:
                    item['status'] = 'normal'
            
            return result
        except Exception as e:
            self._log_error(f"유통기한 임박 아이템 조회 오류", e)
            return []
    
    def get_expired_items(self) -> List[Dict]:
        """유통기한 만료 아이템 조회"""
        try:
            today = datetime.now().date()
            
            query = """
                SELECT pi.id, pi.warehouse_id, pi.product_id, pi.exp, pi.entry_time,
                       p.name, p.category
                FROM product_item pi
                JOIN product p ON pi.product_id = p.id
                WHERE pi.exp < %s
                ORDER BY pi.exp ASC
            """
            result = self.db.execute_dict_query(query, (today,))
            
            if not result:
                return []
                
            # 남은 일수 계산 추가
            for item in result:
                exp_date = item['exp']
                item['days_remaining'] = (exp_date - today).days
                item['status'] = 'expired'
            
            return result
        except Exception as e:
            self._log_error(f"유통기한 만료 아이템 조회 오류", e)
            return []
    
    def add_item(self, product_id: str, warehouse_id: str, exp_date: Union[datetime, str], entry_time: Optional[str] = None) -> Optional[str]:
        """제품 아이템 추가"""
        try:
            # 유효한 제품 ID 확인
            product_query = "SELECT id FROM product WHERE id = %s"
            product_result = self.db.execute_query(product_query, (product_id,))
            
            if not product_result:
                self.logger.warning(f"존재하지 않는 제품 ID: {product_id}")
                return None
            
            # 입고 시간이 없으면 현재 시간 사용
            if not entry_time:
                entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 새 아이템 ID 생성 (최대 ID + 1)
            id_query = "SELECT MAX(CAST(id AS UNSIGNED)) FROM product_item"
            id_result = self.db.execute_query(id_query)
            
            if id_result and id_result[0][0]:
                new_id = str(int(id_result[0][0]) + 1)
            else:
                new_id = "1"
            
            # 적절한 자릿수로 패딩
            new_id = new_id.zfill(2)
            
            # 아이템 추가
            query = """
                INSERT INTO product_item 
                (id, warehouse_id, product_id, exp, entry_time) 
                VALUES (%s, %s, %s, %s, %s)
            """
            
            affected = self.db.execute_update(query, (new_id, warehouse_id, product_id, exp_date, entry_time))
            
            if affected > 0:
                # 창고 용량 업데이트
                self._update_warehouse_capacity(warehouse_id)
                return new_id
            else:
                return None
                
        except Exception as e:
            self._log_error(f"제품 아이템 추가 오류 (제품: {product_id})", e)
            return None
    
    def remove_item(self, item_id: str) -> bool:
        """제품 아이템 제거"""
        try:
            # 아이템 정보 가져오기 (로깅 목적)
            item_query = "SELECT warehouse_id, product_id FROM product_item WHERE id = %s"
            item_result = self.db.execute_query(item_query, (item_id,))
            
            if not item_result:
                self.logger.warning(f"존재하지 않는 아이템 ID: {item_id}")
                return False
            
            warehouse_id = item_result[0][0]
            product_id = item_result[0][1]
            
            # 아이템 삭제
            query = "DELETE FROM product_item WHERE id = %s"
            affected = self.db.execute_update(query, (item_id,))
            
            if affected > 0:
                # 로그 기록: used_capacity를 업데이트할 필요 없음 (실시간 계산으로 변경)
                self.logger.info(f"제품 아이템 제거 성공: ID={item_id}, 창고={warehouse_id}, 제품={product_id}")
                return True
            else:
                return False
                
        except Exception as e:
            self._log_error(f"제품 아이템 제거 오류 (ID: {item_id})", e)
            return False
    
    def get_warehouse_usage(self, warehouse_id: str = None) -> Dict[str, int]:
        """창고별 사용량 계산 (DB에서 실시간 조회)"""
        try:
            query = """
                SELECT warehouse_id, COUNT(*) as count
                FROM product_item
            """
            params = []
            
            if warehouse_id:
                query += " WHERE warehouse_id = %s"
                params.append(warehouse_id)
                
            query += " GROUP BY warehouse_id"
            
            result = self.db.execute_dict_query(query, tuple(params) if params else None)
            
            usage = {}
            if result:
                for row in result:
                    usage[row["warehouse_id"]] = row["count"]
                    
            return usage
            
        except Exception as e:
            self._log_error(f"창고 사용량 계산 오류", e)
            return {}

class EmployeeRepository(BaseRepository):
    """직원 정보 관리 리포지토리"""
    
    def get_all(self) -> List[Dict]:
        """모든 직원 정보 조회"""
        try:
            query = "SELECT id, name, rfid_uid, role FROM employee"
            result = self.db.execute_dict_query(query)
            
            if not result:
                return []
                
            return result
        except Exception as e:
            self._log_error("직원 정보 조회 오류", e)
            return []
    
    def get_by_id(self, employee_id: str) -> Optional[Dict]:
        """ID로 직원 정보 조회"""
        try:
            query = "SELECT id, name, rfid_uid, role FROM employee WHERE id = %s"
            result = self.db.execute_dict_query(query, (employee_id,))
            
            if not result:
                return None
                
            return result[0]
        except Exception as e:
            self._log_error(f"직원 정보 조회 오류 (ID: {employee_id})", e)
            return None
    
    def get_by_rfid(self, rfid_uid: int) -> Optional[Dict]:
        """RFID로 직원 정보 조회"""
        try:
            query = "SELECT id, name, rfid_uid, role FROM employee WHERE rfid_uid = %s"
            result = self.db.execute_dict_query(query, (rfid_uid,))
            
            if not result:
                return None
                
            return result[0]
        except Exception as e:
            self._log_error(f"직원 정보 조회 오류 (RFID: {rfid_uid})", e)
            return None
    
    def update_rfid(self, employee_id: str, rfid_uid: int) -> bool:
        """직원 RFID 업데이트"""
        try:
            query = "UPDATE employee SET rfid_uid = %s WHERE id = %s"
            affected = self.db.execute_update(query, (rfid_uid, employee_id))
            return affected > 0
        except Exception as e:
            self._log_error(f"직원 RFID 업데이트 오류 (ID: {employee_id})", e)
            return False

class AccessLogRepository(BaseRepository):
    """출입 로그 관리 리포지토리"""
    
    def get_logs(self, limit: int = 20, offset: int = 0, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """출입 로그 조회"""
        try:
            query = """
                SELECT id, card_id, employee_name, access_type, timestamp, created_at 
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
            
            result = self.db.execute_dict_query(query, tuple(params))
            
            if not result:
                return []
                
            return result
        except Exception as e:
            self._log_error("출입 로그 조회 오류", e)
            return []
    
    def get_daily_stats(self, date: str) -> Optional[Dict]:
        """특정 날짜의 출입 통계 조회"""
        try:
            query = """
                SELECT entries, exits, current_count 
                FROM daily_access_stats 
                WHERE date = %s
            """
            result = self.db.execute_dict_query(query, (date,))
            
            if not result:
                return None
                
            return result[0]
        except Exception as e:
            self._log_error(f"일일 출입 통계 조회 오류 (날짜: {date})", e)
            return None
    
    def update_daily_stats(self, date: str, entries: int, exits: int, current_count: int) -> bool:
        """일일 출입 통계 업데이트"""
        try:
            # 기존 데이터 확인
            check_query = "SELECT id FROM daily_access_stats WHERE date = %s"
            result = self.db.execute_query(check_query, (date,))
            
            if result:
                # 업데이트
                query = """
                    UPDATE daily_access_stats 
                    SET entries = %s, exits = %s, current_count = %s 
                    WHERE date = %s
                """
                affected = self.db.execute_update(query, (entries, exits, current_count, date))
            else:
                # 새로 삽입
                query = """
                    INSERT INTO daily_access_stats 
                    (date, entries, exits, current_count) 
                    VALUES (%s, %s, %s, %s)
                """
                affected = self.db.execute_update(query, (date, entries, exits, current_count))
            
            return affected > 0
        except Exception as e:
            self._log_error(f"일일 출입 통계 업데이트 오류 (날짜: {date})", e)
            return False
    
    def add_log(self, card_id: str, employee_name: str, access_type: str, timestamp: Optional[datetime] = None) -> bool:
        """출입 로그 추가"""
        try:
            if timestamp is None:
                timestamp = datetime.now()
                
            query = """
                INSERT INTO access_logs 
                (card_id, employee_name, access_type, timestamp) 
                VALUES (%s, %s, %s, %s)
            """
            affected = self.db.execute_update(query, (card_id, employee_name, access_type, timestamp))
            return affected > 0
        except Exception as e:
            self._log_error("출입 로그 추가 오류", e)
            return False
    
    def get_last_access(self, card_id: str) -> Optional[Dict]:
        """특정 카드의 마지막 출입 기록 조회"""
        try:
            query = """
                SELECT id, card_id, employee_name, access_type, timestamp 
                FROM access_logs 
                WHERE card_id = %s 
                ORDER BY timestamp DESC 
                LIMIT 1
            """
            result = self.db.execute_dict_query(query, (card_id,))
            
            if not result:
                return None
                
            return result[0]
        except Exception as e:
            self._log_error(f"마지막 출입 기록 조회 오류 (카드: {card_id})", e)
            return None


class WarningLogRepository(BaseRepository):
    """경고 로그 관리 리포지토리"""
    
    def log_temperature_warning(self, warehouse_id: str, temperature: float, status: str) -> bool:
        """온도 경고 로그 저장"""
        try:
            query = """
                INSERT INTO temp_warning_logs 
                (warehouse_id, temperature, status, dttm) 
                VALUES (%s, %s, %s, NOW())
            """
            affected = self.db.execute_update(query, (warehouse_id, temperature, status))
            return affected > 0
        except Exception as e:
            self._log_error(f"온도 경고 로그 저장 오류 (창고: {warehouse_id})", e)
            return False
    
    def get_temp_warnings(self, warehouse_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """온도 경고 로그 조회"""
        try:
            query = """
                SELECT warehouse_id, temperature, status, dttm 
                FROM temp_warning_logs
            """
            
            params = []
            
            if warehouse_id:
                query += " WHERE warehouse_id = %s"
                params.append(warehouse_id)
            
            query += " ORDER BY dttm DESC LIMIT %s"
            params.append(limit)
            
            result = self.db.execute_dict_query(query, tuple(params))
            
            if not result:
                return []
                
            return result
        except Exception as e:
            self._log_error("온도 경고 로그 조회 오류", e)
            return []
    
    def log_access_warning(self, card_id: str, reason: str) -> bool:
        """출입 경고 로그 저장"""
        try:
            query = """
                INSERT INTO access_warning_logs 
                (card_id, reason, dttm) 
                VALUES (%s, %s, NOW())
            """
            affected = self.db.execute_update(query, (card_id, reason))
            return affected > 0
        except Exception as e:
            self._log_error(f"출입 경고 로그 저장 오류 (카드: {card_id})", e)
            return False