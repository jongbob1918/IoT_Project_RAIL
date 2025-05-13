from datetime import datetime
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request
from api import get_controller

# Blueprint 초기화
bp = Blueprint('inventory', __name__)

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

@bp.route("/status", methods=["GET"])
def get_inventory_status():
    """재고 상태 조회"""
    try:
        controller = get_inventory_controller()
        status = controller.get_inventory_status()
        return jsonify({
            "success": True, 
            "data": status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@bp.route("/items", methods=["GET"])
def get_inventory_items():
    """재고 물품 목록 조회"""
    try:
        category = request.args.get("category")
        limit = request.args.get("limit", default=20, type=int)
        offset = request.args.get("offset", default=0, type=int)
        
        controller = get_inventory_controller()
        items = controller.get_inventory_items(category, limit, offset)
        
        return jsonify({
            "success": True,
            "data": items,
            "total_count": len(items),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@bp.route("/items/<item_id>", methods=["GET"])
def get_inventory_item(item_id):
    """재고 물품 상세 조회"""
    try:
        controller = get_inventory_controller()
        item = controller.get_inventory_item(item_id)
        
        if not item:
            return jsonify({
                "success": False,
                "error": "물품을 찾을 수 없습니다.",
                "timestamp": datetime.now().isoformat()
            }), 404
            
        return jsonify({
            "success": True,
            "data": item,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500 