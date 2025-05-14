import sys
import datetime
import logging
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic

from modules.base_page import BasePage
from modules.data_manager import DataManager
from modules.error_handler import ErrorHandler  # 새로 추가할 예외 처리 모듈

# 로깅 설정
logger = logging.getLogger(__name__)

class AccessPage(BasePage):  # BasePage 상속으로 변경
    """출입 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None, data_manager=None):
        """
        출입 관리 페이지 초기화
        
        Args:
            parent: 부모 위젯
            data_manager: 데이터 관리자 객체 (의존성 주입)
        """
        super().__init__(parent)
        self.page_name = "출입 관리"  # 기본 클래스 속성 설정
        
        # UI 로드
        uic.loadUi("ui/widgets/access.ui", self)
        
        # 데이터 관리자 설정 (의존성 주입 패턴 적용)
        self.data_manager = data_manager if data_manager else DataManager.get_instance()
        self.set_data_manager(self.data_manager)  # 부모 클래스 메서드 호출
        
        # 객체 초기화
        self.init_data()
        
        # 날짜 콤보박스 설정
        self.setup_date_combo()
        
        # 기본 UI 설정
        self.setup_ui()
        
        # 데이터 변경 이벤트 연결
        self.connect_data_signals()
        
        # 상태 메시지 초기화
        self.show_status_message("서버 연결 대기 중...", is_info=True)
        
        logger.info("출입 관리 페이지 초기화 완료")
    
    def init_data(self):
        """데이터 초기화"""
        self.access_logs = []
        self.filtered_logs = []  # 날짜로 필터링된 로그
        self.page = 1
        self.items_per_page = 20
        self.last_update_time = None  # 마지막 데이터 업데이트 시간
    
    def setup_date_combo(self):
        """날짜 콤보박스 설정"""
        if hasattr(self, 'combo_date'):
            self.combo_date.clear()
            
            # 오늘 날짜
            today = datetime.date.today()
            
            # 최근 7일 날짜 추가 (오늘 포함)
            self.combo_date.addItem("전체 기간", "all")
            
            for i in range(7):
                date = today - datetime.timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                display_str = date.strftime("%Y년 %m월 %d일")
                
                # 오늘인 경우 표시 방식 변경
                if i == 0:
                    display_str += " (오늘)"
                
                self.combo_date.addItem(display_str, date_str)
            
            # 기본값 설정 (오늘)
            self.combo_date.setCurrentIndex(1)  # 오늘 날짜 선택
    
    def setup_ui(self):
        """UI 기본 설정"""
        self.table_access.setColumnWidth(0, 80)   # 직원ID
        self.table_access.setColumnWidth(1, 100)  # 이름
        self.table_access.setColumnWidth(2, 120)  # 부서
        self.table_access.setColumnWidth(3, 150)  # 입장시간
        self.table_access.setColumnWidth(4, 150)  # 퇴장시간
        
        # 페이지 변경 버튼 이벤트 연결
        if hasattr(self, 'btn_prev'):
            self.btn_prev.clicked.connect(self.prev_page)
        if hasattr(self, 'btn_next'):
            self.btn_next.clicked.connect(self.next_page)
        
        # 출입문 제어 버튼 이벤트 연결
        if hasattr(self, 'btn_open_door'):
            self.btn_open_door.clicked.connect(self.open_door)
        if hasattr(self, 'btn_close_door'):
            self.btn_close_door.clicked.connect(self.close_door)
    
    def connect_data_signals(self):
        """데이터 변경 이벤트 연결"""
        # 알림 이벤트 연결
        self.data_manager.notification_added.connect(self.on_notification)
        
        # 날짜 변경 이벤트 연결
        if hasattr(self, 'combo_date'):
            self.combo_date.currentIndexChanged.connect(self.on_date_changed)
        
        # 출입 로그 변경 이벤트 연결
        if hasattr(self.data_manager, 'access_logs_changed'):
            self.data_manager.access_logs_changed.connect(self.on_access_logs_changed)
        
        # 서버 이벤트 연결
        if hasattr(self.data_manager, '_server_connection') and hasattr(self.data_manager._server_connection, 'eventReceived'):
            self.data_manager._server_connection.eventReceived.connect(self.handle_server_event)
    
    def handle_server_event(self, category, action, payload):
        """서버 이벤트 처리"""
        # 출입 관련 이벤트일 경우에만 처리
        if category == "access":
            self.handleAccessEvent(action, payload)
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 출입 관련 알림인 경우 처리
        if "출입" in message or "입장" in message or "퇴장" in message:
            # 중복 요청 방지를 위해 데이터 매니저에게 갱신 요청
            if hasattr(self.data_manager, 'refresh_access_logs'):
                self.data_manager.refresh_access_logs()
    
    def on_access_logs_changed(self):
        """출입 로그 데이터 변경 시 호출"""
        self.access_logs = self.data_manager.get_access_logs()
        self.filter_by_date()
        self.update_table()
        
        # 상태 메시지 업데이트
        if hasattr(self, 'lbl_status'):
            self.lbl_status.setText(f"출입 로그 {len(self.access_logs)}건 로드됨")
            self.lbl_status.setStyleSheet("color: green;")
    
    def on_date_changed(self, index):
        """날짜 선택 변경 시 처리"""
        self.filter_by_date()
        self.page = 1  # 페이지 초기화
        self.update_table()
    
    def filter_by_date(self):
        """선택된 날짜로 로그 필터링"""
        if not hasattr(self, 'combo_date') or len(self.access_logs) == 0:
            self.filtered_logs = self.access_logs.copy()
            return
        
        selected_date_value = self.combo_date.currentData()
        
        # 전체 기간 선택 시
        if selected_date_value == "all":
            self.filtered_logs = self.access_logs.copy()
            return
            
        # 특정 날짜 선택 시
        self.filtered_logs = []
        for log in self.access_logs:
            entry_time = log.get("entry_time", "")
            if entry_time.startswith(selected_date_value):
                self.filtered_logs.append(log)
    
    def update_table(self):
        """테이블에 데이터 표시"""
        # 테이블 초기화
        self.table_access.setRowCount(0)
        
        # 현재 페이지에 해당하는 데이터 계산
        start_idx = (self.page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        
        # 필터링된 접근 로그 중 페이징 처리
        if self.filtered_logs and len(self.filtered_logs) > 0:
            current_page_data = self.filtered_logs[start_idx:end_idx]
            
            # 테이블에 데이터 추가
            for row, log in enumerate(current_page_data):
                self.table_access.insertRow(row)
                self.table_access.setItem(row, 0, QTableWidgetItem(log.get("uid", "")))
                self.table_access.setItem(row, 1, QTableWidgetItem(log.get("name", "")))
                self.table_access.setItem(row, 2, QTableWidgetItem(log.get("department", "")))
                self.table_access.setItem(row, 3, QTableWidgetItem(log.get("entry_time", "")))
                self.table_access.setItem(row, 4, QTableWidgetItem(log.get("exit_time", "")))
        
        # 페이지 정보 업데이트 (페이지 표시 라벨이 있는 경우)
        if hasattr(self, 'lbl_page'):
            total_pages = max(1, (len(self.filtered_logs) + self.items_per_page - 1) // self.items_per_page)
            self.lbl_page.setText(f"{self.page} / {total_pages}")
            
            # 페이지 이동 버튼 활성화/비활성화
            if hasattr(self, 'btn_prev'):
                self.btn_prev.setEnabled(self.page > 1)
            if hasattr(self, 'btn_next'):
                self.btn_next.setEnabled(self.page < total_pages)
        
        # 레코드 수 표시 (레코드 수 라벨이 있는 경우)
        if hasattr(self, 'lbl_records'):
            self.lbl_records.setText(f"총 {len(self.filtered_logs)}건")
            
        logger.debug(f"출입 테이블 업데이트: {len(self.filtered_logs)}건 중 {min(start_idx+1, len(self.filtered_logs)) if self.filtered_logs else 0}-{min(end_idx, len(self.filtered_logs))}번째 항목 표시")
    
    def prev_page(self):
        """이전 페이지 이동"""
        if self.page > 1:
            self.page -= 1
            self.update_table()
    
    def next_page(self):
        """다음 페이지 이동"""
        total_pages = max(1, (len(self.filtered_logs) + self.items_per_page - 1) // self.items_per_page)
        if self.page < total_pages:
            self.page += 1
            self.update_table()
    
    def handleAccessEvent(self, action, payload):
        """서버로부터 출입 이벤트 처리"""
        # 새로운 출입 이벤트가 발생하면 로그 갱신
        if action in ["entry", "exit"]:
            # 중앙 데이터 매니저에서 출입 로그를 갱신
            if hasattr(self.data_manager, 'refresh_access_logs'):
                self.data_manager.refresh_access_logs()
            
            # 알림 추가
            if action == "entry":
                message = f"{payload.get('name', '직원')}님 입장"
                self.data_manager.add_notification(message)
            elif action == "exit":
                message = f"{payload.get('name', '직원')}님 퇴장"
                self.data_manager.add_notification(message)
            
            logger.info(f"출입 이벤트: {action} - {payload.get('name', '알 수 없음')}")
    
    def open_door(self):
        """출입문 열기 버튼 이벤트 핸들러"""
        if not self.data_manager.is_server_connected():
            self.handle_connection_error("출입문 열기 실패")
            return
            
        try:
            # 출입문 열기 API 요청 - 데이터 매니저를 통해 수행
            response = self.data_manager.open_door()
            
            if response and response.get("success", False):
                # 성공 메시지 표시
                ErrorHandler.show_info_message("출입문 제어", "출입문이 열렸습니다.")
                
                # 알림 추가
                self.data_manager.add_notification("출입문이 열렸습니다.")
                
                logger.info("출입문 열기 요청 성공")
            else:
                # 실패 메시지 표시
                error_msg = response.get("error", "알 수 없는 오류가 발생했습니다.")
                self.handle_api_error("출입문 열기 실패", error_msg)
                
        except Exception as e:
            # 예외 처리
            self.handle_api_exception("출입문 열기 요청 오류", e)
    
    def close_door(self):
        """출입문 닫기 버튼 이벤트 핸들러"""
        if not self.data_manager.is_server_connected():
            self.handle_connection_error("출입문 닫기 실패")
            return
            
        try:
            # 출입문 닫기 API 요청 - 데이터 매니저를 통해 수행
            response = self.data_manager.close_door()
            
            if response and response.get("success", False):
                # 성공 메시지 표시
                ErrorHandler.show_info_message("출입문 제어", "출입문이 닫혔습니다.")
                
                # 알림 추가
                self.data_manager.add_notification("출입문이 닫혔습니다.")
                
                logger.info("출입문 닫기 요청 성공")
            else:
                # 실패 메시지 표시
                error_msg = response.get("error", "알 수 없는 오류가 발생했습니다.")
                self.handle_api_error("출입문 닫기 실패", error_msg)
                
        except Exception as e:
            # 예외 처리
            self.handle_api_exception("출입문 닫기 요청 오류", e)
    
    # === BasePage 메서드 오버라이드 ===
    def on_server_connected(self):
        """서버 연결 성공 시 처리 - 기본 클래스 메서드 오버라이드"""
        # 데이터 매니저를 통해 데이터가 자동으로 갱신됨
        self.show_status_message("서버 연결 상태: 연결됨", is_success=True)
        logger.info("서버 연결 성공")
    
    def on_server_disconnected(self):
        """서버 연결 실패 시 처리 - 기본 클래스 메서드 오버라이드"""
        self.show_status_message("서버 연결 상태: 연결 안됨", is_error=True)
        
        # 테이블 초기화
        self.access_logs = []
        self.filtered_logs = []
        self.update_table()
            
        logger.warning("서버 연결 실패")