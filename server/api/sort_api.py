# server/api/sort_api.py
from flask import Blueprint, jsonify, request
from controllers.sort_controller import SortController
import time
from datetime import datetime

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
    try:
        if not sort_controller:
            return jsonify({
                "success": False,
                "error": {"message": "컨트롤러가 초기화되지 않았습니다."},
                "timestamp": datetime.now().isoformat()
            }), 500
        
        status = sort_controller.get_status()
        
        # 표준 응답 형식으로 변환
        return jsonify({
            "success": True,
            "data": status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {"message": str(e)},
            "timestamp": datetime.now().isoformat()
        }), 500

# ==== 분류기 제어 API ====
@sort_bp.route('/control', methods=['POST'])
def control_sorter():
    """분류기 시작/정지 제어 API"""
    if not sort_controller:
        return jsonify({"error": "컨트롤러가 초기화되지 않았습니다."}), 500
    
    data = request.json
    if not data or 'action' not in data:
        return jsonify({"error": "필수 파라미터 누락: action"}), 400
    
    action = data['action']
    
    if action == 'start':
        success = sort_controller.start_sorter()
        message = "분류기 시작 명령 전송 성공" if success else "분류기 시작 명령 전송 실패"
    elif action == 'stop':
        success = sort_controller.stop_sorter()
        message = "분류기 정지 명령 전송 성공" if success else "분류기 정지 명령 전송 실패"
    elif action == "pause":
        success = sort_controller.pause_sorter()
        message = "분류기 일시정지 명령 전송 성공" if success else "분류기 일시정지 명령 전송 실패"
    else:
        return jsonify({"error": f"알 수 없는 액션: {action}"}), 400
    
    return jsonify({
        "success": success, 
        "message": message,
        "current_state": sort_controller.state
    })
