import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import logging

from modules.base_page import BasePage
from modules.data_manager import DataManager
from modules.error_handler import ErrorHandler

# 로깅 설정
logger = logging.getLogger(__name__)

class EnvironmentPage(BasePage):
    """환경 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None, data_manager=None):
        """
        환경 관리 페이지 초기화
        
        Args:
            parent: 부모 위젯
            data_manager: 데이터 관리자 객체 (의존성 주입)
        """
        super().__init__(parent)
        self.page_name = "환경 관리"  # 기본 클래스 속성 설정
        
        # UI 로드
        uic.loadUi("ui/widgets/environment.ui", self)
        
        # 데이터 관리자 설정 (의존성 주입 패턴 적용)
        self.data_manager = data_manager if data_manager else DataManager.get_instance()
        self.set_data_manager(self.data_manager)  # 부모 클래스 메서드 호출
        
        # 온도 임계값 설정
        self.temp_thresholds = self.data_manager.get_temperature_thresholds()
        
        # 초기 창고 상태 정보 설정
        self.initialize_warehouse_data()
        
        # 팬 상태 표시 라벨 생성 (이 줄을 추가)
        self.create_fan_status_labels()
        
        # 개발 모드인 경우 시뮬레이션 컨트롤 추가 (선택 사항)
        if hasattr(self.data_manager, 'DEBUG_MODE') and self.data_manager.DEBUG_MODE:
            self.setup_simulation_controls()
        
        # 창고별 위젯 매핑
        self.map_warehouse_widgets()
        
        # 온도 입력 제한 설정 및 초기값 설정
        self.setup_temperature_controls()
        
        # 초기 UI 업데이트
        self.update_ui()
        
        # 데이터 변경 이벤트 연결
        self.connect_data_signals()
        
        logger.info("환경 관리 페이지 초기화 완료")

        # 헤더 레이블 폰트 설정
        headers = [self.label_title_A, self.label_title_B, self.label_title_C]
        for label in headers:
            font = label.font()
            font.setBold(True)
            font.setWeight(QFont.Weight.Bold)
            label.setFont(font)
    
    def initialize_warehouse_data(self):
        """초기 창고 상태 정보 설정"""
        self.warehouses = {
            "A": {
                "name": "냉동 창고 (A)", 
                "current_temp": 0.0, 
                "target_temp": -24.0, 
                "status": "알 수 없음", 
                "mode": "정지",
                "fan_mode": "off",  # 팬 모드 추가: off, cool, heat
                "fan_speed": 0      # 팬 속도 추가: 0(정지), 1(저속), 2(중속), 3(고속)
            },
            "B": {
                "name": "냉장 창고 (B)", 
                "current_temp": 0.0, 
                "target_temp": 5.0, 
                "status": "알 수 없음", 
                "mode": "정지",
                "fan_mode": "off",
                "fan_speed": 0
            },
            "C": {
                "name": "상온 창고 (C)", 
                "current_temp": 0.0, 
                "target_temp": 20.0, 
                "status": "알 수 없음", 
                "mode": "정지",
                "fan_mode": "off",
                "fan_speed": 0
            }
    }
    
    def map_warehouse_widgets(self):
        """각 창고별 위젯 매핑"""
        self.warehouse_widgets = {
            "A": {
                "current_temp": self.label_current_temp_A,
                "target_temp": self.label_target_temp_A,
                "temp_input": self.input_temp_A,
                "status_indicator": self.label_status_A,
                "mode_indicator": self.label_mode_A,
                "fan_status": getattr(self, "label_fan_status_A", None),  # 팬 상태 라벨 추가
                "set_temp_btn": self.btn_set_temp_A
            },
            "B": {
                "current_temp": self.label_current_temp_B,
                "target_temp": self.label_target_temp_B,
                "temp_input": self.input_temp_B,
                "status_indicator": self.label_status_B,
                "mode_indicator": self.label_mode_B,
                "fan_status": getattr(self, "label_fan_status_B", None),  # 팬 상태 라벨 추가
                "set_temp_btn": self.btn_set_temp_B
            },
            "C": {
                "current_temp": self.label_current_temp_C,
                "target_temp": self.label_target_temp_C,
                "temp_input": self.input_temp_C,
                "status_indicator": self.label_status_C,
                "mode_indicator": self.label_mode_C,
                "fan_status": getattr(self, "label_fan_status_C", None),  # 팬 상태 라벨 추가
                "set_temp_btn": self.btn_set_temp_C
            }
        }
    
    def setup_temperature_controls(self):
        """온도 입력 제한 설정 및 초기값 설정"""
        try:
            # 온도 입력 범위 제한 - 데이터 매니저에서 가져오기
            self.temp_ranges = {
                "A": (self.temp_thresholds["A"]["min"], self.temp_thresholds["A"]["max"]),
                "B": (self.temp_thresholds["B"]["min"], self.temp_thresholds["B"]["max"]),
                "C": (self.temp_thresholds["C"]["min"], self.temp_thresholds["C"]["max"])
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
        except Exception as e:
            logger.error(f"온도 컨트롤 설정 오류: {str(e)}")
            self.show_status_message("온도 컨트롤 초기화 오류", is_error=True)

    # warehouse_data_changed 시그널 핸들러 수정
    def update_warehouse_data(self):
        """데이터 관리자로부터 창고 데이터 업데이트"""
        try:
            warehouse_data = self.data_manager.get_warehouse_data()
            
            # 온도 임계값 업데이트 (변경될 수 있으므로)
            self.temp_thresholds = self.data_manager.get_temperature_thresholds()
            
            # 범위 업데이트 및 QValidator 재설정
            updated_ranges = False
            if self.temp_thresholds:
                for wh_id in self.warehouses:
                    if wh_id in self.temp_thresholds:
                        old_min, old_max = self.temp_ranges.get(wh_id, (None, None))
                        new_min = self.temp_thresholds[wh_id].get("min")
                        new_max = self.temp_thresholds[wh_id].get("max")
                        
                        if old_min != new_min or old_max != new_max:
                            # 범위가 변경됨
                            self.temp_ranges[wh_id] = (new_min, new_max)
                            updated_ranges = True
                            
                            # QValidator 업데이트
                            widgets = self.warehouse_widgets[wh_id]
                            temp_validator = QDoubleValidator(new_min, new_max, 1)
                            temp_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
                            widgets["temp_input"].setValidator(temp_validator)
            
            # 범위 변경 시 알림 표시
            if updated_ranges:
                self.show_status_message("온도 범위가 업데이트되었습니다.", is_info=True)
            
            # 기존 로직 계속 실행
            for wh_id, data in warehouse_data.items():
                if wh_id in self.warehouses:
                    # 현재 온도 업데이트
                    self.warehouses[wh_id]["current_temp"] = data["temperature"]
                    self.warehouses[wh_id]["status"] = data["status"]
                    
                    # 모드 업데이트 (온도 비교)
                    self.update_operation_mode(wh_id)
            
            # UI 업데이트
            self.update_ui()
        except Exception as e:
            logger.error(f"창고 데이터 업데이트 오류: {str(e)}")
            self.handle_data_fetch_error("창고 데이터 업데이트", str(e))


    def connect_data_signals(self):
        """데이터 변경 이벤트 연결"""
        self.data_manager.warehouse_data_changed.connect(self.update_warehouse_data)
        self.data_manager.notification_added.connect(self.on_notification)
        
        # 서버 이벤트 연결
        if hasattr(self.data_manager, '_server_connection') and hasattr(self.data_manager._server_connection, 'eventReceived'):
            self.data_manager._server_connection.eventReceived.connect(self.handle_server_event)
    
    def handle_server_event(self, category, action, payload):
        """서버 이벤트 처리"""
        # 환경 관련 이벤트인 경우 처리
        if category == "environment":
            self.handleEnvironmentEvent(action, payload)
    
    def update_warehouse_data(self):
        """데이터 관리자로부터 창고 데이터 업데이트"""
        try:
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
        except Exception as e:
            logger.error(f"창고 데이터 업데이트 오류: {str(e)}")
            self.handle_data_fetch_error("창고 데이터 업데이트", str(e))
    
    def create_fan_status_labels(self):
        """팬 상태 표시 라벨 동적 생성"""
        try:
            # 각 창고별 팬 상태 라벨 생성
            frames = [self.frame_A, self.frame_B, self.frame_C]
            warehouse_ids = ["A", "B", "C"]
            
            for i, frame in enumerate(frames):
                wh_id = warehouse_ids[i]
                
                # 팬 상태 라벨 생성
                label_fan_status = QLabel(frame)
                label_fan_status.setGeometry(QRect(440, 120, 121, 21))
                label_fan_status.setStyleSheet("background-color: #9E9E9E; color: white; padding: 3px; border-radius: 3px;")
                label_fan_status.setText("팬: 정지")
                label_fan_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label_fan_status.setObjectName(f"label_fan_status_{wh_id}")
                
                # 클래스 변수로 저장
                setattr(self, f"label_fan_status_{wh_id}", label_fan_status)
                
                logger.debug(f"창고 {wh_id}의 팬 상태 라벨 생성 완료")
                
        except Exception as e:
            logger.error(f"팬 상태 라벨 생성 오류: {str(e)}")

    def update_operation_mode(self, wh_id):
        """운영 모드(냉방/난방/정지) 업데이트"""
        try:
            warehouse = self.warehouses[wh_id]
            fan_mode = warehouse.get("fan_mode", "off")
            fan_speed = warehouse.get("fan_speed", 0)
            
            # 팬 모드에 따라 표시 텍스트 결정
            if fan_mode == "cool":
                warehouse["mode"] = "냉방 모드"
            elif fan_mode == "heat":
                if wh_id == "C":  # C 창고만 난방 지원
                    warehouse["mode"] = "난방 모드"
                else:  # A, B 창고는 난방 지원 안함
                    warehouse["mode"] = "정지"
            else:  # off 또는 알 수 없는 모드
                warehouse["mode"] = "정지"
                
            # 팬 속도가 0이면 정지 상태로 간주
            if fan_speed == 0:
                warehouse["mode"] = "정지"
                
        except Exception as e:
            logger.error(f"운영 모드 업데이트 오류: {str(e)}")
            
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 환경 관련 알림인 경우 처리
        if "온도" in message or "창고" in message:
            # 알림만 처리하고 데이터 업데이트는 이벤트에 의해 처리됨
            pass
    
    def update_ui(self):
        """UI 업데이트"""
        try:
            # 각 창고별 UI 업데이트
            for wh_id, warehouse in self.warehouses.items():
                widgets = self.warehouse_widgets[wh_id]
                
                # 현재 온도 및 설정 온도 표시
                widgets["current_temp"].setText(f"현재 온도: {warehouse['current_temp']:.1f}°C")
                widgets["target_temp"].setText(f"설정 온도: {warehouse['target_temp']:.1f}°C")
                
                # 상태 표시기 업데이트
                if warehouse["status"] == "정상":
                    widgets["status_indicator"].setText("정상")
                    widgets["status_indicator"].setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px; padding: 2px;")
                    # 정상 상태일 때도 mode_indicator 표시
                    widgets["mode_indicator"].show()
                elif warehouse["status"] == "경고":  # "주의"에서 "경고"로 변경
                    widgets["status_indicator"].setText("경고")
                    widgets["status_indicator"].setStyleSheet("background-color: #F44336; color: white; border-radius: 5px; padding: 2px;")
                    # 경고 상태일 때도 mode_indicator 표시
                    widgets["mode_indicator"].show()
                else:  # 연결 안됨 등 기타 상태
                    widgets["status_indicator"].setText(warehouse["status"])
                    widgets["status_indicator"].setStyleSheet("background-color: #9E9E9E; color: white; border-radius: 5px; padding: 2px;")
                    widgets["mode_indicator"].show()
                    
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
                
                # 팬 상태 표시 업데이트 (새로 추가)
                if "fan_status" in widgets and widgets["fan_status"] is not None:
                    fan_mode = warehouse.get("fan_mode", "off")
                    fan_speed = warehouse.get("fan_speed", 0)
                    
                    if fan_mode == "cool":
                        if fan_speed == 0:
                            fan_text = "팬: 정지"
                            fan_color = "#9E9E9E"  # 회색
                        else:
                            fan_text = f"냉방 팬: {fan_speed}단계"
                            fan_color = "#2196F3"  # 파란색
                    elif fan_mode == "heat":
                        if fan_speed == 0:
                            fan_text = "팬: 정지"
                            fan_color = "#9E9E9E"  # 회색
                        else:
                            fan_text = f"난방 팬: {fan_speed}단계"
                            fan_color = "#FF5722"  # 주황색
                    else:  # off
                        fan_text = "팬: 정지"
                        fan_color = "#9E9E9E"  # 회색
                    
                    widgets["fan_status"].setText(fan_text)
                    widgets["fan_status"].setStyleSheet(f"background-color: {fan_color}; color: white; padding: 3px; border-radius: 3px;")
                    widgets["fan_status"].show()
                    
        except Exception as e:
            logger.error(f"UI 업데이트 오류: {str(e)}")
            self.show_status_message(f"UI 업데이트 오류: {str(e)}", is_error=True)
    
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
                self.handle_data_fetch_error("온도 설정", f"최소 온도는 {temp_min}°C입니다.")
                return
            elif target_temp > temp_max:
                target_temp = temp_max
                widgets["temp_input"].setText(f"{temp_max}")
                self.handle_data_fetch_error("온도 설정", f"최대 온도는 {temp_max}°C입니다.")
                return
            
            # 기존 값과 다른 경우에만 서버에 요청
            if target_temp != self.warehouses[wh_id]["target_temp"]:
                # 서버 연결 확인
                if not self.data_manager.is_server_connected():
                    self.handle_connection_error("온도 설정")
                    return
                    
                try:
                    # 서버 API 호출 - 데이터 매니저를 통해 처리
                    response = self.data_manager.set_target_temperature(wh_id, target_temp)
                    
                    # 응답 처리
                    if response and response.get("success", False):
                        # 타겟 온도 업데이트
                        self.warehouses[wh_id]["target_temp"] = target_temp
                        
                        # 모드 업데이트
                        self.update_operation_mode(wh_id)
                        
                        # UI 업데이트
                        self.update_ui()
                        
                        # 알림 추가
                        message = f"{self.warehouses[wh_id]['name']} 목표 온도가 {target_temp:.1f}°C로 변경되었습니다."
                        self.data_manager.add_notification(message)
                        
                        # 성공 메시지 표시
                        ErrorHandler.show_info_message("설정 성공", f"{self.warehouses[wh_id]['name']} 온도 설정이 성공적으로 적용되었습니다.")
                    else:
                        # 오류 메시지 표시
                        error_msg = response.get("message", "알 수 없는 오류가 발생했습니다.")
                        self.handle_api_error("온도 설정 오류", error_msg)
                except Exception as e:
                    # 오류 메시지 표시
                    self.handle_api_exception("온도 설정 요청 오류", e)
                    
        except ValueError:
            # 입력값이 숫자가 아닌 경우
            # 기존 설정 온도로 다시 설정
            widgets["temp_input"].setText(f"{self.warehouses[wh_id]['target_temp']}")
            ErrorHandler.show_warning_message("입력 오류", "유효한 온도 값을 입력해주세요.")
    
    def handleEnvironmentEvent(self, action, payload):
        """서버로부터 환경 이벤트 처리"""
        try:
            # temperature_update 액션 처리
            if action == "temperature_update" and "warehouse_id" in payload and "temperature" in payload:
                wh_id = payload.get("warehouse_id")
                temperature = payload.get("temperature")
                
                if wh_id in self.warehouses:
                    self.warehouses[wh_id]["current_temp"] = temperature
                    self.update_operation_mode(wh_id)
                    self.update_ui()
                    
                    logger.debug(f"환경 이벤트: 창고 {wh_id} 온도 업데이트 - {temperature}°C")
                    
            # 팬 상태 업데이트 처리 추가
            elif action == "fan_status_update" and "warehouse" in payload:
                wh_id = payload.get("warehouse")
                fan_mode = payload.get("mode", "off")
                fan_speed = payload.get("speed", 0)
                
                if wh_id in self.warehouses:
                    self.warehouses[wh_id]["fan_mode"] = fan_mode
                    self.warehouses[wh_id]["fan_speed"] = fan_speed
                    
                    # 팬 모드에 따라 운영 모드도 동기화
                    if fan_mode == "cool":
                        self.warehouses[wh_id]["mode"] = "냉방 모드"
                    elif fan_mode == "heat":
                        self.warehouses[wh_id]["mode"] = "난방 모드"
                    elif fan_speed == 0:
                        self.warehouses[wh_id]["mode"] = "정지"
                    
                    logger.debug(f"환경 이벤트: 창고 {wh_id} 팬 상태 업데이트 - 모드: {fan_mode}, 속도: {fan_speed}")
                    self.update_ui()
                    
            # 창고 경고 상태 처리 추가
            elif action == "warehouse_warning" and "warehouse" in payload:
                wh_id = payload.get("warehouse")
                warning = payload.get("warning", False)
                
                if wh_id in self.warehouses:
                    status = "경고" if warning else "정상"  
                    self.warehouses[wh_id]["status"] = status
                    logger.debug(f"환경 이벤트: 창고 {wh_id} 경고 상태 - {warning}")
                    self.update_ui()
                    
        except Exception as e:
            logger.error(f"환경 이벤트 처리 오류: {str(e)}")
            self.show_status_message(f"환경 이벤트 처리 오류: {str(e)}", is_error=True)
    
    # === BasePage 메서드 오버라이드 ===
    def on_server_connected(self):
        """서버 연결 성공 시 처리 - 기본 클래스 메서드 오버라이드"""
        self.data_manager.add_notification("서버에 연결되었습니다. 환경 제어 시스템 활성화됨.")
        
        # 서버에서 현재 온도 데이터는 데이터 매니저가 자동으로 가져옴
        
        logger.info("서버 연결 성공")
    
    def on_server_disconnected(self):
        """서버 연결 실패 시 처리 - 기본 클래스 메서드 오버라이드"""
        self.data_manager.add_notification("서버 연결이 끊어졌습니다. 환경 제어 시스템을 사용할 수 없습니다.")
        
        # 연결 안됨 상태로 UI 업데이트
        for wh_id in self.warehouses:
            self.warehouses[wh_id]["status"] = "연결 안됨"
            self.warehouses[wh_id]["mode"] = "정지"
        
        self.update_ui()
        
        logger.warning("서버 연결 실패")