import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import json
import datetime
import random

from modules.data_manager import DataManager

class EnvironmentPage(QWidget):
    """환경 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 로드
        uic.loadUi("ui/widgets/environment.ui", self)
        
        # 데이터 관리자 가져오기
        self.data_manager = DataManager.get_instance()
        
        # 온도 임계값 설정
        self.temp_thresholds = self.data_manager.get_temperature_thresholds()
        
        # 초기 창고 상태 정보
        self.warehouses = {
            "A": {"name": "냉동 창고 (A)", "current_temp": -20.0, "target_temp": -20.0, "status": "정상", "mode": "정지"},
            "B": {"name": "냉장 창고 (B)", "current_temp": 5.0, "target_temp": 5.0, "status": "정상", "mode": "정지"},
            "C": {"name": "상온 창고 (C)", "current_temp": 20.0, "target_temp": 20.0, "status": "정상", "mode": "정지"}
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
            "A": (-25.0, -15.0),  # 냉동 창고: -25°C ~ -15°C
            "B": (0.0, 10.0),     # 냉장 창고: 0°C ~ 10°C
            "C": (15.0, 25.0)     # 상온 창고: 15°C ~ 25°C
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
        
        # UI 업데이트 타이머 설정
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # 1초 간격으로 UI 업데이트
        
        # 데이터 변경 이벤트 연결
        self.data_manager.warehouse_data_changed.connect(self.update_warehouse_data)
        self.data_manager.notification_added.connect(self.on_notification)
    
    def update_warehouse_data(self):
        """데이터 관리자로부터 창고 데이터 업데이트"""
        warehouse_data = self.data_manager.get_warehouse_data()
        
        for wh_id, data in warehouse_data.items():
            if wh_id in self.warehouses:
                # 현재 온도 업데이트
                self.warehouses[wh_id]["current_temp"] = data["temperature"]
                self.warehouses[wh_id]["status"] = data["status"]
                
                # 모드 업데이트 (온도 비교)
                self.update_operation_mode(wh_id)
        
        # UI 업데이트
        self.update_ui()
    
    def update_operation_mode(self, wh_id):
        """운영 모드(냉방/난방/정지) 업데이트"""
        warehouse = self.warehouses[wh_id]
        
        # 현재 온도와 목표 온도의 차이
        temp_diff = warehouse["current_temp"] - warehouse["target_temp"]
        
        # 온도 차이가 1도 이하면 정지 모드
        if abs(temp_diff) <= 1.0:
            warehouse["mode"] = "정지"
        # 현재 온도가 목표 온도보다 높으면 냉방 모드
        elif temp_diff > 0:
            warehouse["mode"] = "냉방 모드"
        # 현재 온도가 목표 온도보다 낮으면 난방 모드
        else:
            warehouse["mode"] = "난방 모드"
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 환경 관련 알림인 경우 처리
        if "온도" in message or "창고" in message:
            self.update_warehouse_data()
    
    def update_ui(self):
        """UI 업데이트"""
        # 각 창고별 UI 업데이트
        for wh_id, warehouse in self.warehouses.items():
            widgets = self.warehouse_widgets[wh_id]
            
            # 현재 온도 및 설정 온도 표시
            widgets["current_temp"].setText(f"현재 온도: {warehouse['current_temp']:.1f}°C")
            widgets["target_temp"].setText(f"설정 온도: {warehouse['target_temp']:.1f}°C")
            
            # 모드 표시 업데이트
            if warehouse["mode"] == "냉방 모드":
                widgets["mode_indicator"].setText("냉방 모드")
                widgets["mode_indicator"].setStyleSheet("background-color: #2196F3; color: white; padding: 3px; border-radius: 3px;")
            elif warehouse["mode"] == "난방 모드":
                widgets["mode_indicator"].setText("난방 모드")
                widgets["mode_indicator"].setStyleSheet("background-color: #FF5722; color: white; padding: 3px; border-radius: 3px;")
            else:  # 정지 모드
                widgets["mode_indicator"].setText("정지")
                widgets["mode_indicator"].setStyleSheet("background-color: #9E9E9E; color: white; padding: 3px; border-radius: 3px;")
            
            # 상태 표시기 업데이트
            if warehouse["status"] == "정상":
                widgets["status_indicator"].setText("정상")
                widgets["status_indicator"].setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px; padding: 2px;")
            elif warehouse["status"] == "주의":
                widgets["status_indicator"].setText("주의")
                widgets["status_indicator"].setStyleSheet("background-color: #FFEB3B; color: black; border-radius: 5px; padding: 2px;")
            else:  # 비정상
                widgets["status_indicator"].setText("경고")
                widgets["status_indicator"].setStyleSheet("background-color: #F44336; color: white; border-radius: 5px; padding: 2px;")
    
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
            
            # 기존 값과 다른 경우에만 서버에 요청
            if target_temp != self.warehouses[wh_id]["target_temp"]:
                # 데이터 매니저를 통해 알림 생성
                self.data_manager.add_notification(f"{self.warehouses[wh_id]['name']} 목표 온도가 {self.warehouses[wh_id]['target_temp']:.1f}°C에서 {target_temp:.1f}°C로 변경되었습니다.")
                
                # 타겟 온도 업데이트
                self.warehouses[wh_id]["target_temp"] = target_temp
                
                # 모드 업데이트
                self.update_operation_mode(wh_id)
                
                # UI 업데이트
                self.update_ui()
                
                # 성공 메시지 표시
                QMessageBox.information(self, "설정 성공", f"{self.warehouses[wh_id]['name']} 온도 설정이 성공적으로 적용되었습니다.")
                
                # 서버 연결이 있는 경우, 서버에 데이터 전송 (코드만 추가, 미사용)
                try:
                    server_conn = self.data_manager._server_connection
                    if server_conn and server_conn.is_connected:
                        # API 호출 코드 (미사용)
                        pass
                except Exception as e:
                    print(f"서버 요청 오류: {e}")
                    
        except ValueError:
            # 입력값이 숫자가 아닌 경우
            # 기존 설정 온도로 다시 설정
            widgets["temp_input"].setText(f"{self.warehouses[wh_id]['target_temp']}")
            QMessageBox.warning(self, "입력 오류", "유효한 온도 값을 입력해주세요.")
    
    def handleEnvironmentEvent(self, action, payload):
        """서버로부터 환경 이벤트 처리"""
        if action == "temperature_update" and "warehouse_id" in payload and "temperature" in payload:
            wh_id = payload.get("warehouse_id")
            temperature = payload.get("temperature")
            
            if wh_id in self.warehouses:
                self.warehouses[wh_id]["current_temp"] = temperature
                self.update_operation_mode(wh_id)
                self.update_ui()
    
    def onConnectionStatusChanged(self, connected):
        """서버 연결 상태 변경 시 호출되는 메서드"""
        if connected:
            # 연결 성공 시 처리
            self.data_manager.add_notification("서버에 연결되었습니다. 환경 제어 시스템 활성화됨.")
        else:
            # 연결 실패 시 처리
            self.data_manager.add_notification("서버 연결이 끊어졌습니다. 환경 제어 시스템 제한 모드로 작동 중.")