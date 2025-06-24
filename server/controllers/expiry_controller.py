import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class ExpiryController:
    """유통기한 관리 컨트롤러 클래스
    
    유통기한 관리 시스템의 비즈니스 로직을 처리하는 클래스입니다.
    유통기한 경고 및 만료 물품 관리 기능을 제공합니다.
    """
    
    def __init__(self, tcp_handler, websocket_manager, inventory_controller=None, db_helper=None):
        self.tcp_handler = tcp_handler
        self.ws_manager = websocket_manager
        self.inventory_controller = inventory_controller
        self.logger = logging.getLogger(__name__)
        
        # db_helper 대신 직접 리포지토리 사용
        from db import product_item_repo
        self.product_item_repo = product_item_repo

    def get_expiry_alerts(self, days_threshold: int = 7) -> List[Dict]:
        """유통기한 경고 목록을 조회합니다."""
        return self.product_item_repo.get_expiring_items(days_threshold)
        
    def get_expired_items(self) -> List[Dict]:
        """유통기한 만료 물품을 조회합니다."""
        return self.product_item_repo.get_expired_items()
        
    def process_expired_item(self, item_id: str, action: str, description: str) -> bool:
        # 직접 repository 사용
        target_item = self.product_item_repo.get_by_id(item_id)
        if not target_item:
            self.logger.error(f"물품을 찾을 수 없음: {item_id}")
            return False
                
        # 처리 작업 검증
        if action not in ["dispose", "return"]:
            self.logger.error(f"잘못된 처리 작업: {action}")
            return False
            
        # 처리 작업 수행
        self.logger.info(f"만료 물품 처리: {item_id} ({action})")
        
        # 재고에서 제거
        if action == "dispose":
            return self.product_item_repo.remove_item(item_id)
        elif action == "return":
            # 여기에 반품 처리 로직 추가
            return self.product_item_repo.remove_item(item_id)  
        return True
        
    def check_expiry_dates(self):
        """모든 물품의 유통기한을 검사합니다."""
        today = datetime.now().date()
        
        # 데이터베이스에서 모든 물품 조회
        all_items = self.product_item_repo.get_all()
        
        expired_items = []
        today_items = []
        upcoming_items = []
        
        for item in all_items:
            # product_item_repo의 결과는 'exp' 필드를 사용합니다
            exp_date = item['exp']
            days_remaining = (exp_date - today).days
            
            # 상태 업데이트
            if days_remaining < 0:
                item["status"] = "expired"
                expired_items.append(item)
            elif days_remaining == 0:
                item["status"] = "danger"
                today_items.append(item)
            elif days_remaining <= 7:
                item["status"] = "warning"
                upcoming_items.append(item)
            else:
                item["status"] = "normal"
                
            item["days_remaining"] = days_remaining
        
        # 상태 데이터 생성
        status_data = {
            "expired_count": len(expired_items),
            "today_count": len(today_items),
            "upcoming_count": len(upcoming_items),
            "reference_date": today.isoformat()
        }
        
        # WebSocket으로 상태 브로드캐스트
        self.ws_manager.broadcast("expiry_status", status_data)
                
    def update_gui(self):
        """GUI를 업데이트합니다."""
        # 상태 업데이트하고 GUI에 전송
        self.check_expiry_dates() 