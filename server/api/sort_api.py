# server/api/sort_api.py
from flask import Blueprint, jsonify
from controllers.sort.sort_controller import SortController

# 블루프린트 생성
sort_bp = Blueprint('sort', __name__, url_prefix='/api/sort')

# 컨트롤러 인스턴스 (app.py에서 초기화 후 전달)
sort_controller = None

# ==== 컨트롤러 설정 ====
def init_controller(controller):
    global sort_controller
    sort_controller = controller

# ==== 상태 조회 API ====
@sort_bp.route('/status', methods=['GET'])
def get_status():
    """분류기 상태 조회 API"""
    if not sort_controller:
        return jsonify({"error": "컨트롤러가 초기화되지 않았습니다."}), 500
    
    status = sort_controller.get_status()
    return jsonify(status)

# 아래 API들은 주석 처리 - 나중에 구현
"""
# ==== 분류기 시작 API ====
@sort_bp.route('/start', methods=['POST'])
def start_sorter():
    if not sort_controller:
        return jsonify({"error": "컨트롤러가 초기화되지 않았습니다."}), 500
    
    result = sort_controller.start_sorter()
    return jsonify(result), 200 if result["success"] else 400

# ==== 분류기 정지 API ====
@sort_bp.route('/stop', methods=['POST'])
def stop_sorter():
    if not sort_controller:
        return jsonify({"error": "컨트롤러가 초기화되지 않았습니다."}), 500
    
    result = sort_controller.stop_sorter()
    return jsonify(result), 200 if result["success"] else 400

# ==== 분류기 비상정지 API ====
@sort_bp.route('/emergency', methods=['POST'])
def emergency_stop():
    if not sort_controller:
        return jsonify({"error": "컨트롤러가 초기화되지 않았습니다."}), 500
    
    result = sort_controller.emergency_stop()
    return jsonify(result), 200 if result["success"] else 400
"""