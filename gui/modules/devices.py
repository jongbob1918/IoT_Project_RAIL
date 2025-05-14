import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import datetime
import logging

from modules.base_page import BasePage
from modules.data_manager import DataManager
from modules.error_handler import ErrorHandler

# 로깅 설정
logger = logging.getLogger(__name__)

class DevicesPage(BasePage):
    """장치 관리 페이지 위젯 클래스"""
    
    def __init__(self, parent=None, data_manager=None):
        """
        장치 관리 페이지 초기화
        
        Args:
            parent: 부모 위젯
            data_manager: 데이터 관리자 객체 (의존성 주입)
        """
        super().__init__(parent)
        self.page_name = "장치 관리"  # 기본 클래스 속성 설정
        
        # UI 로드
        uic.loadUi("ui/widgets/devices.ui", self)
        
        # 데이터 관리자 설정 (의존성 주입 패턴 적용)
        self.data_manager = data_manager if data_manager else DataManager.get_instance()
        self.set_data_manager(self.data_manager)  # 부모 클래스 메서드 호출
        
        # 컨베이어 상태 초기화
        self.conveyor_running = False
        
        # 분류 박스 재고량 초기화
        self.initialize_counters()
        
        # UI 업데이트 타이머 설정
        self.setup_update_timer()
        
        # 데이터 변경 이벤트 연결
        self.connect_data_signals()
        
        logger.info("장치 관리 페이지 초기화 완료")
    
    def initialize_counters(self):
        """카운터 초기화"""
        self.inventory_counts = {
            "A": 0,  # 냉동 창고
            "B": 0,  # 냉장 창고
            "C": 0,  # 상온 창고
            "error": 0  # 오류 건수
        }
        self.waiting_items = 0
        self.total_processed = 0
    
    def setup_update_timer(self):
        """타이머 설정"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # 1초 간격으로 UI 업데이트
    
    def connect_data_signals(self):
        """데이터 변경 이벤트 연결"""
        self.data_manager.conveyor_status_changed.connect(self.update_conveyor_status)
        self.data_manager.notification_added.connect(self.on_notification)
    
    def update_conveyor_status(self):
        """컨베이어 상태 업데이트"""
        try:
            conveyor_status = self.data_manager.get_conveyor_status()
            
            if conveyor_status == 1:  # 가동중
                self.conveyor_status.setText("작동중")
                self.conveyor_status.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 3px; padding: 2px;")
                self.conveyor_running = True
            else:  # 정지
                self.conveyor_status.setText("일시정지")
                self.conveyor_status.setStyleSheet("background-color: #FFC107; color: black; border-radius: 3px; padding: 2px;")
                self.conveyor_running = False
        except Exception as e:
            logger.error(f"컨베이어 상태 업데이트 오류: {str(e)}")
            self.show_status_message("컨베이어 상태 업데이트 오류", is_error=True)
    
    def on_notification(self, message):
        """알림 발생 시 처리"""
        # 컨베이어 관련 알림인 경우 로그에 추가
        if "컨베이어" in message or "벨트" in message or "인식" in message or "분류" in message:
            current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
            log_message = f"{current_time} - {message}"
            self.add_log_message(log_message)
    
    def add_log_message(self, message):
        """로그 목록에 메시지 추가"""
        if hasattr(self, 'list_logs'):
            self.list_logs.insertItem(0, message)
            
            # 최대 50개 로그만 유지
            if self.list_logs.count() > 50:
                self.list_logs.takeItem(self.list_logs.count() - 1)
    
    def update_ui(self):
        """UI 요소 업데이트"""
        try:
            # 서버 연결 상태 확인
            if self.is_server_connected():
                # 서버에서 최신 데이터 가져오기
                try:
                    # 재고 데이터 가져오기
                    warehouse_data = self.data_manager.get_warehouse_data()
                    
                    # 재고 라벨 업데이트
                    self.inventory_A.setText(f"{warehouse_data['A']['used']}개")
                    self.inventory_B.setText(f"{warehouse_data['B']['used']}개")
                    self.inventory_C.setText(f"{warehouse_data['C']['used']}개")
                    
                    # 에러 건수는 서버에서 제공하지 않을 경우 0으로 설정
                    error_count = 0
                    self.inventory_error.setText(f"{error_count}개")
                    
                    # 대기 건수와 총 처리 건수 (서버에서 제공하지 않을 경우 예상 값 사용)
                    waiting_count = 0  # 서버에서 제공하지 않을 경우 0으로 설정
                    total_count = sum([warehouse_data[wh]['used'] for wh in ['A', 'B', 'C']])
                    
                    self.inventory_waiting.setText(f"{waiting_count}개")
                    self.inventory_waiting_2.setText(f"{total_count}개")
                    
                    # 오류는 항상 빨간색
                    if error_count > 0:
                        self.inventory_error.setStyleSheet("color: #F44336; font-weight: bold;")
                    else:
                        self.inventory_error.setStyleSheet("color: #757575;")
                    
                except Exception as e:
                    logger.error(f"재고 데이터 가져오기 오류: {str(e)}")
                    self.handle_data_fetch_error("재고 데이터 가져오기", str(e))
            else:
                # 서버 연결이 없는 경우 UI 초기화
                self.reset_ui_for_disconnection()
        
        except Exception as e:
            logger.error(f"UI 업데이트 중 오류: {str(e)}")
            self.show_status_message(f"UI 업데이트 오류: {str(e)}", is_error=True)
    
    def reset_ui_for_disconnection(self):
        """서버 연결이 없을 때 UI 초기화"""
        self.inventory_A.setText("연결 필요")
        self.inventory_B.setText("연결 필요")
        self.inventory_C.setText("연결 필요")
        self.inventory_error.setText("연결 필요")
        self.inventory_waiting.setText("연결 필요")
        self.inventory_waiting_2.setText("연결 필요")
        
        # 컨베이어 상태 표시 초기화
        self.conveyor_status.setText("연결 안됨")
        self.conveyor_status.setStyleSheet("background-color: #757575; color: white; border-radius: 3px; padding: 2px;")
    
    def handleSorterEvent(self, action, payload):
        """서버로부터 분류기 이벤트 처리 - JSON 스키마에 맞게 수정"""
        try:
            if action == "status_update":
                is_running = payload.get("is_running", False)
                self.conveyor_running = is_running
                
                # 컨베이어 상태 업데이트 - 작동중 또는 정지 두 가지 상태만 표시
                if is_running:
                    self.conveyor_status.setText("작동중")
                    self.conveyor_status.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 3px; padding: 2px;")
                else:
                    self.conveyor_status.setText("정지")
                    self.conveyor_status.setStyleSheet("background-color: #9E9E9E; color: white; border-radius: 3px; padding: 2px;")
                
                logger.debug(f"분류기 상태 업데이트: {'가동중' if is_running else '정지'}")
            
            elif action == "process_item":
                item = payload.get("item", {})
                qr_code = item.get("qr_code", "") 
                destination = item.get("destination", "")
                timestamp = payload.get("timestamp", "")
                
                # 로그 메시지 생성 - QR 코드 참조로 통일
                if destination in ["A", "B", "C"]:
                    log_message = f"{timestamp} - QR {qr_code} 인식됨, 창고 {destination}으로 분류"
                else:
                    log_message = f"{timestamp} - QR {qr_code} 인식 실패. 분류 오류 발생."
                
                # 로그 목록에 추가
                self.add_log_message(log_message)
                
                logger.info(f"아이템 처리: {log_message}")
        except Exception as e:
            logger.error(f"분류기 이벤트 처리 오류: {str(e)}")
            self.show_status_message(f"분류기 이벤트 처리 오류: {str(e)}", is_error=True)
    
    # === BasePage 메서드 오버라이드 ===
    def on_server_connected(self):
        """서버 연결 성공 시 처리 - 기본 클래스 메서드 오버라이드"""
        current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
        log_message = f"{current_time} - 서버에 연결되었습니다."
        self.add_log_message(log_message)
        logger.info("서버 연결 성공")
    
    def on_server_disconnected(self):
        """서버 연결 실패 시 처리 - 기본 클래스 메서드 오버라이드"""
        current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
        log_message = f"{current_time} - 서버 연결이 끊어졌습니다."
        self.add_log_message(log_message)
        
        # 연결이 끊어지면 컨베이어는 정지 상태로 표시
        self.conveyor_status.setText("연결 안됨")
        self.conveyor_status.setStyleSheet("background-color: #757575; color: white; border-radius: 3px; padding: 2px;")
        self.conveyor_running = False
        
        # UI 초기화
        self.reset_ui_for_disconnection()
        
        logger.warning("서버 연결 실패")
    
    def handle_data_fetch_error(self, context, error_message):
        """데이터 가져오기 오류 처리"""
        logger.error(f"{context}: {error_message}")
        error_log = f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 오류: {context} - {error_message}"
        self.add_log_message(error_log)
        ErrorHandler.show_warning_message(context, error_message)