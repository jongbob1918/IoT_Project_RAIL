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
    # 클래스 변수: 오류 다이얼로그가 표시되었는지 추적
    _reconnect_dialog_shown = False

    def __init__(self):
        super().__init__()
        uic.loadUi("ui/main_window.ui", self)
        self.setWindowTitle("RAIL - 물류 관리 시스템")

        # 서버 연결 객체와 데이터 관리자 초기화
        self.init_data_manager()
        self.setup_server_connection()
        
        # 개별 페이지 UI 파일 로드
        self.init_pages()
      
        # 서버 연결 시도
        self.connect_to_server()

        # 대시보드 스타일 설정
        self.setup_ui_styles()

        # 이벤트 핸들러 연결
        self.connect_event_handlers()

        # 초기 페이지 설정
        self.stackedWidget.setCurrentWidget(self.page_dashboard)
        self.activate_button(self.btn_dashboard, self.page_dashboard)

        # 상태바에 서버 연결 상태 표시 추가
        self.server_status_label = QLabel("서버 연결 상태: 연결 시도 중...")
        self.statusBar().addWidget(self.server_status_label)

        # 서버 연결 시도 - 비동기적으로 처리
        QTimer.singleShot(100, self.connect_to_server)  # 약간의 지연 후 연결 시도
            
    def init_data_manager(self):
        """데이터 관리자 초기화"""
        self.data_manager = DataManager.get_instance()
    
    def setup_server_connection(self):
        """서버 연결 객체 초기화"""
        # config.py 파일의 설정과 일치하도록 서버 호스트 및 포트 설정
        server_host = "localhost"  # config에서는 0.0.0.0으로 설정되어 있지만 클라이언트에서는 localhost 사용
        server_port = 8000         # config의 SERVER_PORT와 일치
        
        # 서버 연결 객체 생성
        self.server_conn = ServerConnection(server_host, server_port)
        
        # 데이터 관리자에 서버 연결 객체 설정
        self.data_manager.set_server_connection(self.server_conn)
        
        # 서버 연결 상태 변경 이벤트 연결
        self.server_conn.connectionStatusChanged.connect(self.on_connection_status_changed)
        
        # 서버 이벤트 각 페이지에 연결
        self.setup_event_handlers()
    
    def connect_to_server(self):
        """서버에 연결 시도 - 비동기적으로 처리"""
        try:
            if hasattr(self, 'server_conn'):
                # 연결 시도
                if not self.server_conn.connect_to_server():
                    # 연결 실패 시에도 UI는 계속 표시
                    print("서버 연결 실패. UI는 제한된 기능으로 계속 실행됩니다.")
                    self.server_status_label.setText("서버 연결 상태: 연결 안됨")
                    self.server_status_label.setStyleSheet("color: red;")
                    
                    # 연결 상태 업데이트
                    self.data_manager.set_offline_mode(True)
                    
                    # 자동 재연결 타이머 시작
                    self.server_conn.start_reconnect_timer()
            else:
                print("오류: 서버 연결 객체가 초기화되지 않았습니다.")
                self.server_status_label.setText("서버 연결 상태: 초기화 오류")
                self.server_status_label.setStyleSheet("color: red;")
                
                # 연결 상태 업데이트
                self.data_manager.set_offline_mode(True)
        except Exception as e:
            print(f"서버 연결 시도 중 오류: {str(e)}")
            self.server_status_label.setText("서버 연결 상태: 오류")
            self.server_status_label.setStyleSheet("color: red;")
            
            # 연결 상태 업데이트
            self.data_manager.set_offline_mode(True)   
            
    def init_pages(self):
        """페이지들 초기화"""
        self.page_dashboard = DashboardPage()
        self.page_devices = DevicesPage()
        self.page_environment = EnvironmentPage()
        self.page_inventory = InventoryPage()
        self.page_expiration = ExpirationPage()     
        self.page_access = AccessPage()       

        # 각 페이지에 서버 연결 상태 변경 이벤트 연결
        self.pages = [self.page_dashboard, self.page_devices, self.page_environment, 
                    self.page_inventory, self.page_expiration, self.page_access]
        
        # 페이지에 연결 상태 변경 이벤트 연결
        for page in self.pages:
            self.server_conn.connectionStatusChanged.connect(page.onConnectionStatusChanged)
        
        
        # stackedWidget에 페이지 추가
        self.stackedWidget.addWidget(self.page_dashboard)
        self.stackedWidget.addWidget(self.page_devices)
        self.stackedWidget.addWidget(self.page_environment)
        self.stackedWidget.addWidget(self.page_inventory)
        self.stackedWidget.addWidget(self.page_expiration)        
        self.stackedWidget.addWidget(self.page_access)
    
    def setup_ui_styles(self):
        """UI 스타일 설정"""
        # 대시보드 스타일 설정
        self.stackedWidget.setStyleSheet("background-color: #ffffff;")        
        # 사이드바 스타일 설정
        self.sidebarWidget.setStyleSheet("background-color: #2c2c2c;")
        # 사이드바 버튼 리스트
        self.buttons = [self.btn_dashboard, self.btn_devices, self.btn_environment, 
                       self.btn_inventory, self.btn_expiration, self.btn_access]
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
    
    def connect_event_handlers(self):
        """이벤트 핸들러 연결"""
        # 사이드바 버튼 클릭 이벤트 연결
        self.btn_dashboard.clicked.connect(lambda: self.activate_button(self.btn_dashboard, self.page_dashboard))
        self.btn_devices.clicked.connect(lambda: self.activate_button(self.btn_devices, self.page_devices))
        self.btn_environment.clicked.connect(lambda: self.activate_button(self.btn_environment, self.page_environment))
        self.btn_inventory.clicked.connect(lambda: self.activate_button(self.btn_inventory, self.page_inventory))
        self.btn_expiration.clicked.connect(lambda: self.activate_button(self.btn_expiration, self.page_expiration))        
        self.btn_access.clicked.connect(lambda: self.activate_button(self.btn_access, self.page_access))
    
    def setup_event_handlers(self):
        """서버 이벤트 핸들러 설정"""
        # 서버에서 오는 이벤트를 각 페이지로 라우팅
        self.server_conn.eventReceived.connect(self.on_server_event)
    
    def on_server_event(self, category, action, payload):
        """서버 이벤트 수신 시 각 페이지에 전달"""
        # API 구조와 일치하도록 업데이트
        if category == "sorter" and hasattr(self.page_devices, "handleSorterEvent"):
            self.page_devices.handleSorterEvent(action, payload)
            
            # 대시보드에도 일부 이벤트 전달
            if action == "status_update" and "is_running" in payload:
                self.data_manager._conveyor_status = 1 if payload["is_running"] else 0
                self.data_manager.conveyor_status_changed.emit()
                
        elif category == "environment" and hasattr(self.page_environment, "handleEnvironmentEvent"):
            self.page_environment.handleEnvironmentEvent(action, payload)
            
            # 환경 데이터 대시보드에도 전달
            if action == "temperature_update" and payload.get("warehouse_id") in self.data_manager._warehouse_data:
                warehouse_id = payload.get("warehouse_id")
                temperature = payload.get("current_temp")  # current_temp 필드명으로 수정
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
                    
        elif category == "inventory" and hasattr(self.page_inventory, "handleInventoryEvent"):
            # 인벤토리 이벤트 처리 (필요시 구현)
            pass
            
        elif category == "expiry" and hasattr(self.page_expiration, "handleExpiryEvent"):
            # 유통기한 이벤트 처리 (필요시 구현)
            pass
            
        elif category == "access" and hasattr(self.page_access, "handleAccessEvent"):
            # 출입 이벤트 처리 (필요시 구현)
            pass
    
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
        
        # 연결 실패 시 재연결 다이얼로그 표시 (API 호출 오류가 아닌 경우)
        if not connected and not message.startswith("서버 요청 오류") and not message.startswith("재연결 시도 횟수 초과"):
            self.show_reconnect_dialog(message)
    
    def notify_connection_to_pages(self, connected):
        """각 페이지에 연결 상태 변경 알림"""
        message = "연결됨" if connected else "연결 안됨"
        
        # 데이터 관리자에 오프라인 모드 설정
        if not connected:
            self.data_manager.set_offline_mode(True)
        else:
            self.data_manager.set_offline_mode(False)
            
        # 로그에 기록
        print(f"서버 연결 상태 변경: {message}")
    
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
            # 재연결 시도 - 자동 재연결 타이머 시작
            if hasattr(self, 'server_conn'):
                self.server_conn.start_reconnect_timer()
            else:
                print("오류: 서버 연결 객체가 초기화되지 않았습니다.")

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
    
    def closeEvent(self, event):
        """애플리케이션 종료 시 호출되는 이벤트 핸들러"""
        # 서버 연결 종료
        if hasattr(self, 'server_conn'):
            self.server_conn.disconnect_from_server()
        
        # 데이터 관리자 종료
        if hasattr(self, 'data_manager'):
            self.data_manager.shutdown()
        
        # 기본 종료 이벤트 처리
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = WindowClass()
    win.show()
    sys.exit(app.exec())