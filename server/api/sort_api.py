from flask import Blueprint, request, jsonify
from api import get_controller


bp = Blueprint('sort_api', __name__)

def get_sort_controller():
    """분류 컨트롤러를 가져옵니다."""
    # 새로운 방식으로 시도
    controller = get_controller('sort')
    if controller:
        return controller
    
    # 이전 방식 시도 (이전 버전 호환성)
    from api import controller as main_controller
    if main_controller and hasattr(main_controller, 'sort_controller'):
        return main_controller.sort_controller
    
    # 더미 컨트롤러 반환 - 에러 방지
    class DummySortController:
        def start_sorting(self):
            return {"status": "error", "message": "분류 컨트롤러가 초기화되지 않았습니다."}
        
        def stop_sorting(self):
            return {"status": "error", "message": "분류 컨트롤러가 초기화되지 않았습니다."}
            
        def emergency_stop(self):
            return {"status": "error", "message": "분류 컨트롤러가 초기화되지 않았습니다."}
            
        def get_status(self):
            return {"status": "unknown", "message": "분류 컨트롤러가 초기화되지 않았습니다."}
    
    return DummySortController()

# ==== 분류 시작 ====
@bp.route('/inbound/start', methods=['POST'])
def start_inbound():
    """분류기 작동을 시작합니다."""
    sort_controller = get_sort_controller()
    result = sort_controller.start_sorting()
    
    if result.get("status") == "error":
        return jsonify(result), 400
    
    return jsonify(result)

# ==== 분류 종료 ====
@bp.route('/inbound/stop', methods=['POST'])
def stop_inbound():
    """분류기 작동을 정지합니다."""
    sort_controller = get_sort_controller()
    result = sort_controller.stop_sorting()
    
    if result.get("status") == "error":
        return jsonify(result), 400
    
    return jsonify(result)

# ==== 비상 정지 ====
@bp.route('/emergency/stop', methods=['POST'])
def emergency_stop():
    """분류기를 긴급 정지합니다."""
    sort_controller = get_sort_controller()
    result = sort_controller.emergency_stop()
    
    if result.get("status") == "error":
        return jsonify(result), 400
    
    return jsonify(result)

# ==== 분류기 상태 조회 ====
@bp.route('/inbound/status', methods=['GET'])
def get_inbound_status():
    """현재 분류기 상태를 조회합니다."""
    sort_controller = get_sort_controller()
    result = sort_controller.get_status()
    return jsonify(result)