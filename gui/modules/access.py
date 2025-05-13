import sys
import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic

from modules.data_manager import DataManager

class AccessPage(QWidget):
    """출입 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 로드
        uic.loadUi("ui/widgets/access.ui", self)
        
        # 데이터 관리자 가져오기
        self.data_manager = DataManager.get_instance()
        
        # 날짜 콤보박스 설정
        self.setup_date_combo()
        
        # 기본 UI 설정
        self.setup_ui()
        
        # 테이블 초기화
        self.access_logs = []
        self.filtered_logs = []  # 날짜로 필터링된 로그
        self.page = 1
        self.items_per_page = 20
        
        # 타이머 설정 (데이터 갱신)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.fetch_access_data)
        self.update_timer.start(5000)  # 5초마다 업데이트
        
        # 데이터 변경 이벤트 연결
        self.data_manager.notification_added.connect(self.on_notification)
        
        # 날짜 변경 이벤트 연결
        if hasattr(self, 'combo_date'):
            self.combo_date.currentIndexChanged.connect(self.on_date_changed)
    
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
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 출입 관련 알림인 경우 처리
        if "출입" in message or "입장" in message or "퇴장" in message:
            self.fetch_access_data()
    
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
            
            if server_conn and server_conn.is_connected:
                # ServerConnection 객체를 통해 API 호출
                try:
                    # 서버에서 출입 로그 데이터 가져오기
                    # 서버 연결 객체에 get_access_logs 메서드가 있어야 함
                    # 없다면 아래 코드 추가 필요
                    self.access_logs = server_conn.get_access_logs()
                    
                    # 날짜 필터링 적용
                    self.filter_by_date()
                    
                    # 테이블 업데이트
                    self.update_table()
                except Exception as e:
                    print(f"출입 데이터 가져오기 오류: {str(e)}")
            else:
                # 서버 연결이 없는 경우
                if hasattr(self, 'lbl_status'):
                    self.lbl_status.setText("서버 연결 상태: 연결 안됨")
                    self.lbl_status.setStyleSheet("color: red;")
        except Exception as e:
            print(f"fetch_access_data 실행 중 오류: {str(e)}")
    
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
    
    def onConnectionStatusChanged(self, connected):
        """서버 연결 상태 변경 시 호출되는 메서드"""
        if connected:
            # 연결 성공 시 처리
            self.fetch_access_data()  # 데이터 새로고침
            if hasattr(self, 'lbl_status'):
                self.lbl_status.setText("서버 연결 상태: 연결됨")
                self.lbl_status.setStyleSheet("color: green;")
        else:
            # 연결 실패 시 처리
            if hasattr(self, 'lbl_status'):
                self.lbl_status.setText("서버 연결 상태: 연결 안됨")
                self.lbl_status.setStyleSheet("color: red;")