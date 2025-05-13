from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QDate
import random

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
        if exp_date_str:
            try:
                exp_date = QDate.fromString(exp_date_str, "yyyy-MM-dd")
                today = QDate.currentDate()
                days_diff = exp_date.daysTo(today)
                
                if days_diff > 0:
                    # 유통기한 경과
                    exp_label.setText(f"유통기한: D+{days_diff} (경과)")
                    exp_label.setStyleSheet("color: #F44336;")  # 빨간색
                elif days_diff == 0:
                    # 오늘 만료
                    exp_label.setText(f"유통기한: 오늘 만료")
                    exp_label.setStyleSheet("color: #FF9800;")  # 주황색
                else:
                    # 임박
                    exp_label.setText(f"유통기한: D{days_diff} (임박)")
                    exp_label.setStyleSheet("color: #FFC107;")  # 노란색
            except Exception as e:
                exp_label.setText(f"유통기한: {exp_date_str}")
        
        # 수량
        count_label = QLabel(f"수량: {self.product_data.get('quantity', 0)}개")
        
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