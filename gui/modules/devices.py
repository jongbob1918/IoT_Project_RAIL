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

class DevicesPage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/widgets/devices.ui", self)

        # WebSocket 설정
        self.ws = websocket.WebSocketApp(
            "ws://localhost:8000/ws",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open
        
        # 가동 버튼 스타일
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                border-radius: 3px; 
                padding: 5px;
            }
            QPushButton:pressed {
                background-color: #388E3C;
                padding-left: 4px;
                padding-top: 4px;
            }
        """)

        # 정지 버튼 스타일
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #FFC107; 
                color: black; 
                border-radius: 3px; 
                padding: 5px;
            }
            QPushButton:pressed {
                background-color: #FFA000;
                padding-left: 4px;
                padding-top: 4px;
            }
        """)        

        # 비상정지 버튼 스타일
        self.btn_emergencyStop.setStyleSheet("""
            QPushButton {
                background-color: #F44336; 
                color: white; 
                border-radius: 3px; 
                padding: 5px;
            }
            QPushButton:pressed {
                background-color: #D32F2F;
                padding-left: 4px;
                padding-top: 4px;
            }
        """)
        
        # 컨베이어 벨트 제어 버튼 설정
        self.btn_start.clicked.connect(self.start_conveyor)
        self.btn_stop.clicked.connect(self.stop_conveyor)
        self.btn_emergencyStop.clicked.connect(self.emergency_stop_conveyor)
        
        # 컨베이어 상태
        self.conveyor_running = False
        
        # 분류 박스 재고량 초기화
        self.inventory_counts = {
            "A": 0,  # 물건(비식품)
            "B": 0,  # 실온 식품
            "C": 0,  # 냉장 식품
            "error": 0  # 오류 건수
        }
        self.waiting_items = 0
        self.total_processed = 0
        
        # 로그 생성 타이머 설정
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.generate_random_log)
        self.log_timer.start(5000)  # 5초 간격으로 임의 로그 생성
        
        # WebSocket 연결 시작
        self.start_websocket()
        
        # UI 업데이트 타이머 설정
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # 1초 간격으로 UI 업데이트
        
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
        
        # 초기 데이터 요청
        self.request_conveyor_status()
        self.request_inventory_status()

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            category = data.get("category")
            action = data.get("action")
            payload = data.get("payload", {})

            # 컨베이어 상태 메시지 처리
            if category == "conv" and action == "status":
                status = payload.get("status")
                
                # UI 업데이트
                if status == "running":
                    self.conveyor_status.setText("작동중")
                    self.conveyor_status.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 3px; padding: 2px;")
                    self.conveyor_running = True
                    # 로그 타이머 시작
                    if not self.log_timer.isActive():
                        self.log_timer.start(5000)
                elif status == "emergency":
                    self.conveyor_status.setText("비상정지")
                    self.conveyor_status.setStyleSheet("background-color: #F44336; color: white; border-radius: 3px; padding: 2px;")                    
                    self.conveyor_running = False
                    self.log_timer.stop()
                else:
                    self.conveyor_status.setText("일시정지")                   
                    self.conveyor_status.setStyleSheet("background-color: #FFC107; color: black; border-radius: 3px; padding: 2px;")
                    self.conveyor_running = False
                    self.log_timer.stop()
            
            # 재고 메시지 처리
            elif category == "inv" and action == "realtime":
                if "boxes" in payload:
                    boxes = payload.get("boxes", {})
                    self.inventory_counts["A"] = boxes.get("A", 0)
                    self.inventory_counts["B"] = boxes.get("B", 0)
                    self.inventory_counts["C"] = boxes.get("C", 0)
                    self.inventory_counts["error"] = boxes.get("error", 0)
                
                if "waiting" in payload:
                    self.waiting_items = payload.get("waiting", 0)
                
                if "total" in payload:
                    self.total_processed = payload.get("total", 0)
            
            # 새 로그 이벤트 처리
            elif category == "conv" and action == "log":
                if "item" in payload:
                    item = payload.get("item", {})
                    barcode = item.get("barcode", "")
                    category = item.get("category", "")
                    warehouse = item.get("warehouse", "")
                    timestamp = QDateTime.fromSecsSinceEpoch(
                        payload.get("ts", int(QDateTime.currentSecsSinceEpoch()))
                    ).toString("hh:mm:ss")
                    
                    # 로그 메시지 생성
                    log_message = f"{timestamp} - QR {barcode} 인식됨, "
                    
                    if category == "food_frozen":
                        log_message += "냉동식품으로 분류 (창고 C)"
                    elif category == "food_refrigerated":
                        log_message += "냉장식품으로 분류 (창고 B)"
                    elif category == "food_room_temp":
                        log_message += "실온식품으로 분류 (창고 C)"
                    elif category == "non_food":
                        log_message += "물건으로 분류 (창고 A)"
                    else:
                        log_message += f"알 수 없는 분류 ({category}, 창고 {warehouse})"
                    
                    # 로그 목록에 추가
                    self.list_logs.insertItem(0, log_message)
                    
                    # 최대 50개 로그만 유지
                    if self.list_logs.count() > 50:
                        self.list_logs.takeItem(self.list_logs.count() - 1)
                        
        except Exception as e:
            print(f"메시지 처리 오류: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket 오류: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket 연결 종료")
        # 5초 후 재연결 시도
        QTimer.singleShot(5000, self.start_websocket)

    def request_conveyor_status(self):
        data = {
            "version": "v1",
            "type": "request",
            "category": "conv",
            "action": "get_status",
            "request_id": "c1",
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(data)

    def request_inventory_status(self):
        data = {
            "version": "v1",
            "type": "request",
            "category": "inv",
            "action": "get_realtime",
            "request_id": "i1",
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(data)

    def start_conveyor(self):
        data = {
            "version": "v1",
            "type": "request",
            "category": "conv",
            "action": "control",
            "request_id": "c2",
            "payload": {
                "status": "on",
                "speed": 2  # 중간 속도로 시작
            },
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(data)
        self.conveyor_running = True
        self.conveyor_status.setText("작동중")
        self.conveyor_status.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 3px; padding: 2px;")
        
        # 로그 타이머 시작 (작동 시 로그 생성)
        if not self.log_timer.isActive():
            self.log_timer.start(5000)

    def stop_conveyor(self):
        data = {
            "version": "v1",
            "type": "request",
            "category": "conv",
            "action": "control",
            "request_id": "c3",
            "payload": {
                "status": "off"
            },
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(data)
        self.conveyor_running = False
        self.conveyor_status.setText("일시정지")
        self.conveyor_status.setStyleSheet("background-color: #FFC107; color: black; border-radius: 3px; padding: 2px;")
        
        
        # 로그 타이머 중지 (정지 시 로그 생성 중단)
        self.log_timer.stop()

    def emergency_stop_conveyor(self):
        data = {
            "version": "v1",
            "type": "request",
            "category": "conv",
            "action": "emergency_stop",
            "request_id": "c4",
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(data)
        self.conveyor_running = False
        self.conveyor_status.setText("비상정지")
        self.conveyor_status.setStyleSheet("background-color: #F44336; color: white; border-radius: 3px; padding: 2px;")
        
        # 로그 타이머 중지 (비상정지 시 로그 생성 중단)
        self.log_timer.stop()
        
        # 비상정지 로그 추가
        current_time = QTime.currentTime().toString("hh:mm:ss")
        emergency_log = f"{current_time} - 비상정지 버튼 작동. 컨베이어 벨트 정지됨."
        self.list_logs.insertItem(0, emergency_log)

    def generate_random_log(self):
        """임의의 바코드 인식 및 물품 분류 로그를 생성합니다."""
        if not self.conveyor_running:
            return
            
        # 현재 시간
        current_time = QTime.currentTime().toString("hh:mm:ss")
        
        # 임의의 바코드 생성 (6자리)
        qr = str(random.randint(100000, 999999))
        
        # 물품 유형 결정 (A: 물건, B: 실온식품, C: 냉장식품)
        item_types = [
            ("A", "물건으로 분류 (창고 A)"),
            ("B", "실온식품으로 분류 (창고 B)"),
            ("C", "냉장식품으로 분류 (창고 C)")
        ]
        
        # 가끔 오류 발생시키기 (10% 확률)
        if random.random() < 0.1:
            log_message = f"{current_time} - QR {qr} 인식 실패. 분류 오류 발생."
            box_type = "error"
        else:
            box_type, message = random.choice(item_types)
            log_message = f"{current_time} - QR {qr} 인식됨, {message}"
        
        # 재고 카운트 업데이트
        self.inventory_counts[box_type] += 1
        self.total_processed += 1
        
        # 대기 물품 수 랜덤 업데이트
        self.waiting_items = max(0, self.waiting_items + random.randint(-1, 2))
        
        # 로그 목록에 추가
        self.list_logs.insertItem(0, log_message)
        
        # 최대 50개 로그만 유지
        if self.list_logs.count() > 50:
            self.list_logs.takeItem(self.list_logs.count() - 1)

    def update_ui(self):
        # 재고 라벨 업데이트
        self.inventory_A.setText(f"{self.inventory_counts['A']}개")
        self.inventory_B.setText(f"{self.inventory_counts['B']}개")
        self.inventory_C.setText(f"{self.inventory_counts['C']}개")
        self.inventory_error.setText(f"{self.inventory_counts['error']}개")
        
        # 대기 물품 및 전체 분류 물품 업데이트
        self.inventory_waiting.setText(f"{self.waiting_items}개")
        self.inventory_waiting_2.setText(f"{self.total_processed}개")

        # 서버로부터 최신 데이터 주기적 요청
        if hasattr(self, 'ws') and self.ws:
            # 10초마다 데이터 갱신 (현재 시간을 10으로 나눈 나머지가 0일 때)
            current_second = QTime.currentTime().second()
            if current_second % 10 == 0:
                self.request_conveyor_status()
                self.request_inventory_status()
                
        # 오류는 항상 빨간색
        if self.inventory_counts["error"] > 0:
            self.inventory_error.setStyleSheet("color: #F44336; font-weight: bold;")
        else:
            self.inventory_error.setStyleSheet("color: #757575;")

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
