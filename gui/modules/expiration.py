import sys
import datetime
import logging
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic

from modules.base_page import BasePage
from modules.data_manager import DataManager
from modules.error_handler import ErrorHandler
from modules.expiration_item_custom import ExpirationItemCustom

# 로깅 설정
logger = logging.getLogger(__name__)

class ExpirationPage(BasePage):
    """유통기한 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None, data_manager=None):
        """
        유통기한 관리 페이지 초기화
        
        Args:
            parent: 부모 위젯
            data_manager: 데이터 관리자 객체 (의존성 주입)
        """
        super().__init__(parent)
        self.page_name = "유통기한 관리"  # 기본 클래스 속성 설정
        
        # UI 로드
        uic.loadUi("ui/widgets/expiration.ui", self)
        
        # 데이터 관리자 설정 (의존성 주입 패턴 적용)
        self.data_manager = data_manager if data_manager else DataManager.get_instance()
        self.set_data_manager(self.data_manager)  # 부모 클래스 메서드 호출
        
        # 날짜 범위 UI 숨기기
        self.horizontalLayoutWidget.hide()
        
        # 더 많은 항목 버튼 숨기기
        if hasattr(self, 'btnMoreItems'):
            self.btnMoreItems.hide()
        
        # 유통기한 아이템 컨테이너 설정
        self.setup_scroll_layout()
        
        # 아이템 데이터 목록
        self.expiry_items = []
        
        # 데이터 변경 이벤트 연결
        self.connect_data_signals()
        
        # 초기 데이터 로드
        self.search_expired_items()
        
        logger.info("유통기한 관리 페이지 초기화 완료")

        # 헤더 레이블 폰트 설정
        headers = [self.label]
        for label in headers:
            font = label.font()
            font.setBold(True)
            font.setWeight(QFont.Weight.Bold)
            label.setFont(font)
            
        # 스크롤 영역 위치 조정 (날짜 필터 숨겼으므로)
        self.scrollArea.setGeometry(10, 50, 841, 561)
    
    def connect_data_signals(self):
        """데이터 변경 이벤트 연결"""
        self.data_manager.expiry_data_changed.connect(self.on_expiry_data_changed)
        self.data_manager.notification_added.connect(self.on_notification)
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 유통기한 관련 알림인 경우 처리
        if "유통기한" in message or "만료" in message or "경과" in message:
            # 알림만 처리하고 데이터 업데이트는 이벤트에 의해 처리됨
            pass
    
    def on_expiry_data_changed(self):
        """유통기한 데이터 변경 이벤트 처리"""
        # 데이터가 변경되었으므로 UI 갱신
        self.search_expired_items()
    
    def setup_scroll_layout(self):
        """스크롤 영역 레이아웃 설정"""
        self.scroll_layout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(20)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    
    def clear_items_layout(self):
        """기존 아이템 위젯을 모두 제거합니다."""
        try:
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
        except Exception as e:
            logger.error(f"아이템 레이아웃 초기화 오류: {str(e)}")
            
    def display_items(self, items):
        """아이템 목록을 UI에 표시합니다."""
        try:
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
        except Exception as e:
            logger.error(f"아이템 표시 오류: {str(e)}")
            self.show_status_message("아이템 표시 오류", is_error=True)

    def search_expired_items(self):
        """유통기한 경과/임박 물품을 검색합니다."""
        try:
            # 날짜 범위 없이 데이터 로드
            self.fetch_expiry_items()
        except Exception as e:
            logger.error(f"유통기한 검색 오류: {str(e)}")
            self.handle_data_fetch_error("유통기한 검색", str(e))

    def fetch_expiry_items(self):
        """유통기한 임박/경과 물품 데이터를 요청합니다."""
        try:
            # 기존 데이터 초기화
            self.clear_items_layout()
            
            # 서버 연결 상태 확인
            if not self.data_manager.is_server_connected():
                self.show_connection_error_message()
                return
                
            # 데이터 매니저를 통해 API 요청
            try:
                # 유통기한 경과 항목 가져오기
                expired_items = self.data_manager._server_connection.get_expired_items()
                
                # 유통기한 경고 항목 가져오기 (2일 이내)
                alert_items = self.data_manager._server_connection.get_expiry_alerts(days=2)
                
                # 데이터 병합 및 가공
                items = []
                
                # 경과 항목 처리
                if expired_items and expired_items.get("success", False):
                    for item in expired_items.get("data", []):
                        # API에서 반환된 항목을 ExpirationItemCustom에 맞게 변환
                        transformed_item = self.transform_api_item(item, True)
                        items.append(transformed_item)
                
                # 경고 항목 처리
                if alert_items and alert_items.get("success", False):
                    for item in alert_items.get("data", []):
                        # 이미 경과 항목에 있는 경우 건너뛰기
                        if any(i.get("id") == item.get("id") for i in items):
                            continue
                        
                        # API에서 반환된 항목을 ExpirationItemCustom에 맞게 변환
                        transformed_item = self.transform_api_item(item, False)
                        items.append(transformed_item)
                
                # 항목 표시
                self.display_items(items)
                logger.info(f"유통기한 관련 항목 {len(items)}건 로드 완료")
                
                # 성공 상태 메시지 표시
                self.show_status_message(f"유통기한 관련 항목 {len(items)}건 로드 완료", is_success=True)
                
            except Exception as e:
                logger.error(f"유통기한 데이터 가져오기 오류: {str(e)}")
                self.handle_api_exception("유통기한 데이터 조회", e)
                
                # 오류 메시지 표시
                error_label = QLabel("데이터를 가져올 수 없습니다. 연결 상태를 확인하세요.")
                error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                error_label.setStyleSheet("font-size: 14px; color: #F44336;")
                self.scroll_layout.addWidget(error_label)
            
            # 스크롤 영역 크기 조정
            self.scrollAreaWidgetContents.updateGeometry()
            
        except Exception as e:
            logger.error(f"유통기한 물품 로드 오류: {e}")
            self.handle_data_fetch_error("유통기한 물품 로드", str(e))
            # 에러 발생 시 빈 목록 표시
            self.display_items([])
    
    def transform_api_item(self, api_item, is_expired):
        """API 응답 항목을 ExpirationItemCustom에 맞는 형식으로 변환"""
        # 필요한 필드 추출 및 변환
        item = {
            "id": api_item.get("id", ""),
            "name": api_item.get("name", ""),  # product_name이 아닌 name 필드 사용
            "exp": api_item.get("exp", ""),
            "days_remaining": api_item.get("days_remaining", None),  # 서버에서 계산된 days_remaining 포함
            "quantity": api_item.get("quantity", 1),
            "location": f"{api_item.get('warehouse_id', '')}창고",
            "is_expired": is_expired
        }
        return item
    
    def show_connection_error_message(self):
        """서버 연결 오류 메시지를 화면에 표시"""
        error_label = QLabel("서버에 연결되어 있지 않습니다. 서버 연결이 필요합니다.")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("font-size: 14px; color: #F44336;")
        self.scroll_layout.addWidget(error_label)
    
    # === BasePage 메서드 오버라이드 ===
    def on_server_connected(self):
        """서버 연결 성공 시 처리 - 기본 클래스 메서드 오버라이드"""
        self.search_expired_items()  # 데이터 새로고침
        self.show_status_message("서버 연결 성공, 데이터를 로드합니다.", is_success=True)
        logger.info("서버 연결 성공")
    
    def on_server_disconnected(self):
        """서버 연결 실패 시 처리 - 기본 클래스 메서드 오버라이드"""
        self.clear_items_layout()
        # 연결 오류 메시지 표시
        error_label = QLabel("서버 연결이 끊어졌습니다. 유통기한 데이터를 가져올 수 없습니다.")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("font-size: 14px; color: #F44336;")
        self.scroll_layout.addWidget(error_label)
        
        self.show_status_message("서버 연결 끊김, 데이터를 가져올 수 없습니다.", is_error=True)
        logger.warning("서버 연결 실패")