import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import json
import logging

from modules.base_page import BasePage
from modules.data_manager import DataManager
from modules.error_handler import ErrorHandler

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# 로깅 설정
logger = logging.getLogger(__name__)

class ChartFrame(QWidget):
    """차트를 표시하는 위젯 클래스"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        
        # 데이터 관리자
        self.data_manager = data_manager
        
        # 레이아웃 설정
        self.layout = QVBoxLayout(self)
        
        # matplotlib Figure 생성
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        
        # 데이터 업데이트 버튼
        self.btn_update = QPushButton("차트 업데이트")
        self.btn_update.clicked.connect(self.update_chart)
        self.layout.addWidget(self.btn_update)
        
        # 초기 차트 그리기
        self.update_chart()
        
        logger.info("재고 차트 프레임 초기화 완료")
    
    def update_chart(self):
        """창고별 물품 비율 파이 차트 업데이트"""
        try:
            # 창고별 물품 분포 데이터 가져오기
            warehouse_data = self.get_warehouse_distribution()
            
            # Figure 초기화
            self.figure.clear()
            
            # 서브플롯 추가 및 파이 차트 그리기
            ax = self.figure.add_subplot(111)
            
            # 파이 차트 데이터 및 레이블
            labels = list(warehouse_data.keys())
            sizes = list(warehouse_data.values())
            colors = ['#4285F4', '#34A853', '#FBBC05', '#EA4335']
            
            # 파이 차트 그리기
            patches, texts, autotexts = ax.pie(
                sizes, 
                labels=labels, 
                colors=colors,
                autopct='%1.1f%%',
                shadow=False, 
                startangle=90
            )
            
            # 글자 색상 설정
            for text in texts:
                text.set_color('black')
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(9)
            
            # 원 모양 유지
            ax.axis('equal')
            
            # 제목 설정
            ax.set_title('창고별 물품 비율')
            
            # 캔버스 업데이트
            self.canvas.draw()
            
            logger.debug("재고 분포 차트 업데이트 완료")
        except Exception as e:
            logger.error(f"차트 업데이트 오류: {str(e)}")
    
    def get_warehouse_distribution(self):
        """창고별 물품 분포 데이터 가져오기"""
        try:
            # 실제 데이터 가져오기 (data_manager 사용)
            if self.data_manager:
                warehouse_data = self.data_manager.get_warehouse_data()
                distribution = {}
                
                for wh_id, data in warehouse_data.items():
                    # 창고 이름과 물품 수량으로 변환
                    distribution[f"{self.get_warehouse_name(wh_id)} ({wh_id})"] = data["used"]
                
                # 데이터가 있으면 반환
                if distribution and sum(distribution.values()) > 0:
                    return distribution
        except Exception as e:
            logger.error(f"창고별 물품 분포 데이터 가져오기 오류: {str(e)}")
        
        # 서버 연결이 없거나 데이터가 없는 경우
        return {"데이터 없음": 1}
    
    def get_warehouse_name(self, warehouse_id):
        """창고 ID로부터 이름 반환"""
        names = {
            "A": "냉동 창고",
            "B": "냉장 창고",
            "C": "상온 창고"
        }
        return names.get(warehouse_id, f"창고 {warehouse_id}")

class InventoryPage(BasePage):
    """재고 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None, data_manager=None):
        """
        재고 관리 페이지 초기화
        
        Args:
            parent: 부모 위젯
            data_manager: 데이터 관리자 객체 (의존성 주입)
        """
        super().__init__(parent)
        self.page_name = "재고 관리"  # 기본 클래스 속성 설정
        
        # UI 로드
        uic.loadUi("ui/widgets/inventory.ui", self)
        
        # 데이터 관리자 설정 (의존성 주입 패턴 적용)
        self.data_manager = data_manager if data_manager else DataManager.get_instance()
        self.set_data_manager(self.data_manager)  # 부모 클래스 메서드 호출
        
        # 차트 프레임 초기화
        self.init_chart_frame()
        
        # 프로그레스 바 초기화
        self.init_progress_bars()
        
        # 버튼 이벤트 연결
        self.connect_buttons()
        
        # 서버 연결 상태 표시 초기화
        self.init_status_label()
        
        # 타이머 설정 (서버 연결 상태 갱신)
        self.setup_update_timer()
        
        # 데이터 변경 이벤트 연결
        self.connect_data_signals()
        
        # 초기 서버 연결 상태 표시 업데이트
        self.update_connection_status()
        
        # 초기 창고 데이터 업데이트
        self.update_warehouse_data()
        
        logger.info("재고 관리 페이지 초기화 완료")
    
    def setup_update_timer(self):
        """타이머 설정"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_connection_status)
        self.update_timer.timeout.connect(self.update_warehouse_data)
        self.update_timer.start(5000)  # 5초마다 업데이트
    
    def connect_buttons(self):
        """버튼 이벤트 연결"""
        if hasattr(self, 'btn_inventory_list'):
            self.btn_inventory_list.clicked.connect(self.show_inventory_list)
    
    def init_status_label(self):
        """서버 연결 상태 표시 초기화"""
        if hasattr(self, 'lbl_status'):
            self.lbl_status.setText("서버 연결 상태: 연결 안됨")
            self.lbl_status.setStyleSheet("color: red;")
    
    def connect_data_signals(self):
        """데이터 변경 이벤트 연결"""
        self.data_manager.notification_added.connect(self.on_notification)
        self.data_manager.inventory_data_changed.connect(self.on_inventory_changed)
    
    def init_chart_frame(self):
        """차트 프레임 초기화"""
        try:
            # 차트 프레임이 UI에 있는지 확인
            if hasattr(self, 'chartFrame'):
                # 기존 레이아웃 제거
                if self.chartFrame.layout():
                    # 기존 레이아웃의 모든 아이템 제거
                    while self.chartFrame.layout().count():
                        item = self.chartFrame.layout().takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()
                    
                    # 기존 레이아웃 제거
                    QWidget().setLayout(self.chartFrame.layout())
                
                # 새 차트 프레임 생성 및 추가
                self.chart_widget = ChartFrame(self.chartFrame, self.data_manager)
                layout = QVBoxLayout(self.chartFrame)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(self.chart_widget)
                self.chartFrame.setLayout(layout)
        except Exception as e:
            logger.error(f"차트 프레임 초기화 오류: {str(e)}")
            self.show_status_message("차트 프레임 초기화 오류", is_error=True)

    def init_progress_bars(self):
        """프로그레스 바 초기화"""
        # 프로그레스 바 초기값 설정
        if hasattr(self, 'progressBar_A'):
            self.progressBar_A.setValue(0)
        if hasattr(self, 'progressBar_B'):
            self.progressBar_B.setValue(0)
        if hasattr(self, 'progressBar_C'):
            self.progressBar_C.setValue(0)
            
        # 레이블 초기값 설정
        if hasattr(self, 'label_a_count'):
            self.label_a_count.setText("0개 (0%)")
        if hasattr(self, 'label_b_count'):
            self.label_b_count.setText("0개 (0%)")
        if hasattr(self, 'label_c_count'):
            self.label_c_count.setText("0개 (0%)")
        if hasattr(self, 'label_total_count'):
            self.label_total_count.setText("0개")
    
    def update_warehouse_data(self):
        """창고 데이터 업데이트 (프로그레스 바 및 레이블)"""
        try:
            if not self.is_server_connected():
                return
                
            # 창고 데이터 가져오기
            warehouse_data = self.data_manager.get_warehouse_data()
            
            # 총 상품 수 계산
            total_items = 0
            
            # 각 창고별 데이터 업데이트
            for wh_id in ['A', 'B', 'C']:
                wh_data = warehouse_data.get(wh_id, {})
                used = wh_data.get("used", 0)
                capacity = wh_data.get("capacity", 100)
                
                # 프로그레스 바 업데이트
                progress_bar = getattr(self, f'progressBar_{wh_id}', None)
                if progress_bar:
                    percentage = int((used / capacity) * 100) if capacity > 0 else 0
                    progress_bar.setValue(percentage)
                
                # 레이블 업데이트
                label_count = getattr(self, f'label_{wh_id.lower()}_count', None)
                if label_count:
                    label_count.setText(f"{used}개 ({percentage}%)")
                
                # 총 개수에 추가
                total_items += used
            
            # 총 물품 수 업데이트
            if hasattr(self, 'label_total_count'):
                self.label_total_count.setText(f"{total_items}개")
                
            logger.debug("창고 데이터 업데이트 완료")
        except Exception as e:
            logger.error(f"창고 데이터 업데이트 오류: {str(e)}")
    
    def show_inventory_list(self):
        """재고 목록 팝업 표시"""
        try:
            dialog = InventoryListDialog(self, self.data_manager)
            dialog.exec()
        except Exception as e:
            logger.error(f"재고 목록 팝업 표시 오류: {str(e)}")
            self.handle_data_fetch_error("재고 목록 표시", str(e))
    
    def update_connection_status(self):
        """서버 연결 상태 업데이트"""
        try:
            if not hasattr(self, 'lbl_status'):
                return
                
            if self.is_server_connected():
                self.lbl_status.setText("서버 연결 상태: 연결됨")
                self.lbl_status.setStyleSheet("color: green;")
                
                # 서버 연결 시 차트 업데이트
                if hasattr(self, 'chart_widget'):
                    self.chart_widget.update_chart()
            else:
                self.lbl_status.setText("서버 연결 상태: 연결 안됨")
                self.lbl_status.setStyleSheet("color: red;")
        except Exception as e:
            logger.error(f"연결 상태 업데이트 오류: {str(e)}")
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 재고 관련 알림인 경우 처리
        if "입고" in message or "상품" in message or "재고" in message:
            # 차트 업데이트
            if hasattr(self, 'chart_widget'):
                self.chart_widget.update_chart()
            
            # 창고 데이터 업데이트
            self.update_warehouse_data()
    
    def on_inventory_changed(self):
        """재고 데이터 변경 시 처리"""
        # 차트 업데이트
        if hasattr(self, 'chart_widget'):
            self.chart_widget.update_chart()
        
        # 창고 데이터 업데이트
        self.update_warehouse_data()
    
    # === BasePage 메서드 오버라이드 ===
    def on_server_connected(self):
        """서버 연결 성공 시 처리 - 기본 클래스 메서드 오버라이드"""
        if hasattr(self, 'lbl_status'):
            self.lbl_status.setText("서버 연결 상태: 연결됨")
            self.lbl_status.setStyleSheet("color: green;")
        
        # 차트 업데이트
        if hasattr(self, 'chart_widget'):
            self.chart_widget.update_chart()
        
        # 창고 데이터 업데이트
        self.update_warehouse_data()
        
        self.show_status_message("서버 연결 성공", is_success=True)
        logger.info("서버 연결 성공")
    
    def on_server_disconnected(self):
        """서버 연결 실패 시 처리 - 기본 클래스 메서드 오버라이드"""
        if hasattr(self, 'lbl_status'):
            self.lbl_status.setText("서버 연결 상태: 연결 안됨")
            self.lbl_status.setStyleSheet("color: red;")
        
        self.show_status_message("서버 연결 끊김", is_error=True)
        logger.warning("서버 연결 실패")

class InventoryListDialog(QDialog):
    """재고 목록 팝업 다이얼로그"""
    
    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.setWindowTitle("재고 목록")
        self.setMinimumSize(800, 600)
        
        # 데이터 관리자
        self.data_manager = data_manager
        
        # 레이아웃 설정
        self.setup_ui()
        
        # 데이터 초기화
        self.init_data()
        
        # 초기 데이터 로드
        self.fetch_inventory_data()
        
        logger.info("재고 목록 다이얼로그 초기화 완료")
    
    def init_data(self):
        """데이터 초기화"""
        self.inventory_items = []
        self.filtered_items = []
        self.current_page = 1
        self.items_per_page = 20
    
    def setup_ui(self):
        """UI 구성"""
        main_layout = QVBoxLayout(self)
        
        # 상단 필터 영역
        filter_layout = QHBoxLayout()
        
        # 검색 필드
        search_label = QLabel("검색:")
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("상품명 또는 ID 검색")
        self.btn_search = QPushButton("검색")
        self.btn_search.clicked.connect(self.apply_search_filter)
        
        # 창고 선택 콤보박스
        warehouse_label = QLabel("창고:")
        self.combo_warehouse = QComboBox()
        self.combo_warehouse.addItem("전체", "all")
        self.combo_warehouse.addItem("냉동 창고 (A)", "A")
        self.combo_warehouse.addItem("냉장 창고 (B)", "B")
        self.combo_warehouse.addItem("상온 창고 (C)", "C")
        
        # 날짜 필터
        date_from_label = QLabel("시작일:")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy/MM/dd")
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        
        date_to_label = QLabel("종료일:")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy/MM/dd")
        self.date_to.setDate(QDate.currentDate())
        
        # 필터 리셋 버튼
        self.btn_reset = QPushButton("필터 초기화")
        self.btn_reset.clicked.connect(self.reset_search_filter)
        
        # 필터 레이아웃에 위젯 추가
        filter_layout.addWidget(search_label)
        filter_layout.addWidget(self.input_search)
        filter_layout.addWidget(self.btn_search)
        filter_layout.addWidget(warehouse_label)
        filter_layout.addWidget(self.combo_warehouse)
        filter_layout.addWidget(date_from_label)
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(date_to_label)
        filter_layout.addWidget(self.date_to)
        filter_layout.addWidget(self.btn_reset)
        
        # 테이블 위젯
        self.setup_table()
        
        # 상태 및 페이지네이션 영역
        status_layout = QHBoxLayout()
        
        # 레코드 수 표시
        self.lbl_total_records = QLabel("총 0건")
        
        # 필터 결과 표시
        self.lbl_filter_result = QLabel("")
        
        # 페이지 이동 버튼
        self.btn_prev_page = QPushButton("이전")
        self.btn_prev_page.clicked.connect(self.prev_page)
        self.btn_prev_page.setEnabled(False)
        
        self.lbl_page = QLabel("1 / 1")
        
        self.btn_next_page = QPushButton("다음")
        self.btn_next_page.clicked.connect(self.next_page)
        self.btn_next_page.setEnabled(False)
        
        # 상태 및 페이지네이션 레이아웃에 위젯 추가
        status_layout.addWidget(self.lbl_total_records)
        status_layout.addStretch()
        status_layout.addWidget(self.lbl_filter_result)
        status_layout.addStretch()
        status_layout.addWidget(self.btn_prev_page)
        status_layout.addWidget(self.lbl_page)
        status_layout.addWidget(self.btn_next_page)
        
        # 메인 레이아웃에 위젯 추가
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.table_inventory)
        main_layout.addLayout(status_layout)
        
        # 닫기 버튼
        button_layout = QHBoxLayout()
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def setup_table(self):
        """테이블 위젯 설정"""
        self.table_inventory = QTableWidget()
        self.table_inventory.setColumnCount(5)
        self.table_inventory.setHorizontalHeaderLabels(["상품아이디", "상품명", "입고일", "창고", "수량"])
        self.table_inventory.setAlternatingRowColors(True)
        self.table_inventory.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f5f5f5;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #4285F4;
                color: white;
                padding: 5px;
                border: 1px solid #ddd;
            }
        """)
        
        # 칼럼 너비 설정
        self.table_inventory.setColumnWidth(0, 120)  # 상품아이디
        self.table_inventory.setColumnWidth(1, 200)  # 상품명
        self.table_inventory.setColumnWidth(2, 120)  # 입고일
        self.table_inventory.setColumnWidth(3, 80)   # 창고
        self.table_inventory.setColumnWidth(4, 80)   # 수량
    
    def fetch_inventory_data(self):
        """서버에서 재고 데이터 가져오기"""
        try:
            # 서버 연결 확인
            if not self.is_server_connected():
                self.show_connection_error()
                return
                
            try:
                # API 호출: 재고 물품 목록 조회
                server_conn = self.data_manager._server_connection
                response = server_conn.get_inventory_items(limit=100, offset=0)
                
                if response and response.get("success", False):
                    # 데이터 가져오기 성공 - data 필드에서 아이템 리스트 추출
                    self.inventory_items = response.get("data", [])
                    logger.info(f"재고 데이터 {len(self.inventory_items)}건 로드 완료")
                else:
                    # 오류 발생 - error 객체에서 메시지 추출
                    logger.warning("재고 데이터 가져오기 실패")
                    self.inventory_items = []
                    
                    # 오류 메시지 표시
                    error_obj = response.get("error", {})
                    error_msg = error_obj.get("message", "알 수 없는 오류가 발생했습니다.")
                    self.show_api_error("데이터 로드 오류", error_msg)
            except Exception as e:
                logger.error(f"재고 API 호출 오류: {str(e)}")
                self.inventory_items = []
                
                # 오류 메시지 표시
                self.show_api_exception("API 호출 오류", e)
            
            # 필터 적용
            self.apply_search_filter()
        
        except Exception as e:
            logger.error(f"fetch_inventory_data 실행 중 오류: {str(e)}")
            self.inventory_items = []
            self.apply_search_filter()
            
            # 오류 메시지 표시
            ErrorHandler.show_error_message("오류", f"재고 데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")

        def is_server_connected(self):
            """서버 연결 상태 확인"""
            return self.data_manager and self.data_manager._server_connection and self.data_manager._server_connection.is_connected
        
        def show_connection_error(self):
            """서버 연결 오류 표시"""
            ErrorHandler.show_warning_message("서버 연결 오류", "서버에 연결되어 있지 않습니다. 서버 연결이 필요합니다.")
            self.inventory_items = []
        
        def show_api_error(self, title, message):
            """API 오류 표시"""
            ErrorHandler.show_warning_message(title, message)
        
        def show_api_exception(self, title, exception):
            """API 예외 표시"""
            ErrorHandler.show_error_message(title, f"{title} 중 오류: {str(exception)}")
        
        def apply_search_filter(self):
            """검색 및 필터 적용"""
        try:
            # 필터 조건 가져오기
            search_text = self.input_search.text().lower()
            from_date = self.date_from.date()
            to_date = self.date_to.date()
            selected_warehouse = self.combo_warehouse.currentData()
            
            # 필터링
            self.filtered_items = []
            for item in self.inventory_items:
                # 검색어 필터
                if search_text and not (
                    search_text in item.get("product_name", "").lower() or
                    search_text in item.get("sku", "").lower()
                ):
                    continue
                
                # 날짜 필터
                item_date = QDate.fromString(item.get("received_date", ""), "yyyy-MM-dd")
                if not (from_date <= item_date <= to_date):
                    continue
                
                # 창고 필터
                if selected_warehouse != "all" and item.get("warehouse", "") != selected_warehouse:
                    continue
                
                # 모든 필터 통과
                self.filtered_items.append(item)
            
            # 페이지 정보 업데이트
            self.current_page = 1
            self.update_pagination()
            
            # 테이블 업데이트
            self.update_table()
            
            # 총 레코드 수 표시 업데이트
            self.lbl_total_records.setText(f"총 {len(self.filtered_items)}건")
            
            # 필터링 결과 표시
            if len(self.filtered_items) > 0:
                self.lbl_filter_result.setText(f"검색 결과: {len(self.filtered_items)}건")
                self.lbl_filter_result.setStyleSheet("color: blue;")
            else:
                self.lbl_filter_result.setText("검색 결과가 없습니다.")
                self.lbl_filter_result.setStyleSheet("color: red;")
        except Exception as e:
            logger.error(f"검색 필터 적용 오류: {str(e)}")
            ErrorHandler.show_warning_message("검색 오류", f"필터 적용 중 오류가 발생했습니다: {str(e)}")
    
    def reset_search_filter(self):
        """검색 및 필터 초기화"""
        try:
            # 검색어 초기화
            self.input_search.clear()
            
            # 날짜 필터 초기화
            self.date_from.setDate(QDate.currentDate().addDays(-7))
            self.date_to.setDate(QDate.currentDate())
            
            # 창고 필터 초기화
            self.combo_warehouse.setCurrentIndex(0)  # 전체 선택
            
            # 필터 적용
            self.apply_search_filter()
        except Exception as e:
            logger.error(f"필터 초기화 오류: {str(e)}")
            ErrorHandler.show_warning_message("필터 초기화 오류", f"필터 초기화 중 오류가 발생했습니다: {str(e)}")
    
    def update_pagination(self):
        """페이지 정보 업데이트"""
        # 전체 페이지 수 계산
        total_pages = max(1, (len(self.filtered_items) + self.items_per_page - 1) // self.items_per_page)
        
        # 현재 페이지 범위 조정
        if self.current_page > total_pages:
            self.current_page = total_pages
        
        # 페이지 정보 표시 업데이트
        self.lbl_page.setText(f"{self.current_page} / {total_pages}")
        
        # 페이지 버튼 활성화/비활성화
        self.btn_prev_page.setEnabled(self.current_page > 1)
        self.btn_next_page.setEnabled(self.current_page < total_pages)
    
    def update_table(self):
        """테이블 데이터 업데이트"""
        try:
            # 테이블 초기화
            self.table_inventory.setRowCount(0)
            
            # 현재 페이지에 표시할 데이터 범위 계산
            start_idx = (self.current_page - 1) * self.items_per_page
            end_idx = min(start_idx + self.items_per_page, len(self.filtered_items))
            
            # 테이블에 데이터 추가
            for i, item in enumerate(self.filtered_items[start_idx:end_idx]):
                row = self.table_inventory.rowCount()
                self.table_inventory.insertRow(row)
                
                # 데이터 설정 (순서 변경됨)
                self.table_inventory.setItem(row, 0, QTableWidgetItem(item.get("sku", "")))           # 상품아이디
                self.table_inventory.setItem(row, 1, QTableWidgetItem(item.get("product_name", "")))  # 상품명
                self.table_inventory.setItem(row, 2, QTableWidgetItem(item.get("received_date", ""))) # 입고일
                self.table_inventory.setItem(row, 3, QTableWidgetItem(item.get("warehouse", "")))     # 창고
                self.table_inventory.setItem(row, 4, QTableWidgetItem(str(item.get("quantity", 0))))  # 수량
                
                # 행 색상 설정 (조건에 따라)
                if item.get("is_expiring_soon", False):
                    for col in range(self.table_inventory.columnCount()):
                        cell = self.table_inventory.item(row, col)
                        if cell:
                            cell.setBackground(QColor(255, 243, 224))  # 유통기한 임박: 연한 주황색
                
                elif item.get("is_low_stock", False):
                    for col in range(self.table_inventory.columnCount()):
                        cell = self.table_inventory.item(row, col)
                        if cell:
                            cell.setBackground(QColor(232, 234, 246))  # 재고 부족: 연한 푸른색
        except Exception as e:
            logger.error(f"테이블 업데이트 오류: {str(e)}")
            ErrorHandler.show_warning_message("테이블 업데이트 오류", f"테이블 업데이트 중 오류가 발생했습니다: {str(e)}")
    
    def prev_page(self):
        """이전 페이지로 이동"""
        if self.current_page > 1:
            self.current_page -= 1
            self.update_pagination()
            self.update_table()
    
    def next_page(self):
        """다음 페이지로 이동"""
        total_pages = max(1, (len(self.filtered_items) + self.items_per_page - 1) // self.items_per_page)
        if self.current_page < total_pages:
            self.current_page += 1
            self.update_pagination()
            self.update_table()

            