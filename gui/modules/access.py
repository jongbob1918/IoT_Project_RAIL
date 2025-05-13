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

class AccessPage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/widgets/access.ui", self)
        
        # 기본 UI 설정
        self.setup_ui()
        
        # WebSocket 설정
        self.ws = websocket.WebSocketApp(
            "ws://localhost:8000/ws",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open
        
        # 테이블 초기 데이터
        self.total_entries = 32
        self.total_exits = 15
        self.current_people = 17
        self.page = 1
        self.total_pages = 5
        self.items_per_page = 20
        
        # 페이지네이션 버튼 연결
        self.btn_first.clicked.connect(lambda: self.go_to_page(1))
        self.btn_prev.clicked.connect(lambda: self.go_to_page(max(1, self.page - 1)))
        self.btn_next.clicked.connect(lambda: self.go_to_page(min(self.total_pages, self.page + 1)))
        self.btn_last.clicked.connect(lambda: self.go_to_page(self.total_pages))
        
        # 검색 기능 연결
        self.txt_search.textChanged.connect(self.search_access_logs)
        
        # 날짜 선택 콤보박스 설정
        self.setup_date_combo()
        self.combo_date.currentIndexChanged.connect(self.on_date_changed)
        
        # 출입 유형 및 구역 필터링 연결
        self.combo_type.currentIndexChanged.connect(self.apply_filters)
        self.combo_area.currentIndexChanged.connect(self.apply_filters)
        
        # WebSocket 연결 시작
        self.start_websocket()
        
        # 초기 데이터 로드
        self.load_mock_data()
        
        # 실시간 데이터 업데이트를 위한 타이머 설정
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_access_data)
        self.update_timer.start(5000)  # 5초마다 업데이트
    
    def setup_ui(self):
        """UI 기본 설정"""
        # 테이블 설정
        self.table_access.setColumnWidth(0, 80)   # 직원ID
        self.table_access.setColumnWidth(1, 100)  # 이름
        self.table_access.setColumnWidth(2, 120)  # 부서
        self.table_access.setColumnWidth(3, 150)  # 입장시간
        self.table_access.setColumnWidth(4, 150)  # 퇴장시간
        self.table_access.setColumnWidth(5, 150)  # 출입구역
        
        # 테이블 헤더 설정
        header = self.table_access.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # 통계 라벨 스타일 설정
        self.lbl_total_entry.setStyleSheet("color: #4285F4; font-weight: bold;")
        self.lbl_total_exit.setStyleSheet("color: #0F9D58; font-weight: bold;")
        self.lbl_current_people.setStyleSheet("color: #DB4437; font-weight: bold;")
    
    def setup_date_combo(self):
        """날짜 콤보박스 설정"""
        self.combo_date.clear()
        
        # 오늘 날짜부터 7일 이전까지 날짜 추가
        today = QDate.currentDate()
        for i in range(7):
            date = today.addDays(-i)
            self.combo_date.addItem(date.toString("yyyy-MM-dd"))
    
    def start_websocket(self):
        """WebSocket 연결 시작"""
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
    
    def on_open(self, ws):
        """WebSocket 연결 성공 시 호출"""
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
        
        # 초기 데이터 요청
        self.request_access_logs()
    
    def on_message(self, ws, message):
        """WebSocket 메시지 수신 시 호출"""
        try:
            data = json.loads(message)
            category = data.get("category")
            action = data.get("action")
            payload = data.get("payload", {})
            
            # 출입 로그 이벤트 처리
            if category == "access" and action == "logs":
                if "logs" in payload:
                    logs = payload.get("logs", [])
                    
                    # UI 업데이트는 메인 스레드에서 실행
                    QMetaObject.invokeMethod(self, "update_access_logs", 
                                           Qt.ConnectionType.QueuedConnection,
                                           Q_ARG(list, logs))
                    
            # 출입 승인 이벤트 처리
            elif category == "access" and action == "grant":
                uid = payload.get("uid", "")
                status = payload.get("status", "")
                timestamp = payload.get("ts", 0)
                
                # 입장 처리
                if status == "granted":
                    self.total_entries += 1
                    self.current_people += 1
                    self.update_summary_labels()
                    
                    # 로그 추가
                    self.add_entry_log(uid, timestamp)
                    
            # 출입 거부 이벤트 처리
            elif category == "access" and action == "deny":
                uid = payload.get("uid", "")
                status = payload.get("status", "")
                reason = payload.get("reason", "")
                timestamp = payload.get("ts", 0)
                
                # 거부 이벤트 처리 로직 추가
            
        except Exception as e:
            print(f"메시지 처리 오류: {e}")
    
    def on_error(self, ws, error):
        """WebSocket 오류 발생 시 호출"""
        print(f"WebSocket 오류: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """WebSocket 연결 종료 시 호출"""
        print("WebSocket 연결 종료")
        # 5초 후 재연결 시도
        QTimer.singleShot(5000, self.start_websocket)
    
    def request_access_logs(self):
        """서버에 출입 로그 요청"""
        selected_date = self.combo_date.currentText()
        
        # REST API 요청 대신 WebSocket 요청 사용
        data = {
            "version": "v1",
            "type": "request",
            "category": "access",
            "action": "get_logs",
            "request_id": "a2",
            "payload": {
                "date": selected_date,
                "page": self.page,
                "page_size": self.items_per_page
            },
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(data)
    
    def load_mock_data(self):
        """임시 데이터 로드 (서버 연결 전 테스트용)"""
        # 테이블 초기화
        self.table_access.setRowCount(0)
        
        # 임시 데이터 생성
        departments = ["물류팀", "관리팀", "품질관리", "재고관리", "보안팀"]
        areas = ["창고 A", "창고 B", "창고 C", "사무실", "출하장"]
        
        for i in range(15):  # 임의로 15개 데이터 생성
            row_position = self.table_access.rowCount()
            self.table_access.insertRow(row_position)
            
            # 직원 ID (EMP + 4자리 숫자)
            emp_id = f"EMP{random.randint(1000, 9999)}"
            
            # 이름 (임의 생성)
            names = ["홍길동", "김영희", "이철수", "박민지", "정수민", "강태오", "윤서연"]
            name = random.choice(names)
            
            # 부서 (임의 선택)
            department = random.choice(departments)
            
            # 입장 시간 (오늘 날짜 기준)
            entry_time = QTime(random.randint(8, 17), random.randint(0, 59))
            entry_datetime = QDateTime(QDate.currentDate(), entry_time)
            entry_str = entry_datetime.toString("yyyy-MM-dd hh:mm:ss")
            
            # 퇴장 시간 (입장 시간 이후, 30% 확률로 아직 퇴장 안함)
            if random.random() > 0.3:
                exit_time = entry_time.addSecs(random.randint(1800, 28800))  # 30분~8시간 후
                exit_datetime = QDateTime(QDate.currentDate(), exit_time)
                exit_str = exit_datetime.toString("yyyy-MM-dd hh:mm:ss")
            else:
                exit_str = ""
            
            # 출입 구역
            area = random.choice(areas)
            
            # 테이블에 데이터 추가
            self.table_access.setItem(row_position, 0, QTableWidgetItem(emp_id))
            self.table_access.setItem(row_position, 1, QTableWidgetItem(name))
            self.table_access.setItem(row_position, 2, QTableWidgetItem(department))
            self.table_access.setItem(row_position, 3, QTableWidgetItem(entry_str))
            self.table_access.setItem(row_position, 4, QTableWidgetItem(exit_str))
            self.table_access.setItem(row_position, 5, QTableWidgetItem(area))
        
        # 페이지 정보 업데이트
        self.lbl_page.setText(f"{self.page} / {self.total_pages}")
        
        # 통계 정보 업데이트
        self.update_summary_labels()
    
    def update_access_logs(self, logs):
        """서버로부터 받은 로그 데이터로 테이블 업데이트"""
        # 테이블 초기화
        self.table_access.setRowCount(0)
        
        for log in logs:
            row_position = self.table_access.rowCount()
            self.table_access.insertRow(row_position)
            
            uid = log.get("uid", "")
            name = log.get("name", "")
            act = log.get("act", "")
            time_str = log.get("time", "")
            
            # 여기서는 임의로 처리 (실제로는 서버에서 받아야 함)
            emp_id = f"EMP{random.randint(1000, 9999)}"
            department = random.choice(["물류팀", "관리팀", "품질관리", "재고관리", "보안팀"])
            area = random.choice(["창고 A", "창고 B", "창고 C", "창고 D", "사무실", "출하장"])
            
            # 테이블에 데이터 추가
            self.table_access.setItem(row_position, 0, QTableWidgetItem(emp_id))
            self.table_access.setItem(row_position, 1, QTableWidgetItem(name))
            self.table_access.setItem(row_position, 2, QTableWidgetItem(department))
            
            if act == "entry":
                # 입장 기록인 경우
                self.table_access.setItem(row_position, 3, QTableWidgetItem(time_str))
                self.table_access.setItem(row_position, 4, QTableWidgetItem(""))
            elif act == "exit":
                # 퇴장 기록인 경우 (여기서는 단순화를 위해 퇴장만 있는 경우도 처리)
                self.table_access.setItem(row_position, 3, QTableWidgetItem(""))
                self.table_access.setItem(row_position, 4, QTableWidgetItem(time_str))
            
            self.table_access.setItem(row_position, 5, QTableWidgetItem(area))
    
    def add_entry_log(self, uid, timestamp):
        """새로운 입장 로그 추가"""
        # 테이블의 첫 번째 행에 새 로그 추가
        self.table_access.insertRow(0)
        
        # 랜덤 데이터 생성 (실제로는 서버에서 받아야 함)
        emp_id = f"EMP{random.randint(1000, 9999)}"
        name = random.choice(["홍길동", "김영희", "이철수", "박민지", "정수민", "강태오", "윤서연"])
        department = random.choice(["물류팀", "관리팀", "품질관리", "재고관리", "보안팀"])
        area = random.choice(["창고 A", "창고 B", "창고 C", "창고 D", "사무실", "출하장"])
        
        # 시간 형식 변환
        entry_time = QDateTime.fromSecsSinceEpoch(timestamp).toString("yyyy-MM-dd hh:mm:ss")
        
        # 테이블에 데이터 추가
        self.table_access.setItem(0, 0, QTableWidgetItem(emp_id))
        self.table_access.setItem(0, 1, QTableWidgetItem(name))
        self.table_access.setItem(0, 2, QTableWidgetItem(department))
        self.table_access.setItem(0, 3, QTableWidgetItem(entry_time))
        self.table_access.setItem(0, 4, QTableWidgetItem(""))
        self.table_access.setItem(0, 5, QTableWidgetItem(area))
        
        # 마지막 행 제거 (테이블 크기 유지)
        if self.table_access.rowCount() > self.items_per_page:
            self.table_access.removeRow(self.table_access.rowCount() - 1)
    
    def update_summary_labels(self):
        """통계 라벨 업데이트"""
        self.lbl_total_entry.setText(f"{self.total_entries}명")
        self.lbl_total_exit.setText(f"{self.total_exits}명")
        self.lbl_current_people.setText(f"{self.current_people}명")
    
    def go_to_page(self, page):
        """페이지 이동"""
        if page != self.page and 1 <= page <= self.total_pages:
            self.page = page
            self.lbl_page.setText(f"{self.page} / {self.total_pages}")
            self.request_access_logs()
            
            # 서버 응답이 없을 때를 대비한 임시 데이터 로드
            self.load_mock_data()
    
    def on_date_changed(self, index):
        """날짜 선택 변경 시 호출"""
        self.page = 1  # 페이지 초기화
        self.request_access_logs()
        
        # 서버 응답이 없을 때를 대비한 임시 데이터 로드
        self.load_mock_data()
        
        # 필터 적용
        self.apply_filters()
    
    def search_access_logs(self):
        """검색어로 로그 필터링"""
        self.apply_filters()
        
    def apply_filters(self):
        """모든 필터 조건 적용"""
        search_text = self.txt_search.text().lower()
        access_type = self.combo_type.currentText()
        area = self.combo_area.currentText()
        
        # 모든 행에 대해 필터링
        for row in range(self.table_access.rowCount()):
            row_visible = True
            
            # 검색어 필터
            if search_text:
                text_match = False
                for col in range(self.table_access.columnCount()):
                    item = self.table_access.item(row, col)
                    if item and search_text in item.text().lower():
                        text_match = True
                        break
                if not text_match:
                    row_visible = False
            
            # 출입 유형 필터
            if access_type != "전체" and row_visible:
                entry_item = self.table_access.item(row, 3)  # 입장시간 열
                exit_item = self.table_access.item(row, 4)   # 퇴장시간 열
                
                if access_type == "입장" and (not entry_item or not entry_item.text()):
                    row_visible = False
                elif access_type == "퇴장" and (not exit_item or not exit_item.text()):
                    row_visible = False
            
            # 출입 구역 필터
            if area != "전체" and row_visible:
                area_item = self.table_access.item(row, 5)  # 출입구역 열
                if not area_item or area_item.text() != area:
                    row_visible = False
            
            # 행 표시 여부 설정
            self.table_access.setRowHidden(row, not row_visible)
    
    def update_access_data(self):
        """실시간 데이터 업데이트 (시뮬레이션)"""
        # 랜덤하게 입장 또는 퇴장 이벤트 발생
        if random.random() < 0.3:  # 30% 확률로 이벤트 발생
            if random.random() < 0.6 or self.current_people == 0:  # 입장 (60% 확률 또는 현재 인원이 0명일 때)
                self.total_entries += 1
                self.current_people += 1
                
                # 새 입장 로그 추가
                timestamp = int(QDateTime.currentSecsSinceEpoch())
                self.add_entry_log("", timestamp)
            else:  # 퇴장
                self.total_exits += 1
                self.current_people = max(0, self.current_people - 1)
                
                # 퇴장 처리 (기존 입장 기록 중 하나를 선택하여 퇴장 시간 추가)
                for row in range(self.table_access.rowCount()):
                    exit_item = self.table_access.item(row, 4)
                    if exit_item and not exit_item.text():
                        exit_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
                        self.table_access.setItem(row, 4, QTableWidgetItem(exit_time))
                        break
            
            # 통계 정보 업데이트
            self.update_summary_labels()
    
    def send_message(self, data):
        """WebSocket 메시지 전송"""
        try:
            if hasattr(self, 'ws') and self.ws:
                self.ws.send(json.dumps(data))
        except Exception as e:
            print(f"메시지 전송 오류: {e}")
    
    def closeEvent(self, event):
        """위젯이 닫힐 때 WebSocket 연결 종료"""
        if hasattr(self, 'ws') and self.ws:
            self.ws.close()
        event.accept()
