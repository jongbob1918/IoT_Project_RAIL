# db/migration.py
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

# 데이터베이스 연결 모듈 임포트
from .db_connection import DBConnection
from .config import DBConfig

logger = logging.getLogger(__name__)

class DatabaseMigration:
    """데이터베이스 마이그레이션 및 초기화 관리 클래스"""
    
    def __init__(self, db_config: Optional[DBConfig] = None):
        """초기화
        
        Args:
            db_config: 데이터베이스 설정 객체
        """
        self.config = db_config or DBConfig.from_config_file()
            
        # 필수 테이블 목록
        self.required_tables = [
            "warehouse", "product", "product_item", "employee", 
            "error", "temp_warning_logs", "rfid_scan_logs",
            "access_logs", "daily_access_stats"
        ]
        
        # DB 연결 객체 (지연 초기화)
        self._db_connection = None
        
        logger.info(f"데이터베이스 마이그레이션 초기화: {self.config}")
    
    @property
    def db(self) -> DBConnection:
        """데이터베이스 연결 객체 반환 (지연 초기화)"""
        if self._db_connection is None:
            self._db_connection = DBConnection(self.config)
        return self._db_connection
    
    def init_database(self) -> bool:
        """데이터베이스 초기화 및 테이블 생성
        
        데이터베이스가 존재하지 않으면 생성하고, 필요한 테이블을 생성합니다.
        
        Returns:
            bool: 초기화 성공 여부
        """
        try:
            # 1. 데이터베이스 존재 여부 확인
            if not self._check_database_exists():
                # 1.1. DB가 없으면 새로 생성
                logger.info(f"데이터베이스 '{self.config.database}'가 존재하지 않습니다. 생성합니다.")
                if not self._create_database():
                    logger.error("데이터베이스 생성 실패")
                    return False
                
                # 1.2. 기본 테이블 생성 (target_temp 컬럼 포함)
                logger.info("기본 테이블을 생성합니다.")
                if not self._create_tables():
                    logger.error("기본 테이블 생성 실패")
                    return False
            else:
                # 2. DB가 이미 존재하는 경우
                logger.info(f"데이터베이스 '{self.config.database}'가 이미 존재합니다. 테이블을 확인합니다.")
                
                # 2.1. 누락된 테이블 확인
                missing_tables = self._check_missing_tables()
                
                if missing_tables:
                    # 2.2. 누락된 테이블 생성
                    logger.info(f"누락된 테이블이 있습니다: {', '.join(missing_tables)}")
                    if not self._create_missing_tables(missing_tables):
                        logger.error("누락된 테이블 생성 실패")
                        return False
                else:
                    logger.info("모든 필요한 테이블이 존재합니다.")
                
                # 2.3. 필요한 스키마 업데이트 (target_temp 컬럼 추가 등)
                self._update_warehouse_schema()
            
            logger.info("데이터베이스 초기화가 완료되었습니다.")
            return True
            
        except Exception as e:
            logger.error(f"데이터베이스 초기화 중 오류 발생: {str(e)}")
            return False
    
    def _check_database_exists(self) -> bool:
        """데이터베이스 존재 여부 확인"""
        try:
            # MySQL 기본 연결
            import mysql.connector
            conn = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password
            )
            
            cursor = conn.cursor()
            cursor.execute(f"SHOW DATABASES LIKE '{self.config.database}'")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return bool(result)
        except Exception as e:
            logger.error(f"데이터베이스 존재 여부 확인 중 오류: {str(e)}")
            return False
    
    def _create_database(self) -> bool:
        """데이터베이스 생성"""
        try:
            # MySQL 기본 연결
            import mysql.connector
            conn = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password
            )
            
            cursor = conn.cursor()
            
            # UTF-8 문자 집합으로 데이터베이스 생성
            cursor.execute(f"CREATE DATABASE {self.config.database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            cursor.close()
            conn.close()
            
            logger.info(f"데이터베이스 '{self.config.database}' 생성 완료")
            return True
        except Exception as e:
            logger.error(f"데이터베이스 생성 중 오류: {str(e)}")
            return False
    
    def _create_tables(self) -> bool:
        """기본 테이블 생성"""
        try:
            # 기본 테이블 SQL 정의
            table_sql = {
                "warehouse": """
                    CREATE TABLE IF NOT EXISTS `warehouse` (
                      `id` varchar(20) NOT NULL,
                      `warehouse_type` varchar(50) DEFAULT NULL,
                      `min_temp` float DEFAULT NULL,
                      `max_temp` float DEFAULT NULL,
                      `target_temp` float DEFAULT NULL,
                      `capacity` int DEFAULT NULL,
                      `used_capacity` int DEFAULT NULL,
                      PRIMARY KEY (`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "product": """
                    CREATE TABLE IF NOT EXISTS `product` (
                      `id` varchar(10) NOT NULL,
                      `name` varchar(100) DEFAULT NULL,
                      `category` varchar(50) DEFAULT NULL,
                      `price` int DEFAULT NULL,
                      `warehouse_id` varchar(20) DEFAULT NULL,
                      PRIMARY KEY (`id`),
                      KEY `warehouse_id` (`warehouse_id`),
                      CONSTRAINT `product_ibfk_1` FOREIGN KEY (`warehouse_id`) REFERENCES `warehouse` (`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "product_item": """
                    CREATE TABLE IF NOT EXISTS `product_item` (
                      `id` varchar(20) NOT NULL,
                      `warehouse_id` varchar(20) DEFAULT NULL,
                      `product_id` varchar(10) DEFAULT NULL,
                      `exp` date DEFAULT NULL,
                      `entry_time` varchar(20) DEFAULT NULL,
                      PRIMARY KEY (`id`),
                      KEY `warehouse_id` (`warehouse_id`),
                      KEY `product_id` (`product_id`),
                      CONSTRAINT `product_item_ibfk_1` FOREIGN KEY (`warehouse_id`) REFERENCES `warehouse` (`id`),
                      CONSTRAINT `product_item_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `product` (`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "employee": """
                    CREATE TABLE IF NOT EXISTS `employee` (
                      `id` varchar(20) NOT NULL,
                      `name` varchar(50) DEFAULT NULL,
                      `rfid_uid` int DEFAULT NULL,
                      `role` varchar(50) DEFAULT NULL,
                      PRIMARY KEY (`id`),
                      UNIQUE KEY `rfid_uid` (`rfid_uid`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "error": """
                    CREATE TABLE IF NOT EXISTS `error` (
                      `error_code` varchar(10) NOT NULL,
                      `error_range` varchar(50) DEFAULT NULL,
                      `desc` text,
                      `method` text,
                      PRIMARY KEY (`error_code`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "temp_warning_logs": """
                    CREATE TABLE IF NOT EXISTS `temp_warning_logs` (
                      `id` int NOT NULL AUTO_INCREMENT,
                      `warehouse_id` varchar(10) DEFAULT NULL,
                      `temperature` decimal(5,2) DEFAULT NULL,
                      `status` varchar(20) DEFAULT NULL,
                      `dttm` datetime DEFAULT NULL,
                      PRIMARY KEY (`id`),
                      KEY `warehouse_id` (`warehouse_id`),
                      CONSTRAINT `temp_warning_logs_ibfk_1` FOREIGN KEY (`warehouse_id`) REFERENCES `warehouse` (`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "rfid_scan_logs": """
                    CREATE TABLE IF NOT EXISTS `rfid_scan_logs` (
                      `id` int NOT NULL AUTO_INCREMENT,
                      `rfid_uid` int DEFAULT NULL,
                      `access_result` varchar(10) DEFAULT NULL,
                      `error_code` varchar(10) DEFAULT NULL,
                      `dttm` datetime DEFAULT NULL,
                      PRIMARY KEY (`id`),
                      KEY `rfid_uid` (`rfid_uid`),
                      KEY `error_code` (`error_code`),
                      CONSTRAINT `rfid_scan_logs_ibfk_1` FOREIGN KEY (`rfid_uid`) REFERENCES `employee` (`rfid_uid`),
                      CONSTRAINT `rfid_scan_logs_ibfk_2` FOREIGN KEY (`error_code`) REFERENCES `error` (`error_code`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "access_logs": """
                    CREATE TABLE IF NOT EXISTS `access_logs` (
                      `id` int NOT NULL AUTO_INCREMENT,
                      `card_id` varchar(50) DEFAULT NULL,
                      `employee_name` varchar(100) DEFAULT NULL,
                      `access_type` varchar(20) DEFAULT NULL,
                      `timestamp` datetime DEFAULT NULL,
                      `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """,
                "daily_access_stats": """
                    CREATE TABLE IF NOT EXISTS `daily_access_stats` (
                      `id` int NOT NULL AUTO_INCREMENT,
                      `date` date DEFAULT NULL,
                      `entries` int DEFAULT 0,
                      `exits` int DEFAULT 0,
                      `current_count` int DEFAULT 0,
                      `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (`id`),
                      UNIQUE KEY `date` (`date`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            }
            
            # 테이블 생성 순서 (외래 키 관계 고려)
            table_order = [
                "warehouse", "employee", "error", "product", 
                "product_item", "temp_warning_logs", "rfid_scan_logs",
                "access_logs", "daily_access_stats"
            ]
            
            # 테이블 생성
            for table in table_order:
                if table in table_sql:
                    try:
                        self.db.execute_update(table_sql[table])
                        logger.info(f"테이블 '{table}' 생성 완료")
                    except Exception as e:
                        logger.error(f"테이블 '{table}' 생성 중 오류: {str(e)}")
                else:
                    logger.warning(f"테이블 '{table}'의 SQL 정의가 없습니다.")
            
            # 기본 데이터 삽입 (warehouse 테이블)
            try:
                check_query = "SELECT COUNT(*) FROM warehouse"
                result = self.db.execute_query(check_query)
                
                if result and result[0][0] == 0:
                    # target_temp를 포함한 초기 데이터 삽입
                    insert_sql = """
                        INSERT INTO `warehouse` VALUES
                        ('A', '냉동', -30, -18, -22, 16, 0),  /* 목표 온도: -22 */
                        ('B', '냉장', 0, 10, 5, 16, 0),       /* 목표 온도: 5 */
                        ('C', '상온', 15, 25, 20, 16, 0);     /* 목표 온도: 20 */
                    """
                    self.db.execute_update(insert_sql)
                    logger.info("기본 창고 데이터 삽입 완료")
            except Exception as e:
                logger.error(f"기본 데이터 삽입 중 오류: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"테이블 생성 중 오류: {str(e)}")
            return False
    
    def _check_missing_tables(self) -> List[str]:
        """필요한 테이블 중 누락된 테이블 확인"""
        try:
            # 현재 테이블 목록 조회
            query = "SHOW TABLES"
            result = self.db.execute_query(query)
            
            if not result:
                return self.required_tables
            
            existing_tables = [row[0] for row in result]
            missing_tables = [table for table in self.required_tables if table not in existing_tables]
            
            return missing_tables
        except Exception as e:
            logger.error(f"테이블 확인 중 오류: {str(e)}")
            return self.required_tables
    
    def _create_missing_tables(self, missing_tables: List[str]) -> bool:
        """누락된 테이블만 생성"""
        try:
            # 전체 테이블 생성 메서드 호출 (이미 존재하는 테이블은 "IF NOT EXISTS"로 인해 무시됨)
            return self._create_tables()
        except Exception as e:
            logger.error(f"누락된 테이블 생성 중 오류: {str(e)}")
            return False
    
    def _update_warehouse_schema(self) -> bool:
        """warehouse 테이블의 스키마 업데이트 (target_temp 컬럼 추가 등)"""
        try:
            # 컬럼 존재 여부 확인
            columns_query = "SHOW COLUMNS FROM warehouse"
            columns_result = self.db.execute_query(columns_query)
            
            if not columns_result:
                logger.warning("warehouse 테이블 구조를 가져올 수 없습니다.")
                return False
            
            # 컬럼 이름 목록 생성
            columns = [col[0] for col in columns_result]
            
            # target_temp 컬럼 추가 (없는 경우)
            if 'target_temp' not in columns:
                logger.info("warehouse 테이블에 target_temp 컬럼 추가")
                alter_query = """
                    ALTER TABLE warehouse 
                    ADD COLUMN target_temp float DEFAULT NULL
                    AFTER max_temp
                """
                self.db.execute_update(alter_query)
                
                # 기본 목표 온도 설정
                update_queries = [
                    "UPDATE warehouse SET target_temp = -22 WHERE id = 'A' AND target_temp IS NULL",
                    "UPDATE warehouse SET target_temp = 5 WHERE id = 'B' AND target_temp IS NULL",
                    "UPDATE warehouse SET target_temp = 20 WHERE id = 'C' AND target_temp IS NULL"
                ]
                
                for query in update_queries:
                    self.db.execute_update(query)
                
                logger.info("warehouse 테이블 스키마 업데이트 완료")
            
            return True
        except Exception as e:
            logger.error(f"warehouse 테이블 스키마 업데이트 중 오류: {str(e)}")
            return False