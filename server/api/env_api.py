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
@bp.route('/warehouse/<warehouse>', methods=['GET'])  # 'environment/' 제거
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

# ==== 온도 설정 ====
@bp.route('/control', methods=['PUT'])  # 'environment/' 제거
def set_environment_control():
    """창고 온도 제어 설정을 변경합니다."""
    data = request.json
    
    # 필수 파라미터 확인
    if not data or 'warehouse' not in data or 'target_temp' not in data:
        return jsonify({
            "status": "error",
            "message": "필수 파라미터 누락: warehouse, target_temp"
        }), 400
    
    warehouse = data['warehouse']
    target_temp = data['target_temp']
    
    # 창고 ID 검증
    if warehouse not in ['A', 'B', 'C']:
        return jsonify({"status": "error", "message": "유효하지 않은 창고 ID"}), 400
    
    # 온도 유효성 검증
    try:
        target_temp = float(target_temp)
    except ValueError:
        return jsonify({"status": "error", "message": "온도는 숫자여야 합니다"}), 400
    
    env_controller = get_env_controller()
    result = env_controller.set_target_temperature(warehouse, target_temp)
    
    if result.get("status") == "error":
        return jsonify(result), 400
    
    return jsonify(result)

# 온도 설정 API
@bp.route('/temperature', methods=['POST'])
def set_temperature():
    """특정 창고의 목표 온도를 설정합니다."""
    data = request.json
    
    # 필수 파라미터 확인
    if not data:
        return jsonify({"status": "error", "message": "요청 본문이 필요합니다."}), 400
    
    if "warehouse" not in data or "temperature" not in data:
        return jsonify({"status": "error", "message": "필수 파라미터 누락: warehouse, temperature"}), 400
    
    warehouse = data.get('warehouse')
    
    # 타입 검증
    if not isinstance(warehouse, str):
        return jsonify({"status": "error", "message": "창고 ID는 문자열이어야 합니다."}), 400
    
    try:
        temperature = int(data.get('temperature'))
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "온도는 정수여야 합니다."}), 400
    
    # 입력값 검증
    if warehouse not in ['A', 'B', 'C']:
        return jsonify({"status": "error", "message": "유효하지 않은 창고 ID입니다. A, B, C 중 하나여야 합니다."}), 400
    
    # 온도 범위 검증 (창고별 적정 범위)
    valid_ranges = {
        'A': (-30, -18),  # 냉동
        'B': (0, 10),     # 냉장
        'C': (15, 25)     # 상온
    }
    
    min_temp, max_temp = valid_ranges[warehouse]
    if temperature < min_temp or temperature > max_temp:
        return jsonify({
            "status": "error", 
            "message": f"{warehouse} 창고의 온도는 {min_temp}°C에서 {max_temp}°C 사이여야 합니다."
        }), 400
    
    # 환경 컨트롤러를 통해 명령 전송
    env_controller = get_env_controller()
    if not env_controller:
        return jsonify({"status": "error", "message": "환경 제어 컨트롤러가 초기화되지 않았습니다."}), 500
    
    # 명령 전송
    success = env_controller.set_temperature(warehouse, temperature)
    
    if success:
        return jsonify({
            "status": "success",
            "message": f"{warehouse} 창고 온도가 {temperature}°C로 설정되었습니다."
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"{warehouse} 창고 온도 설정 중 오류가 발생했습니다."
        }), 500

# 온도 경고 조회 API
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