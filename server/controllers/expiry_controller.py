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
        """유통기한 관리 컨트롤러 초기화
        
        Args:
            tcp_handler: TCP 통신 핸들러
            websocket_manager: WebSocket 통신 관리자
            inventory_controller: 재고 관리 컨트롤러
            db_helper: 데이터베이스 헬퍼
        """
        self.tcp_handler = tcp_handler
        self.ws_manager = websocket_manager
        self.inventory_controller = inventory_controller
        self.db = db_helper
        self.logger = logging.getLogger(__name__)
        
        # 임시 유통기한 데이터
        self.expiry_items = [
            {
                "item_id": "B001",
                "barcode": "B0301250510",
                "name": "CJ 묵은지 김치",
                "warehouse_id": "B",
                "shelf_id": "B01",
                "expiry_date": "2025-05-10",
                "days_remaining": 5,
                "status": "warning",
                "entry_date": "2025-05-03"
            },
            {
                "item_id": "C001",
                "barcode": "C0806250505",
                "name": "롯데 샌드위치용 식빵",
                "warehouse_id": "C",
                "shelf_id": "C01",
                "expiry_date": "2025-05-05",
                "days_remaining": 0,
                "status": "expired",
                "entry_date": "2025-05-01"
            }
        ]
        
    def get_expiry_alerts(self, days_threshold: int = 7) -> List[Dict]:
        """유통기한 경고 목록을 조회합니다.
        
        Args:
            days_threshold (int): 경고 기준 일수
            
        Returns:
            List[Dict]: 유통기한 경고 목록
        """
        today = datetime.now().date()
        alerts = []
        
        for item in self.expiry_items:
            expiry_date = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
            days_remaining = (expiry_date - today).days
            
            if 0 <= days_remaining <= days_threshold:
                item_copy = item.copy()
                item_copy["days_remaining"] = days_remaining
                alerts.append(item_copy)
                
        return alerts
        
    def get_expired_items(self) -> List[Dict]:
        """유통기한 만료 물품을 조회합니다.
        
        Returns:
            List[Dict]: 유통기한 만료 물품 목록
        """
        today = datetime.now().date()
        expired_items = []
        
        for item in self.expiry_items:
            expiry_date = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
            days_remaining = (expiry_date - today).days
            
            if days_remaining < 0:
                item_copy = item.copy()
                item_copy["days_remaining"] = days_remaining
                expired_items.append(item_copy)
                
        return expired_items
        
    def process_expired_item(self, item_id: str, action: str, description: str) -> bool:
        """유통기한 만료 물품을 처리합니다.
        
        Args:
            item_id (str): 물품 ID
            action (str): 처리 작업 (dispose/return)
            description (str): 처리 내용 설명
            
        Returns:
            bool: 처리 성공 여부
        """
        # 물품 존재 확인
        target_item = None
        for item in self.expiry_items:
            if item["item_id"] == item_id:
                target_item = item
                break
                
        if not target_item:
            self.logger.error(f"물품을 찾을 수 없음: {item_id}")
            return False
            
        # 처리 작업 검증
        if action not in ["dispose", "return"]:
            self.logger.error(f"잘못된 처리 작업: {action}")
            return False
            
        # 처리 작업 수행
        self.logger.info(f"만료 물품 처리: {item_id} ({action})")
        
        # 재고에서 제거 (물품 폐기 또는 반품)
        if action == "dispose":
            # 재고 제거 로직 (예: DB 업데이트)
            pass
        elif action == "return":
            # 반품 처리 로직
            pass
            
        # 처리 기록 저장
        log_entry = {
            "item_id": item_id,
            "action": action,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.db:
            self.db.save_expiry_process_log(log_entry)
            
        return True
        
    def check_expiry_dates(self):
        """모든 물품의 유통기한을 검사합니다."""
        today = datetime.now().date()
        
        for item in self.expiry_items:
            expiry_date = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
            days_remaining = (expiry_date - today).days
            
            # 상태 업데이트
            if days_remaining < 0:
                item["status"] = "expired"
            elif days_remaining <= 3:
                item["status"] = "danger"
            elif days_remaining <= 7:
                item["status"] = "warning"
            else:
                item["status"] = "normal"
                
            item["days_remaining"] = days_remaining
            
        # GUI 업데이트
        self.update_gui()
        
    def update_gui(self):
        """GUI를 업데이트합니다."""
        # 오늘 만료
        today = datetime.now().date()
        today_items = []
        
        # 이미 만료됨
        expired_items = []
        
        # 곧 만료 예정
        upcoming_items = []
        
        for item in self.expiry_items:
            expiry_date = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
            days_remaining = (expiry_date - today).days
            
            if days_remaining < 0:
                expired_items.append(item)
            elif days_remaining == 0:
                today_items.append(item)
            elif days_remaining <= 7:
                upcoming_items.append(item)
                
        status_data = {
            "expired_count": len(expired_items),
            "today_count": len(today_items),
            "upcoming_count": len(upcoming_items),
            "reference_date": today.isoformat()
        }
        
        # WebSocket으로 상태 브로드캐스트
        self.ws_manager.broadcast("expiry_status", status_data) 