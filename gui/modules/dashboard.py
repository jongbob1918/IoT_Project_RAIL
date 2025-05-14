import sys
import os
import datetime
import logging
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic

from modules.base_page import BasePage
from modules.data_manager import DataManager
from modules.error_handler import ErrorHandler

# 로깅 설정
logger = logging.getLogger(__name__)

class DashboardPage(BasePage):
    """대시보드 페이지 위젯 클래스"""
    
    def __init__(self, parent=None, data_manager=None):
        """
        대시보드 페이지 초기화
        
        Args:
            parent: 부모 위젯
            data_manager: 데이터 관리자 객체 (의존성 주입)
        """
        super().__init__(parent)
        self.page_name = "대시보드"  # 기본 클래스 속성 설정
        
        # UI 로드
        uic.loadUi("ui/widgets/dashboard.ui", self)
        
        # 데이터 관리자 설정 (의존성 주입 패턴 적용)
        self.data_manager = data_manager if data_manager else DataManager.get_instance()
        self.set_data_manager(self.data_manager)  # 부모 클래스 메서드 호출
        
        # 시간 표시를 위한 타이머 설정 (필수 기능이므로 유지)
        self.setup_time_timer()
        
        # 초기화
        self.setup_progress_bars()
        self.update_warehouse_status()
        
        # 알림 리스트 설정
        self.setup_notification_list()
        
        # 유통기한 초기화
        self.set_expired_count(0)
        self.set_expiring_soon_count(0)
        
        # 컨베이어 초기화
        self.update_conveyor_status()
        
        # 데이터 변경 이벤트 연결
        self.connect_data_signals()
        
        logger.info("대시보드 페이지 초기화 완료")
    
    def setup_time_timer(self):
        """시간 표시용 타이머 설정"""
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)  # 1초마다 시간만 업데이트
    
    def connect_data_signals(self):
        """데이터 변경 이벤트 연결"""
        self.data_manager.warehouse_data_changed.connect(self.update_warehouse_status)
        self.data_manager.expiry_data_changed.connect(self.update_expiry_status)
        self.data_manager.conveyor_status_changed.connect(self.update_conveyor_status)
        self.data_manager.notification_added.connect(self.add_notification)
        self.data_manager.inventory_data_changed.connect(self.update_inventory_status)
    
    def setup_progress_bars(self):
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
    
    def setup_notification_list(self):
        """알림 목록 초기화"""
        # QListWidget 스타일 설정
        if hasattr(self, 'noti_list'):
            self.noti_list.setAlternatingRowColors(True)
            self.noti_list.setStyleSheet("""
                QListWidget {
                    background-color: #f8f8f8; 
                    border: 1px solid #ddd;
                    border-radius: 3px;
                }
                QListWidget::item {
                    padding: 4px;
                    border-bottom: 1px solid #eee;
                }
                QListWidget::item:alternate {
                    background-color: #f0f0f0;
                }
            """)
            
            # 알림 없음 메시지 추가
            self.noti_list.addItem("알림이 없습니다.")
    
    def update_time(self):
        """현재 시간만 업데이트"""
        # 현재 시간 업데이트
        current_datetime = QDateTime.currentDateTime()
        self.datetime.setText(current_datetime.toString("yyyy.MM.dd. hh:mm:ss"))
    
    def update_inventory_status(self):
        """입고 현황 업데이트"""
        try:
            today_input = self.data_manager.get_today_input()
            self.in_total.setText(f"{today_input['total']}건")
            self.in_warehouse_A.setText(f"{today_input['A']}건")
            self.in_warehouse_B.setText(f"{today_input['B']}건")
            self.in_warehouse_C.setText(f"{today_input['C']}건")
        except Exception as e:
            logger.error(f"입고 현황 업데이트 오류: {str(e)}")
            self.show_status_message("입고 현황 업데이트 오류", is_error=True)
    
    def update_warehouse_status(self):
        """창고 상태 업데이트"""
        try:
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
                status = warehouse_data[warehouse_id]['status']
                status_label.setText(f"상태: {status}")
                
                # 상태에 따른 색상 설정
                if status == "정상":
                    status_label.setStyleSheet("""
                        background-color: #CCFFCC;
                        border-radius: 5px;
                        padding: 2px;
                    """)
                elif status == "주의":
                    status_label.setStyleSheet("""
                        background-color: #FFFF99;
                        border-radius: 5px;
                        padding: 2px;
                    """)
                else:  # 비정상
                    status_label.setStyleSheet("""
                        background-color: #FFCCCC;
                        border-radius: 5px;
                        padding: 2px;
                    """)
        except Exception as e:
            logger.error(f"창고 상태 업데이트 오류: {str(e)}")
            self.show_status_message("창고 상태 업데이트 오류", is_error=True)
    
    def update_expiry_status(self):
        """유통기한 정보 업데이트"""
        try:
            expiry_data = self.data_manager.get_expiry_data()
            self.set_expired_count(expiry_data['over'])
            self.set_expiring_soon_count(expiry_data['soon'])
        except Exception as e:
            logger.error(f"유통기한 정보 업데이트 오류: {str(e)}")
            self.show_status_message("유통기한 정보 업데이트 오류", is_error=True)
    
    def update_conveyor_status(self):
        """컨베이어 상태 업데이트"""
        try:
            conveyor_status = self.data_manager.get_conveyor_status()
            self.set_conveyor_status(conveyor_status)
        except Exception as e:
            logger.error(f"컨베이어 상태 업데이트 오류: {str(e)}")
            self.show_status_message("컨베이어 상태 업데이트 오류", is_error=True)
    
    def set_expired_count(self, count):
        """유통기한 경과 상품 수량 설정"""
        self.exp_over.setText(f"경과 {count}건")
    
    def set_expiring_soon_count(self, count):
        """유통기한 임박 상품 수량 설정"""
        self.exp_soon.setText(f"임박 {count}건")
    
    def set_conveyor_status(self, is_on):
        """컨베이어 상태 설정"""
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

    def add_notification(self, message):
        """알림 목록에 새 알림 추가"""
        if not hasattr(self, 'noti_list'):
            return
            
        # 현재 시간 가져오기
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        notification = f"[{current_time}] {message}"
        
        # 첫 알림인 경우 '알림이 없습니다' 항목 제거
        if self.noti_list.count() == 1 and self.noti_list.item(0).text() == "알림이 없습니다.":
            self.noti_list.clear()
        
        # 새 알림을 맨 위에 추가
        self.noti_list.insertItem(0, notification)
        
        # 알림 아이템 스타일 설정
        item = self.noti_list.item(0)
        if item:
            # 중요도에 따라 색상 변경
            if "오류" in message or "경고" in message or "비정상" in message or "실패" in message:
                item.setForeground(QColor("#F44336"))  # 빨간색 (중요 알림)
            elif "주의" in message or "경과" in message or "임박" in message:
                item.setForeground(QColor("#FF9800"))  # 주황색 (주의 알림)
            else:
                item.setForeground(QColor("#2196F3"))  # 파란색 (일반 알림)
        
        # 최대 10개 알림만 유지
        while self.noti_list.count() > 10:
            self.noti_list.takeItem(self.noti_list.count() - 1)
    
    # === BasePage 메서드 오버라이드 ===
    def on_server_connected(self):
        """서버 연결 성공 시 처리 - 기본 클래스 메서드 오버라이드"""
        self.add_notification("서버에 연결되었습니다.")
        logger.info("서버 연결 성공")
    
    def on_server_disconnected(self):
        """서버 연결 실패 시 처리 - 기본 클래스 메서드 오버라이드"""
        self.add_notification("서버 연결이 끊어졌습니다. 연결이 필요합니다.")
        
        # 데이터 표시 비활성화
        for warehouse_id in ['A', 'B', 'C']:
            temp_label = getattr(self, f"warehouse_{warehouse_id}_temp")
            temp_label.setText("온도 정보 없음")
            
            status_label = getattr(self, f"warehouse_{warehouse_id}_status")
            status_label.setText("상태: 연결 안됨")
            status_label.setStyleSheet("background-color: #CCCCCC; border-radius: 5px; padding: 2px;")
            
        logger.warning("서버 연결 실패")
    
    def handle_data_fetch_error(self, context, error_message):
        """데이터 가져오기 오류 처리"""
        logger.error(f"{context}: {error_message}")
        self.add_notification(f"데이터 업데이트 실패: {context}")
        self.show_status_message(f"오류: {error_message}", is_error=True)
        ErrorHandler.show_warning_message(context, error_message)
    
    def show_status_message(self, message, is_error=False, is_success=False, is_info=False):
        """
        상태 메시지 표시 (라벨이 있는 경우) - BasePage에서 상속받은 메서드
        대시보드에서는 알림으로 표시
        """
        if is_error:
            self.add_notification(f"오류: {message}")
        elif is_success:
            self.add_notification(f"성공: {message}")
        elif is_info:
            self.add_notification(f"정보: {message}")
        else:
            self.add_notification(message)