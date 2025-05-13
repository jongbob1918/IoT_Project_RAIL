from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger('utils.middleware')

def validate_request(schema):
    """
    요청 본문을 검증하는 데코레이터
    
    매개변수:
    - schema (dict): 유효성 검사 스키마, 다음 키를 포함:
        - required (list): 필수 필드 목록
        - types (dict): 필드 이름과 예상 타입의 매핑
    
    사용 예:
    @validate_request({
        "required": ["user_id", "name"],
        "types": {
            "user_id": int,
            "name": str,
            "age": int  # 선택적 필드
        }
    })
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # JSON 요청 본문 확인
            if not request.is_json:
                return jsonify({
                    "status": "error",
                    "message": "JSON 형식의 요청 본문이 필요합니다."
                }), 400
            
            data = request.json
            
            # 필수 필드 확인
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        "status": "error",
                        "message": f"필수 필드 누락: {field}"
                    }), 400
            
            # 타입 확인
            type_checks = schema.get("types", {})
            for field, expected_type in type_checks.items():
                if field in data and not isinstance(data[field], expected_type):
                    # 숫자 타입의 경우 문자열에서 변환 시도
                    if expected_type in (int, float) and isinstance(data[field], str):
                        try:
                            if expected_type == int:
                                data[field] = int(data[field])
                            else:
                                data[field] = float(data[field])
                            continue
                        except ValueError:
                            pass
                    
                    # 변환 실패 또는 다른 타입 불일치
                    type_name = expected_type.__name__
                    return jsonify({
                        "status": "error",
                        "message": f"필드 '{field}'의 타입이 잘못되었습니다. {type_name} 타입이 필요합니다."
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_request():
    """요청 정보를 로그에 기록하는 데코레이터"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.debug(f"요청: {request.method} {request.path} - 데이터: {request.json if request.is_json else 'N/A'}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator 