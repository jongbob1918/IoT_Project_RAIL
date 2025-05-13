import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import json
import datetime
import random

from modules.data_manager import DataManager

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

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
    
    def update_chart(self):
        """창고별 물품 비율 파이 차트 업데이트"""
        # 샘플 데이터 (실제 구현 시에는 data_manager에서 데이터 가져오기)
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
    
    def get_warehouse_distribution(self):
        """창고별 물품 분포 데이터 가져오기"""
        # 실제 데이터 가져오기 (data_manager 사용)
        if self.data_manager:
            try:
                # 서버 연결 객체 가져오기
                server_conn = self.data_manager._server_connection
                
                if server_conn and server_conn.is_connected:
                    # 서버에서 창고별 물품 분포 데이터 가져오기
                    # 실제 코드에서는 API 호출
                    # return actual_data
                    pass
            except Exception as e:
                print(f"창고별 물품 분포 데이터 가져오기 오류: {str(e)}")
        
        # 서버 연결이 없거나 데이터를 가져오는데 실패한 경우 샘플 데이터 반환
        return {
            '냉동 창고 (A)': 35,
            '냉장 창고 (B)': 25,
            '상온 창고 (C)': 40
        }

class InventoryPage(QWidget):
    """재고 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 로드
        uic.loadUi("ui/widgets/inventory.ui", self)
        
        # 데이터 관리자 가져오기
        self.data_manager = DataManager.get_instance()
        
        # 차트 프레임 초기화
        self.init_chart_frame()
        
        # 버튼 이벤트 연결
        if hasattr(self, 'btn_inventory_list'):
            self.btn_inventory_list.clicked.connect(self.show_inventory_list)
        
        # 서버 연결 상태 표시 초기화
        if hasattr(self, 'lbl_status'):
            self.lbl_status.setText("서버 연결 상태: 연결 안됨")
            self.lbl_status.setStyleSheet("color: red;")
        
        # 타이머 설정 (서버 연결 상태 갱신)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_connection_status)
        self.update_timer.start(5000)  # 5초마다 업데이트
        
        # 데이터 변경 이벤트 연결
        self.data_manager.notification_added.connect(self.on_notification)
        
        # 초기 서버 연결 상태 표시 업데이트
        self.update_connection_status()
    
    def init_chart_frame(self):
        """차트 프레임 초기화"""
        # 차트 프레임이 UI에 있는지 확인
        if hasattr(self, 'chartframe'):
            # 기존 레이아웃 제거
            if self.chartframe.layout():
                # 기존 레이아웃의 모든 아이템 제거
                while self.chartframe.layout().count():
                    item = self.chartframe.layout().takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                
                # 기존 레이아웃 제거
                QWidget().setLayout(self.chartframe.layout())
            
            # 새 차트 프레임 생성 및 추가
            self.chart_widget = ChartFrame(self.chartframe, self.data_manager)
            layout = QVBoxLayout(self.chartframe)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.chart_widget)
            self.chartframe.setLayout(layout)
    
    def show_inventory_list(self):
        """재고 목록 팝업 표시"""
        dialog = InventoryListDialog(self, self.data_manager)
        dialog.exec()
    
    def update_connection_status(self):
        """서버 연결 상태 업데이트"""
        if not hasattr(self, 'lbl_status'):
            return
            
        server_conn = self.data_manager._server_connection
        if server_conn and server_conn.is_connected:
            self.lbl_status.setText("서버 연결 상태: 연결됨")
            self.lbl_status.setStyleSheet("color: green;")
            
            # 서버 연결 시 차트 업데이트
            if hasattr(self, 'chart_widget'):
                self.chart_widget.update_chart()
        else:
            self.lbl_status.setText("서버 연결 상태: 연결 안됨")
            self.lbl_status.setStyleSheet("color: red;")
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 재고 관련 알림인 경우 처리
        if "입고" in message or "상품" in message or "재고" in message:
            # 알림 표시를 위한 추가 작업이 필요한 경우 여기에 구현
            # 차트 업데이트
            if hasattr(self, 'chart_widget'):
                self.chart_widget.update_chart()
    
    def onConnectionStatusChanged(self, connected):
        """서버 연결 상태 변경 시 호출되는 메서드"""
        if connected:
            # 연결 성공 시 처리
            if hasattr(self, 'lbl_status'):
                self.lbl_status.setText("서버 연결 상태: 연결됨")
                self.lbl_status.setStyleSheet("color: green;")
        else:
            # 연결 실패 시 처리
            if hasattr(self, 'lbl_status'):
                self.lbl_status.setText("서버 연결 상태: 연결 안됨")
                self.lbl_status.setStyleSheet("color: red;")

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
        self.inventory_items = []
        self.filtered_items = []
        self.current_page = 1
        self.items_per_page = 20
        
        # 초기 데이터 로드
        self.fetch_inventory_data()
    
    def setup_ui(self):
        """UI 구성"""
        main_layout = QVBoxLayout(self)
        
        # 상단 필터 영역
        filter_layout = QHBoxLayout()
        
        # 검색 필드
        search_label = QLabel("검색:")
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("상품명 또는 SKU 검색")
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
        self.table_inventory = QTableWidget()
        self.table_inventory.setColumnCount(5)
        self.table_inventory.setHorizontalHeaderLabels(["상품명", "SKU", "창고", "입고일", "수량"])
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
        self.table_inventory.setColumnWidth(0, 200)  # 상품명
        self.table_inventory.setColumnWidth(1, 120)  # SKU
        self.table_inventory.setColumnWidth(2, 80)   # 창고
        self.table_inventory.setColumnWidth(3, 120)  # 입고일
        self.table_inventory.setColumnWidth(4, 80)   # 수량
        
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
    
    def fetch_inventory_data(self):
        """서버에서 재고 데이터 가져오기"""
        try:
            # 서버 연결 객체 가져오기
            if self.data_manager:
                server_conn = self.data_manager._server_connection
                
                if server_conn and server_conn.is_connected:
                    # ServerConnection 객체를 통해 API 호출
                    try:
                        # 서버에서 재고 데이터 가져오기
                        # 실제 코드에서는 API 호출
                        pass
                    except Exception as e:
                        print(f"재고 데이터 가져오기 오류: {str(e)}")
                        
                    # 필터 적용
                    self.apply_search_filter()
                else:
                    # 서버 연결이 없는 경우 임시 데이터 사용 (테스트용)
                    self.inventory_items = []  # 데이터 초기화
                    
            # 필터 적용
            self.apply_search_filter()
            
        except Exception as e:
            print(f"fetch_inventory_data 실행 중 오류: {str(e)}")
    
    def apply_search_filter(self):
        """검색 및 필터 적용"""
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
    
    def reset_search_filter(self):
        """검색 및 필터 초기화"""
        # 검색어 초기화
        self.input_search.clear()
        
        # 날짜 필터 초기화
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_to.setDate(QDate.currentDate())
        
        # 창고 필터 초기화
        self.combo_warehouse.setCurrentIndex(0)  # 전체 선택
        
        # 필터 적용
        self.apply_search_filter()
    
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
        # 테이블 초기화
        self.table_inventory.setRowCount(0)
        
        # 현재 페이지에 표시할 데이터 범위 계산
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.filtered_items))
        
        # 테이블에 데이터 추가
        for i, item in enumerate(self.filtered_items[start_idx:end_idx]):
            row = self.table_inventory.rowCount()
            self.table_inventory.insertRow(row)
            
            # 데이터 설정 (ID와 위치 칼럼 제거)
            self.table_inventory.setItem(row, 0, QTableWidgetItem(item.get("product_name", "")))
            self.table_inventory.setItem(row, 1, QTableWidgetItem(item.get("sku", "")))
            self.table_inventory.setItem(row, 2, QTableWidgetItem(item.get("warehouse", "")))
            self.table_inventory.setItem(row, 3, QTableWidgetItem(item.get("received_date", "")))
            self.table_inventory.setItem(row, 4, QTableWidgetItem(str(item.get("quantity", 0))))
            
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


class InventoryPage(QWidget):
    """재고 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 로드
        uic.loadUi("ui/widgets/inventory.ui", self)
        
        # 데이터 관리자 가져오기
        self.data_manager = DataManager.get_instance()

        # 차트 프레임 초기화
        self.init_chart_frame()
        
        # 버튼 이벤트 연결
        if hasattr(self, 'btn_inventory_list'):
            self.btn_inventory_list.clicked.connect(self.show_inventory_list)
        
        # 서버 연결 상태 표시 초기화
        if hasattr(self, 'lbl_status'):
            self.lbl_status.setText("서버 연결 상태: 연결 안됨")
            self.lbl_status.setStyleSheet("color: red;")
        
        # 타이머 설정 (서버 연결 상태 갱신)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_connection_status)
        self.update_timer.start(5000)  # 5초마다 업데이트
        
        # 데이터 변경 이벤트 연결
        self.data_manager.notification_added.connect(self.on_notification)
        
        # 초기 서버 연결 상태 표시 업데이트
        self.update_connection_status()

    def init_chart_frame(self):
        """차트 프레임 초기화"""
        # 차트 프레임이 UI에 있는지 확인
        if hasattr(self, 'chartframe'):
            # 기존 레이아웃 제거
            if self.chartframe.layout():
                # 기존 레이아웃의 모든 아이템 제거
                while self.chartframe.layout().count():
                    item = self.chartframe.layout().takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                
                # 기존 레이아웃 제거
                QWidget().setLayout(self.chartframe.layout())
            
            # 새 차트 프레임 생성 및 추가
            self.chart_widget = ChartFrame(self.chartframe, self.data_manager)
            layout = QVBoxLayout(self.chartframe)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.chart_widget)
            self.chartframe.setLayout(layout)
    
    def show_inventory_list(self):
        """재고 목록 팝업 표시"""
        dialog = InventoryListDialog(self, self.data_manager)
        dialog.exec()
    
    def update_connection_status(self):
        """서버 연결 상태 업데이트"""
        if not hasattr(self, 'lbl_status'):
            return
            
        server_conn = self.data_manager._server_connection
        if server_conn and server_conn.is_connected:
            self.lbl_status.setText("서버 연결 상태: 연결됨")
            self.lbl_status.setStyleSheet("color: green;")
        else:
            self.lbl_status.setText("서버 연결 상태: 연결 안됨")
            self.lbl_status.setStyleSheet("color: red;")
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 재고 관련 알림인 경우 처리
        if "입고" in message or "상품" in message or "재고" in message:
            # 알림 표시를 위한 추가 작업이 필요한 경우 여기에 구현
            pass
    
    def onConnectionStatusChanged(self, connected):
        """서버 연결 상태 변경 시 호출되는 메서드"""
        if connected:
            # 연결 성공 시 처리
            if hasattr(self, 'lbl_status'):
                self.lbl_status.setText("서버 연결 상태: 연결됨")
                self.lbl_status.setStyleSheet("color: green;")
        else:
            # 연결 실패 시 처리
            if hasattr(self, 'lbl_status'):
                self.lbl_status.setText("서버 연결 상태: 연결 안됨")
                self.lbl_status.setStyleSheet("color: red;")