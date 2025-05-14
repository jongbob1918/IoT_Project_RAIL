import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import logging

from modules.server_connection import ServerConnection
from modules.data_manager import DataManager
from modules.error_handler import ErrorHandler  # 오류 처리 모듈 추가

from modules.dashboard import DashboardPage
from modules.devices import DevicesPage
from modules.environment import EnvironmentPage
from modules.inventory import InventoryPage
from modules.expiration import ExpirationPage
from modules.access import AccessPage

# 로깅 설정
logger = logging.getLogger(__name__)

class WindowClass(QMainWindow):
    # 클래스 변수: 오류 다이얼로그가 표시되었는지 추적
    _reconnect_dialog_shown = False
    
    # 상수 정의 - 연결 상태 알림 간격
    CONNECTION_RETRY_INTERVAL = 30  # 서버 연결 재시도 시간 간격 (초)

    def __init__(self):
        super().__init__()
        uic.loadUi("ui/main_window.ui", self)
        self.setWindowTitle("RAIL - 물류 관리 시스템")
        
        # 연결 상태 관련 변수 초기화
        self.last_connection_attempt = 0  # 마지막 연결 시도 시간
        self.last_reconnect_dialog_time = 0  # 마지막 재연결 다이얼로그 표시 시간

        # 상태바에 서버 연결 상태 표시 추가
        self.server_status_label = QLabel()
        self.statusBar().addWidget(self.server_status_label)
        self.server_status_label.setText("서버 연결 상태: 연결 시도 중...")

        # 데이터 관리자 초기화
        self.init_data_manager()
        
        # 서버 연결 설정
        self.setup_server_connection()
        
        # 개별 페이지 UI 파일 로드
        self.init_pages()
    
        # 약간의 지연 후 연결 시도
        QTimer.singleShot(100, self.connect_to_server)

        # 대시보드 스타일 설정
        self.setup_ui_styles()

        # 이벤트 핸들러 연결
        self.connect_event_handlers()

        # 초기 페이지 설정
        self.stackedWidget.setCurrentWidget(self.page_dashboard)
        self.activate_button(self.btn_dashboard, self.page_dashboard)
        
        # 자동 재연결 타이머 설정
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self.check_reconnect)
        self.reconnect_timer.start(5000)  # 5초마다 연결 상태 확인
      
    def init_data_manager(self):
        """데이터 관리자 초기화"""
        self.data_manager = DataManager.get_instance()
    
    def setup_server_connection(self):
        """서버 연결 객체 초기화"""
        # config.py 파일의 설정과 일치하도록 서버 호스트 및 포트 설정
        server_host = "192.168.2.2"  # config에서는 127.0.0.1으로 설정
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
        # 현재 시간 기록
        current_time = QDateTime.currentMSecsSinceEpoch() / 1000  # 초 단위 변환
        self.last_connection_attempt = current_time
            
        try:
            if hasattr(self, 'server_conn'):
                # 연결 시도
                if not self.server_conn.connect_to_server():
                    # 연결 실패 시에도 UI는 계속 표시
                    logger.warning("서버 연결 실패. UI는 제한된 기능으로 계속 실행됩니다.")
                    self.server_status_label.setText("서버 연결 상태: 연결 안됨")
                    self.server_status_label.setStyleSheet("color: red;")
                    
                    # 처음 연결 실패 시에만 다이얼로그 표시
                    if not self._reconnect_dialog_shown:
                        self._reconnect_dialog_shown = True
                        self.show_reconnect_dialog("서버에 연결할 수 없습니다.")
                    
                    # 재연결 타이머 시작
                    self.server_conn.start_reconnect_timer()
            else:
                logger.error("오류: 서버 연결 객체가 초기화되지 않았습니다.")
                self.server_status_label.setText("서버 연결 상태: 초기화 오류")
                self.server_status_label.setStyleSheet("color: red;")
        except Exception as e:
            logger.error(f"서버 연결 시도 중 오류: {str(e)}")
            self.server_status_label.setText("서버 연결 상태: 오류")
            self.server_status_label.setStyleSheet("color: red;")
    
    def check_reconnect(self):
        """자동 재연결이 필요한지 확인"""
        # 이미 연결되어 있으면 재연결 시도 안함
        if hasattr(self, 'server_conn') and self.server_conn.is_connected:
            return
            
        # 현재 시간 확인
        current_time = QDateTime.currentMSecsSinceEpoch() / 1000  # 초 단위 변환
        
        # 마지막 연결 시도 후 일정 시간이 지났는지 확인 (30초)
        if (current_time - self.last_connection_attempt) > self.CONNECTION_RETRY_INTERVAL:
            # 마지막 재연결 다이얼로그 표시 후 충분한 시간이 지났으면 다시 다이얼로그 표시 (60초)
            if (current_time - self.last_reconnect_dialog_time) > 60:
                # 다이얼로그 표시 여부는 상황에 따라 결정
                pass
            
            # 연결 재시도
            logger.info("자동 재연결 시도 중...")
            self.connect_to_server()
            
    def init_pages(self):
        """페이지들 초기화"""
        # 데이터 관리자 참조 전달
        self.page_dashboard = DashboardPage(data_manager=self.data_manager)
        self.page_devices = DevicesPage(data_manager=self.data_manager)
        self.page_environment = EnvironmentPage(data_manager=self.data_manager)
        self.page_inventory = InventoryPage(data_manager=self.data_manager)
        self.page_expiration = ExpirationPage(data_manager=self.data_manager)     
        self.page_access = AccessPage(data_manager=self.data_manager)       

        # 각 페이지에 서버 연결 상태 변경 이벤트 연결
        self.pages = [self.page_dashboard, self.page_devices, self.page_environment, 
                    self.page_inventory, self.page_expiration, self.page_access]
        
        # 페이지에 연결 상태 변경 이벤트 연결
        for page in self.pages:
            if hasattr(page, 'onConnectionStatusChanged'):
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
            # access 카테고리의 이벤트 처리
            if hasattr(self.page_access, "handleAccessEvent"):
                self.page_access.handleAccessEvent(action, payload)
    
    def on_connection_status_changed(self, connected, message):
        """서버 연결 상태 변경 이벤트 핸들러"""
        # 라벨이 존재하는지 확인
        if hasattr(self, 'server_status_label'):
            if connected:
                self.server_status_label.setText("서버 연결 상태: 연결됨")
                self.server_status_label.setStyleSheet("color: green;")
                self._reconnect_dialog_shown = False  # 연결 성공 시 다이얼로그 표시 플래그 초기화
            else:
                self.server_status_label.setText(f"서버 연결 상태: 연결 안됨")
                self.server_status_label.setStyleSheet("color: red;")
                
                # 디버그용 메시지 (상세 메시지는 UI에 표시하지 않음)
                logger.error(f"서버 연결 상태 변경: {message}")
        else:
            # 개발자 콘솔에 로깅
            logger.info(f"서버 연결 상태: {'연결됨' if connected else message}")
        
        # 각 페이지에 연결 상태 알림 (상세 구현은 페이지에서 처리)
        self.notify_connection_to_pages(connected)
        
        # 데이터 관리자에 서버 연결 상태 업데이트
        self.data_manager._server_connected = connected
        
        # 연결 실패 시 재연결 다이얼로그 표시 (일정 조건 충족 시)
        if not connected and not message.startswith("서버 요청 오류") and not message.startswith("재연결 시도 횟수 초과"):
            # 마지막 다이얼로그 표시 이후 충분한 시간이 지났는지 확인 (60초)
            current_time = QDateTime.currentMSecsSinceEpoch() / 1000  # 초 단위 변환
            if (current_time - self.last_reconnect_dialog_time) > 60:
                # 최초 연결 시도 시에만 다이얼로그 표시
                if not self._reconnect_dialog_shown:
                    self.show_reconnect_dialog(message)
                    self._reconnect_dialog_shown = True
    
    def notify_connection_to_pages(self, connected):
        """각 페이지에 연결 상태 변경 알림"""
        # 로그에 기록
        logger.info(f"서버 연결 상태 변경: {'연결됨' if connected else '연결 안됨'}")
    
    def show_reconnect_dialog(self, error_message):
        """서버 재연결 다이얼로그 표시 - 제한적으로 표시"""
        # 현재 시간 기록 (중복 다이얼로그 방지)
        current_time = QDateTime.currentMSecsSinceEpoch() / 1000  # 초 단위 변환
        self.last_reconnect_dialog_time = current_time
        
        # 사용자에게 간결한 메시지 표시
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Icon.Warning)
        msgBox.setWindowTitle("서버 연결 오류")
        msgBox.setText("서버 연결에 문제가 발생했습니다.")
        msgBox.setInformativeText("서버에 재연결을 시도하시겠습니까?")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msgBox.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if msgBox.exec() == QMessageBox.StandardButton.Yes:
            # 재연결 시도 - 자동 재연결 타이머 시작
            if hasattr(self, 'server_conn'):
                self.server_conn.start_reconnect_timer()
                # 재연결 다이얼로그가 표시되었다는 플래그 설정
                self._reconnect_dialog_shown = True
            else:
                logger.error("오류: 서버 연결 객체가 초기화되지 않았습니다.")
                ErrorHandler.show_error_message("연결 오류", "서버 연결 객체가 초기화되지 않았습니다.")

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