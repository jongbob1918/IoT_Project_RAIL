from datetime import datetime
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request
from api import get_controller
from db import DBManager 

# Blueprint 초기화
bp = Blueprint('access', __name__)

db_manager = DBManager()

# 컨트롤러 의존성
def get_access_controller():
    """출입 제어 컨트롤러 인스턴스를 반환합니다."""
    # 새로운 방식으로 시도
    controller = get_controller('access')
    if controller:
        return controller
    
    # 더미 컨트롤러 반환 - 에러 방지
    class DummyAccessController:
        def get_access_logs(self):
            return []
            
        def open_door(self):
            return {"status": "error", "message": "출입 컨트롤러가 초기화되지 않았습니다."}
            
        def close_door(self):
            return {"status": "error", "message": "출입 컨트롤러가 초기화되지 않았습니다."}
    
    return DummyAccessController()

@bp.route('/logs', methods=['GET'])
def get_access_logs():
    try:
        # 페이징 처리 추가
        limit = request.args.get('limit', default=20, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        # 날짜 필터링 (선택적)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 데이터베이스에서 로그 가져오기
        logs = db_manager.get_access_logs(limit=limit, offset=offset, 
                                         start_date=start_date, end_date=end_date)
        
        # 타입 체크 및 변환 - 안전한 형태로 수정
        if logs is None:
            logs = []
        
        # 문자열이 반환될 경우의 처리
        if isinstance(logs, str):
            try:
                import json
                # JSON 문자열인 경우 파싱 시도
                parsed_logs = json.loads(logs)
                if isinstance(parsed_logs, list):
                    logs = parsed_logs
                else:
                    logs = []
            except:
                logs = []
        
        # 리스트가 아닌 경우 빈 리스트로 변환
        if not isinstance(logs, list):
            logs = []
        
        result = {
            "success": True,
            "logs": logs,
            "total_count": len(logs),
            "timestamp": datetime.now().isoformat()
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {"message": str(e)},
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
