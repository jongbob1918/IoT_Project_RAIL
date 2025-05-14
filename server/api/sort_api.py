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
    else:
        return jsonify({"error": f"알 수 없는 액션: {action}"}), 400
    
    return jsonify({
        "success": success, 
        "message": message,
        "current_state": sort_controller.state
    })

# ==== 분류기 비상정지 API ====
@sort_bp.route('/emergency', methods=['POST'])
def emergency_stop():
    if not sort_controller:
        return jsonify({"error": "컨트롤러가 초기화되지 않았습니다."}), 500
    
    result = sort_controller.emergency_stop()
    return jsonify(result), 200 if result["success"] else 400

# ==== 바코드 분류 명령 API ====
@sort_bp.route('/barcode', methods=['POST'])
def process_barcode():
    """바코드 분류 명령 API"""
    if not sort_controller:
        return jsonify({"error": "컨트롤러가 초기화되지 않았습니다."}), 500
    
    data = request.json
    if not data or 'barcode' not in data:
        return jsonify({"error": "필수 파라미터 누락: barcode"}), 400
    
    barcode = data['barcode']
    
    # 카테고리가 이미 지정된 경우
    category = data.get('category', '')
    
    # 카테고리가 지정되지 않은 경우 바코드 첫 자리로 결정
    if not category and len(barcode) > 0:
        first_digit = barcode[0]
        
        # 바코드 첫 자리로 분류
        if first_digit in ["1", "4", "7"]:
            category = "A"  # 냉동 보관
        elif first_digit in ["2", "5", "8"]:
            category = "B"  # 냉장 보관
        elif first_digit in ["3", "6", "9"]:
            category = "C"  # 상온 보관
        else:
            category = "E"  # 오류
    
    # 프로토콜에 맞는 분류 명령 생성 및 전송
    from utils.protocol import create_message, DEVICE_SORTER, MSG_COMMAND, SORT_CMD_SORT
    command = create_message(DEVICE_SORTER, MSG_COMMAND, f"{SORT_CMD_SORT}{category}")
    
    # 디바이스 연결 상태 확인
    is_connected = sort_controller.tcp_handler.is_device_connected(DEVICE_SORTER)
    if not is_connected:
        return jsonify({
            "success": False,
            "barcode": barcode,
            "category": category,
            "message": "분류기 장치가 연결되어 있지 않습니다."
        }), 503
    
    # 명령 전송
    success = sort_controller.tcp_handler.send_message(DEVICE_SORTER, command)
    
    response = {
        "success": success,
        "barcode": barcode,
        "category": category,
        "message": f"분류 명령 전송 {'성공' if success else '실패'}"
    }
    
    # 로그에 바코드 정보 추가
    if success:
        sort_controller._add_sort_log({
            "barcode": barcode,
            "category": category,
            "timestamp": time.time()
        })
    
    return jsonify(response)