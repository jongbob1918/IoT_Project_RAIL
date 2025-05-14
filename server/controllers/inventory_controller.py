import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

class InventoryController:
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
        
        # 임시 재고 데이터 (shelf_id 제거, 창고 기반 관리)
        self.inventory_items = [
            {
                "item_id": "A001",
                "barcode": "A0102250601",
                "name": "농심 한입 닭가슴살",
                "warehouse_id": "A",
                "expiry_date": "2025-06-01",
                "status": "normal",
                "entry_date": "2025-05-01"
            },
            {
                "item_id": "B001",
                "barcode": "B0301250510",
                "name": "CJ 묵은지 김치",
                "warehouse_id": "B",
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
        warehouses = {}
        
        # DB에서 창고 정보 조회
        if self.db and hasattr(self.db, 'get_warehouses'):
            warehouse_info = self.db.get_warehouses()
            
            # 각 창고별 재고 수량 계산
            warehouse_counts = {}
            for item in self.inventory_items:
                wh_id = item["warehouse_id"]
                if wh_id not in warehouse_counts:
                    warehouse_counts[wh_id] = 0
                warehouse_counts[wh_id] += 1
            
            # 창고별 정보 구성
            for wh in warehouse_info:
                wh_id = wh["id"]
                warehouses[wh_id] = {
                    "total_capacity": wh["capacity"],
                    "used_capacity": warehouse_counts.get(wh_id, 0),
                    "utilization_rate": warehouse_counts.get(wh_id, 0) / wh["capacity"] if wh["capacity"] > 0 else 0
                }
        else:
            # DB 연결이 없을 경우 기본값 사용
            self.logger.warning("데이터베이스 연결 없음 - 기본 창고 정보 사용")
            default_warehouses = ["A", "B", "C"]
            warehouse_counts = {}
            
            # 각 창고별 재고 수량 계산
            for item in self.inventory_items:
                wh_id = item["warehouse_id"]
                if wh_id not in warehouse_counts:
                    warehouse_counts[wh_id] = 0
                warehouse_counts[wh_id] += 1
                
            # 기본 창고 정보 설정
            for wh_id in default_warehouses:
                warehouses[wh_id] = {
                    "total_capacity": 100,  # 기본 용량
                    "used_capacity": warehouse_counts.get(wh_id, 0),
                    "utilization_rate": warehouse_counts.get(wh_id, 0) / 100
                }
        
        return {
            "total_items": len(self.inventory_items),
            "warehouse_counts": warehouse_counts,
            "warehouses": warehouses
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