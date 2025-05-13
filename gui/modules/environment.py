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

class EnvironmentPage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/widgets/environment.ui", self)

        # WebSocket 설정
        self.ws = websocket.WebSocketApp(
            "ws://localhost:8000/ws",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open
        
        # 초기 창고 상태 정보
        self.warehouses = {
            "A": {"name": "냉동 창고 (A)", "current_temp": -18.5, "target_temp": -18.0, "status": "정상", "mode": "냉각모드 작동중"},
            "B": {"name": "냉장 창고 (B)", "current_temp": 4.2, "target_temp": 4.0, "status": "정상", "mode": "냉각모드 작동중"},
            "C": {"name": "상온 창고 (C)", "current_temp": 24.2, "target_temp": 24.0, "status": "정상", "mode": "가열모드 작동중"}
        }
        
        # 각 창고별 위젯 매핑
        self.warehouse_widgets = {
            "A": {
                "current_temp": self.label_current_temp_A,
                "target_temp": self.label_target_temp_A,
                "temp_input": self.input_temp_A,
                "status_indicator": self.label_status_A,
                "mode_indicator": self.label_mode_A,
                "set_temp_btn": self.btn_set_temp_A
            },
            "B": {
                "current_temp": self.label_current_temp_B,
                "target_temp": self.label_target_temp_B,
                "temp_input": self.input_temp_B,
                "status_indicator": self.label_status_B,
                "mode_indicator": self.label_mode_B,
                "set_temp_btn": self.btn_set_temp_B
            },
            "C": {
                "current_temp": self.label_current_temp_C,
                "target_temp": self.label_target_temp_C,
                "temp_input": self.input_temp_C,
                "status_indicator": self.label_status_C,
                "mode_indicator": self.label_mode_C,
                "set_temp_btn": self.btn_set_temp_C
            }
        }
        
        # 온도 입력 제한 설정 및 초기값 설정
        self.temp_ranges = {
            "A": (-30.0, 0.0),  # 냉동 창고: -30°C ~ 0°C
            "B": (0.0, 10.0),   # 냉장 창고: 0°C ~ 10°C
            "C": (15.0, 30.0)   # 상온 창고: 15°C ~ 30°C
        }
        
        # 각 창고별 설정
        for wh_id, warehouse in self.warehouses.items():
            widgets = self.warehouse_widgets[wh_id]
            
            # 설정 온도 입력 초기화
            widgets["temp_input"].setText(f"{warehouse['target_temp']}")
            
            # Double Validator 설정 - 각 창고마다 온도 범위 다르게 설정
            temp_min, temp_max = self.temp_ranges[wh_id]
            temp_validator = QDoubleValidator(temp_min, temp_max, 1)
            temp_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            widgets["temp_input"].setValidator(temp_validator)
            
            # 온도 설정 버튼 클릭 이벤트 연결
            widgets["set_temp_btn"].clicked.connect(
                lambda checked, wh=wh_id: self.set_temperature(wh)
            )
        
        # 초기 UI 업데이트
        self.update_ui()
        
        # WebSocket 연결 시작
        self.start_websocket()
        
        # UI 업데이트 타이머 설정
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # 1초 간격으로 UI 업데이트
        
        # 온도 시뮬레이션 타이머
        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self.simulate_temp_changes)
        self.simulation_timer.start(5000)  # 5초 간격으로 온도 변동 시뮬레이션
    
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
        
        # 초기 환경 데이터 요청
        self.request_environment_data()

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            category = data.get("category")
            action = data.get("action")
            payload = data.get("payload", {})

            # 환경 데이터 메시지 처리
            if category == "env" and action == "realtime":
                if "wh" in payload:
                    warehouses = payload.get("wh", [])
                    for wh in warehouses:
                        wh_id = wh.get("id")
                        if wh_id in self.warehouses:
                            self.warehouses[wh_id]["current_temp"] = wh.get("temp", self.warehouses[wh_id]["current_temp"])
                    
                    # UI 업데이트
                    self.update_ui()
            
            # 설정 응답 처리
            elif category == "env" and action == "control_response":
                wh_id = payload.get("warehouse_id")
                status = payload.get("status", "ok")
                
                if wh_id in self.warehouses:
                    if status == "ok":
                        # 설정 성공 시 UI 업데이트
                        self.warehouses[wh_id]["target_temp"] = payload.get("target_temp", self.warehouses[wh_id]["target_temp"])
                        
                        # 성공 메시지 표시
                        QMessageBox.information(self, "설정 성공", f"{self.warehouses[wh_id]['name']} 온도 설정이 성공적으로 적용되었습니다.")
                    else:
                        # 실패 메시지 표시
                        QMessageBox.warning(self, "설정 실패", f"{self.warehouses[wh_id]['name']} 온도 설정 적용에 실패했습니다: {payload.get('message', '알 수 없는 오류')}")
                    
                    # UI 업데이트
                    self.update_ui()
                    
        except Exception as e:
            print(f"메시지 처리 오류: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket 오류: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket 연결 종료")
        # 5초 후 재연결 시도
        QTimer.singleShot(5000, self.start_websocket)

    def request_environment_data(self):
        data = {
            "version": "v1",
            "type": "request",
            "category": "env",
            "action": "get_status",
            "request_id": "e1",
            "payload": {
                "warehouses": ["A", "B", "C"]
            },
            "ts": int(QDateTime.currentSecsSinceEpoch())
        }
        self.send_message(data)

    def update_ui(self):
        # 각 창고별 UI 업데이트
        for wh_id, warehouse in self.warehouses.items():
            widgets = self.warehouse_widgets[wh_id]
            
            # 현재 온도 및 설정 온도 표시
            widgets["current_temp"].setText(f"현재 온도: {warehouse['current_temp']}°C")
            widgets["target_temp"].setText(f"설정 온도: {warehouse['target_temp']}°C")
            
            # 모드 표시 및 업데이트 (현재 온도와 설정 온도 비교)
            if abs(warehouse['current_temp'] - warehouse['target_temp']) <= 0.5:
                # 온도가 목표 범위 내에 있으면 정상 상태
                warehouse['mode'] = "정상"
                widgets["mode_indicator"].setText("정상")
                widgets["mode_indicator"].setStyleSheet("background-color: #4CAF50; color: white; padding: 3px; border-radius: 3px;")
            elif warehouse['current_temp'] > warehouse['target_temp']:
                # 현재 온도가 설정 온도보다 높으면 냉각 모드
                warehouse['mode'] = "냉각모드 작동중"
                widgets["mode_indicator"].setText("냉각모드 작동중")
                widgets["mode_indicator"].setStyleSheet("background-color: #2196F3; color: white; padding: 3px; border-radius: 3px;")
            else:
                # 현재 온도가 설정 온도보다 낮으면 가열 모드
                warehouse['mode'] = "가열모드 작동중"
                widgets["mode_indicator"].setText("가열모드 작동중")
                widgets["mode_indicator"].setStyleSheet("background-color: #FF5722; color: white; padding: 3px; border-radius: 3px;")
            
            # 상태 표시기 업데이트
            if warehouse["status"] == "정상":
                widgets["status_indicator"].setText("정상")
                widgets["status_indicator"].setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px; padding: 2px;")
            elif warehouse["status"] == "경고":
                widgets["status_indicator"].setText("경고")
                widgets["status_indicator"].setStyleSheet("background-color: #FFC107; color: black; border-radius: 5px; padding: 2px;")
            else:
                widgets["status_indicator"].setText("오류")
                widgets["status_indicator"].setStyleSheet("background-color: #F44336; color: white; border-radius: 5px; padding: 2px;")
            
        # 주기적으로 서버에 환경 데이터 요청
        # 10초마다 데이터 갱신 (현재 시간을 10으로 나눈 나머지가 0일 때)
        current_second = QTime.currentTime().second()
        if current_second % 10 == 0:
            self.request_environment_data()

    def set_temperature(self, wh_id):
        """온도 설정 입력값을 처리합니다"""
        widgets = self.warehouse_widgets[wh_id]
        
        try:
            # 입력된 온도값 가져오기
            temp_text = widgets["temp_input"].text().replace(',', '.')  # 콤마를 점으로 변환
            target_temp = float(temp_text)
            
            # 온도 범위 확인
            temp_min, temp_max = self.temp_ranges[wh_id]
            if target_temp < temp_min:
                target_temp = temp_min
                widgets["temp_input"].setText(f"{temp_min}")
                QMessageBox.warning(self, "입력 오류", f"최소 온도는 {temp_min}°C입니다.")
            elif target_temp > temp_max:
                target_temp = temp_max
                widgets["temp_input"].setText(f"{temp_max}")
                QMessageBox.warning(self, "입력 오류", f"최대 온도는 {temp_max}°C입니다.")
            
            # 서버에 설정 적용 요청
            data = {
                "version": "v1",
                "type": "request",
                "category": "env",
                "action": "control",
                "request_id": f"e{wh_id}",
                "payload": {
                    "warehouse_id": wh_id,
                    "target_temp": target_temp
                },
                "ts": int(QDateTime.currentSecsSinceEpoch())
            }
            self.send_message(data)
            
            # 일단 UI를 미리 업데이트 (실제 응답이 오면 다시 업데이트)
            self.warehouses[wh_id]["target_temp"] = target_temp
            
            # UI 업데이트
            self.update_ui()
            
        except ValueError:
            # 입력값이 숫자가 아닌 경우
            # 기존 설정 온도로 다시 설정
            widgets["temp_input"].setText(f"{self.warehouses[wh_id]['target_temp']}")
            QMessageBox.warning(self, "입력 오류", "유효한 온도 값을 입력해주세요.")

    def simulate_temp_changes(self):
        """실제 서버가 없으므로 온도 변화를 시뮬레이션합니다."""
        for wh_id, warehouse in self.warehouses.items():
            # 설정값과 현재값의 차이 계산
            temp_diff = warehouse["target_temp"] - warehouse["current_temp"]
            
            # 천천히 설정값으로 수렴
            adjustment_factor = 0.1
            
            # 랜덤 변동 추가 (-0.3 ~ +0.3)
            random_temp = (random.random() - 0.5) * 0.6
            
            # 새 온도 값 계산
            new_temp = warehouse["current_temp"] + (temp_diff * adjustment_factor) + random_temp
            
            # 값 업데이트
            self.warehouses[wh_id]["current_temp"] = round(new_temp, 1)
            
            # 상태 업데이트 (온도가 설정값과 많이 다르면 경고 또는 오류)
            if abs(temp_diff) > 5:
                self.warehouses[wh_id]["status"] = "오류"
            elif abs(temp_diff) > 2:
                self.warehouses[wh_id]["status"] = "경고"
            else:
                self.warehouses[wh_id]["status"] = "정상"
        
        # UI 업데이트
        self.update_ui()

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