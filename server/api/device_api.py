from flask import Blueprint, jsonify, request
from utils.protocol import create_message, DEVICE_SORTER, MSG_COMMAND, MSG_ERROR
import logging

# 블루프린트 생성
device_bp = Blueprint('device', __name__, url_prefix='/api/device')

# 로거 설정
logger = logging.getLogger("api.device")

# tcp 핸들러 인스턴스 (app.py에서 초기화 후 전달)
tcp_handler = None

# ==== 초기화 함수 ====
def init_handler(handler):
    global tcp_handler
    tcp_handler = handler

# ==== 디바이스 명령 전송 API ====
@device_bp.route('/command', methods=['POST'])
def send_command():
    """디바이스에 명령 전송 API"""
    if not tcp_handler:
        return jsonify({"error": "TCP 핸들러가 초기화되지 않았습니다."}), 500
    
    data = request.json
    if not data:
        return jsonify({"error": "요청 본문이 없습니다."}), 400
    
    # 필수 파라미터 검증
    required_params = ["device", "type", "payload"]
    for param in required_params:
        if param not in data:
            return jsonify({"error": f"필수 파라미터 누락: {param}"}), 400
    
    device_id = data["device"]
    msg_type = data["type"]
    payload = data["payload"]
    
    # 프로토콜에 맞는 메시지 생성
    command = create_message(device_id, msg_type, payload)
    
    # 메시지 전송
    success = tcp_handler.send_message(device_id, command)
    
    if success:
        logger.info(f"명령 전송 성공: 디바이스={device_id}, 타입={msg_type}, 페이로드={payload}")
        return jsonify({
            "success": True,
            "message": "명령이 성공적으로 전송되었습니다."
        })
    else:
        logger.error(f"명령 전송 실패: 디바이스={device_id}, 타입={msg_type}, 페이로드={payload}")
        return jsonify({
            "success": False,
            "message": "명령 전송에 실패했습니다."
        }), 500

# ==== 분류 명령 전송 API (편의를 위한 래퍼) ====
@device_bp.route('/sort', methods=['POST'])
def send_sort_command():
    """분류 명령 전송 API"""
    if not tcp_handler:
        return jsonify({"error": "TCP 핸들러가 초기화되지 않았습니다."}), 500
    
    data = request.json
    if not data or "category" not in data:
        return jsonify({"error": "필수 파라미터 누락: category"}), 400
    
    category = data["category"]
    if category not in ["A", "B", "C", "E"]:
        return jsonify({"error": f"유효하지 않은 분류 카테고리: {category}"}), 400
    
    # 프로토콜에 맞는 분류 명령 생성 (soA, soB 등)
    command = create_message(DEVICE_SORTER, MSG_COMMAND, f"so{category}")
    
    # 명령 전송
    success = tcp_handler.send_message(DEVICE_SORTER, command)
    
    if success:
        logger.info(f"분류 명령 전송 성공: 카테고리={category}")
        return jsonify({
            "success": True,
            "message": f"분류 명령이 성공적으로 전송되었습니다. (카테고리: {category})"
        })
    else:
        logger.error(f"분류 명령 전송 실패: 카테고리={category}")
        return jsonify({
            "success": False,
            "message": "분류 명령 전송에 실패했습니다."
        }), 500 