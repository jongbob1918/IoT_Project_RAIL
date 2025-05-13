import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import koreanize_matplotlib
import random
import json
import websocket
import threading
import datetime

class InventoryListDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("물품 리스트")
        self.resize(800, 600)
        
        # 메인 레이아웃
        layout = QVBoxLayout(self)
        
        # 헤더 레이아웃
        header_layout = QHBoxLayout()
        layout.addLayout(header_layout)
        
        # 경로 표시
        path_label = QLabel("물류관리 시스템 > 재고 관리 > 물품 리스트")
        path_label.setFont(QFont("", 10))
        header_layout.addWidget(path_label)
        header_layout.addStretch()
        
        # 관리자 표시
        admin_label = QLabel("관리자: 홍길동")
        admin_label.setFont(QFont("", 10))
        header_layout.addWidget(admin_label)
        
        # 물품 리스트 헤더
        list_header = QLabel("물품 리스트")
        list_header.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(list_header)
        
        # 검색 레이아웃
        search_layout = QHBoxLayout()
        layout.addLayout(search_layout)
        
        # 검색어 입력
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색어 입력...")
        search_layout.addWidget(self.search_input)
        
        # 필터 드롭다운
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("필터")
        self.filter_combo.addItem("바코드")
        self.filter_combo.addItem("제품명")
        self.filter_combo.addItem("창고")
        self.filter_combo.addItem("유통기한")
        search_layout.addWidget(self.filter_combo)
        
        # 내보내기 버튼
        export_btn = QPushButton("내보내기")
        export_btn.setFixedWidth(100)
        search_layout.addWidget(export_btn)
        
        # 테이블 위젯
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["No.", "입고일", "바코드", "상품명", "유통기한", "수량", "위치"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # 페이지네이션 레이아웃
        pagination_layout = QHBoxLayout()
        layout.addLayout(pagination_layout)
        
        pagination_layout.addStretch()
        
        # 페이지네이션 버튼
        first_page_btn = QPushButton("<<")
        prev_page_btn = QPushButton("<")
        self.page_label = QLabel("1 / 5")
        next_page_btn = QPushButton(">")
        last_page_btn = QPushButton(">>")
        
        pagination_layout.addWidget(first_page_btn)
        pagination_layout.addWidget(prev_page_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(next_page_btn)
        pagination_layout.addWidget(last_page_btn)
        
        # 샘플 데이터 로드
        self.load_sample_data()
        
    def load_sample_data(self):
        # 샘플 데이터
        data = [
            ("2025-05-01", "1250123545", "DHA 등 필수 영양소 150g", "2028-04-28", "1000", "B4"),
            ("2025-05-01", "4560982312", "고추장 500g", "2026-08-15", "200", "A2"),
            ("2025-05-02", "7891234567", "냉동 삼겹살 1kg", "2026-01-10", "150", "C3"),
            ("2025-05-02", "3216549870", "우유 1L", "2025-05-20", "300", "C1"),
            ("2025-05-03", "9876543210", "즉석밥 210g", "2027-12-31", "500", "B2"),
            ("2025-05-03", "1357924680", "냉동 만두 500g", "2026-06-15", "250", "C1"),
            ("2025-05-04", "2468013579", "사과주스 1.5L", "2025-09-30", "180", "B3"),
            ("2025-05-04", "1122334455", "김치 1kg", "2025-07-15", "100", "C2"),
            ("2025-05-05", "6677889900", "초콜릿 100g", "2027-02-28", "400", "A1"),
            ("2025-05-05", "5544332211", "냉동 피자", "2026-03-10", "120", "C4")
        ]
        
        # 테이블에 데이터 추가
        self.table.setRowCount(len(data))
        
        for i, (indate, barcode, name, expdate, quantity, location) in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.table.setItem(i, 1, QTableWidgetItem(indate))
            self.table.setItem(i, 2, QTableWidgetItem(barcode))
            self.table.setItem(i, 3, QTableWidgetItem(name))
            self.table.setItem(i, 4, QTableWidgetItem(expdate))
            self.table.setItem(i, 5, QTableWidgetItem(quantity))
            self.table.setItem(i, 6, QTableWidgetItem(location))

class InventoryPage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/widgets/inventory.ui", self)
        
        # 타이머 설정 (10초마다 데이터 갱신)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(10000)  # 10초마다 갱신
        
        # 재고 데이터 초기화
        self.inventory_data = {
            'A': {'count': 50, 'percentage': 33, 'usage': 56},
            'B': {'count': 30, 'percentage': 20, 'usage': 24},
            'C': {'count': 70, 'percentage': 47, 'usage': 35}
        }
        
        # 웹소켓 설정
        self.ws = websocket.WebSocketApp(
            "ws://localhost:8000/ws",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open
        
        # 웹소켓 스레드 시작
        self.start_websocket()
        
        # 원 그래프 생성
        self.fig = Figure(figsize=(4, 3), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        layout = QVBoxLayout(self.chartFrame)
        layout.addWidget(self.canvas)
        
        # 물품 리스트 보기 버튼 연결
        self.btn_inventory_list.clicked.connect(self.open_inventory_list)
        
        # 초기 데이터 로드 및 UI 업데이트
        self.update_ui()
        
    def start_websocket(self):
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def on_open(self, ws):
        print("WebSocket 연결 성공")
        # 인증 메시지 전송
        auth_message = {
            "version": "v1",
            "type": "request",
            "category": "auth",
            "action": "authenticate",
            "request_id": "a1",
            "payload": {
                "token": "JWT_TOKEN"  # 실제 토큰으로 교체
            },
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(auth_message)
        
        # 초기 데이터 요청
        self.request_inventory_data()

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            category = data.get("category")
            action = data.get("action")
            payload = data.get("payload", {})

            # 재고 데이터 처리
            if category == "inv" and action == "grid_status":
                if "warehouses" in payload:
                    wh_data = payload.get("warehouses", {})
                    for wh_id, wh_info in wh_data.items():
                        if wh_id in self.inventory_data:
                            self.inventory_data[wh_id]['usage'] = wh_info.get('usage', 0)
                    
                    self.update_ui()
            
            # 재고 항목 데이터 처리
            elif category == "inv" and action == "items":
                if "items" in payload:
                    items = payload.get("items", [])
                    count_a = count_b = count_c = 0
                    
                    for item in items:
                        wh = item.get("warehouse", "")
                        if wh == "A":
                            count_a += 1
                        elif wh == "B":
                            count_b += 1
                        elif wh == "C":
                            count_c += 1
                    
                    total = count_a + count_b + count_c
                    if total > 0:
                        self.inventory_data['A']['count'] = count_a
                        self.inventory_data['B']['count'] = count_b
                        self.inventory_data['C']['count'] = count_c
                        
                        self.inventory_data['A']['percentage'] = round(count_a / total * 100)
                        self.inventory_data['B']['percentage'] = round(count_b / total * 100)
                        self.inventory_data['C']['percentage'] = round(count_c / total * 100)
                        
                        self.update_ui()
                
        except Exception as e:
            print(f"메시지 처리 오류: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket 오류: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket 연결 종료")
        # 5초 후 재연결 시도
        QTimer.singleShot(5000, self.start_websocket)

    def request_inventory_data(self):
        # 격자 상태 요청
        grid_status_request = {
            "version": "v1",
            "type": "request",
            "category": "inv",
            "action": "get_grid_status",
            "request_id": "i2",
            "payload": {
                "wh": "all"
            },
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(grid_status_request)
        
        # 재고 목록 요청
        items_request = {
            "version": "v1",
            "type": "request",
            "category": "inv",
            "action": "get_items",
            "request_id": "i1",
            "payload": {
                "page": 1,
                "page_size": 100
            },
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(items_request)
        
    def send_message(self, data):
        try:
            if hasattr(self, 'ws') and self.ws:
                self.ws.send(json.dumps(data))
        except Exception as e:
            print(f"메시지 전송 오류: {e}")
    
    def update_pie_chart(self):
        """원 그래프를 업데이트합니다."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        
        # 데이터 준비
        labels = [f'창고 A ({self.inventory_data["A"]["percentage"]}%)',
                 f'창고 B ({self.inventory_data["B"]["percentage"]}%)',
                 f'창고 C ({self.inventory_data["C"]["percentage"]}%)']
        
        sizes = [self.inventory_data['A']['count'],
                self.inventory_data['B']['count'],
                self.inventory_data['C']['count']]
        
        colors = ['#4285F4', '#0F9D58', '#F4B400']
        
        # 원 그래프 그리기
        wedges, texts, autotexts = ax.pie(sizes, colors=colors, autopct='%1.1f%%',
                                         startangle=90, shadow=False)
        
        # 범례 설정
        ax.legend(wedges, labels, loc='upper center', bbox_to_anchor=(0.5, 0.1),
                 frameon=False, ncol=2)
        
        ax.set_title('창고별 물품 분포', pad=20, fontsize=14)
        ax.axis('equal')  # 원을 원형으로 보이게 함
        
        self.canvas.draw()
    
    def update_progress_bars(self):
        """프로그레스 바와 레이블을 업데이트합니다."""
        # 프로그레스 바 업데이트
        self.progressBar_A.setValue(self.inventory_data['A']['usage'])
        self.progressBar_B.setValue(self.inventory_data['B']['usage'])
        self.progressBar_C.setValue(self.inventory_data['C']['usage'])
        
        # 레이블 업데이트
        self.label_a_count.setText(f"{self.inventory_data['A']['count']}개 ({self.inventory_data['A']['percentage']}%)")
        self.label_b_count.setText(f"{self.inventory_data['B']['count']}개 ({self.inventory_data['B']['percentage']}%)")
        self.label_c_count.setText(f"{self.inventory_data['C']['count']}개 ({self.inventory_data['C']['percentage']}%)")
        
        # 전체 물품 수 업데이트
        total_count = sum(wh['count'] for wh in self.inventory_data.values())
        self.label_total_count.setText(f"{total_count}개")
    
    def update_ui(self):
        """UI 요소를 업데이트합니다."""
        self.update_pie_chart()
        self.update_progress_bars()
    
    def update_data(self):
        """서버로부터 최신 데이터를 요청합니다."""
        self.request_inventory_data()
        
    def open_inventory_list(self):
        """물품 리스트 다이얼로그를 엽니다."""
        dialog = InventoryListDialog(self)
        dialog.exec()
        
    def closeEvent(self, event):
        """위젯이 닫힐 때 호출됩니다."""
        # 타이머 중지
        if hasattr(self, 'update_timer') and self.update_timer.isActive():
            self.update_timer.stop()
        
        # 웹소켓 연결 종료
        if hasattr(self, 'ws') and self.ws:
            self.ws.close()
            
        event.accept()