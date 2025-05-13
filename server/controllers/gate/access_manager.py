# server/controllers/gate/access_manager.py
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ==== 출입 관리 클래스 ====
class AccessManager:
    # ==== 출입 관리자 초기화 ====
    def __init__(self, db_helper=None):
        self.db_helper = db_helper
        
        # 최근 출입 상태 캐시 (카드 ID -> 마지막 출입 상태)
        self.last_access_state = {}
        
        # 미등록 카드 실패 횟수 (3회 이상 시 경고)
        self.unregistered_attempts = {}
        
        logger.info("출입 관리자 초기화 완료")
    
    # ==== 출입 권한 확인 ====
    def check_access(self, card_id: str) -> Dict[str, Any]:
        """카드 ID를 확인하고 출입 권한이 있는지 확인합니다."""
        # 카드 ID 유효성 검사
        if not card_id or len(card_id) < 4:
            logger.warning(f"유효하지 않은 카드 ID: {card_id}")
            return {
                "access": False,
                "reason": "invalid_card"
            }
        
        # DB 연결 확인
        if not self.db_helper:
            logger.warning("DB 연결 없음 - 모든 카드에 출입 허용")
            
            # DB 없이 출입 상태(입장/퇴장) 관리
            entry_type = "entry"
            if card_id in self.last_access_state:
                # 마지막 상태가 입장이면 퇴장으로 전환
                entry_type = "exit" if self.last_access_state[card_id] == "entry" else "entry"
            
            # 상태 업데이트
            self.last_access_state[card_id] = entry_type
            
            return {
                "access": True,
                "entry_type": entry_type,
                "employee_name": f"직원{card_id[-4:]}"  # 임시 이름
            }
        
        try:
            # DB에서 카드 ID 확인
            employee = self.db_helper.get_employee_by_card(card_id)
            
            # 등록된 카드인지 확인
            if not employee:
                # 미등록 시도 횟수 증가
                if card_id not in self.unregistered_attempts:
                    self.unregistered_attempts[card_id] = 1
                else:
                    self.unregistered_attempts[card_id] += 1
                
                # 3회 이상 시도 시 경고 로그 및 이벤트
                if self.unregistered_attempts[card_id] >= 3:
                    logger.warning(f"미등록 카드 3회 이상 시도: {card_id}")
                    
                    # 경고 기록 저장
                    self.db_helper.save_access_warning(card_id, "unregistered_multiple_attempts")
                    
                    # 카운터 초기화
                    self.unregistered_attempts[card_id] = 0
                
                logger.warning(f"미등록 카드 접근 시도: {card_id}")
                return {
                    "access": False,
                    "reason": "unregistered_card"
                }
            
            # 권한 확인
            if not employee.get("access_allowed", False):
                logger.warning(f"권한 없는 카드 접근 시도: {card_id}, {employee.get('name')}")
                return {
                    "access": False,
                    "reason": "access_denied",
                    "employee_name": employee.get("name")
                }
            
            # 이전 출입 기록 확인하여 입장/퇴장 상태 결정
            entry_type = "entry"
            last_log = self.db_helper.get_last_access_log(card_id)
            
            if last_log and last_log["type"] == "entry" and last_log["date"] == datetime.now().strftime("%Y-%m-%d"):
                # 같은 날 마지막 기록이 입장이면 퇴장으로 설정
                entry_type = "exit"
            
            # 상태 캐시 업데이트
            self.last_access_state[card_id] = entry_type
            
            return {
                "access": True,
                "entry_type": entry_type,
                "employee_name": employee.get("name"),
                "employee_id": employee.get("id"),
                "department": employee.get("department")
            }
        
        except Exception as e:
            logger.error(f"출입 권한 확인 중 오류: {str(e)}")
            return {
                "access": False,
                "reason": "system_error"
            }
    
    # ==== 출입 기록 조회 ====
    def get_access_logs(self, date: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """특정 날짜의 출입 기록을 조회합니다."""
        # 날짜 지정이 없으면 오늘 날짜 사용
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # DB 연결 확인
        if not self.db_helper:
            logger.warning("DB 연결 없음 - 출입 기록 조회 불가")
            return []
        
        try:
            # DB에서 출입 기록 조회
            logs = self.db_helper.get_access_logs(date, limit)
            return logs
        except Exception as e:
            logger.error(f"출입 기록 조회 중 오류: {str(e)}")
            return []
    
    # ==== 직원 정보 조회 ====
    def get_employee_info(self, card_id: str) -> Dict[str, Any]:
        """카드 ID로 직원 정보를 조회합니다."""
        # DB 연결 확인
        if not self.db_helper:
            logger.warning("DB 연결 없음 - 직원 정보 조회 불가")
            return {}
        
        try:
            # DB에서 직원 정보 조회
            employee = self.db_helper.get_employee_by_card(card_id)
            
            if not employee:
                return {}
            
            return employee
        except Exception as e:
            logger.error(f"직원 정보 조회 중 오류: {str(e)}")
            return {}
    
    # ==== 출입 경고 기록 ====
    def log_access_warning(self, card_id: str, reason: str) -> bool:
        """출입 경고 상황을 기록합니다."""
        # DB 연결 확인
        if not self.db_helper:
            logger.warning("DB 연결 없음 - 출입 경고 기록 불가")
            return False
        
        try:
            # DB에 경고 기록 저장
            self.db_helper.save_access_warning(card_id, reason)
            logger.warning(f"출입 경고 기록: {card_id}, 사유: {reason}")
            return True
        except Exception as e:
            logger.error(f"출입 경고 기록 중 오류: {str(e)}")
            return False
    
    # ==== 출입 상태 초기화 ====
    def reset_daily_status(self):
        """일일 출입 상태를 초기화합니다."""
        # 상태 캐시 초기화
        self.last_access_state = {}
        
        # 미등록 시도 횟수 초기화
        self.unregistered_attempts = {}
        
        logger.info("일일 출입 상태 초기화 완료")