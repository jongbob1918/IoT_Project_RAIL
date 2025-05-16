# db/config.py
import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DBConfig:
    """데이터베이스 설정 관리 클래스"""
    host: str
    port: int
    user: str
    password: str
    database: str
    
    @classmethod
    def from_env(cls):
        """환경 변수에서 DB 설정 로드"""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "rail_db")
        )
    
    @classmethod
    def from_config_file(cls, config_module=None):
        """설정 파일에서 DB 설정 로드"""
        try:
            # 메인 구성 파일에서 설정 가져오기
            import sys
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
            
            return cls(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
            )
        except ImportError as e:
            logger.warning(f"메인 config.py 파일에서 설정을 가져올 수 없습니다: {str(e)}. 환경 변수를 사용합니다.")
            return cls.from_env()
    
    def get_connection_string(self):
        """연결 문자열 반환"""
        return f"mysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def __str__(self):
        """문자열 표현 (비밀번호 마스킹)"""
        return f"DBConfig(host={self.host}, port={self.port}, user={self.user}, database={self.database})"