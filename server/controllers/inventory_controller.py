import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

class InventoryController:
    def __init__(self, tcp_handler, websocket_manager, db_helper=None):
        self.tcp_handler = tcp_handler
        self.ws_manager = websocket_manager
        self.logger = logging.getLogger(__name__)
        
        # db_helper 대신 직접 리포지토리 사용
        from db import product_item_repo, warehouse_repo
        self.product_item_repo = product_item_repo
        self.warehouse_repo = warehouse_repo
        
        # 데이터베이스에서 데이터 로드 시도
        items = self.product_item_repo.get_all()
        if items:
            self.inventory_items = items
        else:
            # 기본 항목 설정
            self.inventory_items = [
                # 기존 하드코딩된 항목들
            ]
        
    def get_inventory_status(self) -> Dict:
        """재고 현황 요약 정보 조회"""
        try:
            # 창고 정보 가져오기
            warehouse_info = self.warehouse_repo.get_all()
            
            # 창고별 재고 수량 계산
            count_query = """
                SELECT warehouse_id, COUNT(*) as count
                FROM product_item
                GROUP BY warehouse_id
            """
            count_results = self.product_item_repo.db.execute_dict_query(count_query)
            
            # 카운트 결과 처리
            warehouse_counts = {}
            if count_results:
                for row in count_results:
                    wh_id = row["warehouse_id"]
                    count = row["count"]
                    warehouse_counts[wh_id] = count
                    self.logger.info(f"창고 {wh_id}의 물품 수: {count}")
            
            # 창고별 정보 구성
            warehouses = {}
            
            # 기본 창고 아이디 목록 (warehouse_info 조회 실패시 사용)
            default_warehouse_ids = ["A", "B", "C"]
            
            # warehouse_info가 있으면 사용, 없으면 기본값 사용
            if warehouse_info:
                for wh in warehouse_info:
                    wh_id = wh["id"]
                    capacity = wh.get("capacity", 100)
                    used = warehouse_counts.get(wh_id, 0)
                    usage_percent = (used / capacity * 100) if capacity > 0 else 0
                    
                    warehouses[wh_id] = {
                        "total_capacity": capacity,
                        "used_capacity": used,
                        "utilization_rate": usage_percent / 100,
                        # 추가: 클라이언트 호환성을 위한 필드
                        "used": used,
                        "capacity": capacity,
                        "usage_percent": usage_percent
                    }
            else:
                # warehouse_info 조회 실패 시 기본값 사용
                self.logger.warning("창고 정보 조회 실패, 기본값 사용")
                for wh_id in default_warehouse_ids:
                    used = warehouse_counts.get(wh_id, 0)
                    warehouses[wh_id] = {
                        "total_capacity": 100,
                        "used_capacity": used, 
                        "utilization_rate": used / 100,
                        # 추가: 클라이언트 호환성을 위한 필드
                        "used": used,
                        "capacity": 100,
                        "usage_percent": used
                    }
            
            result = {
                "total_items": sum(warehouse_counts.values()),
                "warehouse_counts": warehouse_counts,
                "warehouses": warehouses
            }
            
            # 디버깅 로그 추가
            self.logger.info(f"준비된 인벤토리 상태 데이터: {result}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"재고 상태 조회 오류: {str(e)}")
            # 오류 시 기본값 반환
            return {
                "total_items": 0,
                "warehouse_counts": {},
                "warehouses": {
                    "A": {"total_capacity": 100, "used_capacity": 0, "utilization_rate": 0, "used": 0, "capacity": 100, "usage_percent": 0},
                    "B": {"total_capacity": 100, "used_capacity": 0, "utilization_rate": 0, "used": 0, "capacity": 100, "usage_percent": 0},
                    "C": {"total_capacity": 100, "used_capacity": 0, "utilization_rate": 0, "used": 0, "capacity": 100, "usage_percent": 0}
                }
            }
            
    def get_inventory_items(self, category: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict]:
        """재고 물품 목록을 조회합니다."""
        # 카테고리 필터링
        filtered_items = self.inventory_items
        if category:
            filtered_items = [item for item in self.inventory_items if item["warehouse_id"] == category]
            
        # 페이지네이션
        paginated_items = filtered_items[offset:offset+limit]
        
        # 제품명 추가하기 위한 결과 리스트
        result_items = []
        
        for item in paginated_items:
            # 기본 아이템 데이터 복사
            result_item = item.copy()
            
            # 제품 정보 조회 (제품명)
            try:
                product_id = item.get("product_id")
                # product 테이블에서 직접 조회 (join 쿼리 사용)
                query = """
                    SELECT p.name
                    FROM product p
                    WHERE p.id = %s
                """
                product_result = self.product_item_repo.db.execute_dict_query(query, (product_id,))
                
                if product_result and len(product_result) > 0:
                    result_item["product_name"] = product_result[0]["name"]
                else:
                    result_item["product_name"] = f"상품-{product_id}"
            except Exception as e:
                self.logger.error(f"제품 정보 조회 오류: {str(e)}")
                result_item["product_name"] = f"상품-{product_id}"
            
            result_items.append(result_item)
                
        return result_items
        
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