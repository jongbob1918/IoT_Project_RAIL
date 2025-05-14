from datetime import datetime
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request
from api import get_controller
import logging

# Blueprint 초기화
bp = Blueprint('expiry', __name__)

# 로거 설정
logger = logging.getLogger(__name__)

# 컨트롤러 의존성
def get_expiry_controller():
    """유통기한 관리 컨트롤러 인스턴스를 반환합니다."""
    # 새로운 방식으로 시도
    controller = get_controller('expiry')
    if controller:
        return controller
        
    # 이전 방식 시도 (이전 버전 호환성)
    from api import controller as main_controller
    if main_controller and hasattr(main_controller, 'expiry_controller'):
        return main_controller.expiry_controller
    
    # 더미 컨트롤러 반환 - 에러 방지
    class DummyExpiryController:
        def get_expiry_alerts(self, days=7):
            return []
            
        def get_expired_items(self):
            return []
    
    return DummyExpiryController()

@bp.route("/alerts", methods=["GET"])
def get_expiry_alerts():
    """유통기한 경고 목록 조회"""
    try:
        days = request.args.get("days", default=7, type=int)
        
        controller = get_expiry_controller()
        alerts = controller.get_expiry_alerts(days)
        
        # 결과 타입 체크 및 변환
        if alerts is None:
            alerts = []
            
        if not isinstance(alerts, list):
            logger.warning(f"유통기한 경고: 예상치 못한 데이터 타입 - {type(alerts).__name__}")
            alerts = []
        
        return jsonify({
            "success": True,
            "data": alerts,
            "total_count": len(alerts),
            "days_threshold": days,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"유통기한 경고 조회 오류: {str(e)}")
        return jsonify({
            "success": False,
            "error": {"message": str(e)},
            "timestamp": datetime.now().isoformat()
        }), 500

@bp.route("/expired", methods=["GET"])
def get_expired_items():
    """유통기한 만료 물품 목록 조회"""
    try:
        controller = get_expiry_controller()
        items = controller.get_expired_items()
        
        # 결과 타입 체크 및 변환
        if items is None:
            items = []
            
        if not isinstance(items, list):
            logger.warning(f"유통기한 만료: 예상치 못한 데이터 타입 - {type(items).__name__}")
            items = []
        
        return jsonify({
            "success": True,
            "data": items,
            "total_count": len(items),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"유통기한 만료 조회 오류: {str(e)}")
        return jsonify({
            "success": False,
            "error": {"message": str(e)},
            "timestamp": datetime.now().isoformat()
        }), 500 