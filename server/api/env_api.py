# server/api/env_api.py
from flask import Blueprint, request, jsonify
from api import get_controller

# Blueprint 초기화 - 고유한 이름 부여
bp = Blueprint('env_api', __name__)

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
    
    # 더미 컨트롤러 반환 - 에러 방지
    class DummyEnvController:
        def get_status(self):
            return {"status": "error", "message": "환경 컨트롤러가 초기화되지 않았습니다."}
        
        def get_warehouse_status(self, warehouse):
            return {"status": "error", "message": "환경 컨트롤러가 초기화되지 않았습니다."}
            
        def set_target_temperature(self, warehouse, target_temp):
            return {"status": "error", "message": "환경 컨트롤러가 초기화되지 않았습니다."}
    
    return DummyEnvController()

# ==== 환경 상태 조회 ====
@bp.route('/environment/status', methods=['GET'])
def get_environment_status():
    """현재 환경 상태를 조회합니다."""
    env_controller = get_env_controller()
    result = env_controller.get_status()
    return jsonify(result)

# ==== 창고별 상태 조회 ====
@bp.route('/environment/warehouse/<warehouse>', methods=['GET'])
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
@bp.route('/environment/control', methods=['PUT'])
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