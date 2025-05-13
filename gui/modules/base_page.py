import logging
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSlot

from modules.error_handler import ErrorHandler  # 오류 처리 모듈 가져오기

logger = logging.getLogger(__name__)

class BasePage(QWidget):
    """
    모든 페이지의 기본 클래스
    공통 기능을 여기에 구현하고 각 페이지에서 상속
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_manager = None
        self.page_name = "Base"  # 자식 클래스에서 오버라이드
        
    def set_data_manager(self, data_manager):
        """데이터 관리자 설정"""
        self.data_manager = data_manager
        
    @pyqtSlot(bool, str)
    def onConnectionStatusChanged(self, connected, message=""):
        """서버 연결 상태 변경 시 호출되는 메서드"""
        try:
            if connected:
                logger.info(f"{self.page_name} 페이지: 서버 연결됨")
                self.on_server_connected()
            else:
                logger.warning(f"{self.page_name} 페이지: 서버 연결 끊김 - {message}")
                self.on_server_disconnected()
        except Exception as e:
            logger.error(f"연결 상태 변경 처리 중 오류 발생: {str(e)}")
    
    def is_server_connected(self):
        """서버 연결 상태 확인 (유틸리티 메서드)"""
        if not self.data_manager:
            return False
            
        try:
            server_conn = self.data_manager._server_connection
            return server_conn and hasattr(server_conn, 'is_connected') and server_conn.is_connected
        except Exception as e:
            logger.error(f"서버 연결 상태 확인 중 오류 발생: {str(e)}")
            return False
    
    def on_server_connected(self):
        """서버 연결 시 처리 - 자식 클래스에서 오버라이드"""
        pass
    
    def on_server_disconnected(self):
        """서버 연결 끊김 시 처리 - 자식 클래스에서 오버라이드"""
        pass
    
    def show_status_message(self, message, is_error=False, is_success=False, is_info=False):
        """
        상태 메시지 표시 (라벨이 있는 경우)
        
        Args:
            message: 표시할 메시지
            is_error: 오류 메시지인지 여부
            is_success: 성공 메시지인지 여부
            is_info: 정보 메시지인지 여부
        """
        try:
            if hasattr(self, 'lbl_status'):
                self.lbl_status.setText(message)
                
                if is_error:
                    self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
                elif is_success:
                    self.lbl_status.setStyleSheet("color: green; font-weight: bold;")
                elif is_info:
                    self.lbl_status.setStyleSheet("color: blue;")
                else:
                    self.lbl_status.setStyleSheet("")
        except Exception as e:
            logger.error(f"상태 메시지 표시 중 오류 발생: {str(e)}")
                
    def handle_connection_error(self, context):
        """
        서버 연결 오류 처리
        
        Args:
            context: 오류 컨텍스트 (어떤 작업 중 발생했는지)
        """
        try:
            logger.warning(f"{context}: 서버 연결 없음")
            self.show_status_message("서버 연결 상태: 연결 안됨", is_error=True)
            
            if hasattr(ErrorHandler, 'show_warning_message'):
                ErrorHandler.show_warning_message("서버 연결 오류", "서버에 연결되어 있지 않습니다.")
        except Exception as e:
            logger.error(f"연결 오류 처리 중 예외 발생: {str(e)}")
    
    def handle_api_error(self, context, error_message):
        """
        API 오류 처리
        
        Args:
            context: 오류 컨텍스트 (어떤 API 호출 중 발생했는지)
            error_message: 오류 메시지
        """
        try:
            logger.warning(f"{context}: {error_message}")
            self.show_status_message(f"오류: {error_message}", is_error=True)
            
            if hasattr(ErrorHandler, 'show_warning_message'):
                ErrorHandler.show_warning_message(context, error_message)
        except Exception as e:
            logger.error(f"API 오류 처리 중 예외 발생: {str(e)}")
    
    def handle_api_exception(self, context, exception):
        """
        API 예외 처리
        
        Args:
            context: 예외 컨텍스트 (어떤 API 호출 중 발생했는지)
            exception: 발생한 예외 객체
        """
        try:
            logger.error(f"{context}: {str(exception)}")
            self.show_status_message(f"오류: {str(exception)}", is_error=True)
            
            if hasattr(ErrorHandler, 'show_error_message'):
                ErrorHandler.show_error_message(context, f"{context}가 발생했습니다: {str(exception)}")
        except Exception as e:
            logger.error(f"API 예외 처리 중 오류 발생: {str(e)}")
            
    def handle_data_fetch_error(self, context, error_message):
        """
        데이터 가져오기 오류 처리
        
        Args:
            context: 오류 컨텍스트 (어떤 데이터를 가져오는 중이었는지)
            error_message: 오류 메시지
        """
        try:
            logger.error(f"{context}: {error_message}")
            self.show_status_message(f"오류: {error_message}", is_error=True)
            
            if hasattr(ErrorHandler, 'show_warning_message'):
                ErrorHandler.show_warning_message(context, error_message)
        except Exception as e:
            logger.error(f"데이터 가져오기 오류 처리 중 예외 발생: {str(e)}")