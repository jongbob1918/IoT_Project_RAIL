import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

class InventoryController:
    """재고 관리 컨트롤러 클래스
    
    재고 관리 시스템의 비즈니스 로직을 처리하는 클래스입니다.
    재고 물품 조회, 선반 배치 관리 등의 기능을 제공합니다.
    """
    
    def __init__(self, tcp_handler, websocket_manager, db_helper=None):
        """재고 관리 컨트롤러 초기화
        
        Args:
            tcp_handler: TCP 통신 핸들러
            websocket_manager: WebSocket 통신 관리자
            db_helper: 데이터베이스 헬퍼
        """
        self.tcp_handler = tcp_handler
        self.ws_manager = websocket_manager
        self.db = db_helper
        self.logger = logging.getLogger(__name__)
        
        # 임시 재고 데이터
        self.inventory_items = [
            {
                "item_id": "A001",
                "barcode": "A0102250601",
                "name": "농심 한입 닭가슴살",
                "warehouse_id": "A",
                "shelf_id": "A01",
                "expiry_date": "2025-06-01",
                "status": "normal",
                "entry_date": "2025-05-01"
            },
            {
                "item_id": "B001",
                "barcode": "B0301250510",
                "name": "CJ 묵은지 김치",
                "warehouse_id": "B",
                "shelf_id": "B01",
                "expiry_date": "2025-05-10",
                "status": "warning",
                "entry_date": "2025-05-03"
            }
        ]
        
    def get_inventory_status(self) -> Dict:
        """현재 재고 상태를 조회합니다.
        
        Returns:
            Dict: 재고 상태 정보
        """
        # 창고별 재고 수량 계산
        warehouse_counts = {}
        for item in self.inventory_items:
            wh_id = item["warehouse_id"]
            if wh_id not in warehouse_counts:
                warehouse_counts[wh_id] = 0
            warehouse_counts[wh_id] += 1
            
        return {
            "total_items": len(self.inventory_items),
            "warehouse_counts": warehouse_counts,
            "warehouses": [
                {
                    "warehouse_id": "A",
                    "total_capacity": 100,
                    "used_capacity": warehouse_counts.get("A", 0),
                    "utilization_rate": warehouse_counts.get("A", 0) / 100
                },
                {
                    "warehouse_id": "B",
                    "total_capacity": 100,
                    "used_capacity": warehouse_counts.get("B", 0),
                    "utilization_rate": warehouse_counts.get("B", 0) / 100
                },
                {
                    "warehouse_id": "C",
                    "total_capacity": 100,
                    "used_capacity": warehouse_counts.get("C", 0),
                    "utilization_rate": warehouse_counts.get("C", 0) / 100
                },
                {
                    "warehouse_id": "D",
                    "total_capacity": 100,
                    "used_capacity": warehouse_counts.get("D", 0),
                    "utilization_rate": warehouse_counts.get("D", 0) / 100
                }
            ]
        }
        
    def get_inventory_items(self, category: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict]:
        """재고 물품 목록을 조회합니다.
        
        Args:
            category (Optional[str]): 필터링할 창고 ID
            limit (int): 한 페이지당 항목 수
            offset (int): 시작 위치
            
        Returns:
            List[Dict]: 재고 물품 목록
        """
        # 카테고리 필터링
        filtered_items = self.inventory_items
        if category:
            filtered_items = [item for item in self.inventory_items if item["warehouse_id"] == category]
            
        # 페이지네이션
        paginated_items = filtered_items[offset:offset+limit]
            
        return paginated_items
        
    def get_inventory_item(self, item_id: str) -> Optional[Dict]:
        """특정 재고 물품을 조회합니다.
        
        Args:
            item_id (str): 물품 ID
            
        Returns:
            Optional[Dict]: 재고 물품 정보
        """
        for item in self.inventory_items:
            if item["item_id"] == item_id:
                return item
                
        return None
        
    def handle_message(self, message: Dict):
        """TCP 메시지 처리
        
        Args:
            message (Dict): 메시지 데이터
        """
        try:
            if message.get('tp') == 'evt':
                if message.get('evt') == 'barcode':
                    # 바코드 스캔 이벤트 처리
                    barcode = message.get('val', {}).get('c')
                    if barcode:
                        self.logger.info(f"바코드 스캔: {barcode}")
                        # 여기에 바코드 처리 로직 추가
            
        except Exception as e:
            self.logger.error(f"메시지 처리 중 오류 발생: {str(e)}")
            
    def update_gui(self):
        """GUI를 업데이트합니다."""
        status_data = self.get_inventory_status()
        
        # WebSocket으로 상태 브로드캐스트
        self.ws_manager.broadcast("inventory_status", status_data) 