from datetime import datetime
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request
from api import get_controller

# Blueprint 초기화
bp = Blueprint('access', __name__)

# 컨트롤러 의존성
def get_access_controller():
    """출입 제어 컨트롤러 인스턴스를 반환합니다."""
    # 새로운 방식으로 시도
    controller = get_controller('access')
    if controller:
        return controller
        
    # 이전 방식 시도
    from api import controller as main_controller
    if main_controller and hasattr(main_controller, 'access_controller'):
        return main_controller.access_controller
    
    # 더미 컨트롤러 반환 - 에러 방지
    class DummyAccessController:
        def get_access_logs(self):
            return []
            
        def open_door(self):
            return {"status": "error", "message": "출입 컨트롤러가 초기화되지 않았습니다."}
            
        def close_door(self):
            return {"status": "error", "message": "출입 컨트롤러가 초기화되지 않았습니다."}
    
    return DummyAccessController()

@bp.route("/logs", methods=["GET"])
def get_access_logs():
    """출입 기록 조회"""
    try:
        controller = get_access_controller()
        logs = controller.get_access_logs()
        return jsonify({
            "success": True, 
            "logs": logs,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@bp.route("/open-door", methods=["POST"])
def open_door():
    """출입문 열기"""
    try:
        controller = get_access_controller()
        result = controller.open_door()
        return jsonify({
            "success": True, 
            "message": "출입문이 열렸습니다.",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@bp.route("/close-door", methods=["POST"])
def close_door():
    """출입문 닫기"""
    try:
        controller = get_access_controller()
        result = controller.close_door()
        return jsonify({
            "success": True, 
            "message": "출입문이 닫혔습니다.",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
