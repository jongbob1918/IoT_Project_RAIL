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
            
    def get_expiry_alerts(self, days_threshold: int = 7) -> List[Dict]:
        """유통기한 경고 목록을 조회합니다.
        
        Args:
            days_threshold (int): 경고 기준 일수
            
        Returns:
            List[Dict]: 유통기한 경고 목록
        """
        # 데이터베이스에서 유통기한 경고 조회
        if self.db and hasattr(self.db, 'get_expiry_alerts'):
            return self.db.get_expiry_alerts(days_threshold)
        
        # 데이터베이스 연결이 없는 경우 빈 배열 반환
        today = datetime.now().date()
        
        
    def get_expired_items(self) -> List[Dict]:
        """유통기한 만료 물품을 조회합니다.
        
        Returns:
            List[Dict]: 유통기한 만료 물품 목록
        """
        # 데이터베이스에서 유통기한 만료 물품 조회
        if self.db and hasattr(self.db, 'get_expired_items'):
            return self.db.get_expired_items()
        
        # 데이터베이스 연결이 없는 경우 빈 배열 반환
        today = datetime.now().date()
        
    def process_expired_item(self, item_id: str, action: str, description: str) -> bool:
        """유통기한 만료 물품을 처리합니다.
        
        Args:
            item_id (str): 물품 ID
            action (str): 처리 작업 (dispose/return)
            description (str): 처리 내용 설명
            
        Returns:
            bool: 처리 성공 여부
        """
        # 물품 존재 확인 - DB에서 조회
        if self.db and hasattr(self.db, 'get_item_by_id'):
            target_item = self.db.get_item_by_id(item_id)
            if not target_item:
                self.logger.error(f"물품을 찾을 수 없음: {item_id}")
                return False
        else:
            self.logger.error("데이터베이스 연결 없음 - 물품 처리 불가")
            return False
                
        # 처리 작업 검증
        if action not in ["dispose", "return"]:
            self.logger.error(f"잘못된 처리 작업: {action}")
            return False
            
        # 처리 작업 수행
        self.logger.info(f"만료 물품 처리: {item_id} ({action})")
        
        # 재고에서 제거 (물품 폐기 또는 반품)
        if action == "dispose":
            # 재고 제거 로직 (DB 업데이트)
            if self.db and hasattr(self.db, 'dispose_item'):
                self.db.dispose_item(item_id)
        elif action == "return":
            # 반품 처리 로직
            if self.db and hasattr(self.db, 'return_item'):
                self.db.return_item(item_id)
            
        # 처리 기록 저장
        log_entry = {
            "item_id": item_id,
            "action": action,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.db and hasattr(self.db, 'save_expiry_process_log'):
            self.db.save_expiry_process_log(log_entry)
            
        return True
        
    def check_expiry_dates(self):
        """모든 물품의 유통기한을 검사합니다."""
        today = datetime.now().date()
        
        # 데이터베이스에서 모든 물품 조회
        all_items = []
        if self.db and hasattr(self.db, 'get_all_items'):
            all_items = self.db.get_all_items()
        
        expired_items = []
        today_items = []
        upcoming_items = []
        
        for item in all_items:
            expiry_date = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
            days_remaining = (expiry_date - today).days
            
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