# modules/error_handler.py
import logging
from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

class ErrorHandler:
    """
    중앙화된 예외 처리를 위한 클래스
    모든 GUI 컴포넌트에서 공통으로 사용할 수 있는 오류 처리 메서드 제공
    """
    
    @staticmethod
    def show_error_message(title, message):
        """
        오류 메시지 표시 (심각한 오류)
        
        Args:
            title: 메시지 창 제목
            message: 표시할 오류 메시지
        """
        logger.error(f"오류: {title} - {message}")
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()
    
    @staticmethod
    def show_warning_message(title, message):
        """
        경고 메시지 표시 (일반 오류)
        
        Args:
            title: 메시지 창 제목
            message: 표시할 경고 메시지
        """
        logger.warning(f"경고: {title} - {message}")
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()
    
    @staticmethod
    def show_info_message(title, message):
        """
        정보 메시지 표시
        
        Args:
            title: 메시지 창 제목
            message: 표시할 정보 메시지
        """
        logger.info(f"정보: {title} - {message}")
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()
    
    @staticmethod
    def show_confirmation_dialog(title, message):
        """
        확인 다이얼로그 표시
        
        Args:
            title: 다이얼로그 제목
            message: 표시할 확인 메시지
            
        Returns:
            bool: 사용자가 '예'를 선택했으면 True, 그렇지 않으면 False
        """
        logger.info(f"확인 요청: {title} - {message}")
        reply = QMessageBox.question(
            None, 
            title, 
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    @staticmethod
    def handle_api_error(response, default_message="요청 처리 중 오류가 발생했습니다"):
        """
        API 응답 오류 처리
        
        Args:
            response: API 응답 객체
            default_message: 기본 오류 메시지
            
        Returns:
            str: 오류 메시지
        """
        if not response:
            return default_message
            
        error_msg = response.get("error", "")
        if error_msg:
            return error_msg
            
        message = response.get("message", "")
        if message:
            return message
            
        return default_message