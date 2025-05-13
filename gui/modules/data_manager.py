import os
import sys
import json
import time
import datetime
import threading
import logging
import requests
from typing import Dict, Any, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DataManager")

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
        
        logger.info("DataManager 초기화 시작")
        
        # config.py의 WAREHOUSES 설정과 일치하도록 온도 임계값 설정
        self.temp_thresholds = {
            'A': {'min': -30, 'max': -18},  # 냉동 (-30°C ~ -18°C)
            'B': {'min': 0, 'max': 10},     # 냉장 (0°C ~ 10°C)
            'C': {'min': 15, 'max': 25}     # 상온 (15°C ~ 25°C)
        }
        
        # 창고 데이터 초기화 (DB의 warehouse 테이블과 일치)
        self._warehouse_data = {
            "A": {
                "type": "freezer",
                "capacity": 16, 
                "used": 0, 
                "temperature": 0.0, 
                "status": "알 수 없음", 
                "usage_percent": 0
            },
            "B": {
                "type": "refrigerator",
                "capacity": 16, 
                "used": 0, 
                "temperature": 0.0, 
                "status": "알 수 없음", 
                "usage_percent": 0
            },
            "C": {
                "type": "room_temp",
                "capacity": 16, 
                "used": 0, 
                "temperature": 0.0, 
                "status": "알 수 없음", 
                "usage_percent": 0
            }
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
            "over": 0,  # 유통기한 경과
            "soon": 0   # 유통기한 임박 (7일 이내)
        }
        
        # 컨베이어 상태 초기화 (0: 정지, 1: 가동중)
        self._conveyor_status = 0
        
        # 출입 데이터 초기화
        self._access_logs = []
        
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
        
        logger.info("DataManager 초기화 완료")
    
    def set_server_connection(self, server_connection):
        """서버 연결 객체 설정"""
        self._server_connection = server_connection
        logger.info("서버 연결 객체 설정 완료")
    
    def _poll_server_data(self):
        """서버에서 주기적으로 데이터를 폴링하는 스레드 함수"""
        logger.info("데이터 폴링 스레드 시작")
        
        while self._running:
            try:
                if self._server_connected and self._server_connection is not None:
                    # 서버 데이터 가져오기
                    self._fetch_all_data()
                else:
                    # 서버 연결 시도
                    self._try_connect_server()
                
            except Exception as e:
                logger.error(f"데이터 폴링 중 오류: {str(e)}")
                self._server_connected = False
                
                # 알림 추가
                message = f"서버 데이터 폴링 오류: {str(e)}"
                self._add_notification_thread_safe(message)
            
            # 폴링 간격 (5초)
            time.sleep(5)
        
        logger.info("데이터 폴링 스레드 종료")
    
    def _add_notification_thread_safe(self, message):
        """스레드 안전한 알림 추가 메서드"""
        # 메인 스레드에서 시그널 발생
        self.notification_added.emit(message)
        
        # 알림 목록에 추가
        self._notifications.append({
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    def _try_connect_server(self):
        """서버 연결 시도"""
        if self._server_connection:
            # 이미 연결된 경우 건너뛰기
            if self._server_connection.is_connected:
                self._server_connected = True
                return True
            
            # 재연결 시도
            if self._server_connection.connect_to_server():
                self._server_connected = True
                return True
            else:
                self._server_connected = False
                return False
        
        return False
    
    def _fetch_data_safely(self, fetch_function, error_message, retry=True):
        """안전하게 데이터 가져오기 위한 헬퍼 함수"""
        if not self._server_connection or not self._server_connected:
            logger.warning("서버 연결 없음 - 데이터를 가져올 수 없습니다.")
            return False
            
        try:
            # 함수 실행
            fetch_function()
            return True
        except Exception as e:
            logger.error(f"{error_message}: {str(e)}")
            
            # 일시적인 연결 오류 시 재연결 시도
            if retry and ("연결이 끊어졌습니다" in str(e) or "Connection" in str(e)):
                logger.info("연결 오류 감지, 재연결 시도...")
                if self._try_connect_server():
                    logger.info("재연결 성공, 데이터 다시 가져오기 시도")
                    return self._fetch_data_safely(fetch_function, error_message, retry=False)
            
            # 오류 알림 추가
            self.add_notification(f"데이터 가져오기 오류: {error_message}")
            return False
    
    def _fetch_all_data(self):
        """모든 서버 데이터 가져오기"""
        try:
            self._fetch_environment_data()
            self._fetch_inventory_data()
            self._fetch_expiry_data()
            self._fetch_conveyor_status()
            logger.debug("모든 서버 데이터 가져오기 완료")
        except Exception as e:
            logger.error(f"서버 데이터 가져오기 실패: {str(e)}")
            raise
    
    def _fetch_environment_data(self):
        """환경 데이터 가져오기"""
        if not self._server_connection:
            return
        
        try:
            # 환경 상태 조회 API 호출
            response = self._server_connection.get_environment_status()
            
            # JSON 구조에 맞게 응답 처리
            if response and response.get("success", False):
                warehouse_data = response.get("data", {})
                
                for warehouse_id, data in warehouse_data.items():
                    if warehouse_id in self._warehouse_data:
                        # JSON 구조에 맞게 데이터 맵핑
                        self._warehouse_data[warehouse_id]["temperature"] = data.get("current_temp")
                        self._warehouse_data[warehouse_id]["target_temp"] = data.get("target_temp")
                        self._warehouse_data[warehouse_id]["status"] = data.get("status")
                        self._warehouse_data[warehouse_id]["used"] = data.get("used")
                        self._warehouse_data[warehouse_id]["capacity"] = data.get("capacity")
                        self._warehouse_data[warehouse_id]["usage_percent"] = data.get("usage_percent")
                
                # 변경 신호 발생
                self.warehouse_data_changed.emit()
                logger.debug("환경 데이터 업데이트 완료")
            
        except Exception as e:
            logger.error(f"환경 데이터 가져오기 오류: {str(e)}")
            raise
    
    def _fetch_inventory_data(self):
        """재고 데이터 가져오기"""
        if not self._server_connection:
            return
        
        try:
            # 재고 상태 조회 API 호출
            response = self._server_connection.get_inventory_status()
            
            # 응답 처리 (예시)
            if response and "success" in response and response["success"]:
                data = response.get("data", {})
                
                # 창고별 사용량 업데이트
                for warehouse_id, warehouse_data in data.get("warehouses", {}).items():
                    if warehouse_id in self._warehouse_data:
                        self._warehouse_data[warehouse_id]["used"] = warehouse_data.get("used", 0)
                        self._warehouse_data[warehouse_id]["capacity"] = warehouse_data.get("capacity", 100)
                        
                        # 사용률 계산
                        if self._warehouse_data[warehouse_id]["capacity"] > 0:
                            usage_percent = int((self._warehouse_data[warehouse_id]["used"] / 
                                             self._warehouse_data[warehouse_id]["capacity"]) * 100)
                            self._warehouse_data[warehouse_id]["usage_percent"] = min(100, usage_percent)
                
                # 오늘 입고량 업데이트
                today_input = data.get("today_input", {})
                if today_input:
                    self._today_input = today_input
                
                # 변경 신호 발생
                self.warehouse_data_changed.emit()
                self.inventory_data_changed.emit()
                logger.debug("재고 데이터 업데이트 완료")
            
        except Exception as e:
            logger.error(f"재고 데이터 가져오기 오류: {str(e)}")
            raise
    
    def _fetch_expiry_data(self):
        """유통기한 데이터 가져오기"""
        if not self._server_connection:
            return
        
        try:
            # 유통기한 만료 항목 조회
            expired_response = self._server_connection.get_expired_items()
            
            # 유통기한 경고 항목 조회 (7일 이내)
            alerts_response = self._server_connection.get_expiry_alerts(days=7)
            
            # 응답 처리
            if expired_response and "success" in expired_response and expired_response["success"]:
                self._expiry_data["over"] = expired_response.get("total_count", 0)
            
            if alerts_response and "success" in alerts_response and alerts_response["success"]:
                self._expiry_data["soon"] = alerts_response.get("total_count", 0)
            
            # 변경 신호 발생
            self.expiry_data_changed.emit()
            logger.debug("유통기한 데이터 업데이트 완료")
            
        except Exception as e:
            logger.error(f"유통기한 데이터 가져오기 오류: {str(e)}")
            raise
    
    def _fetch_conveyor_status(self):
        """컨베이어 상태 가져오기"""
        if not self._server_connection:
            return
        
        try:
            # 분류기 상태 조회 API 호출
            response = self._server_connection.get_sorting_status()
            
            # 응답 처리
            if response:
                is_running = response.get("is_running", False)
                self._conveyor_status = 1 if is_running else 0
                
                # 변경 신호 발생
                self.conveyor_status_changed.emit()
                logger.debug(f"컨베이어 상태 업데이트: {'가동중' if is_running else '정지'}")
            
        except Exception as e:
            logger.error(f"컨베이어 상태 가져오기 오류: {str(e)}")
            raise
    
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
    
    def get_access_logs(self):
        """출입 로그 반환"""
        return self._access_logs
    
    def get_temperature_thresholds(self):
        """온도 임계값 반환"""
        return self.temp_thresholds
    
    def get_notifications(self):
        """알림 목록 반환"""
        return self._notifications
    
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
    
    # ==== 상태 변경 메서드 ====
    def add_notification(self, message):
        """알림 목록에 메시지 추가"""
        self._notifications.append({
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        })
        self.notification_added.emit(message)
        logger.info(f"알림 추가: {message}")
    
    def update_server_connection_status(self, connected):
        """서버 연결 상태 업데이트"""
        self._server_connected = connected
        logger.info(f"서버 연결 상태 업데이트: {'연결됨' if connected else '연결 끊김'}")
    
    def shutdown(self):
        """애플리케이션 종료 시 호출"""
        self._running = False
        
        # 스레드 종료 대기
        if hasattr(self, 'polling_thread') and self.polling_thread.is_alive():
            self.polling_thread.join(1.0)
            
        logger.info("DataManager 종료 완료")

    def set_offline_mode(self, is_offline=True):
        """오프라인 모드 설정"""
        self._offline_mode = is_offline
        
        if is_offline:
            logger.info("오프라인 모드 활성화: 기본 데이터 사용")
            
            # 연결 상태 업데이트
            self._server_connected = False
            
            # 기본 데이터 로드 (더미 데이터)
            self._load_default_data()
            
            # UI 업데이트 신호 발생
            self.warehouse_data_changed.emit()
            self.inventory_data_changed.emit()
            self.expiry_data_changed.emit()
            self.conveyor_status_changed.emit()
            
            # 알림 추가
            self.add_notification("서버 연결 없음 - 제한된 기능으로 실행 중")
        else:
            logger.info("오프라인 모드 비활성화: 실시간 데이터 사용")

    def _load_default_data(self):
        """오프라인 모드를 위한 기본 데이터 로드"""
        # 기본 창고 데이터
        self._warehouse_data = {
            "A": {
                "type": "freezer",
                "capacity": 16, 
                "used": 5, 
                "temperature": -22.0, 
                "status": "정상", 
                "usage_percent": 31
            },
            "B": {
                "type": "refrigerator",
                "capacity": 16, 
                "used": 8, 
                "temperature": 4.0, 
                "status": "정상", 
                "usage_percent": 50
            },
            "C": {
                "type": "room_temp",
                "capacity": 16, 
                "used": 12, 
                "temperature": 20.0, 
                "status": "정상", 
                "usage_percent": 75
            }
        }
        
        # 기본 입고 현황
        self._today_input = {
            "total": 25,
            "A": 5,
            "B": 8,
            "C": 12
        }
        
        # 기본 유통기한 데이터
        self._expiry_data = {
            "over": 3, 
            "soon": 7   
        }
        
        # 컨베이어 상태
        self._conveyor_status = 0  # 정지   