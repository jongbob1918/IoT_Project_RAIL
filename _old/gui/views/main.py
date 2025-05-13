import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QListWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6 import uic

# UI 파일이 위치한 디렉토리 경로 설정
UI_DIR = os.path.dirname(os.path.abspath(__file__))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("풀필먼트 시스템")
        self.setMinimumSize(800, 600)
        
        # 모든 UI 파일 로드 (절대 경로 사용)
        try:
            self.dashboard_widget = uic.loadUi(os.path.join(UI_DIR, "dashboard.ui"))
            self.device_management_widget = uic.loadUi(os.path.join(UI_DIR, "device_management.ui"))
            self.warehouse_environment_widget = uic.loadUi(os.path.join(UI_DIR, "warehouse_environment.ui"))
            self.inventory_widget = uic.loadUi(os.path.join(UI_DIR, "inventory.ui"))
            self.expiry_management_widget = uic.loadUi(os.path.join(UI_DIR, "expiry_management.ui"))
            self.access_management_widget = uic.loadUi(os.path.join(UI_DIR, "access_management.ui"))
            
            # 물품 리스트 화면 (서브화면)
            self.product_list_widget = uic.loadUi(os.path.join(UI_DIR, "product_list.ui"))
        
        except Exception as e:
            print(f"UI 파일 로드 중 오류 발생: {e}")
            sys.exit(1)
            
        # 스택 위젯 설정 - 메인 화면들
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.stacked_widget.addWidget(self.dashboard_widget)
        self.stacked_widget.addWidget(self.device_management_widget)
        self.stacked_widget.addWidget(self.warehouse_environment_widget)
        self.stacked_widget.addWidget(self.inventory_widget)
        self.stacked_widget.addWidget(self.expiry_management_widget)
        self.stacked_widget.addWidget(self.access_management_widget)
        self.stacked_widget.addWidget(self.product_list_widget)
        
        # 각 화면의 메뉴 리스트 항목 클릭 이벤트 연결
        self.connect_menu_lists()
        
        # 물품 리스트 관련 버튼 연결
        self.inventory_widget.productListButton.clicked.connect(self.show_product_list)
        self.product_list_widget.backButton.clicked.connect(self.back_to_inventory)
        
    def connect_menu_lists(self):
        # 모든 메뉴 리스트 위젯에 클릭 이벤트 연결
        self.dashboard_widget.menuList.itemClicked.connect(self.navigate_menu)
        self.device_management_widget.menuList.itemClicked.connect(self.navigate_menu)
        self.warehouse_environment_widget.menuList.itemClicked.connect(self.navigate_menu)
        self.inventory_widget.menuList.itemClicked.connect(self.navigate_menu)
        self.expiry_management_widget.menuList.itemClicked.connect(self.navigate_menu)
        self.access_management_widget.menuList.itemClicked.connect(self.navigate_menu)
    
    def navigate_menu(self, item):
        # 메뉴 항목 클릭 시 해당 화면으로 이동
        menu_text = item.text()
        
        if menu_text == "대시보드":
            self.stacked_widget.setCurrentWidget(self.dashboard_widget)
        elif menu_text == "장치 관리":
            self.stacked_widget.setCurrentWidget(self.device_management_widget)
        elif menu_text == "창고 환경":
            self.stacked_widget.setCurrentWidget(self.warehouse_environment_widget)
        elif menu_text == "재고 관리":
            self.stacked_widget.setCurrentWidget(self.inventory_widget)
        elif menu_text == "유통기한 관리":
            self.stacked_widget.setCurrentWidget(self.expiry_management_widget)
        elif menu_text == "입출입 관리":
            self.stacked_widget.setCurrentWidget(self.access_management_widget)
    
    def show_product_list(self):
        # 물품 리스트 화면으로 이동
        self.stacked_widget.setCurrentWidget(self.product_list_widget)
    
    def back_to_inventory(self):
        # 재고 관리 화면으로 돌아가기
        self.stacked_widget.setCurrentWidget(self.inventory_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())