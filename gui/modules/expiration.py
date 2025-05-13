import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import json
import websocket
import threading
import datetime
import random

# 직접 구현한 커스텀 유통기한 아이템 위젯
from modules.expiration_item_custom import ExpirationItemCustom

class ExpirationPage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/widgets/expiration.ui", self)
        
        # 날짜 범위 초기 설정 (오늘부터 30일 전까지)
        today = QDate.currentDate()
        self.dateFrom.setDate(today.addDays(-30))
        self.dateTo.setDate(today.addDays(30))
        
        # 검색 버튼 이벤트 연결
        self.btnSearch.clicked.connect(self.search_expired_items)
        self.btnMoreItems.clicked.connect(self.load_more_items)
        
        # 유통기한 아이템 컨테이너 설정
        self.scroll_layout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(20)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 현재 페이지 번호
        self.current_page = 1
        
        # WebSocket 설정
        self.ws = websocket.WebSocketApp(
            "ws://localhost:8000/ws",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open
        
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
        
        # 더 많은 항목 버튼 스타일
        self.btnMoreItems.setStyleSheet("""
            QPushButton {
                background-color: #F8F8F8; 
                border: 1px solid #E0E0E0;
                border-radius: 3px; 
                padding: 5px;
            }
            QPushButton:pressed {
                background-color: #E8E8E8;
                padding-left: 4px;
                padding-top: 4px;
            }
        """)
        
        # WebSocket 연결 시작
        self.start_websocket()
        
        # 초기 데이터 로드
        self.search_expired_items()
        
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
                "token": "JWT_TOKEN"  # 실제 토큰으로 교체해야 함
            },
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(auth_message)
        
        # 유통기한 경고 구독
        self.subscribe_to_expiry_alerts()

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            category = data.get("category")
            action = data.get("action")
            payload = data.get("payload", {})

            # 유통기한 경고 메시지 처리
            if category == "exp" and action == "alert":
                items = payload.get("items", [])
                if items:
                    # 알림 메시지 표시
                    QTimer.singleShot(0, lambda: self.show_expiry_notification(items))
                    # 화면 갱신
                    QTimer.singleShot(0, self.search_expired_items)
                        
        except Exception as e:
            print(f"메시지 처리 오류: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket 오류: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket 연결 종료")
        # 5초 후 재연결 시도
        QTimer.singleShot(5000, self.start_websocket)

    def subscribe_to_expiry_alerts(self):
        # 유통기한 경고 구독 메시지
        data = {
            "version": "v1",
            "type": "request",
            "category": "exp",
            "action": "subscribe",
            "request_id": "e1",
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(data)

    def show_expiry_notification(self, items):
        """유통기한 경고 알림을 표시합니다."""
        if not items:
            return
            
        # 알림 메시지 생성
        item_names = [item.get('name', '') for item in items]
        if len(item_names) > 3:
            message = f"{item_names[0]}, {item_names[1]} 등 {len(item_names)}개 상품의 유통기한이 임박했습니다."
        else:
            message = f"{', '.join(item_names)} 상품의 유통기한이 임박했습니다."
        
        # 알림 대화상자 표시
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("유통기한 경고")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

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
            if self.scroll_layout.count() == 0:  # 첫 페이지일 때만 표시
                empty_label = QLabel("검색 조건에 맞는 항목이 없습니다.")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_label.setStyleSheet("font-size: 14px; color: #757575;")
                self.scroll_layout.addWidget(empty_label)
            return
        
        # 왼쪽 열과 오른쪽 열 위젯을 담을 FlowLayout 생성
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
        
        # 항목이 추가된 후 스크롤 영역 아래로 스크롤
        if self.current_page > 1:
            QTimer.singleShot(100, self.scroll_to_bottom)

    def search_expired_items(self):
        """날짜 범위 내의 유통기한 경과/임박 물품을 검색합니다."""
        # 페이지 초기화
        self.current_page = 1
        
        # 날짜 범위 가져오기
        from_date = self.dateFrom.date().toString("yyyy-MM-dd")
        to_date = self.dateTo.date().toString("yyyy-MM-dd")
        
        # API 호출 (여기서는 서버 대신 더미 데이터 생성)
        self.fetch_expiry_items(from_date, to_date, self.current_page)

    def load_more_items(self):
        """추가 유통기한 경과/임박 물품을 로드합니다."""
        self.current_page += 1
        
        # 날짜 범위 가져오기
        from_date = self.dateFrom.date().toString("yyyy-MM-dd")
        to_date = self.dateTo.date().toString("yyyy-MM-dd")
        
        # API 호출 (추가 페이지 로드)
        self.fetch_expiry_items(from_date, to_date, self.current_page, append=True)
    
    def scroll_to_bottom(self):
        """스크롤 영역을 아래로 스크롤합니다."""
        scrollbar = self.scrollArea.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # 로딩 중에 더보기 버튼 비활성화 및 텍스트 변경
        self.btnMoreItems.setEnabled(True)
        self.btnMoreItems.setText("더 많은 항목 보기")

    def fetch_expiry_items(self, from_date, to_date, page, append=False):
        """서버로부터 유통기한 임박/경과 물품 데이터를 요청합니다."""
        try:
            # 로딩 중 버튼 상태 변경
            self.btnMoreItems.setEnabled(False)
            self.btnMoreItems.setText("로딩 중...")
            
            # 실제 구현에서는 여기서 API 호출
            # 여기서는 테스트용 더미 데이터 생성
            if not append:
                self.clear_items_layout()
            
            # 로딩 시간 시뮬레이션 (실제 구현에서는 제거)
            QTimer.singleShot(800, lambda: self._complete_fetch(from_date, to_date, page, append))
            
        except Exception as e:
            print(f"유통기한 물품 로드 오류: {e}")
            QMessageBox.warning(self, "오류", "데이터를 불러오는 중 오류가 발생했습니다.")
            self.btnMoreItems.setEnabled(True)
            self.btnMoreItems.setText("더 많은 항목 보기")
    
    def _complete_fetch(self, from_date, to_date, page, append):
        """데이터 로딩을 완료하고 UI에 표시합니다."""
        # 더미 데이터 로드 (실제 구현에서는 서버 API 호출)
        items = self.get_dummy_items(page, from_date, to_date)
        
        # UI에 아이템 추가
        self.display_items(items)
        
        # 더 많은 항목 버튼 활성화/비활성화
        has_more = len(items) >= 6  # 6개 미만이면 더 이상 없다고 가정
        self.btnMoreItems.setEnabled(has_more)
        self.btnMoreItems.setText("더 많은 항목 보기")
        
        # 데이터가 없거나 더 이상 없을 경우 버튼 상태 변경
        if not has_more:
            if page > 1:
                self.btnMoreItems.setText("마지막 페이지입니다")
            else:
                self.btnMoreItems.setText("항목이 없습니다")
        
        # 스크롤 영역 크기 조정 (필요한 경우)
        self.scrollAreaWidgetContents.updateGeometry()

    def get_dummy_items(self, page, from_date, to_date):
        """테스트용 더미 데이터를 생성합니다. 실제 구현에서는 서버 API 호출로 대체."""
        # 임의의 상품명 목록
        product_names = [
            "시리얼 과자", "초콜릿", "사과", "우유", "두부", "요거트", 
            "치즈", "달걀", "쌀", "소시지", "라면", "식빵", 
            "샐러드", "소고기", "닭고기", "돼지고기", "참치캔", "과자"
        ]
        
        # 창고 위치 목록
        locations = ["A-12", "B-05", "C-08", "D-02", "A-01", "B-12", "C-03", "D-07"]
        
        # 결과 항목 수 (마지막 페이지는 적게)
        count = 6 if page < 3 else (3 if page == 3 else 0)
        
        items = []
        today = QDate.currentDate()
        
        for i in range(count):
            # 유통기한 임의 생성
            if i % 3 == 0:
                # 경과된 유통기한
                days_diff = random.randint(1, 20)
                exp_date = today.addDays(-days_diff)
            elif i % 3 == 1:
                # 오늘 만료
                exp_date = today
            else:
                # 임박한 유통기한
                days_diff = random.randint(1, 7)
                exp_date = today.addDays(days_diff)
            
            item = {
                "id": f"{page}-{i}",
                "name": random.choice(product_names),
                "exp": exp_date.toString("yyyy-MM-dd"),
                "quantity": random.randint(1, 10),
                "location": random.choice(locations),
                "image_url": ""  # 실제 구현에서는 이미지 URL 추가
            }
            items.append(item)
        
        return items

    def send_message(self, data):
        try:
            if hasattr(self, 'ws') and self.ws:
                self.ws.send(json.dumps(data))
        except Exception as e:
            print(f"메시지 전송 오류: {e}")

    def closeEvent(self, event):
        # 위젯이 닫힐 때 WebSocket 연결 종료
        if hasattr(self, 'ws') and self.ws:
            self.ws.close()
        event.accept()