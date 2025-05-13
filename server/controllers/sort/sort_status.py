# server/controllers/sort/sort_status.py
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# ==== 분류기 상태 열거형 ====
class SortState(Enum):
    STOPPED = "stopped"           # 정지 상태
    RUNNING = "running"           # 실행 중
    EMERGENCY_STOP = "emergency"  # 비상 정지

# ==== 분류기 상태 관리 클래스 ====
class SortStatus:
    def __init__(self, controller):
        self.controller = controller
        self._state = SortState.STOPPED
        self.physical_emergency = False
        self.motor_active = False
        
        # 물품 카운터
        self.items_waiting = 0
        self.items_processed = 0
        
        # 분류대별 물품 수 카운터
        self.sorted_items = {
            "A": 0,  # 냉동
            "B": 0,  # 냉장
            "C": 0,  # 상온
            "D": 0,  # 비식품
            "E": 0   # 오류물품
        }
        
        logger.info("분류기 상태 관리자 초기화 완료")
    
    # ==== 상태 속성 getter/setter ====
    @property
    def state(self):
        return self._state.value
    
    @state.setter
    def state(self, new_state):
        # 문자열로 상태 설정 시 Enum으로 변환
        if isinstance(new_state, str):
            try:
                new_state = SortState(new_state)
            except ValueError:
                logger.error(f"잘못된 상태 값: {new_state}")
                return
        
        # 상태 변경 시 로그 기록
        if new_state != self._state:
            logger.info(f"분류기 상태 변경: {self._state.value} -> {new_state.value}")
            self._state = new_state
            
            # 상태에 따른 후속 처리
            if new_state == SortState.STOPPED:
                self.motor_active = False
            elif new_state == SortState.RUNNING:
                self.motor_active = True
            elif new_state == SortState.EMERGENCY_STOP:
                self.motor_active = False
    
    # ==== 현재 상태 반환 (딕셔너리) ====
    def get_status_data(self):
        return {
            "status": self._state.value,
            "physical_emergency": self.physical_emergency,
            "motor_active": self.motor_active,
            "items_waiting": self.items_waiting,
            "items_processed": self.items_processed,
            "sorted_items": self.sorted_items
        }
    
    # ==== 물품 대기 수 증가 ====
    def increment_waiting(self):
        self.items_waiting += 1
        return self.items_waiting
    
    # ==== 물품 대기 수 감소, 처리 수 증가 ====
    def process_item(self, category):
        if self.items_waiting > 0:
            self.items_waiting -= 1
        
        self.items_processed += 1
        
        # 분류 카테고리 카운터 증가
        if category in self.sorted_items:
            self.sorted_items[category] += 1
        
        return {
            "waiting": self.items_waiting,
            "processed": self.items_processed,
            "by_category": self.sorted_items
        }
    
    # ==== 카운터 초기화 ====
    def reset_counters(self):
        self.items_waiting = 0
        self.items_processed = 0
        for category in self.sorted_items:
            self.sorted_items[category] = 0