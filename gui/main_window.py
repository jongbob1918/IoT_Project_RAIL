import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic

from modules.server_connection import ServerConnection
from modules.data_manager import DataManager

from modules.dashboard import DashboardPage
from modules.devices import DevicesPage
from modules.environment import EnvironmentPage
from modules.inventory import InventoryPage
from modules.expiration import ExpirationPage
from modules.access import AccessPage

class WindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/main_window.ui", self)
        self.setWindowTitle("RAIL - 물류 관리 시스템")

        # 서버 연결 객체와 데이터 관리자 초기화
        self.setup_server_connection()
        
        # 데이터 관리자 인스턴스 가져오기
        self.data_manager = DataManager.get_instance()

        # 개별 페이지 UI 파일 로드
        self.page_dashboard = DashboardPage()
        self.page_devices = DevicesPage()
        self.page_environment = EnvironmentPage()
        self.page_inventory = InventoryPage()
        self.page_expiration = ExpirationPage()     
        self.page_access = AccessPage()       
      
        # stackedWidget에 페이지 추가
        self.stackedWidget.addWidget(self.page_dashboard)
        self.stackedWidget.addWidget(self.page_devices)
        self.stackedWidget.addWidget(self.page_environment)
        self.stackedWidget.addWidget(self.page_inventory)
        self.stackedWidget.addWidget(self.page_expiration)        
        self.stackedWidget.addWidget(self.page_access)

        # 서버 연결 시도
        self.connect_to_server()

        # 대시보드 스타일 설정
        self.stackedWidget.setStyleSheet("background-color: #ffffff;")        
        # 사이드바 스타일 설정
        self.sidebarWidget.setStyleSheet("background-color: #2c2c2c;")
        # 사이드바 버튼 리스트
        self.buttons = [self.btn_dashboard, self.btn_devices, self.btn_environment, self.btn_inventory, self.btn_expiration, self.btn_access]
        # 사이드바 버튼 기본 스타일 설정
        for btn in self.buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2c2c2c;
                    color: #eeeeee;
                    border: none;
                    border-radius: 0px;
                    font-size: 14px;
                }           
            """)

        # 사이드바 버튼 클릭 이벤트 연결
        self.btn_dashboard.clicked.connect(lambda: self.activate_button(self.btn_dashboard, self.page_dashboard))
        self.btn_devices.clicked.connect(lambda: self.activate_button(self.btn_devices, self.page_devices))
        self.btn_environment.clicked.connect(lambda: self.activate_button(self.btn_environment, self.page_environment))
        self.btn_inventory.clicked.connect(lambda: self.activate_button(self.btn_inventory, self.page_inventory))
        self.btn_expiration.clicked.connect(lambda: self.activate_button(self.btn_expiration, self.page_expiration))        
        self.btn_access.clicked.connect(lambda: self.activate_button(self.btn_access, self.page_access))

        # 초기 페이지 설정
        self.stackedWidget.setCurrentWidget(self.page_dashboard)
        self.activate_button(self.btn_dashboard, self.page_dashboard)

    def setup_server_connection(self):
        """서버 연결 객체 초기화"""
        # 서버 호스트 및 포트 설정
        server_host = "localhost"
        server_port = 8000
        
        # 서버 연결 객체 생성
        self.server_conn = ServerConnection(server_host, server_port)
        
        # 서버 연결 상태 변경 이벤트 연결
        self.server_conn.connectionStatusChanged.connect(self.on_connection_status_changed)
        
        # 서버 이벤트 각 페이지에 연결
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """서버 이벤트 핸들러 설정"""
        # 각 이벤트 카테고리 핸들러 연결
        self.server_conn.eventReceived.connect(self.on_server_event)
    
    def on_server_event(self, category, action, payload):
        """서버 이벤트 수신 시 각 페이지에 전달"""
        # 각 페이지에 관련 이벤트 전달
        if category == "sorter" and hasattr(self.page_devices, "handleSorterEvent"):
            self.page_devices.handleSorterEvent(action, payload)
            
            # 대시보드에도 일부 이벤트 전달
            if action == "status_update" and "is_running" in payload:
                # 대시보드에 컨베이어 상태 전달
                # 데이터 관리자를 통해 상태 업데이트
                self.data_manager._conveyor_status = 1 if payload["is_running"] else 0
                self.data_manager.conveyor_status_changed.emit()
        
        elif category == "environment" and hasattr(self.page_environment, "handleEnvironmentEvent"):
            self.page_environment.handleEnvironmentEvent(action, payload)
            
            # 환경 데이터 대시보드에도 전달
            if action == "temperature_update" and payload.get("warehouse_id") in self.data_manager._warehouse_data:
                warehouse_id = payload.get("warehouse_id")
                temperature = payload.get("temperature")
                if temperature is not None:
                    self.data_manager._warehouse_data[warehouse_id]["temperature"] = temperature
                    # 상태 업데이트
                    min_temp = self.data_manager.temp_thresholds[warehouse_id]["min"]
                    max_temp = self.data_manager.temp_thresholds[warehouse_id]["max"]
                    if min_temp <= temperature <= max_temp:
                        self.data_manager._warehouse_data[warehouse_id]["status"] = "정상"
                    else:
                        self.data_manager._warehouse_data[warehouse_id]["status"] = "주의"
                    self.data_manager.warehouse_data_changed.emit()
    
    def on_connection_status_changed(self, connected, message):
        """서버 연결 상태 변경 이벤트 핸들러"""
        # 라벨이 존재하는지 확인
        if hasattr(self, 'server_status_label'):
            if connected:
                self.server_status_label.setText("서버 연결 상태: 연결됨")
                self.server_status_label.setStyleSheet("color: green;")
            else:
                self.server_status_label.setText(f"서버 연결 상태: {message}")
                self.server_status_label.setStyleSheet("color: red;")
        else:
            # 개발자 콘솔에 로깅
            print(f"서버 연결 상태: {'연결됨' if connected else message}")
        
        # 각 페이지에 연결 상태 알림
        self.notify_connection_to_pages(connected)
        
        # 데이터 관리자에 서버 연결 상태 업데이트
        self.data_manager._server_connected = connected
        
    def notify_connection_to_pages(self, connected):
        """각 페이지에 연결 상태 알림"""
        for page in [self.page_dashboard, self.page_devices, self.page_environment, 
                    self.page_inventory, self.page_expiration, self.page_access]:
            if hasattr(page, "onConnectionStatusChanged"):
                page.onConnectionStatusChanged(connected)

    def connect_to_server(self):
        """서버에 연결 시도"""
        if hasattr(self, 'server_conn'):
            self.server_conn.connect_to_server()
        else:
            # server_conn이 생성되지 않은 경우 오류 표시
            self.server_status_label.setText("서버 연결 상태: 초기화 오류")
            self.server_status_label.setStyleSheet("color: red;")

    def show_reconnect_dialog(self, error_message):
        """서버 재연결 다이얼로그 표시"""
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Icon.Warning)
        msgBox.setWindowTitle("서버 연결 오류")
        msgBox.setText(f"서버 연결에 문제가 발생했습니다:\n{error_message}")
        msgBox.setInformativeText("서버에 재연결을 시도하시겠습니까?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msgBox.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if msgBox.exec() == QMessageBox.StandardButton.Yes:
            # 재연결 시도
            self.connect_to_server()

    # 사이드바 버튼 클릭 시 배경 활성화
    def activate_button(self, clicked_button, target_page):
        self.stackedWidget.setCurrentWidget(target_page)

        for btn in self.buttons:
            if btn == clicked_button:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4285F4;
                        color: #ffffff;
                        border: none;
                        border-radius: 0px;
                        font-size: 14px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2c2c2c;
                        color: #eaeaea;
                        border: none;
                        border-radius: 0px;
                        font-size: 14px;
                    }
                """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = WindowClass()
    win.show()
    sys.exit(app.exec())