import sys
import os
import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic

from modules.data_manager import DataManager

class DashboardPage(QWidget):
    """대시보드 페이지 위젯 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 로드
        uic.loadUi("ui/widgets/dashboard.ui", self)
        
        # 데이터 관리자 가져오기
        self.data_manager = DataManager.get_instance()
        
        # 타이머 설정
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_and_status)
        self.timer.start(1000)  # 1초마다 업데이트
        
        # 초기화
        self.setupProgressBars()
        self.updateWarehouseStatus()
        
        # 알림 리스트 설정
        self.setupNotificationLabels()
        
        # 유통기한 초기화
        self.setExpiredCount(0)
        self.setExpiringSoonCount(0)
        
        # 컨베이어 초기화
        self.updateConveyorStatus()  # 상태 업데이트 방식 변경
        
        # 데이터 변경 이벤트 연결
        self.data_manager.warehouse_data_changed.connect(self.updateWarehouseStatus)
        self.data_manager.expiry_data_changed.connect(self.updateExpiryStatus)
        self.data_manager.conveyor_status_changed.connect(self.updateConveyorStatus)
        self.data_manager.notification_added.connect(self.addNotification)
        self.data_manager.inventory_data_changed.connect(self.updateInventoryStatus)
    
    def setupProgressBars(self):
        """프로그레스바 스타일 설정 및 초기화"""
        progress_style = """
            QProgressBar {
                border: 1px solid grey;
                border-radius: 3px;
                text-align: center;
            }
            
            QProgressBar::chunk {
                background-color: #2196F3;
            }
        """
        
        for warehouse in ['A', 'B', 'C']:
            bar = getattr(self, f"warehouse_{warehouse}_bar")
            bar.setStyleSheet(progress_style)
            
            # 초기값 설정
            bar.setValue(0)
    
    def setupNotificationLabels(self):
        """알림 라벨 초기화"""
        # 알림 라벨에 기본 스타일 적용
        for i in range(1, 5):
            if hasattr(self, f"noti_recent_{i}"):
                notification_label = getattr(self, f"noti_recent_{i}")
                notification_label.setText("-")
    
    def update_time_and_status(self):
        """현재 시간 및 입고 현황 업데이트"""
        # 현재 시간 업데이트
        current_datetime = QDateTime.currentDateTime()
        self.datetime.setText(current_datetime.toString("yyyy.MM.dd. hh:mm:ss"))
        
        # 입고 현황 업데이트
        self.updateInventoryStatus()
    
    def updateInventoryStatus(self):
        """입고 현황 업데이트"""
        today_input = self.data_manager.get_today_input()
        self.in_total.setText(f"{today_input['total']}건")
        self.in_warehouse_A.setText(f"{today_input['A']}건")
        self.in_warehouse_B.setText(f"{today_input['B']}건")
        self.in_warehouse_C.setText(f"{today_input['C']}건")
    
    def updateWarehouseStatus(self):
        """창고 상태 업데이트"""
        warehouse_data = self.data_manager.get_warehouse_data()
        
        for warehouse_id in warehouse_data:
            # 온도 표시 업데이트
            temp_label = getattr(self, f"warehouse_{warehouse_id}_temp")
            temp_label.setText(f"온도 {warehouse_data[warehouse_id]['temperature']:.1f}°C")
            
            # 프로그레스바 업데이트
            progress_bar = getattr(self, f"warehouse_{warehouse_id}_bar")
            progress_bar.setValue(warehouse_data[warehouse_id]['usage_percent'])
            
            # 상태 표시 업데이트
            status_label = getattr(self, f"warehouse_{warehouse_id}_status")
            status_label.setText(f"상태: {warehouse_data[warehouse_id]['status']}")
            
            # 상태에 따른 색상 설정
            if warehouse_data[warehouse_id]['status'] == "정상":
                status_label.setStyleSheet("""
                    background-color: #CCFFCC;
                    border-radius: 5px;
                    padding: 2px;
                """)
            elif warehouse_data[warehouse_id]['status'] == "주의":
                status_label.setStyleSheet("""
                    background-color: #FFFF99;
                    border-radius: 5px;
                    padding: 2px;
                """)
            else:
                status_label.setStyleSheet("""
                    background-color: #FFCCCC;
                    border-radius: 5px;
                    padding: 2px;
                """)
    
    def updateExpiryStatus(self):
        """유통기한 정보 업데이트"""
        expiry_data = self.data_manager.get_expiry_data()
        self.setExpiredCount(expiry_data['over'])
        self.setExpiringSoonCount(expiry_data['soon'])
    
    def updateConveyorStatus(self):
        """컨베이어 상태 업데이트"""
        conveyor_status = self.data_manager.get_conveyor_status()
        self.setConveyorStatus(conveyor_status)
    
    def setExpiredCount(self, count):
        """유통기한 경과 상품 수량 설정"""
        self.exp_over.setText(f"경과 {count}건")
    
    def setExpiringSoonCount(self, count):
        """유통기한 임박 상품 수량 설정"""
        self.exp_soon.setText(f"임박 {count}건")
    
    def setConveyorStatus(self, is_on):
        """컨베이어 상태 설정 - 수정된 버전 (올바른 상태 표시)"""
        # 데이터 관리자와 일치하도록 변경
        # 0: 정지, 1: 가동중
        status = "가동중" if is_on == 1 else "정지"
        self.conveyor_status.setText(f"{status}")
        
        if is_on == 1:  # 가동중
            self.conveyor_status.setStyleSheet("""
                background-color: #CCFFCC;
                border-radius: 3px;
                padding: 2px;
            """)
        else:  # 정지
            self.conveyor_status.setStyleSheet("""                
                background-color: #CCCCCC;
                border-radius: 3px;
                padding: 2px;
            """)

    def addNotification(self, message):
        """알림 목록에 새 알림 추가"""
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        notification = f"[{current_time}] {message}"
        
        # 최신 알림을 맨 위에 표시
        for i in range(4, 1, -1):
            if hasattr(self, f"noti_recent_{i}") and hasattr(self, f"noti_recent_{i-1}"):
                prev_label = getattr(self, f"noti_recent_{i-1}")
                current_label = getattr(self, f"noti_recent_{i}")
                current_label.setText(prev_label.text())
        
        # 가장 최신 알림을 첫 번째 라벨에 설정
        if hasattr(self, "noti_recent_1"):
            self.noti_recent_1.setText(notification)
            
    def onConnectionStatusChanged(self, connected):
        """서버 연결 상태 변경 시 호출되는 메서드"""
        if connected:
            # 연결 성공 시 처리
            self.addNotification("서버에 연결되었습니다.")
        else:
            # 연결 실패 시 처리
            self.addNotification("서버 연결이 끊어졌습니다.")