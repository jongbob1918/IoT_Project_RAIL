import sys
import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic

from modules.data_manager import DataManager
from modules.expiration_item_custom import ExpirationItemCustom

class ExpirationPage(QWidget):
    """유통기한 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 로드
        uic.loadUi("ui/widgets/expiration.ui", self)
        
        # 데이터 관리자 가져오기
        self.data_manager = DataManager.get_instance()
        
        # 날짜 범위 초기 설정 (현재 날짜 기준 전/후 30일)
        today = QDate.currentDate()
        self.dateFrom.setDate(today.addDays(-30))
        self.dateTo.setDate(today.addDays(30))
        
        # 검색 버튼 이벤트 연결
        self.btnSearch.clicked.connect(self.search_expired_items)
        
        # 더 많은 항목 버튼 숨기기
        if hasattr(self, 'btnMoreItems'):
            self.btnMoreItems.hide()
        
        # 유통기한 아이템 컨테이너 설정
        self.scroll_layout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(20)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 아이템 데이터 목록
        self.expiry_items = []
        
        # 버튼 스타일 설정
        self.setup_button_styles()
        
        # 타이머 설정 (데이터 갱신)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_for_updates)
        self.update_timer.start(10000)  # 10초마다 업데이트 확인
        
        # 데이터 변경 이벤트 연결
        self.data_manager.expiry_data_changed.connect(self.check_for_updates)
        self.data_manager.notification_added.connect(self.on_notification)
        
        # 초기 데이터 로드
        self.search_expired_items()
    
    def setup_button_styles(self):
        """버튼 스타일 설정"""
        # 검색 버튼 스타일
        self.btnSearch.setStyleSheet("""
            QPushButton {
                background-color: #4285F4; 
                color: white; 
                border-radius: 3px; 
                padding: 5px;
            }
            QPushButton:pressed {
                background-color: #3367D6;
                padding-left: 4px;
                padding-top: 4px;
            }
        """)
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 유통기한 관련 알림인 경우 처리
        if "유통기한" in message or "만료" in message or "경과" in message:
            self.check_for_updates()
    
    def check_for_updates(self):
        """데이터 업데이트 확인"""
        # 유통기한 데이터 확인
        expiry_data = self.data_manager.get_expiry_data()
        
        # 유통기한 경과 또는 임박 상품이 있는 경우 화면 갱신
        if expiry_data['over'] > 0 or expiry_data['soon'] > 0:
            self.search_expired_items()
    
    def clear_items_layout(self):
        """기존 아이템 위젯을 모두 제거합니다."""
        # 레이아웃의 모든 위젯 제거
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 중첩된 레이아웃 제거
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
            
    def display_items(self, items):
        """아이템 목록을 UI에 표시합니다."""
        if not items:
            # 결과 없음 메시지
            empty_label = QLabel("검색 조건에 맞는 항목이 없습니다.")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("font-size: 14px; color: #757575;")
            self.scroll_layout.addWidget(empty_label)
            return
        
        # 왼쪽 열과 오른쪽 열 위젯을 담을 레이아웃 생성
        for i in range(0, len(items), 2):
            # 각 행에 대한 컨테이너 위젯 생성
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(15)
            
            # 왼쪽 항목 (커스텀 구현 클래스 사용)
            left_item = ExpirationItemCustom(items[i])
            row_layout.addWidget(left_item)
            
            # 오른쪽 항목 (존재하는 경우)
            if i + 1 < len(items):
                right_item = ExpirationItemCustom(items[i + 1])
                row_layout.addWidget(right_item)
            else:
                # 빈 공간 추가
                spacer = QSpacerItem(380, 10, QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
                row_layout.addItem(spacer)
            
            # 메인 레이아웃에 행 위젯 추가
            self.scroll_layout.addWidget(row_widget)

    def search_expired_items(self):
        """날짜 범위 내의 유통기한 경과/임박 물품을 검색합니다."""
        # 날짜 범위 가져오기
        from_date = self.dateFrom.date().toString("yyyy-MM-dd")
        to_date = self.dateTo.date().toString("yyyy-MM-dd")
        
        # 데이터 로드
        self.fetch_expiry_items(from_date, to_date)

    def fetch_expiry_items(self, from_date, to_date):
        """유통기한 임박/경과 물품 데이터를 요청합니다."""
        try:
            # 기존 데이터 초기화
            self.clear_items_layout()
            
            # 서버 연결 객체 가져오기
            server_conn = self.data_manager._server_connection
            
            if server_conn and server_conn.is_connected:
                # 서버에 API 요청
                try:
                    # 실제 구현에서는 API 호출하여 데이터 받아오기
                    # 예: items = server_conn.get_expiry_items(from_date, to_date)
                    
                    # 빈 데이터로 표시 (실제 구현에서는 제거)
                    self.display_items([])
                except Exception as e:
                    print(f"유통기한 데이터 가져오기 오류: {str(e)}")
                    self.display_items([])
            else:
                # 서버 연결이 없는 경우 빈 데이터 표시
                self.display_items([])
            
            # 스크롤 영역 크기 조정
            self.scrollAreaWidgetContents.updateGeometry()
            
        except Exception as e:
            print(f"유통기한 물품 로드 오류: {e}")
            QMessageBox.warning(self, "오류", "데이터를 불러오는 중 오류가 발생했습니다.")
    
    def onConnectionStatusChanged(self, connected):
        """서버 연결 상태 변경 시 호출되는 메서드"""
        if connected:
            # 연결 성공 시 처리
            self.search_expired_items()  # 데이터 새로고침
        else:
            # 연결 실패 시 처리
            self.clear_items_layout()
            self.display_items([])  # 빈 데이터 표시