# 유틸리티 패키지 서버 전반에서 사용되는 유틸리티 함수 및 클래스 모음
from typing import Dict, Any

# 버전 정보
__version__ = '1.0.0'

# 유틸리티 함수 예시
def serialize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """딕셔너리를 직렬화하기 위한 유틸리티 함수"""
    return {k: str(v) if isinstance(v, (bytes, bytearray)) else v for k, v in data.items()}