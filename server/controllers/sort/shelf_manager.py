# server/controllers/sort/shelf_manager.py
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# ==== 선반 관리 클래스 ====
class ShelfManager:
    def __init__(self, db_helper=None):
        self.db_helper = db_helper
        
        # 창고별 빈 선반 캐시
        self.empty_shelves: Dict[str, List[str]] = {
            "A": [],  # 냉동
            "B": [],  # 냉장
            "C": [],  # 상온
            "D": []   # 비식품
        }
        
        # 초기 선반 데이터 로드
        self._refresh_empty_shelves()
        
        logger.info("선반 관리자 초기화 완료")
    
    # ==== 창고 내 빈 선반 할당 ====
    def assign_shelf(self, warehouse: str) -> Optional[str]:
        """창고 내 빈 선반을 할당하고 해당 선반 ID를 반환합니다."""
        # 오류물품(E)은 선반 할당 안함
        if warehouse == "E":
            return None
        
        # DB 연결 확인
        if not self.db_helper:
            logger.warning("DB 연결 없음 - 기본 선반 할당")
            return f"{warehouse}01"  # 임시 기본값 반환
        
        # 빈 선반 캐시가 비어있으면 갱신
        if not self.empty_shelves[warehouse]:
            self._refresh_empty_shelves()
        
        # 빈 선반이 없으면 None 반환
        if not self.empty_shelves[warehouse]:
            logger.warning(f"창고 {warehouse}에 빈 선반이 없음")
            return None
        
        # 첫 번째 빈 선반 할당
        shelf = self.empty_shelves[warehouse].pop(0)
        
        # DB 업데이트 (선반 상태 -> 점유됨)
        try:
            self.db_helper.update_shelf_status(warehouse, shelf, "occupied")
            logger.debug(f"선반 할당: {warehouse}-{shelf}")
            return f"{warehouse}{shelf}"
        except Exception as e:
            logger.error(f"선반 상태 업데이트 실패: {str(e)}")
            # 캐시에 다시 추가 (실패했으므로)
            self.empty_shelves[warehouse].append(shelf)
            return None
    
    # ==== 각 창고의 빈 선반 목록 새로고침 ====
    def _refresh_empty_shelves(self):
        """DB에서 각 창고의 빈 선반 목록을 조회하여 캐시를 업데이트합니다."""
        if not self.db_helper:
            logger.warning("DB 연결 없음 - 기본 선반 목록 생성")
            # 기본 선반 목록 생성 (테스트용)
            for warehouse in ["A", "B", "C", "D"]:
                self.empty_shelves[warehouse] = [f"{i:02d}" for i in range(1, 11)]
            return
        
        try:
            for warehouse in ["A", "B", "C", "D"]:
                self.empty_shelves[warehouse] = self.db_helper.get_empty_shelves(warehouse)
                logger.debug(f"창고 {warehouse} 빈 선반 조회: {len(self.empty_shelves[warehouse])}개")
        except Exception as e:
            logger.error(f"빈 선반 조회 실패: {str(e)}")
            # 오류 시 기본 선반 목록 생성 (테스트용)
            for warehouse in ["A", "B", "C", "D"]:
                self.empty_shelves[warehouse] = [f"{i:02d}" for i in range(1, 11)]
    
    # ==== 항목 정보를 DB에 저장 ====
    def save_item(self, item_info: dict) -> bool:
        """물품 정보를 데이터베이스에 저장합니다."""
        if not self.db_helper:
            logger.warning("DB 연결 없음 - 항목 저장 불가")
            return False
        
        try:
            self.db_helper.save_item(item_info)
            logger.debug(f"항목 저장 성공: {item_info.get('barcode', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"항목 저장 실패: {str(e)}")
            return False
    
    # ==== 특정 창고의 현재 보관 중인 물품 수 반환 ====
    def get_warehouse_items_count(self, warehouse: str) -> int:
        """특정 창고에 현재 보관 중인 물품 수를 반환합니다."""
        if not self.db_helper:
            logger.warning("DB 연결 없음 - 물품 수 조회 불가")
            return 0
        
        try:
            return self.db_helper.get_warehouse_items_count(warehouse)
        except Exception as e:
            logger.error(f"창고 물품 수 조회 실패: {str(e)}")
            return 0
    
    # ==== 유통기한 경과 물품 조회 ====
    def get_expired_items(self, days_threshold: int = 0) -> List[Dict]:
        """유통기한이 지난 물품 또는 임박한 물품 목록을 반환합니다."""
        if not self.db_helper:
            logger.warning("DB 연결 없음 - 유통기한 경과 물품 조회 불가")
            return []
        
        try:
            return self.db_helper.get_expired_items(days_threshold)
        except Exception as e:
            logger.error(f"유통기한 경과 물품 조회 실패: {str(e)}")
            return []