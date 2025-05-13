# server/db/init_db.py
import logging
import os
import subprocess
from pathlib import Path
import re

# MySQL 관련 라이브러리 임포트 시도
try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    logging.warning("MySQL 라이브러리를 가져올 수 없습니다. 'pip install mysql-connector-python' 명령으로 설치하세요.")

# config.py에서 설정 가져오기 시도
try:
    from config import CONFIG, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    logging.warning("config.py에서 설정을 가져올 수 없습니다. 환경 변수를 사용합니다.")

# 로깅 설정
logger = logging.getLogger(__name__)

def create_database(host, port, user, password, db_name):
    """
    MySQL 데이터베이스 생성
    """
    if not MYSQL_AVAILABLE:
        logger.error("MySQL 라이브러리가 설치되어 있지 않아 데이터베이스를 생성할 수 없습니다.")
        return False
    
    try:
        # MySQL에 연결
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor()
            # 데이터베이스 생성
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name};")
            logger.info(f"데이터베이스 '{db_name}' 생성 완료")
            cursor.close()
            connection.close()
            return True
    
    except Error as e:
        logger.error(f"데이터베이스 생성 오류: {e}")
        return False

def init_database():
    """
    데이터베이스 초기화 함수
    - MySQL 데이터베이스가 존재하는지 확인
    - 없으면 생성하고 백업 파일에서 복원
    - 있으면 필요한 테이블만 확인하고 누락된 테이블만 생성
    """
    if not MYSQL_AVAILABLE:
        logger.error("MySQL 라이브러리가 설치되어 있지 않아 데이터베이스 초기화를 건너뜁니다.")
        return False
        
    # 데이터베이스 접속 정보
    if USE_CONFIG:
        DB_HOST_VALUE = DB_HOST
        DB_PORT_VALUE = DB_PORT
        DB_USER_VALUE = DB_USER
        DB_PASSWORD_VALUE = DB_PASSWORD
        DB_NAME_VALUE = DB_NAME
        logger.info("config.py에서 데이터베이스 설정을 로드했습니다.")
    else:
        DB_HOST_VALUE = os.getenv("DB_HOST", "localhost")
        DB_PORT_VALUE = os.getenv("DB_PORT", "3306")
        DB_USER_VALUE = os.getenv("DB_USER", "root")
        DB_PASSWORD_VALUE = os.getenv("DB_PASSWORD", "0000")
        DB_NAME_VALUE = os.getenv("DB_NAME", "rail_db")
        logger.info("환경 변수에서 데이터베이스 설정을 로드했습니다.")
    
    logger.info(f"데이터베이스 확인: {DB_HOST_VALUE}:{DB_PORT_VALUE}/{DB_NAME_VALUE}")
    
    # 데이터베이스 연결 확인
    try:
        # 먼저 MySQL 서버에 연결
        connection = mysql.connector.connect(
            host=DB_HOST_VALUE,
            port=DB_PORT_VALUE,
            user=DB_USER_VALUE,
            password=DB_PASSWORD_VALUE
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # 데이터베이스 존재 여부 확인
            cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME_VALUE}'")
            db_exists = cursor.fetchone()
            
            if not db_exists:
                logger.info(f"데이터베이스 '{DB_NAME_VALUE}'가 존재하지 않습니다. 생성합니다.")
                
                # 데이터베이스 생성
                create_database(DB_HOST_VALUE, DB_PORT_VALUE, DB_USER_VALUE, DB_PASSWORD_VALUE, DB_NAME_VALUE)
                
                # 데이터베이스 선택
                cursor.execute(f"USE {DB_NAME_VALUE}")
                
                # 백업 파일 경로
                backup_file = Path(__file__).parent / "rail_db_backup.sql"
                
                if backup_file.exists():
                    logger.info(f"백업 파일 '{backup_file}'에서 데이터베이스를 복원합니다.")
                    restore_from_backup(DB_HOST_VALUE, DB_PORT_VALUE, DB_USER_VALUE, DB_PASSWORD_VALUE, DB_NAME_VALUE, backup_file)
                else:
                    logger.warning(f"백업 파일 '{backup_file}'가 존재하지 않습니다.")
            else:
                logger.info(f"데이터베이스 '{DB_NAME_VALUE}'가 이미 존재합니다. 테이블 확인 중...")
                
                # 데이터베이스 선택
                cursor.execute(f"USE {DB_NAME_VALUE}")
                
                # 필요한 테이블 목록
                required_tables = [
                    "warehouse", "warehouse_slot", "unit", "model", "seller",
                    "error", "abnormal_temperature_logs", "barcode_scan_logs"
                ]
                
                # 기존 테이블 확인
                cursor.execute("SHOW TABLES")
                existing_tables = [table[0] for table in cursor.fetchall()]
                
                # 누락된 테이블 확인
                missing_tables = [table for table in required_tables if table not in existing_tables]
                
                if missing_tables:
                    logger.info(f"누락된 테이블이 있습니다: {', '.join(missing_tables)}")
                    
                    # 백업 파일에서 필요한 테이블만 추출하여 생성
                    backup_file = Path(__file__).parent / "rail_db_backup.sql"
                    if backup_file.exists():
                        logger.info(f"백업 파일에서 누락된 테이블을 복원합니다.")
                        restore_missing_tables(connection, backup_file, missing_tables)
                    else:
                        logger.warning(f"백업 파일이 존재하지 않아 누락된 테이블을 생성할 수 없습니다.")
                else:
                    logger.info("모든 필요한 테이블이 존재합니다.")
                
            cursor.close()
            connection.close()
            logger.info("데이터베이스 초기화 완료")
            return True
            
    except Error as e:
        logger.error(f"MySQL 연결 오류: {e}")
        return False
        
    return True

def restore_from_backup(host, port, user, password, db_name, backup_file):
    """전체 데이터베이스를 백업 파일에서 복원"""
    if not MYSQL_AVAILABLE:
        logger.error("MySQL 라이브러리가 설치되어 있지 않아 데이터베이스를 복원할 수 없습니다.")
        return False
        
    try:
        # OS에 따라 명령이 다를 수 있음
        cmd = f"mysql -h {host} -P {port} -u {user} -p{password} {db_name} < {backup_file}"
        subprocess.run(cmd, shell=True, check=True)
        logger.info("데이터베이스 복원 완료")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"데이터베이스 복원 중 오류 발생: {e}")
        
        # 직접 Python으로 SQL 파일 실행
        try:
            connection = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=db_name
            )
            cursor = connection.cursor()
            
            with open(backup_file, 'r') as f:
                sql_script = f.read()
                
            # SQL 스크립트를 개별 명령으로 분리
            sql_commands = []
            current_command = ""
            for line in sql_script.splitlines():
                # 주석이나 빈 줄 건너뛰기
                if line.startswith('--') or line.startswith('/*') or line.strip() == '':
                    continue
                    
                current_command += line + " "
                if line.strip().endswith(';'):
                    sql_commands.append(current_command.strip())
                    current_command = ""
            
            # 각 명령 실행
            for command in sql_commands:
                if command:
                    try:
                        cursor.execute(command)
                    except Exception as exec_error:
                        logger.error(f"명령 실행 중 오류: {exec_error}")
                        logger.error(f"문제의 명령: {command[:100]}...")
                        
            connection.commit()
            cursor.close()
            connection.close()
            logger.info("Python으로 데이터베이스 복원 완료")
            return True
        except Exception as ex:
            logger.error(f"Python으로 복원 중 오류 발생: {ex}")
            return False
    return False

def restore_missing_tables(connection, backup_file, missing_tables):
    """백업 파일에서 누락된 테이블만 추출하여 생성"""
    if not MYSQL_AVAILABLE:
        logger.error("MySQL 라이브러리가 설치되어 있지 않아 테이블을 복원할 수 없습니다.")
        return False
        
    try:
        cursor = connection.cursor()
        
        with open(backup_file, 'r') as f:
            content = f.read()
        
        # 각 테이블 정의 추출
        for table in missing_tables:
            # 테이블 생성 SQL 찾기
            table_pattern = f"DROP TABLE IF EXISTS `{table}`.*?CREATE TABLE `{table}`.*?ENGINE=.*?;"
            match = re.search(table_pattern, content, re.DOTALL)
            
            if match:
                table_sql = match.group(0)
                
                # 테이블 생성 명령 실행
                try:
                    cursor.execute(table_sql)
                    logger.info(f"테이블 '{table}' 생성 완료")
                    
                    # 데이터 삽입 SQL 찾기 (있는 경우)
                    insert_pattern = f"LOCK TABLES `{table}` WRITE;.*?INSERT INTO `{table}` VALUES.*?UNLOCK TABLES;"
                    insert_match = re.search(insert_pattern, content, re.DOTALL)
                    
                    if insert_match:
                        insert_sql = insert_match.group(0)
                        # 삽입 명령 실행
                        try:
                            for command in insert_sql.split(';'):
                                if command.strip():
                                    cursor.execute(command + ';')
                            logger.info(f"테이블 '{table}'에 데이터 삽입 완료")
                        except Exception as insert_error:
                            logger.error(f"테이블 '{table}' 데이터 삽입 중 오류: {insert_error}")
                except Exception as create_error:
                    logger.error(f"테이블 '{table}' 생성 중 오류: {create_error}")
            else:
                logger.warning(f"백업 파일에서 테이블 '{table}'의 정의를 찾을 수 없습니다.")
        
        connection.commit()
        logger.info("누락된 테이블 복원 완료")
        return True
    except Exception as e:
        logger.error(f"누락된 테이블 복원 중 오류 발생: {e}")
        return False

# 테스트 실행
if __name__ == "__main__":
    # 로깅 포맷 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 데이터베이스 초기화
    init_database()