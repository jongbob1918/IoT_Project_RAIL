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
        self.current_sorter_state = "stopped"  # 'stopped', 'running', 'pause' 중 하나
        # UI 로드
        uic.loadUi("ui/widgets/devices.ui", self)
        
        # 데이터 관리자 설정 (의존성 주입 패턴 적용)
        self.data_manager = data_manager if data_manager else DataManager.get_instance()
        self.set_data_manager(self.data_manager)  # 부모 클래스 메서드 호출
        
        # 컨베이어 상태 초기화
        self.conveyor_running = False
        
        # 분류 박스 재고량 초기화
        self.initialize_counters()
        
        # 데이터 변경 이벤트 연결
        self.connect_data_signals()
        
        # 버튼 이벤트 연결
        self.connect_button_signals()
        
        # 버튼 스타일 설정
        self.setup_button_styles()
        
        # 최초 UI 업데이트
        self.update_ui()
        
        logger.info("장치 관리 페이지 초기화 완료")

        # 헤더 레이블 폰트 설정
        headers = [self.label, self.label_2, self.label_10, self.label_5, self.label_6, self.label_7, self.label_9]
        for label in headers:
            font = label.font()
            font.setBold(True)
            font.setWeight(QFont.Weight.Bold)
            label.setFont(font)
    
    def initialize_counters(self):
        """카운터 초기화"""
        self.inventory_counts = {
            "A": 0,  # 냉동 창고
            "B": 0,  # 냉장 창고
            "C": 0,  # 상온 창고
            "error": 0  # 오류 건수
        }
        # 입고 대기 항목 카운터 초기화
        self.waiting_items = 0
        self.total_processed = 0
    
    def connect_data_signals(self):
        """데이터 변경 이벤트 연결"""
        self.data_manager.conveyor_status_changed.connect(self.update_conveyor_status)
        self.data_manager.notification_added.connect(self.on_notification)
        self.data_manager.inventory_data_changed.connect(self.update_ui)
        self.data_manager.waiting_data_changed.connect(self.update_ui)
        
        # 서버 이벤트 연결
        if hasattr(self.data_manager, '_server_connection') and hasattr(self.data_manager._server_connection, 'eventReceived'):
            self.data_manager._server_connection.eventReceived.connect(self.handle_server_event)
    
    def handle_server_event(self, category, action, payload):
        """서버 이벤트 처리"""
        # 분류기 관련 이벤트인 경우 처리
        if category == "sorter":
            self.handleSorterEvent(action, payload)
    
    def connect_button_signals(self):
        """버튼 이벤트 연결"""
        # 컨베이어 제어 버튼 이벤트 연결
        self.btn_start.clicked.connect(self.on_start_conveyor)
        self.btn_pause.clicked.connect(self.on_pause_conveyor)
        self.btn_stop.clicked.connect(self.on_stop_conveyor)
    
    def setup_button_styles(self):
        """버튼 스타일 설정"""
        # 시작 버튼 (초록색)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
                border: 2px solid #2c6b2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        # 일시정지 버튼 (노란색)
        self.btn_pause.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e6ae06;
            }
            QPushButton:pressed {
                background-color: #cc9a06;
                border: 2px solid #b38605;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        # 정지 버튼 (빨간색)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #df3c30;
            }
            QPushButton:pressed {
                background-color: #c6352a;
                border: 2px solid #aa2e24;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
    
    def on_start_conveyor(self):
        """시작 버튼 클릭 이벤트 처리"""
        try:
            if self.current_sorter_state == "running":
                self.show_status_message("분류기가 이미 작동 중입니다.")
                return
            logger.info("분류기 시작 요청")
            self.add_log_message(f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 분류기 시작 요청")
            
            # 서버 연결 확인
            if not self.data_manager.is_server_connected():
                self.show_status_message("서버에 연결되어 있지 않습니다.", is_error=True)
                return
            
            # 버튼 클릭 효과 - 시각적 피드백
            self.btn_start.setStyleSheet(self.btn_start.styleSheet() + "QPushButton:focus { border: 2px solid #2c6b2f; }")
            QTimer.singleShot(150, lambda: self.btn_start.setStyleSheet(self.btn_start.styleSheet().replace("QPushButton:focus { border: 2px solid #2c6b2f; }", "")))
            
            # 데이터 매니저를 통해 서버에 요청 - action 필드 사용하여 JSON 구조 일치
            result = self.data_manager.control_conveyor("start")
            
            if result and result.get("success", False):
                self.current_sorter_state = "running"  # 상태 업데이트
                self.conveyor_status.setText("작동중")
                self.conveyor_status.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 3px; padding: 5px; font-weight: bold;")
                self.conveyor_running = True
                self.add_log_message(f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 분류기 작동 시작")
                
                # 상태 메시지 표시 업데이트
                self.show_status_message("분류기 작동 시작됨", is_success=True)
            else:
                error_msg = result.get("message", "알 수 없는 오류") if result else "서버 응답 없음"
                self.show_status_message(f"분류기 시작 실패: {error_msg}", is_error=True)
                self.add_log_message(f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 분류기 시작 실패: {error_msg}")
                
                #  에러 메시지
                self.handle_api_error("분류기 오류", error_msg)
                        
        except Exception as e:
            logger.error(f"분류기 시작 중 오류: {str(e)}")
            self.show_status_message(f"분류기 시작 오류: {str(e)}", is_error=True)
    
    def on_pause_conveyor(self):
        """일시정지 버튼 클릭 이벤트 처리"""
        try:
            if self.current_sorter_state == "pause":
                self.show_status_message("분류기가 이미 일시정지 상태입니다.")
                return
             # running 상태가 아니면 일시정지 불가
            if self.current_sorter_state == "stopped":
                self.show_status_message("작동 중인 분류기만 일시정지할 수 있습니다.", is_error=True)
                return   
            logger.info("분류기 일시정지 요청")
            self.add_log_message(f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 분류기 일시정지 요청")
            
            # 서버 연결 확인
            if not self.data_manager.is_server_connected():
                self.show_status_message("서버에 연결되어 있지 않습니다.", is_error=True)
                return
            
            # 버튼 클릭 효과 - 시각적 피드백
            self.btn_pause.setStyleSheet(self.btn_pause.styleSheet() + "QPushButton:focus { border: 2px solid #b38605; }")
            QTimer.singleShot(150, lambda: self.btn_pause.setStyleSheet(self.btn_pause.styleSheet().replace("QPushButton:focus { border: 2px solid #b38605; }", "")))
            
            # 데이터 매니저를 통해 서버에 요청 - action 필드 사용
            result = self.data_manager.control_conveyor("pause")

            if result and result.get("success", False):
                self.current_sorter_state = "pause"  # 상태 업데이트
                self.conveyor_status.setText("일시정지")
                self.conveyor_status.setStyleSheet("background-color: #FFC107; color: black; border-radius: 3px; padding: 5px; font-weight: bold;")
                self.conveyor_running = False
                self.add_log_message(f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 분류기 일시정지됨")
                
                # 상태 메시지 표시 업데이트
                self.show_status_message("분류기 일시정지됨", is_success=True)
            else:
                error_msg = result.get("message", "알 수 없는 오류") if result else "서버 응답 없음"
                self.show_status_message(f"분류기 일시정지 실패: {error_msg}", is_error=True)
                self.add_log_message(f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 분류기 일시정지 실패: {error_msg}")
                
                # 에러 처리 개선
                ErrorHandler.show_error_message("분류기 제어 오류", f"분류기 일시정지 중 오류가 발생했습니다: {error_msg}")
        
        except Exception as e:
            logger.error(f"분류기 일시정지 중 오류: {str(e)}")
            self.show_status_message(f"분류기 일시정지 오류: {str(e)}", is_error=True)
    
    def on_stop_conveyor(self):
        """정지 버튼 클릭 이벤트 처리"""
        try:
            if self.current_sorter_state == "stopped":
                self.show_status_message("분류기가 이미 정지 상태입니다.")
                return
            logger.info("분류기 정지 요청")
            self.add_log_message(f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 분류기 정지 요청")
            
            # 서버 연결 확인
            if not self.data_manager.is_server_connected():
                self.show_status_message("서버에 연결되어 있지 않습니다.", is_error=True)
                return
            
            # 버튼 클릭 효과 - 시각적 피드백
            self.btn_stop.setStyleSheet(self.btn_stop.styleSheet() + "QPushButton:focus { border: 2px solid #aa2e24; }")
            QTimer.singleShot(150, lambda: self.btn_stop.setStyleSheet(self.btn_stop.styleSheet().replace("QPushButton:focus { border: 2px solid #aa2e24; }", "")))
            
            # 데이터 매니저를 통해 서버에 요청 - action 필드 사용
            result = self.data_manager.control_conveyor("stop")
            
            if result and result.get("success", False):
                self.current_sorter_state = "stopped"  # 상태 업데이트
                self.conveyor_status.setText("정지")
                self.conveyor_status.setStyleSheet("background-color: #F44336; color: white; border-radius: 3px; padding: 5px; font-weight: bold;")
                self.conveyor_running = False
                self.add_log_message(f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 분류기 정지됨")
                
                # 상태 메시지 표시 업데이트
                self.show_status_message("분류기 정지됨", is_success=True)
            else:
                error_msg = result.get("message", "알 수 없는 오류") if result else "서버 응답 없음"
                self.show_status_message(f"분류기 정지 실패: {error_msg}", is_error=True)
                self.add_log_message(f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 분류기 정지 실패: {error_msg}")
                
                # 에러 처리 개선
                ErrorHandler.show_error_message("분류기 제어 오류", f"분류기 정지 중 오류가 발생했습니다: {error_msg}")
        
        except Exception as e:
            logger.error(f"분류기 정지 중 오류: {str(e)}")
            self.show_status_message(f"분류기 정지 오류: {str(e)}", is_error=True)
    
    def update_conveyor_status(self):
        """컨베이어 상태 업데이트"""
        try:
            conveyor_status = self.data_manager.get_conveyor_status()
            
            if conveyor_status == 1:  # 가동중
                self.conveyor_status.setText("작동중")
                self.conveyor_status.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 3px; padding: 5px; font-weight: bold;")
                self.conveyor_running = True
            elif conveyor_status == 2:  # 일시정지
                self.conveyor_status.setText("일시정지")
                self.conveyor_status.setStyleSheet("background-color: #FFC107; color: black; border-radius: 3px; padding: 5px; font-weight: bold;")
                self.conveyor_running = False
            else:  # 정지 (0 또는 기타 값)
                self.conveyor_status.setText("정지")
                self.conveyor_status.setStyleSheet("background-color: #F44336; color: white; border-radius: 3px; padding: 5px; font-weight: bold;")
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
            if self.data_manager.is_server_connected():
                # 재고 데이터 가져오기
                warehouse_data = self.data_manager.get_warehouse_data()
                
                # 재고 라벨 업데이트
                self.inventory_A.setText(f"{warehouse_data['A']['used']}개")
                self.inventory_B.setText(f"{warehouse_data['B']['used']}개")
                self.inventory_C.setText(f"{warehouse_data['C']['used']}개")
                
                # 대기 항목 데이터 가져오기
                waiting_count = self.data_manager.get_waiting_items()
                self.inventory_waiting.setText(f"{waiting_count}개")
                
                # 에러 건수는 서버에서 제공하지 않을 경우 로그에서 계산
                error_count = 0
                if hasattr(self, 'list_logs'):
                    for i in range(self.list_logs.count()):
                        log_text = self.list_logs.item(i).text()
                        if "오류" in log_text or "실패" in log_text:
                            error_count += 1
                
                self.inventory_error.setText(f"{error_count}개")
                
                # 총 처리 건수 = 창고 재고 합계
                total_count = sum([warehouse_data[wh]['used'] for wh in ['A', 'B', 'C']])
                
                self.inventory_waiting_2.setText(f"{total_count}개")
                
                # 오류는 항상 빨간색
                if error_count > 0:
                    self.inventory_error.setStyleSheet("color: #F44336; font-weight: bold;")
                else:
                    self.inventory_error.setStyleSheet("color: #757575;")
                
                # 컨베이어 제어 버튼 활성화
                self.btn_start.setEnabled(True)
                self.btn_pause.setEnabled(True)
                self.btn_stop.setEnabled(True)
                
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
        self.conveyor_status.setStyleSheet("background-color: #757575; color: white; border-radius: 3px; padding: 5px; font-weight: bold;")
        
        # 버튼 비활성화
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
    
    def handleSorterEvent(self, action, payload):
        try:
            if action == "status_update":
                state = payload.get("state", "")
                if state:
                    self.current_sorter_state = state
                    logger.debug(f"서버에서 받은 상태: '{state}'")
                    # state 값에 따라 UI 업데이트
                    if state == "running":
                        self.conveyor_status.setText("작동중")
                        self.conveyor_status.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 3px; padding: 5px; font-weight: bold;")
                        self.conveyor_running = True
                    elif state == "pause":
                        self.conveyor_status.setText("일시정지")
                        self.conveyor_status.setStyleSheet("background-color: #FFC107; color: black; border-radius: 3px; padding: 5px; font-weight: bold;")
                        self.conveyor_running = False
                    else:  # stopped
                        self.conveyor_status.setText("정지")
                        self.conveyor_status.setStyleSheet("background-color: #F44336; color: white; border-radius: 3px; padding: 5px; font-weight: bold;")
                        self.conveyor_running = False
                        
                    logger.debug(f"분류기 상태 업데이트: {state}")
            
            elif action == "process_item":
                # JSON 구조에 맞게 item, qr_code, destination 필드 참조
                item = payload.get("item", {})
                qr_code = item.get("qr_code", "") 
                destination = item.get("destination", "")
                timestamp = payload.get("timestamp", "")
                
                # 로그 메시지 생성 - QR 코드 참조로 통일
                if destination in ["A", "B", "C"]:
                    log_message = f"{timestamp} - QR {qr_code} 인식됨, 창고 {destination}으로 분류"
                    
                    # 해당 창고의 재고를 1 증가 (UI 반영 용도)
                    if destination in self.inventory_counts:
                        self.inventory_counts[destination] += 1
                else:
                    log_message = f"{timestamp} - QR {qr_code} 인식 실패. 분류 오류 발생."
                    
                    # 오류 카운트 증가
                    self.inventory_counts["error"] += 1
                
                # 로그 목록에 추가
                self.add_log_message(log_message)
                
                logger.info(f"아이템 처리: {log_message}")
        except Exception as e:
            logger.error(f"분류기 이벤트 처리 오류: {str(e)}")
            self.show_status_message(f"분류기 이벤트 처리 오류: {str(e)}", is_error=True)
    
    # === BasePage 메서드 오버라이드 ===
    def on_server_connected(self):
        """서버 연결 성공 시 처리"""
        logger.info("서버 연결 성공")
        
        # 버튼 활성화
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        
        # 상태 표시 업데이트
        self.show_status_message("서버 연결됨", is_success=True)
        
        # 데이터 갱신을 위한 UI 업데이트 호출
        self.update_ui()    
    
    def on_server_disconnected(self):
        """서버 연결 실패 시 처리"""
        logger.warning("서버 연결 실패")
        
        # 연결이 끊어지면 컨베이어는 정지 상태로 표시
        self.conveyor_status.setText("연결 안됨")
        self.conveyor_status.setStyleSheet("background-color: #757575; color: white; border-radius: 3px; padding: 5px; font-weight: bold;")
        self.conveyor_running = False
        
        # 버튼 비활성화
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)

        # UI 초기화
        self.reset_ui_for_disconnection()
        
        # 상태 표시 업데이트
        self.show_status_message("서버 연결 끊김", is_error=True)
    
    def handle_data_fetch_error(self, context, error_message):
        """데이터 가져오기 오류 처리 - 개선된 오류 처리"""
        logger.error(f"{context}: {error_message}")
        error_log = f"{QDateTime.currentDateTime().toString('hh:mm:ss')} - 오류: {context} - {error_message}"
        self.add_log_message(error_log)
        
        # 오류 유형별 메시지 개선
        if "connection" in error_message.lower() or "timeout" in error_message.lower():
            ErrorHandler.show_warning_message("네트워크 오류", f"서버와의 통신 중 문제가 발생했습니다: {error_message}")
        elif "permission" in error_message.lower() or "access" in error_message.lower():
            ErrorHandler.show_warning_message("접근 권한 오류", f"데이터에 접근할 권한이 없습니다: {error_message}")
        else:
            ErrorHandler.show_warning_message(context, error_message)