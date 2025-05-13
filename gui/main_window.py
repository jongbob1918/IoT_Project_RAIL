import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic

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