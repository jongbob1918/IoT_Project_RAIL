import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import datetime

from modules.data_manager import DataManager

class DevicesPage(QWidget):
    """장치 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI 로드
        uic.loadUi("ui/widgets/devices.ui", self)
        
        # 데이터 관리자 가져오기
        self.data_manager = DataManager.get_instance()
        
        # 컨베이어 상태 초기화
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
        
        # UI 업데이트 타이머 설정
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # 1초 간격으로 UI 업데이트
        
        # 데이터 변경 이벤트 연결
        self.data_manager.conveyor_status_changed.connect(self.update_conveyor_status)
        self.data_manager.notification_added.connect(self.on_notification)
    
    def update_conveyor_status(self):
        """컨베이어 상태 업데이트"""
        conveyor_status = self.data_manager.get_conveyor_status()
        
        if conveyor_status == 1:  # 가동중
            self.conveyor_status.setText("작동중")
            self.conveyor_status.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 3px; padding: 2px;")
            self.conveyor_running = True
        else:  # 정지
            self.conveyor_status.setText("일시정지")
            self.conveyor_status.setStyleSheet("background-color: #FFC107; color: black; border-radius: 3px; padding: 2px;")
            self.conveyor_running = False
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 컨베이어 관련 알림인 경우 로그에 추가
        if "컨베이어" in message or "벨트" in message or "인식" in message or "분류" in message:
            current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
            log_message = f"{current_time} - {message}"
            self.list_logs.insertItem(0, log_message)
            
            # 최대 50개 로그만 유지
            if self.list_logs.count() > 50:
                self.list_logs.takeItem(self.list_logs.count() - 1)
    
    def update_ui(self):
        """UI 요소 업데이트"""
        try:
            # 서버 연결 객체 가져오기
            server_conn = self.data_manager._server_connection
            
            if server_conn and server_conn.is_connected:
                # 서버에서 최신 데이터 가져오기
                try:
                    # 재고 데이터 가져오기 (실제로는 서버 연결 객체의 메서드 호출)
                    inventory_data = server_conn.get_inventory_data()
                    if inventory_data:
                        # 재고 라벨 업데이트
                        if "A" in inventory_data and "used" in inventory_data["A"]:
                            self.inventory_A.setText(f"{inventory_data['A']['used']}개")
                        if "B" in inventory_data and "used" in inventory_data["B"]:
                            self.inventory_B.setText(f"{inventory_data['B']['used']}개")
                        if "C" in inventory_data and "used" in inventory_data["C"]:
                            self.inventory_C.setText(f"{inventory_data['C']['used']}개")
                
                except Exception as e:
                    print(f"재고 데이터 가져오기 오류: {str(e)}")
                
                # 오류 건수와 총 처리 건수 가져오기
                try:
                    # 실제 환경에서는 서버에서 데이터 가져오기
                    # 에러 건수 업데이트 (예: 서버에서 해당 데이터 제공 시)
                    error_count = server_conn.get_error_count() if hasattr(server_conn, 'get_error_count') else 0
                    self.inventory_error.setText(f"{error_count}개")
                    
                    # 총 처리 건수와 대기 건수 업데이트
                    waiting_count = server_conn.get_waiting_count() if hasattr(server_conn, 'get_waiting_count') else 0
                    total_count = server_conn.get_total_processed() if hasattr(server_conn, 'get_total_processed') else 0
                    
                    self.inventory_waiting.setText(f"{waiting_count}개")
                    self.inventory_waiting_2.setText(f"{total_count}개")
                    
                except Exception as e:
                    print(f"처리 건수 데이터 가져오기 오류: {str(e)}")
                
                # 오류는 항상 빨간색
                if error_count > 0:
                    self.inventory_error.setStyleSheet("color: #F44336; font-weight: bold;")
                else:
                    self.inventory_error.setStyleSheet("color: #757575;")
        
        except Exception as e:
            print(f"UI 업데이트 중 오류: {str(e)}")
    
    def handleSorterEvent(self, action, payload):
        """서버에서 수신한 분류기 이벤트 처리"""
        if action == "status_update":
            is_running = payload.get("is_running", False)
            self.conveyor_running = is_running
            
            # 컨베이어 상태 업데이트
            if is_running:
                self.conveyor_status.setText("작동중")
                self.conveyor_status.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 3px; padding: 2px;")
            else:
                self.conveyor_status.setText("일시정지")
                self.conveyor_status.setStyleSheet("background-color: #FFC107; color: black; border-radius: 3px; padding: 2px;")
        
        elif action == "process_item":
            # 아이템 처리 이벤트 처리
            item = payload.get("item", {})
            barcode = item.get("barcode", "")
            destination = item.get("destination", "")
            timestamp = payload.get("timestamp", QDateTime.currentDateTime().toString("hh:mm:ss"))
            
            # 로그 메시지 생성
            if destination in ["A", "B", "C"]:
                log_message = f"{timestamp} - QR {barcode} 인식됨, 창고 {destination}으로 분류"
            else:
                log_message = f"{timestamp} - QR {barcode} 인식 실패. 분류 오류 발생."
            
            # 로그 목록에 추가
            self.list_logs.insertItem(0, log_message)
            
            # 최대 50개 로그만 유지
            if self.list_logs.count() > 50:
                self.list_logs.takeItem(self.list_logs.count() - 1)
    
    def onConnectionStatusChanged(self, connected):
        """서버 연결 상태 변경 시 호출되는 메서드"""
        if connected:
            # 연결 성공 시 처리
            current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
            log_message = f"{current_time} - 서버에 연결되었습니다."
            self.list_logs.insertItem(0, log_message)
        else:
            # 연결 실패 시 처리
            current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
            log_message = f"{current_time} - 서버 연결이 끊어졌습니다."
            self.list_logs.insertItem(0, log_message)
            
            # 연결이 끊어지면 컨베이어는 정지 상태로 표시
            self.conveyor_status.setText("연결 안됨")
            self.conveyor_status.setStyleSheet("background-color: #757575; color: white; border-radius: 3px; padding: 2px;")
            self.conveyor_running = False