import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import koreanize_matplotlib

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/widgets/dashboard.ui", self)

        # 그래프 라인 색상
        self.graph_color = '#4285F4'  # 파란색 - 그래프 라인 및 프로그레스바 공통 색상
        
        # 창고별 온도 임계값 정의 (각 창고마다 다름)
        self.temp_thresholds = {
            'A': {'min': 10.0, 'max': 20.0},   # A창고: 10~20도 사이가 정상
            'B': {'min': 2.0, 'max': 8.0},     # B창고: 2~8도 사이가 정상 (냉장)
            'C': {'min': 15.0, 'max': 25.0},   # C창고: 15~25도 사이가 정상
            'D': {'min': -5.0, 'max': 0.0}     # D창고: -5~0도 사이가 정상 (냉동)
        }

        # 현재시간 표시 세팅
        self.current_datetime = QDateTime.currentDateTime()
        self.datetime.setText(self.current_datetime.toString("yyyy.MM.dd. hh:mm:ss"))

        # 현재 입출고 현황 표시 세팅        
        input_total = 120
        output_total = 100
        alert_total = 5
        self.total_status.setText(f"입고 {input_total}건  |  출고 {output_total}건  |  경고 {alert_total}건")
        self.total_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1초마다 현재시간, 입출고 현황 업데이트 되도록 연결
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_and_status)
        self.timer.start(1000)

        # 상태 라벨 초기화
        self.setupStatusLabels()
        
        # 프로그레스바 스타일 설정
        self.setupProgressBars()
        
        # 기타 상태표시 라벨 초기화
        self.setupOtherStatusLabels()

        # 알림 메시지 초기화
        self.setupNotificationLabels()
        
        # 초기 온도 및 상태 설정
        self.updateWarehouseStatus()

        # 입고량/출고량 그래프 생성
        self.createInventoryGraphs()

    # 상태 라벨 초기화
    def setupStatusLabels(self):
        # 상태 라벨 초기화
        for warehouse in ['A', 'B', 'C', 'D']:
            status_label = getattr(self, f"warehouse_{warehouse}_status")
            status_label.setText("상태: 정상")
            status_label.setStyleSheet("""
                background-color: #CCFFCC;
                border-radius: 5px;
                padding: 2px;
            """)

    # 프로그레스바 스타일 설정 및 초기화
    def setupProgressBars(self):
        progress_style = f"""
            QProgressBar {{
                border: 1px solid grey;
                border-radius: 3px;
                text-align: center;
            }}
            
            QProgressBar::chunk {{
                background-color: {self.graph_color};
            }}
        """
        
        for warehouse in ['A', 'B', 'C', 'D']:
            bar = getattr(self, f"warehouse_{warehouse}_bar")
            bar.setStyleSheet(progress_style)

            # 초기값 설정
            bar.setValue(0)
    
    # 기타 상태표시 라벨 초기화
    def setupOtherStatusLabels(self):
        # 유통기한 관련
        self.setExpiredCount(0)
        self.setExpiringSoonCount(0)
        
        # 컨베이어 관련
        self.setConveyorStatus(True)  # 기본값 ON
        
        # 출입 관련
        self.setInOutCount(0)

    # 창고 상태 업데이트 (온도)
    def updateWarehouseStatus(self):
        # 실제로는 이 값들을 센서나 데이터베이스에서 가져와야 함
        warehouse_data = {
            'A': {'temp': 15.2, 'progress': 75},
            'B': {'temp': 0.5, 'progress': 45},  # B창고 온도 비정상 (임계값 2.0°C 미만)
            'C': {'temp': 18.5, 'progress': 60},
            'D': {'temp': -2.5, 'progress': 30}
        }
        
        # 각 창고별 온도, 프로그레스바 값 업데이트
        for warehouse, data in warehouse_data.items():
            self.setWarehouseTemperature(warehouse, data['temp'])
            self.setProgressBarValue(warehouse, data['progress'])

    # 현재시간, 입출고 현황 업데이트
    def update_time_and_status(self):
        self.current_datetime = QDateTime.currentDateTime()
        self.datetime.setText(self.current_datetime.toString("yyyy.MM.dd. hh:mm:ss"))

        input_total = 120
        output_total = 100
        alert_total = 5
        self.total_status.setText(f"입고 {input_total}건  |  출고 {output_total}건  |  경고 {alert_total}건")
        
        # 온도 값 업데이트 (1분마다)
        if self.current_datetime.time().second() == 0:
            self.updateWarehouseStatus()

    # 특정 창고의 온도를 설정하는 메서드
    def setWarehouseTemperature(self, warehouse, temp):
        if warehouse not in ['A', 'B', 'C', 'D']:
            return
            
        temp_label = getattr(self, f"warehouse_{warehouse}_temp")
        status_label = getattr(self, f"warehouse_{warehouse}_status")
        
        # 온도 표시 업데이트
        temp_label.setText(f"온도 {temp}°C")
        
        # 임계값 확인 및 상태 업데이트
        min_temp = self.temp_thresholds[warehouse]['min']
        max_temp = self.temp_thresholds[warehouse]['max']
        
        if min_temp <= temp <= max_temp:
            # 정상 온도 범위
            status_label.setText("상태: 정상")
            status_label.setStyleSheet("""
                background-color: #CCFFCC;
                border-radius: 5px;
                padding: 2px;
            """)
        else:
            # 비정상 온도 범위
            status_label.setText("상태: 비정상")
            status_label.setStyleSheet("""
                background-color: #FFCCCC;
                border-radius: 5px;
                padding: 2px;
            """)
    
    # 특정 창고의 프로그레스바 값을 설정하는 메서드 (외부에서 호출 가능)
    def setProgressBarValue(self, warehouse, value):
        if warehouse not in ['A', 'B', 'C', 'D']:
            return
        
        # 값 범위 제한 (0-100)
        if value < 0:
            value = 0
        elif value > 100:
            value = 100
            
        # 프로그레스바 값 설정
        progress_bar = getattr(self, f"warehouse_{warehouse}_bar")
        progress_bar.setValue(value)
    
    # 유통기한 경과 상품 수량 설정
    def setExpiredCount(self, count):
        self.exp_over.setText(f"경과  {count}건")        
    
    # 유통기한 임박 상품 수량 설정
    def setExpiringSoonCount(self, count):        
        self.exp_soon.setText(f"임박  {count}건")        
    
    # 컨베이어 상태 설정
    def setConveyorStatus(self, is_on):        
        status = "ON" if is_on else "OFF"
        self.conveyor_onoff.setText(f"{status}")
        
        if is_on:
            self.conveyor_onoff.setStyleSheet("""
                background-color: #CCFFCC;
                border-radius: 3px;
                padding: 2px;
            """)
        else:
            self.conveyor_onoff.setStyleSheet("""
                background-color: #CCCCCC;
                border-radius: 3px;
                padding: 2px;
            """)
    
    # 출입 로그 수량 설정
    def setInOutCount(self, count):
        self.inout.setText(f"출입  {count}건")

    # 알림 메시지 라벨 초기화
    def setupNotificationLabels(self):
        # 알림 라벨에 기본 스타일 적용
        for i in range(1, 5):
            notification_label = getattr(self, f"noti_recent_{i}")
        
        # 초기 알림 메시지 없음
        self.clearNotifications()
    
    # 모든 알림 메시지 지우기
    def clearNotifications(self):
        for i in range(1, 5):
            notification_label = getattr(self, f"noti_recent_{i}")
            notification_label.setText("-")

    # 입출고 그래프 생성 메서드
    def createInventoryGraphs(self):
        # 데이터 준비
        days = ['1일', '5일', '10일', '15일', '20일', '25일', '30일']
        x = np.arange(len(days))
        in_data = [120, 140, 135, 150, 145, 160, 155]
        out_data = [100, 130, 125, 140, 135, 150, 145]
        
        # 입고량 그래프 생성
        self.createInputGraph(days, in_data)
        
        # 출고량 그래프 생성
        self.createOutputGraph(days, out_data)
        
        # 그래프 업데이트 타이머 (30분마다 업데이트)
        self.graph_timer = QTimer()
        self.graph_timer.timeout.connect(self.updateInventoryGraphs)
        self.graph_timer.start(30 * 60 * 1000)  # 30분 = 30 * 60 * 1000 ms
    
    # 입고량 그래프 생성
    def createInputGraph(self, days, data):
        # Figure 객체 생성
        self.input_figure = Figure(figsize=(5, 3), dpi=100)
        self.input_canvas = FigureCanvas(self.input_figure)
        
        # QWidget에 그래프 추가
        layout = QVBoxLayout(self.input_monthly_graph)
        layout.addWidget(self.input_canvas)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 그래프 설정
        self.input_ax = self.input_figure.add_subplot(111)
        self.input_ax.set_ylabel('수량', fontsize=9)    
        
        # 라인 그래프 그리기 - 프로그레스바와 동일한 색상 사용
        self.input_line, = self.input_ax.plot(days, data, self.graph_color, marker='o', linewidth=2, markersize=6)
        
        # x축 라벨 설정
        self.input_ax.set_xticks(range(len(days)))
        self.input_ax.set_xticklabels(days)
        self.input_ax.tick_params(axis='both', which='major', labelsize=8)            
        
        self.input_figure.tight_layout(pad=2)
        self.input_canvas.draw()
    
    # 출고량 그래프 생성
    def createOutputGraph(self, days, data):
        # Figure 객체 생성
        self.output_figure = Figure(figsize=(5, 3), dpi=100)
        self.output_canvas = FigureCanvas(self.output_figure)
        
        # QWidget에 그래프 추가
        layout = QVBoxLayout(self.output_monthly_graph)
        layout.addWidget(self.output_canvas)
        layout.setContentsMargins(0, 0, 0, 0)      
        
        # 그래프 설정
        self.output_ax = self.output_figure.add_subplot(111)
        self.output_ax.set_ylabel('수량', fontsize=9)
        
        # 그래프 그리기 - 프로그레스바와 동일한 색상 사용
        self.output_line, = self.output_ax.plot(days, data, self.graph_color, marker='o', linewidth=2, markersize=6)
        
        # x축 라벨 설정
        self.output_ax.set_xticks(range(len(days)))
        self.output_ax.set_xticklabels(days)
        self.output_ax.tick_params(axis='both', which='major', labelsize=8)  
                
        self.output_figure.tight_layout(pad=2)
        self.output_canvas.draw()
    
    # 그래프 업데이트 메서드
    def updateInventoryGraphs(self):
        # 실제로는 여기서 DB나 API에서 새 데이터를 가져옴
        # 예시 데이터
        days = ['1일', '5일', '10일', '15일', '20일', '25일', '30일']
        new_in_data = [110, 145, 130, 155, 140, 165, 160]
        new_out_data = [95, 135, 120, 145, 130, 155, 150]
        
        # 입고량 그래프 업데이트
        self.input_line.set_ydata(new_in_data)
        
        # y축 범위 업데이트
        self.input_ax.relim()
        self.input_ax.autoscale_view()
        
        # 데이터 포인트 값 업데이트
        for txt in self.input_ax.texts:
            txt.remove()
        
        # 캔버스 업데이트
        self.input_canvas.draw()
        
        # 출고량 그래프 업데이트
        self.output_line.set_ydata(new_out_data)
        
        # y축 범위 업데이트
        self.output_ax.relim()
        self.output_ax.autoscale_view()
        
        # 데이터 포인트 값 업데이트
        for txt in self.output_ax.texts:
            txt.remove()        
        
        # 캔버스 업데이트
        self.output_canvas.draw()