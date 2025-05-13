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
        
        # 타이머 설정 (데이터 갱신)
        self.setup_update_timer()
        
        # 데이터 변경 이벤트 연결
        self.connect_data_signals()
        
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
        
        # 상태 메시지 초기화
        self.show_status_message("서버 연결 대기 중...", is_info=True)
    
    def setup_update_timer(self):
        """타이머 설정"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_for_updates)
        self.update_timer.start(5000)  # 5초마다 업데이트
    
    def connect_data_signals(self):
        """데이터 변경 이벤트 연결"""
        self.data_manager.notification_added.connect(self.on_notification)
        
        # 날짜 변경 이벤트 연결
        if hasattr(self, 'combo_date'):
            self.combo_date.currentIndexChanged.connect(self.on_date_changed)
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 출입 관련 알림인 경우 처리
        if "출입" in message or "입장" in message or "퇴장" in message:
            self.check_for_updates()
    
    def check_for_updates(self):
        """데이터 업데이트 필요성 확인 및 갱신"""
        # 연결 상태 확인
        if not self.is_server_connected():
            return
            
        # 마지막 업데이트 이후 충분한 시간이 지났는지 확인 (중복 요청 방지)
        current_time = datetime.datetime.now()
        if (self.last_update_time is None or 
            (current_time - self.last_update_time).total_seconds() >= 3):  # 3초 이상 경과
            self.fetch_access_data()
            self.last_update_time = current_time
    
    def is_server_connected(self):
        """서버 연결 상태 확인"""
        server_conn = self.data_manager._server_connection
        return server_conn and server_conn.is_connected
    
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
    
    def fetch_access_data(self):
        """서버에서 출입 데이터 가져오기"""
        try:
            # 서버 연결 객체 가져오기
            server_conn = self.data_manager._server_connection
            
            if not self.is_server_connected():
                self.handle_connection_error("서버 연결 안됨")
                return
                
            try:
                # 서버에서 출입 로그 데이터 가져오기
                response = server_conn.get_access_logs()
                
                if response and response.get("success", False):
                    # 데이터 변환 및 저장
                    self.access_logs = response.get("logs", [])
                    logger.info(f"출입 로그 {len(self.access_logs)}건 로드 완료")
                    
                    # 상태 메시지 업데이트
                    self.show_status_message(f"출입 로그 {len(self.access_logs)}건 로드됨", is_success=True)
                else:
                    # 실패 처리
                    error_msg = response.get("error", "서버 응답 오류")
                    logger.warning(f"출입 로그 가져오기 실패: {error_msg}")
                    self.handle_api_error("출입 로그 조회 실패", error_msg)
            
            except Exception as e:
                # API 호출 예외 처리
                self.handle_api_exception("출입 데이터 가져오기 오류", e)
                
            # 날짜 필터링 적용 및 테이블 업데이트
            self.filter_by_date()
            self.update_table()
            
        except Exception as e:
            # 일반 예외 처리
            logger.error(f"fetch_access_data 실행 중 오류: {str(e)}")
            ErrorHandler.show_error_message("데이터 처리 오류", f"출입 데이터 처리 중 오류가 발생했습니다: {str(e)}")
    
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
            # 출입 로그 갱신
            self.check_for_updates()
            
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
        if not self.is_server_connected():
            self.handle_connection_error("출입문 열기 실패")
            return
            
        try:
            # 출입문 열기 API 요청
            response = self.data_manager._server_connection.open_door()
            
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
        if not self.is_server_connected():
            self.handle_connection_error("출입문 닫기 실패")
            return
            
        try:
            # 출입문 닫기 API 요청
            response = self.data_manager._server_connection.close_door()
            
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
    
    # === 예외 처리 메서드 ===
    def handle_connection_error(self, context):
        """서버 연결 오류 처리"""
        logger.warning(f"{context}: 서버 연결 없음")
        self.show_status_message("서버 연결 상태: 연결 안됨", is_error=True)
        ErrorHandler.show_warning_message("서버 연결 오류", "서버에 연결되어 있지 않습니다.")
    
    def handle_api_error(self, context, error_message):
        """API 오류 처리"""
        logger.warning(f"{context}: {error_message}")
        self.show_status_message(f"오류: {error_message}", is_error=True)
        ErrorHandler.show_warning_message(context, error_message)
    
    def handle_api_exception(self, context, exception):
        """API 예외 처리"""
        logger.error(f"{context}: {str(exception)}")
        self.show_status_message(f"오류: {str(exception)}", is_error=True)
        ErrorHandler.show_error_message(context, f"{context}가 발생했습니다: {str(exception)}")
    
    # === BasePage 메서드 오버라이드 ===
    def on_server_connected(self):
        """서버 연결 성공 시 처리 - 기본 클래스 메서드 오버라이드"""
        self.fetch_access_data()  # 데이터 새로고침
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
    
    def show_status_message(self, message, is_error=False, is_success=False, is_info=False):
        """상태 메시지 표시 (라벨이 있는 경우)"""
        if hasattr(self, 'lbl_status'):
            self.lbl_status.setText(message)
            
            if is_error:
                self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
            elif is_success:
                self.lbl_status.setStyleSheet("color: green; font-weight: bold;")
            elif is_info:
                self.lbl_status.setStyleSheet("color: blue;")
            else:
                self.lbl_status.setStyleSheet("")