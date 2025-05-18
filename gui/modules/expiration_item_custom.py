from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QDate
import logging
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

class ExpirationItemCustom(QWidget):
    """유통기한 아이템 커스텀 위젯 클래스"""
    
    def __init__(self, product_data):
        super().__init__()
        self.product_data = product_data
        self.init_ui()
        
    def init_ui(self):
        # 기본 스타일 설정
        self.setMinimumSize(380, 110)
        self.setMaximumSize(400, 120)
        self.setStyleSheet("""
            background-color: #F6F6F6;
            border: 1px solid #E0E0E0;
            border-radius: 5px;
        """)
        
        # 레이아웃 설정
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 이미지 영역
        image_label = QLabel()
        image_label.setFixedSize(80, 80)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setText("[이미지]")
        image_label.setStyleSheet("""
            background-color: #E0E0E0;
            border: 1px solid #C0C0C0;
            border-radius: 3px;
        """)
        
        # 정보 영역
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(10, 0, 0, 0)
        info_layout.setSpacing(5)
        
        # 상품명
        name_label = QLabel(f"상품명: {self.product_data.get('name', '알 수 없음')}")
        name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        
        # 유통기한
        exp_date_str = self.product_data.get('exp', '')
        exp_label = QLabel()
        
        # 서버에서 전달된 days_remaining 사용
        is_expired = self.product_data.get('is_expired', False)
        days_remaining = self.product_data.get('days_remaining', None)
        
        if exp_date_str:
            try:
                # API 응답에서 days_remaining이 있는 경우 사용
                if days_remaining is not None:
                    days_diff = days_remaining
                else:
                    # 수동으로 계산
                    exp_date = QDate.fromString(exp_date_str, "yyyy-MM-dd")
                    today = QDate.currentDate()
                    days_diff = today.daysTo(exp_date)  # 방향 수정 (미래 날짜면 양수)
                
                if days_diff < 0 or is_expired:
                    # 유통기한 경과
                    exp_label.setText(f"유통기한: {abs(days_diff)}일 경과")
                    exp_label.setStyleSheet("color: #F44336;")  # 빨간색
                elif days_diff == 0:
                    # 오늘 만료
                    exp_label.setText(f"유통기한: 오늘 만료")
                    exp_label.setStyleSheet("color: #FF9800;")  # 주황색
                else:
                    # 임박
                    exp_label.setText(f"유통기한: {days_diff}일 남음")
                    exp_label.setStyleSheet("color: #FFC107;")  # 노란색
            except Exception as e:
                logger.error(f"유통기한 날짜 처리 오류: {str(e)}")
                exp_label.setText(f"유통기한: {exp_date_str}")
        else:
            exp_label.setText("유통기한: 정보 없음")
        
        # 수량
        count_label = QLabel(f"수량: {self.product_data.get('quantity', 1)}개")
        
        # 위치
        location_label = QLabel(f"위치: {self.product_data.get('location', '알 수 없음')}")
        
        # 레이아웃에 위젯 추가
        info_layout.addWidget(name_label)
        info_layout.addWidget(exp_label)
        info_layout.addWidget(count_label)
        info_layout.addWidget(location_label)
        
        main_layout.addWidget(image_label)
        main_layout.addLayout(info_layout)
        
        self.setLayout(main_layout)
        
        logger.debug(f"유통기한 아이템 위젯 생성 완료: {self.product_data.get('name', '')}")