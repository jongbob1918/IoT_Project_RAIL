import os
import sys
import json
import time
import datetime
import threading
import logging
import random
import requests
from typing import Dict, Any, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DataManager")

# API 서버 기본 URL
SERVER_BASE_URL = "http://localhost:8000/api"

class DataManager(QObject):
    """
    애플리케이션 전체에서 공통으로 사용할 데이터를 관리하는 싱글톤 클래스
    모든 UI 컴포넌트는 이 클래스를 통해 데이터에 접근하고,
    데이터 변경 시 시그널을 통해 UI 업데이트
    """
    
    # 싱글톤 인스턴스
    _instance = None
    
    # 데이터 변경 시그널 정의
    warehouse_data_changed = pyqtSignal()
    inventory_data_changed = pyqtSignal()
    expiry_data_changed = pyqtSignal()
    conveyor_status_changed = pyqtSignal()
    notification_added = pyqtSignal(str)
    
    @classmethod
    def get_instance(cls):
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = DataManager()
        return cls._instance
    
    def __init__(self):
        """초기화 - 싱글톤이므로 한 번만 호출됨"""
        super().__init__()
        
        # 이미 초기화되었는지 확인
        if DataManager._instance is not None:
            raise RuntimeError("이 클래스는 싱글톤입니다. get_instance() 메서드를 사용하세요.")
        
        # 온도 임계값 설정
        self.temp_thresholds = {
            'A': {'min': -30, 'max': -18},  # 냉동 (-30°C ~ -18°C)
            'B': {'min': 0, 'max': 10},     # 냉장 (0°C ~ 10°C)
            'C': {'min': 15, 'max': 25}     # 상온 (15°C ~ 25°C)
        }
        
        # 창고 데이터 초기화
        self._warehouse_data = {
            "A": {"capacity": 100, "used": 0, "temperature": -25.0, "status": "정상", "usage_percent": 37},
            "B": {"capacity": 100, "used": 0, "temperature": 5.0, "status": "정상", "usage_percent": 93},
            "C": {"capacity": 100, "used": 0, "temperature": 20.0, "status": "정상", "usage_percent": 87}
        }
        
        # 오늘 입고 현황 초기화
        self._today_input = {
            "total": 0,
            "A": 0,
            "B": 0,
            "C": 0
        }
        
        # 유통기한 데이터 초기화
        self._expiry_data = {
            "over": 0,
            "soon": 0
        }
        
        # 컨베이어 상태 초기화 (0: 정지, 1: 가동중)
        self._conveyor_status = 0
        
        # 출입 데이터 초기화
        self._access_count = 0
        
        # 알림 목록 초기화
        self._notifications = []
        
        # 서버 연결 상태
        self._server_connected = False
        
        # 서버 연결 객체
        self._server_connection = None
        
        # 데이터 폴링 스레드 시작
        self._running = True
        self.polling_thread = threading.Thread(target=self._poll_server_data, daemon=True)
        self.polling_thread.start()
        
        # 타이머로 랜덤 데이터 변경 (테스트용)
        self._demo_timer = QTimer()
        self._demo_timer.timeout.connect(self._generate_demo_data)
        self._demo_timer.start(5000)  # 5초마다 데이터 변경
    
    def set_server_connection(self, server_connection):
        """서버 연결 객체 설정"""
        self._server_connection = server_connection
    
    def _poll_server_data(self):
        """서버에서 주기적으로 데이터를 폴링하는 스레드 함수"""
        while self._running:
            try:
                if not self._server_connected:
                    # 서버 연결 시도
                    self._try_connect_server()
                
                if self._server_connected and self._server_connection is not None:
                    # 서버 연결 객체를 사용하여 데이터 가져오기
                    try:
                        self._fetch_environment_data()
                        self._fetch_inventory_data()
                        self._fetch_expiry_data()
                        self._fetch_conveyor_status()
                    except Exception as e:
                        logger.error(f"서버에서 데이터 가져오기 실패: {str(e)}")
                        self._server_connected = False
                        self.notification_added.emit(f"서버 데이터 가져오기 실패: {str(e)}")
            except Exception as e:
                logger.error(f"데이터 폴링 중 오류: {str(e)}")
                self._server_connected = False
                self.notification_added.emit(f"서버 연결 실패: {str(e)}")
            
            # 5초 대기
            time.sleep(5)
    
    def _try_connect_server(self):
        """서버 연결 시도"""
        try:
            # ServerConnection 객체가 있으면 사용
            if self._server_connection is not None:
                if self._server_connection.is_connected:
                    self._server_connected = True
                    return True
                else:
                    # 재연결 시도
                    self._server_connected = False
                    return False
            
            # 직접 연결 시도 (서버 연결 객체가 없는 경우)
            try:
                # 서버 상태 확인
                url = f"{SERVER_BASE_URL}/status"
                
                # 실제 환경에서 사용할 코드
                # response = requests.get(url, timeout=2)
                # if response.status_code == 200:
                #     self._server_connected = True
                #     self.notification_added.emit("서버 연결 성공")
                #     return True
                
                # 테스트용 코드 (항상 연결 실패)
                self._server_connected = False
                return False
            except Exception as e:
                logger.error(f"서버 연결 시도 중 오류: {str(e)}")
                self._server_connected = False
                return False
        except Exception as e:
            logger.error(f"서버 연결 처리 중 오류: {str(e)}")
            self._server_connected = False
            return False
    
    def _fetch_environment_data(self):
        """환경 데이터 가져오기"""
        if self._server_connection is not None:
            try:
                # 서버 연결 객체를 통해 API the code is able to call and process the API results
                pass
            except Exception as e:
                logger.error(f"환경 데이터 가져오기 오류: {str(e)}")
        else:
            # 실제 환경에서 사용할 코드
            # url = f"{SERVER_BASE_URL}/environment/status"
            # response = requests.get(url)
            # if response.status_code == 200:
            #     data = response.json()
            #     # 데이터 처리
            #     pass
            pass
    
    def _fetch_inventory_data(self):
        """재고 데이터 가져오기"""
        if self._server_connection is not None:
            try:
                # 서버 연결 객체를 통해 API 호출
                pass
            except Exception as e:
                logger.error(f"재고 데이터 가져오기 오류: {str(e)}")
        else:
            # 실제 환경에서 사용할 코드
            # url = f"{SERVER_BASE_URL}/inventory/status"
            # response = requests.get(url)
            # if response.status_code == 200:
            #     data = response.json()
            #     # 데이터 처리
            #     pass
            pass
    
    def _fetch_expiry_data(self):
        """유통기한 데이터 가져오기"""
        if self._server_connection is not None:
            try:
                # 서버 연결 객체를 통해 API 호출
                pass
            except Exception as e:
                logger.error(f"유통기한 데이터 가져오기 오류: {str(e)}")
        else:
            # 실제 환경에서 사용할 코드
            # url_over = f"{SERVER_BASE_URL}/expiry/expired"
            # url_soon = f"{SERVER_BASE_URL}/expiry/alerts"
            # response_over = requests.get(url_over)
            # response_soon = requests.get(url_soon)
            # if response_over.status_code == 200 and response_soon.status_code == 200:
            #     data_over = response_over.json()
            #     data_soon = response_soon.json()
            #     # 데이터 처리
            #     pass
            pass
    
    def _fetch_conveyor_status(self):
        """컨베이어 상태 가져오기"""
        if self._server_connection is not None:
            try:
                # 서버 연결 객체를 통해 API 호출
                pass
            except Exception as e:
                logger.error(f"컨베이어 상태 가져오기 오류: {str(e)}")
        else:
            # 실제 환경에서 사용할 코드
            # url = f"{SERVER_BASE_URL}/sort/inbound/status"
            # response = requests.get(url)
            # if response.status_code == 200:
            #     data = response.json()
            #     # 데이터 처리
            #     pass
            pass
    
    def _generate_demo_data(self):
        """데모용 랜덤 데이터 생성 (테스트용)"""
        # 창고 데이터 변경
        for warehouse_id in self._warehouse_data:
            # 온도 변동 시뮬레이션
            current_temp = self._warehouse_data[warehouse_id]["temperature"]
            delta = (random.random() - 0.5)  # -0.5 ~ 0.5 사이 랜덤 변동
            
            if warehouse_id == "A":  # 냉동창고
                new_temp = max(-30, min(-18, current_temp + delta))
                if new_temp < -28:
                    status = "주의"
                elif new_temp > -20:
                    status = "주의"
                else:
                    status = "정상"
            elif warehouse_id == "B":  # 냉장창고
                new_temp = max(0, min(10, current_temp + delta))
                if new_temp < 2:
                    status = "주의"
                elif new_temp > 8:
                    status = "주의"
                else:
                    status = "정상"
            else:  # 상온창고
                new_temp = max(15, min(25, current_temp + delta))
                if new_temp < 17:
                    status = "주의"
                elif new_temp > 23:
                    status = "주의"
                else:
                    status = "정상"
            
            # 가끔 발생하는 문제 시뮬레이션 (5% 확률)
            if random.random() < 0.05:
                if random.random() < 0.2:  # 심각한 문제 (1% 확률)
                    status = "비정상"
                    # 갑작스러운 온도 변화
                    delta = random.choice([-3, 3])
                    new_temp = current_temp + delta
                    message = f"{warehouse_id}창고 온도 급격한 변화: {new_temp:.1f}°C"
                    self.notification_added.emit(message)
            
            # 창고 데이터 업데이트
            self._warehouse_data[warehouse_id]["temperature"] = new_temp
            self._warehouse_data[warehouse_id]["status"] = status
        
        # 변경 시그널 발생
        self.warehouse_data_changed.emit()
        
        # 입고 현황 변경 (20% 확률)
        if random.random() < 0.2:
            warehouse = random.choice(["A", "B", "C"])
            count = random.randint(1, 3)
            
            self._today_input[warehouse] += count
            self._today_input["total"] += count
            
            # 창고 사용량 업데이트
            self._warehouse_data[warehouse]["used"] += count
            self._warehouse_data[warehouse]["used"] = min(
                self._warehouse_data[warehouse]["used"],
                self._warehouse_data[warehouse]["capacity"]
            )
            
            # 사용률 계산
            self._warehouse_data[warehouse]["usage_percent"] = int(
                (self._warehouse_data[warehouse]["used"] / 
                 self._warehouse_data[warehouse]["capacity"]) * 100
            )
            
            # 알림 추가
            message = f"{warehouse}창고에 {count}개 상품 입고 완료"
            self.notification_added.emit(message)
            
            # 변경 시그널 발생
            self.inventory_data_changed.emit()
        
        # 유통기한 데이터 변경 (10% 확률)
        if random.random() < 0.1:
            self._expiry_data["over"] = random.randint(0, 5)
            self._expiry_data["soon"] = random.randint(2, 15)
            
            # 알림 추가 (유통기한 경과 상품이 있는 경우)
            if self._expiry_data["over"] > 0:
                message = f"유통기한 경과 상품 {self._expiry_data['over']}개 발견"
                self.notification_added.emit(message)
            
            # 변경 시그널 발생
            self.expiry_data_changed.emit()
        
        # 컨베이어 상태 변경 (15% 확률)
        if random.random() < 0.15:
            # 0(정지)과 1(가동중) 토글
            new_status = 1 - self._conveyor_status
            
            if new_status != self._conveyor_status:
                if new_status == 1:
                    message = "컨베이어 벨트 가동 시작"
                    self.notification_added.emit(message)
                else:
                    message = "컨베이어 벨트 가동 중지"
                    self.notification_added.emit(message)
                
                self._conveyor_status = new_status
                
                # 변경 시그널 발생
                self.conveyor_status_changed.emit()
        
        # 출입 데이터 증가 (20% 확률)
        if random.random() < 0.2:
            self._access_count += 1
        
        # 랜덤 시스템 알림 추가 (5% 확률)
        if random.random() < 0.05:
            notifications = [
                "시스템 상태 점검 완료",
                "데이터베이스 백업 완료", 
                "센서 네트워크 연결 확인",
                "일일 리포트 생성 완료"
            ]
            message = random.choice(notifications)
            self.notification_added.emit(message)
    
    # ==== 데이터 접근 메서드 ====
    def get_warehouse_data(self):
        """창고 데이터 반환"""
        return self._warehouse_data
    
    def get_warehouse_status(self, warehouse_id):
        """특정 창고 상태 반환"""
        if warehouse_id in self._warehouse_data:
            return self._warehouse_data[warehouse_id]
        return None
    
    def get_today_input(self):
        """오늘 입고 현황 반환"""
        return self._today_input
    
    def get_expiry_data(self):
        """유통기한 데이터 반환"""
        return self._expiry_data
    
    def get_conveyor_status(self):
        """컨베이어 상태 반환 (0: 정지, 1: 가동중)"""
        return self._conveyor_status
    
    def get_access_count(self):
        """출입 횟수 반환"""
        return self._access_count
    
    def get_temperature_thresholds(self):
        """온도 임계값 반환"""
        return self.temp_thresholds
    
    # ==== Dashboard.py와 연동하기 위한 특화된 메서드 ====
    def get_progress_bar_values(self):
        """창고별 프로그레스바 값 반환"""
        return {
            "A": self._warehouse_data["A"]["usage_percent"],
            "B": self._warehouse_data["B"]["usage_percent"],
            "C": self._warehouse_data["C"]["usage_percent"]
        }
    
    def get_warehouse_temperatures(self):
        """창고별 온도 값 반환"""
        return {
            "A": self._warehouse_data["A"]["temperature"],
            "B": self._warehouse_data["B"]["temperature"],
            "C": self._warehouse_data["C"]["temperature"]
        }
    
    def get_warehouse_statuses(self):
        """창고별 상태 반환"""
        return {
            "A": self._warehouse_data["A"]["status"],
            "B": self._warehouse_data["B"]["status"],
            "C": self._warehouse_data["C"]["status"]
        }
    
    def get_expiry_counts(self):
        """유통기한 경과/임박 개수 반환"""
        return self._expiry_data
    
    def add_notification(self, message):
        """알림 목록에 메시지 추가"""
        self._notifications.append(message)
        self.notification_added.emit(message)
    
    def update_server_connection_status(self, connected):
        """서버 연결 상태 업데이트"""
        self._server_connected = connected
    
    def shutdown(self):
        """애플리케이션 종료 시 호출"""
        self._running = False
        
        # 스레드 종료 대기
        if self.polling_thread.is_alive():
            self.polling_thread.join(1.0)