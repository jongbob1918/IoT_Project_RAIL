# server/api/env_api.py
from flask import Blueprint, request, jsonify
from api import get_controller
import logging

# Blueprint 초기화 - 고유한 이름 부여
bp = Blueprint('env_api', __name__)
logger = logging.getLogger("api.environment")

def get_env_controller():
    """환경 제어 컨트롤러를 가져옵니다."""
    # 새로운 방식으로 시도
    controller = get_controller('environment')
    if controller:
        return controller
    
    # 이전 방식 시도 (이전 버전 호환성)
    from api import controller as main_controller
    if main_controller and hasattr(main_controller, 'env_controller'):
        return main_controller.env_controller
    
    # 없으면 None 반환
    return None

# ==== 환경 상태 조회 ====
@bp.route('/status', methods=['GET'])
def get_environment_status():
    """현재 환경 상태를 조회합니다."""
    env_controller = get_env_controller()
    if not env_controller:
        return jsonify({
            "status": "error", 
            "message": "환경 컨트롤러가 초기화되지 않았습니다."
        }), 500
    
    result = env_controller.get_status()
    return jsonify(result)

# ==== 창고별 상태 조회 ====
@bp.route('/warehouse/<warehouse>', methods=['GET'])
def get_warehouse_status(warehouse):
    """특정 창고의 환경 상태를 조회합니다."""
    # 창고 ID 검증
    if warehouse not in ['A', 'B', 'C']:
        return jsonify({"status": "error", "message": "유효하지 않은 창고 ID"}), 400
    
    env_controller = get_env_controller()
    result = env_controller.get_warehouse_status(warehouse)
    
    if result.get("status") == "error":
        return jsonify(result), 400
    
    return jsonify(result)

# ==== 온도 설정 (통합 API) ====
@bp.route('/temperature', methods=['PUT', 'POST'])
def set_temperature():
    """창고 온도 제어 설정을 변경합니다.
    
    PUT 또는 POST 메서드를 모두 지원합니다.
    요청 형식:
    {
        "warehouse": "A",  # 창고 ID (A, B, C)
        "temperature": 20  # 설정할 온도 (숫자)
    }
    """
    data = request.json
    
    # 필수 파라미터 확인
    if not data:
        return jsonify({"status": "error", "message": "요청 본문이 필요합니다."}), 400
    
    warehouse = data.get('warehouse') or data.get('target_temp')
    temperature = data.get('temperature') or data.get('target_temp')
    
    if not warehouse or temperature is None:
        return jsonify({
            "status": "error",
            "message": "필수 파라미터 누락: warehouse, temperature"
        }), 400
    
    # 타입 검증
    if not isinstance(warehouse, str):
        return jsonify({"status": "error", "message": "창고 ID는 문자열이어야 합니다."}), 400
    
    try:
        temperature = float(temperature)
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "온도는 숫자여야 합니다."}), 400
    
    # 입력값 검증
    if warehouse not in ['A', 'B', 'C']:
        return jsonify({"status": "error", "message": "유효하지 않은 창고 ID입니다. A, B, C 중 하나여야 합니다."}), 400
    
    # 환경 컨트롤러를 통해 명령 전송
    env_controller = get_env_controller()
    if not env_controller:
        return jsonify({"status": "error", "message": "환경 제어 컨트롤러가 초기화되지 않았습니다."}), 500
    
    # 명령 전송 (set_target_temperature 직접 호출)
    result = env_controller.set_target_temperature(warehouse, temperature)
    
    if result.get("status") == "error":
        return jsonify(result), 400
        
    return jsonify(result)

# ==== 온도 경고 조회 ====
@bp.route('/warnings', methods=['GET'])
def get_temperature_warnings():
    """현재 발생 중인 온도 경고를 조회합니다."""
    env_controller = get_env_controller()
    if not env_controller:
        return jsonify({"status": "error", "message": "환경 제어 컨트롤러가 초기화되지 않았습니다."}), 500
    
    warnings = env_controller.get_warnings()
    return jsonify({
        "status": "success",
        "data": warnings
    })