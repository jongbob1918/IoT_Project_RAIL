from datetime import datetime
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request
from api import get_controller
from db.db_manager import DBManager
import logging

# Blueprint 초기화
bp = Blueprint('inventory', __name__)

# 로거 설정
logger = logging.getLogger(__name__)

# 컨트롤러 의존성
def get_inventory_controller():
    """재고 관리 컨트롤러 인스턴스를 반환합니다."""
    controller = get_controller('inventory')
    if controller:
        return controller
    
    # 이전 방식 시도 (이전 버전 호환성)
    try:
        from api import controller
        if controller and hasattr(controller, 'inventory_controller'):
            return controller.inventory_controller
    except (ImportError, AttributeError):
        pass
    
    # 빈 더미 컨트롤러 반환 - 에러 방지
    class DummyInventoryController:
        def get_inventory_status(self):
            return {"status": "unknown", "message": "인벤토리 컨트롤러가 초기화되지 않았습니다."}
        
        def get_inventory_items(self, category=None, limit=20, offset=0):
            return []
            
        def get_inventory_item(self, item_id):
            return None
    
    return DummyInventoryController()

@bp.route('/waiting', methods=['GET'])
def get_waiting_items():
    """입고 대기 아이템 수 반환"""
    try:
        # 분류기 컨트롤러에서 직접 대기 물품 수를 가져옴
        sort_controller = get_controller('sort')
        if sort_controller:
            waiting_count = sort_controller.items_waiting
        else:
            # 컨트롤러 접근 실패 시 기본값 제공
            logger.warning("분류기 컨트롤러에 접근할 수 없습니다. 대기 물품 수를 0으로 설정합니다.")
            waiting_count = 0
            
        return jsonify({"waiting": waiting_count})
    except Exception as e:
        logger.error(f"입고 대기 아이템 조회 오류: {str(e)}")
        # 오류 발생 시에도 UI에 필요한 기본값 제공
        return jsonify({"waiting": 0})

@bp.route("/status", methods=["GET"])
def get_inventory_status():
    """재고 현황 요약 정보 조회"""
    try:
        controller = get_inventory_controller()
        status = controller.get_inventory_status()
        
        # 결과 타입 체크 및 변환
        if status is None:
            status = {"status": "unknown", "warehouses": {}}
            
        if not isinstance(status, dict):
            logger.warning(f"재고 상태: 예상치 못한 데이터 타입 - {type(status).__name__}")
            status = {"status": "error", "message": "데이터 형식 오류", "warehouses": {}}
        else:
            # 딕셔너리지만 warehouses 키가 없는 경우 추가
            if "warehouses" not in status:
                status["warehouses"] = {}
                
        # GUI에서 기대하는 형식으로 반환
        return jsonify({
            "success": True,
            "data": status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"재고 상태 조회 오류: {str(e)}")
        return jsonify({
            "success": False,
            "error": {"message": str(e)},
            "timestamp": datetime.now().isoformat()
        }), 500

@bp.route("/items", methods=["GET"])
def get_inventory_items():
    try:
        category = request.args.get("category")
        limit = request.args.get("limit", default=20, type=int)
        offset = request.args.get("offset", default=0, type=int)
        
        controller = get_inventory_controller()
        items = controller.get_inventory_items(category, limit, offset)
        
        # None 또는 다른 타입 체크
        if items is None:
            items = []
            
        # 리스트가 아닌 경우 처리 (GUI는 리스트 형식 기대)
        if not isinstance(items, list):
            logger.warning(f"inventory_items: 예상치 못한 데이터 타입 - {type(items).__name__}")
            items = []
        
        # GUI에서 기대하는 형식으로 반환
        return jsonify({
            "success": True,
            "data": items,
            "total_count": len(items),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"재고 목록 조회 오류: {str(e)}")
        return jsonify({
            "success": False,
            "error": {"message": str(e)},
            "timestamp": datetime.now().isoformat()
        }), 500