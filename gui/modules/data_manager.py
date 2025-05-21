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
    waiting_data_changed = pyqtSignal()  # 입고 대기 데이터 변경 시그널 추가
    access_logs_changed = pyqtSignal()   # 출입 로그 변경 시그널 추가 
    notification_added = pyqtSignal(str)
    server_connection_changed = pyqtSignal(bool) # 서버 연결 상태 변경 시그널 추가
    
    @classmethod
    def get_instance(cls):
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = DataManager()
        return cls._instance
    
    def __init__(self):
        """초기화 (싱글톤이므로 한 번만 실행)"""
        super().__init__()  # 추가: 부모 클래스(QObject) 초기화
        
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 설정 불러오기
        logger.info("DataManager 초기화 시작")
        
        # 초기 임계값 기본값 설정 (서버 연결 전)
        self.temp_thresholds = {
            'A': {'min': -30, 'max': -18, 'type': 'freezer'},
            'B': {'min': 0, 'max': 10, 'type': 'refrigerator'},
            'C': {'min': 15, 'max': 25, 'type': 'room_temp'}
        }
            
        # 창고 데이터 초기화 (DB의 warehouse 테이블과 일치)
        self._warehouse_data = {
            "A": {
                "type": "freezer",
                "capacity": 100, 
                "used": 0, 
                "temperature": 0.0, 
                "status": "알 수 없음", 
                "usage_percent": 0
            },
            "B": {
                "type": "refrigerator",
                "capacity": 100, 
                "used": 0, 
                "temperature": 0.0, 
                "status": "알 수 없음", 
                "usage_percent": 0
            },
            "C": {
                "type": "room_temp",
                "capacity": 100, 
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
        
        # 입고 대기 데이터 추가
        self._waiting_items = 0
        
        # 유통기한 데이터 초기화
        self._expiry_data = {
            "over": 0,  # 유통기한 경과
            "soon": 0   # 유통기한 임박 (7일 이내)
        }
        
        # 컨베이어 상태 초기화 (0: 정지, 1: 가동중, 2: 일시정지)
        self._conveyor_status = 0
        
        # 출입 데이터 초기화
        self._access_logs = []
        
        # 알림 목록 초기화
        self._notifications = []
        
        # 서버 연결 상태
        self._server_connected = False
        
        # 서버 연결 객체
        self._server_connection = None
        
        # 마지막 오류 정보 저장
        self._last_error = {
            "time": None,
            "type": None,
            "message": None
        }
        
        # 데이터 타임스탬프 초기화 (마지막 업데이트 시간)
        self._data_timestamps = {
            "warehouse": None,
            "inventory": None,
            "expiry": None,
            "conveyor": None,
            "access_logs": None,
            "waiting": None
        }
        
        # 데이터 폴링 스레드 시작
        self._running = True
        self.polling_thread = threading.Thread(target=self._poll_server_data, daemon=True)
        self.polling_thread.start()
        self._initialized = True
        logger.info("DataManager 초기화 완료")

    # 이전에 제안한 _load_temperature_thresholds 메서드를 다음과 같이 수정

    def _load_temperature_thresholds(self):
        """서버에서 온도 임계값 로드"""
        if not self.is_server_connected() or not self._server_connection:
            logger.warning("서버 연결 없음 - 기본 온도 임계값 사용")
            return False
            
        try:
            # 서버에서 온도 임계값 조회
            thresholds = self._server_connection.get_temperature_thresholds()
            if thresholds:
                # 동일한 필드 이름 사용을 위한 변환
                for wh_id, data in thresholds.items():
                    if "min" in data:
                        self.temp_thresholds[wh_id] = {
                            "min": data["min"],
                            "max": data["max"],
                            "type": data.get("type", "unknown")
                        }
                
                logger.info("서버에서 온도 임계값 로드 완료")
                # 온도 임계값 변경 이벤트 발생 (GUI 업데이트용)
                self.warehouse_data_changed.emit()
                return True
        except Exception as e:
            logger.error(f"온도 임계값 로드 오류: {str(e)}")
        
        return False

    # 폴링 스레드에 온도 임계값 주기적 갱신 로직 추가
    def _poll_server_data(self):
        """실시간 이벤트로 업데이트되지 않는 중요 데이터만 주기적으로 폴링"""
        logger.info("데이터 폴링 스레드 시작 - 최소 폴링 모드")
        
        # 데이터 유형별 폴링 주기 설정 (초 단위)
        polling_intervals = {
            "temperature_thresholds": 120,  # 온도 임계값은 2분마다
            "environment": 120,             # 환경 데이터는 온도 이벤트로 실시간 업데이트되므로 거의 폴링 필요 없음
            # ... 기존 폴링 간격 ...
        }
        
        # 데이터 유형별 마지막 폴링 시간
        last_poll_time = {k: 0 for k in polling_intervals.keys()}
        
        while self._running:
            try:
                if self.is_server_connected():
                    current_time = time.time()
                    
                    # 온도 임계값 (주기적 확인)
                    if current_time - last_poll_time["temperature_thresholds"] >= polling_intervals["temperature_thresholds"]:
                        self._load_temperature_thresholds()
                        last_poll_time["temperature_thresholds"] = current_time
                    
                    # ... 기존 폴링 로직 ...
                
                # 15초 간격으로 폴링 확인
                time.sleep(15)
                
            except Exception as e:
                logger.error(f"데이터 폴링 중 오류: {str(e)}")
                # ... 오류 처리 ...
                time.sleep(15)

    def set_server_connection(self, server_connection):
        """서버 연결 객체 설정"""
        self._server_connection = server_connection
        logger.info("서버 연결 객체 설정 완료")
        
        # 서버 연결 상태 변경 이벤트 연결
        if hasattr(server_connection, 'connectionStatusChanged'):
            server_connection.connectionStatusChanged.connect(self._handle_server_connection_changed)
        
        # 서버 이벤트 핸들러 연결 추가
        if hasattr(server_connection, 'eventReceived'):
            server_connection.eventReceived.connect(self.handle_server_event)
            logger.info("서버 이벤트 핸들러 연결 완료")
        
        # 서버 연결되면 온도 임계값 로드
        if self.is_server_connected():
            self._load_temperature_thresholds()
    
    def _handle_server_connection_changed(self, connected, message=""):
        """서버 연결 상태 변경 처리"""
        self._server_connected = connected
        self.server_connection_changed.emit(connected)
        
        # 서버 연결 되었을 때 즉시 데이터 갱신
        if connected:
            # 온도 임계값 로드
            self._load_temperature_thresholds()
            # 다른 데이터 로드
            self._fetch_all_data()
    
    def handle_server_event(self, category, action, payload):
        """서버 이벤트 처리"""
        logger.debug(f"서버 이벤트 수신: {category}/{action}")
        
        try:
            # 환경 관련 이벤트 처리
            if category == "environment":
                # 팬 상태 업데이트 이벤트
                if action == "fan_status_update" and "warehouse" in payload:
                    warehouse_id = payload.get("warehouse")
                    fan_mode = payload.get("mode", "off")
                    fan_speed = payload.get("speed", 0)
                    
                    # 팬 상태 업데이트
                    self.update_fan_status(warehouse_id, fan_mode, fan_speed)
                    logger.debug(f"팬 상태 업데이트: 창고={warehouse_id}, 모드={fan_mode}, 속도={fan_speed}")
                    
                # 온도 업데이트 이벤트
                elif action == "temperature_update" and "warehouse_id" in payload:
                    warehouse_id = payload.get("warehouse_id")
                    temperature = payload.get("temperature")
                    
                    if warehouse_id in self._warehouse_data:
                        self._warehouse_data[warehouse_id]["temperature"] = temperature
                        self.warehouse_data_changed.emit()
                        
                # 경고 상태 업데이트 이벤트
                elif action == "warehouse_warning" and "warehouse" in payload:
                    warehouse_id = payload.get("warehouse")
                    warning = payload.get("warning", False)
                    
                    if warehouse_id in self._warehouse_data:
                        status = "경고" if warning else "정상"
                        self._warehouse_data[warehouse_id]["status"] = status
                        self.warehouse_data_changed.emit()
                        
                        # 경고 상태 변경 시 알림 추가
                        warehouse_name = "냉동 창고"
                        if warehouse_id == "B":
                            warehouse_name = "냉장 창고"
                        elif warehouse_id == "C":
                            warehouse_name = "상온 창고"
                        
                        if warning:
                            self.add_notification(f"{warehouse_name}({warehouse_id}) 온도 경고 발생")
                        else:
                            self.add_notification(f"{warehouse_name}({warehouse_id}) 온도 정상 복귀")
                    
        except Exception as e:
            logger.error(f"서버 이벤트 처리 오류: {str(e)}")

    def is_server_connected(self):
        """서버 연결 상태 반환 - 모든 페이지가 이 메서드를 사용해야 함"""
        return self._server_connected and self._server_connection and self._server_connection.is_connected
    def _fetch_environment_data(self):
        """환경/창고 데이터 가져오기"""
        if not self.is_server_connected() or not self._should_update_data("warehouse"):
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
                        self._warehouse_data[warehouse_id]["temperature"] = data.get("current_temp", 0.0)
                        self._warehouse_data[warehouse_id]["target_temp"] = data.get("target_temp", 0.0)
                        self._warehouse_data[warehouse_id]["status"] = data.get("status", "알 수 없음")
                        
                        # used와 capacity 값을 직접 매핑
                        # 사용량은 이제 실시간으로 계산된 값
                        self._warehouse_data[warehouse_id]["used"] = data.get("used_capacity", 0)
                        self._warehouse_data[warehouse_id]["capacity"] = data.get("total_capacity", 100)
                        
                        # usage_percent 직접 할당 (계산된 값 사용)
                        if "utilization_rate" in data:
                            self._warehouse_data[warehouse_id]["usage_percent"] = int(data.get("utilization_rate", 0) * 100)
                        else:
                            # 백분율 계산
                            capacity = self._warehouse_data[warehouse_id]["capacity"]
                            used = self._warehouse_data[warehouse_id]["used"]
                            if capacity > 0:
                                usage_percent = (used / capacity) * 100
                                self._warehouse_data[warehouse_id]["usage_percent"] = min(100, int(usage_percent))
                
                # 변경 신호 발생
                self.warehouse_data_changed.emit()
                logger.debug("환경 데이터 업데이트 완료")
        
        except Exception as e:
            logger.error(f"환경 데이터 가져오기 오류: {str(e)}")

    def _poll_server_data(self):
        """실시간 이벤트로 업데이트되지 않는 중요 데이터만 주기적으로 폴링"""
        logger.info("데이터 폴링 스레드 시작 - 최소 폴링 모드")
        
        # 데이터 유형별 폴링 주기 설정 (초 단위)
        polling_intervals = {
            "warehouse": 120,     # 환경/창고 데이터는 2분마다
            "inventory": 300,     # 재고 데이터는 5분마다
            "expiry": 600,        # 유통기한 데이터는 10분마다
            "access_logs": 300,   # 출입 로그는 5분마다
            "waiting": 300        # 대기 데이터는 5분마다
        }
        
        # 데이터 유형별 마지막 폴링 시간
        last_poll_time = {k: 0 for k in polling_intervals.keys()}
        
        while self._running:
            try:
                if self.is_server_connected():
                    current_time = time.time()
                    
                    # 환경/창고 데이터
                    if current_time - last_poll_time["warehouse"] >= polling_intervals["warehouse"]:
                        self._fetch_environment_data()  # 이 부분 수정
                        last_poll_time["warehouse"] = current_time
                    
                    # 재고 데이터
                    if current_time - last_poll_time["inventory"] >= polling_intervals["inventory"]:
                        self._fetch_inventory_data()
                        last_poll_time["inventory"] = current_time
                    
                    # 유통기한 데이터
                    if current_time - last_poll_time["expiry"] >= polling_intervals["expiry"]:
                        self._fetch_expiry_data() 
                        last_poll_time["expiry"] = current_time
                    
                    # 출입 로그
                    if current_time - last_poll_time["access_logs"] >= polling_intervals["access_logs"]:
                        self._fetch_access_logs()
                        last_poll_time["access_logs"] = current_time
                    
                    # 대기 데이터
                    if current_time - last_poll_time["waiting"] >= polling_intervals["waiting"]:
                        self._fetch_waiting_data()
                        last_poll_time["waiting"] = current_time
                
                # 15초 간격으로 폴링 확인
                time.sleep(15)
                
            except Exception as e:
                logger.error(f"데이터 폴링 중 오류: {str(e)}")
                time.sleep(15)
    
    # gui/modules/data_manager.py에 아래 메서드 추가
    def load_page_data(self, page_name):
        """특정 페이지가 활성화됐을 때 해당 페이지에 필요한 데이터만 가져옴"""
        if not self.is_server_connected():
            logger.warning(f"{page_name} 페이지 데이터 로드 실패: 서버 연결 안됨")
            return False
                
        try:
            logger.info(f"{page_name} 페이지 데이터 로드 중...")
            
            if page_name == "dashboard":
                # 대시보드 페이지 - 모든 요약 데이터
                self._fetch_environment_data()
                self._fetch_inventory_data()
                self._fetch_waiting_data()
                self._fetch_expiry_data()
                self._fetch_conveyor_status()
                
            elif page_name == "environment":
                # 환경 페이지 - 환경 데이터만
                self._fetch_environment_data()  # _fetch_environment_data 대신 이 메서드 사용
                
            elif page_name == "inventory":
                # 재고 페이지 - 재고 및 대기 데이터
                self._fetch_inventory_data()
                self._fetch_waiting_data()
                
            elif page_name == "expiration":
                # 유통기한 페이지 - 유통기한 데이터
                self._fetch_expiry_data()
                
            elif page_name == "devices":
                # 장치 페이지 - 컨베이어 상태
                self._fetch_conveyor_status()
                
            elif page_name == "access":
                # 출입 페이지 - 출입 로그
                self._fetch_access_logs()
                
            logger.info(f"{page_name} 페이지 데이터 로드 완료")
            return True
                
        except Exception as e:
            logger.error(f"{page_name} 페이지 데이터 로드 중 오류: {str(e)}")
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
            return False
    def _add_notification_thread_safe(self, message):
        """스레드 안전한 알림 추가 메서드"""
        # 메인 스레드에서 시그널 발생
        self.notification_added.emit(message)
        
        # 알림 목록에 추가
        self._notifications.append({
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    def _fetch_all_data(self):
        """모든 서버 데이터 가져오기"""
        try:
            # 각 데이터 폴링 - 타임스탬프를 확인하여 필요할 때만 갱신
            self._fetch_environment_data()
            self._fetch_inventory_data()
            self._fetch_waiting_data()
            self._fetch_expiry_data()
            self._fetch_conveyor_status()
            self._fetch_access_logs()
            
            logger.debug("모든 서버 데이터 가져오기 완료")
        except Exception as e:
            logger.error(f"서버 데이터 가져오기 실패: {str(e)}")
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
    
    def _should_update_data(self, data_type, min_interval=5):
        """데이터 업데이트 필요성 확인 (중복 요청 방지)"""
        current_time = datetime.datetime.now()
        last_update = self._data_timestamps.get(data_type)
        
        # 마지막 업데이트가 없거나 최소 간격이 지났으면 업데이트 필요
        if last_update is None or (current_time - last_update).total_seconds() >= min_interval:
            self._data_timestamps[data_type] = current_time
            return True
            return False
    
    def _fetch_inventory_data(self):
        """재고 데이터 가져오기"""
        if not self.is_server_connected() or not self._should_update_data("inventory"):
            return
        
        try:
            # 재고 상태 조회 API 호출
            response = self._server_connection.get_inventory_status()
            
            # 디버깅: 전체 응답 로깅
            logger.info(f"서버에서 받은 재고 상태 데이터: {response}")
            
            # 응답 처리
            if response and "success" in response and response["success"]:
                data = response.get("data", {})
                
                # 창고별 사용량 업데이트
                for warehouse_id, warehouse_data in data.get("warehouses", {}).items():
                    if warehouse_id in self._warehouse_data:
                        # 디버깅: 창고 데이터 로깅
                        logger.debug(f"창고 {warehouse_id} 데이터: {warehouse_data}")
                        
                        # 다양한 필드명 지원 (used_capacity 또는 used)
                        self._warehouse_data[warehouse_id]["used"] = warehouse_data.get("used_capacity", warehouse_data.get("used", 0))
                        self._warehouse_data[warehouse_id]["capacity"] = warehouse_data.get("total_capacity", warehouse_data.get("capacity", 100))
                        
                        # 백분율 계산 - 다양한 필드명 지원
                        if "utilization_rate" in warehouse_data:
                            # utilization_rate는 0.0~1.0 범위의 값이므로 100을 곱해야 함
                            utilization_rate = warehouse_data.get("utilization_rate", 0)
                            self._warehouse_data[warehouse_id]["usage_percent"] = min(100, int(utilization_rate * 100))
                        elif "usage_percent" in warehouse_data:
                            # 이미 0~100 범위인 경우
                            self._warehouse_data[warehouse_id]["usage_percent"] = min(100, int(warehouse_data.get("usage_percent", 0)))
                        else:
                            # 직접 계산
                            capacity = self._warehouse_data[warehouse_id]["capacity"]
                            used = self._warehouse_data[warehouse_id]["used"]
                            if capacity > 0:
                                usage_percent = int((used / capacity) * 100)
                                self._warehouse_data[warehouse_id]["usage_percent"] = min(100, usage_percent)
                
                # 디버깅: 업데이트된 로컬 데이터 로깅
                logger.info(f"업데이트된 창고 데이터: {self._warehouse_data}")
                
                # 변경 신호 발생
                self.warehouse_data_changed.emit()
                self.inventory_data_changed.emit()
                logger.debug("재고 데이터 업데이트 완료 - 신호 발생됨")
                
        except Exception as e:
            logger.error(f"재고 데이터 가져오기 오류: {str(e)}")

    def update_fan_status(self, warehouse_id, fan_mode, fan_speed):
        """팬 상태 정보 업데이트
        
        Args:
            warehouse_id (str): 창고 ID (A, B, C)
            fan_mode (str): 팬 모드 (cool, heat, off)
            fan_speed (int): 팬 속도 (0-3)
        
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            # warehouse_data 딕셔너리 업데이트
            if warehouse_id in self.warehouse_data:
                self.warehouse_data[warehouse_id]["fan_mode"] = fan_mode
                self.warehouse_data[warehouse_id]["fan_speed"] = fan_speed
                
                # 알림 추가
                mode_str = "냉방" if fan_mode == "cool" else "난방" if fan_mode == "heat" else "정지"
                speed_str = "정지" if fan_speed == 0 else f"{fan_speed}단계"
                
                warehouse_name = "냉동 창고"
                if warehouse_id == "B":
                    warehouse_name = "냉장 창고"
                elif warehouse_id == "C":
                    warehouse_name = "상온 창고"
                    
                self.add_notification(f"{warehouse_name}({warehouse_id}) 팬 상태 변경: {mode_str}, {speed_str}")
                
                # 데이터 변경 이벤트 발생
                self.warehouse_data_changed.emit()
                
                return True
            else:
                logger.warning(f"팬 상태 업데이트 실패: 존재하지 않는 창고 ID - {warehouse_id}")
                return False
        except Exception as e:
            logger.error(f"팬 상태 업데이트 오류: {str(e)}")
            return False

    def get_fan_status(self, warehouse_id):
        """창고 팬 상태 정보 조회
        
        Args:
            warehouse_id (str): 창고 ID (A, B, C)
        
        Returns:
            dict: 팬 상태 정보 (mode, speed) 또는 None
        """
        try:
            if warehouse_id in self.warehouse_data:
                warehouse = self.warehouse_data[warehouse_id]
                return {
                    "mode": warehouse.get("fan_mode", "off"),
                    "speed": warehouse.get("fan_speed", 0)
                }
            else:
                logger.warning(f"팬 상태 조회 실패: 존재하지 않는 창고 ID - {warehouse_id}")
                return None
        except Exception as e:
            logger.error(f"팬 상태 조회 오류: {str(e)}")
            return None
        
    def _fetch_inventory_data(self):
        """재고 데이터 가져오기"""
        if not self.is_server_connected() or not self._should_update_data("inventory"):
            return
        
        try:
            # 재고 상태 조회 API 호출
            response = self._server_connection.get_inventory_status()
            
            # 응답 처리
            if response and "success" in response and response["success"]:
                data = response.get("data", {})
                
                # 데이터 타입 검사 후 적절히 처리
                if isinstance(data, dict):
                    # 창고별 사용량 업데이트 (딕셔너리 형식인 경우)
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
                elif isinstance(data, list):
                    # 리스트 형식인 경우 (서버 응답 형식이 변경되었거나 다른 API의 응답인 경우)
                    logger.warning("서버로부터 리스트 형태의 재고 데이터를 받았습니다. 데이터 구조 확인이 필요합니다.")
                    # 여기에 리스트 형태 데이터 처리 로직 추가
                    # 예: 리스트의 각 항목에서 warehouse_id를 키로 사용하여 데이터 추출
                    
                # 변경 신호 발생
                self.warehouse_data_changed.emit()
                self.inventory_data_changed.emit()
                logger.debug("재고 데이터 업데이트 완료")
            
        except Exception as e:
            logger.error(f"재고 데이터 가져오기 오류: {str(e)}")
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
    
    def _fetch_waiting_data(self):
        """입고 대기 데이터 가져오기"""
        if not self.is_server_connected() or not self._should_update_data("waiting"):
            return
        
        try:
            # 입고 대기 정보 조회 API 호출
            response = self._server_connection._send_request('GET', 'inventory/waiting')
            
            # 응답 처리
            if response and response.get("success", True):
                # 입고 대기 수량 업데이트
                self._waiting_items = response.get("waiting", 0)
                
                # 변경 신호 발생
                self.waiting_data_changed.emit()
                logger.debug(f"입고 대기 데이터 업데이트 완료: {self._waiting_items}개")
            
        except Exception as e:
            logger.error(f"입고 대기 데이터 가져오기 오류: {str(e)}")
            
            # 이 오류는 필수 데이터가 아니므로 무시하고 계속 진행
            pass
    
    def _fetch_expiry_data(self):
        """유통기한 데이터 가져오기"""
        if not self.is_server_connected() or not self._should_update_data("expiry"):
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
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
    
    def _fetch_conveyor_status(self):
        """컨베이어 상태 가져오기"""
        if not self.is_server_connected() or not self._should_update_data("conveyor"):
            return
        
        try:
            # 분류기 상태 조회 API 호출
            response = self._server_connection.get_sorter_status()
            
            # 응답 처리
            if response:
                # is_running 필드를 통해 상태 결정
                if "is_running" in response:
                    self._conveyor_status = 1 if response["is_running"] else 0
                # 또는 status 필드가 있는 경우
                elif "status" in response:
                    status = response["status"]
                    if status == "running":
                        self._conveyor_status = 1  # 작동중
                    elif status == "pause":
                        self._conveyor_status = 2  # 일시정지
                else:
                        self._conveyor_status = 0  # 정지
                
                # 변경 신호 발생
                self.conveyor_status_changed.emit()
                logger.debug(f"컨베이어 상태 업데이트: {self._conveyor_status}")
            
        except Exception as e:
            logger.error(f"컨베이어 상태 가져오기 오류: {str(e)}")
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
    
    def _fetch_access_logs(self):
        """출입 로그 데이터 가져오기"""
        if not self.is_server_connected() or not self._should_update_data("access_logs"):
            return
        
        try:
            # 출입 로그 API 호출
            response = self._server_connection.get_access_logs()
            
            # 응답 처리
            if response and response.get("success", False):
                self._access_logs = response.get("logs", [])
                
                # 변경 신호 발생
                self.access_logs_changed.emit()
                logger.debug(f"출입 로그 데이터 업데이트 완료: {len(self._access_logs)}건")
            
        except Exception as e:
            logger.error(f"출입 로그 데이터 가져오기 오류: {str(e)}")
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
    
    def refresh_access_logs(self):
        """출입 로그 갱신 요청 - 외부에서 호출 가능"""
        # 타임스탬프 재설정하여 강제 갱신
        self._data_timestamps["access_logs"] = None
        self._fetch_access_logs()
    
    def control_conveyor(self, action):
        """컨베이어 제어 함수"""
        if not self.is_server_connected():
            logger.warning("서버 연결 없음 - 컨베이어를 제어할 수 없습니다.")
            return {"success": False, "message": "서버 연결 없음"}
            
        try:
            # 서버 API 호출
            if action == "start":
                response = self._server_connection._send_request('POST', 'sort/control', {"action": "start"})
                if response and "status" in response and response["status"] != "error":
                    self._conveyor_status = 1  # 가동중
                    self.conveyor_status_changed.emit()
                    logger.info("컨베이어 시작 요청 성공")
                return {"success": True if response and response.get("status") != "error" else False, 
                        "message": response.get("message", "")}
                    
            elif action == "pause":
                response = self._server_connection._send_request('POST', 'sort/control', {"action": "pause"})
                if response and "status" in response and response["status"] != "error":
                    self._conveyor_status = 2  # 일시정지
                    self.conveyor_status_changed.emit()
                    logger.info("컨베이어 일시정지 요청 성공")
                return {"success": True if response and response.get("status") != "error" else False,
                        "message": response.get("message", "")}
                    
            elif action == "stop":
                response = self._server_connection._send_request('POST', 'sort/control', {"action": "stop"})
                if response and "status" in response and response["status"] != "error":
                    self._conveyor_status = 0  # 정지
                    self.conveyor_status_changed.emit()
                    logger.info("컨베이어 정지 요청 성공")
                return {"success": True if response and response.get("status") != "error" else False,
                        "message": response.get("message", "")}
            else:
                logger.error(f"알 수 없는 컨베이어 제어 명령: {action}")
                return {"success": False, "message": f"알 수 없는 컨베이어 제어 명령: {action}"}
        
        except Exception as e:
            logger.error(f"컨베이어 제어 오류: {str(e)}")
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
            
            return {"success": False, "message": str(e)}
    
    # 환경 제어 메서드 추가
    def set_target_temperature(self, warehouse_id, target_temp):
        """창고 목표 온도 설정"""
        if not self.is_server_connected():
            logger.warning("서버 연결 없음 - 온도를 설정할 수 없습니다.")
            return {"success": False, "message": "서버 연결 없음"}
        
        try:
            response = self._server_connection.set_target_temperature(warehouse_id, target_temp)
            
            # 성공 시 타임스탬프 초기화하여 다음 폴링에서 데이터 갱신
            if response and response.get("success", False):
                self._data_timestamps["warehouse"] = None
            
            return response
        except Exception as e:
            logger.error(f"온도 설정 오류: {str(e)}")
            return {"success": False, "message": str(e)}
    
    # 출입 제어 메서드 추가
    def open_door(self):
        """출입문 열기 요청"""
        if not self.is_server_connected():
            logger.warning("서버 연결 없음 - 출입문을 열 수 없습니다.")
            return {"success": False, "message": "서버 연결 없음"}
        
        try:
            response = self._server_connection.open_door()
            return response
        except Exception as e:
            logger.error(f"출입문 열기 오류: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def close_door(self):
        """출입문 닫기 요청"""
        if not self.is_server_connected():
            logger.warning("서버 연결 없음 - 출입문을 닫을 수 없습니다.")
            return {"success": False, "message": "서버 연결 없음"}
        
        try:
            response = self._server_connection.close_door()
            return response
        except Exception as e:
            logger.error(f"출입문 닫기 오류: {str(e)}")
            return {"success": False, "message": str(e)}
    
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
    
    def get_waiting_items(self):
        """입고 대기 항목 수 반환"""
        return self._waiting_items
    
    def get_expiry_data(self):
        """유통기한 데이터 반환"""
        return self._expiry_data
    
    def get_conveyor_status(self):
        """컨베이어 상태 반환 (0: 정지, 1: 가동중, 2: 일시정지)"""
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
    
    def get_last_error(self):
        """마지막 오류 정보 반환"""
        return self._last_error
    
    # ==== 상태 변경 메서드 ====
    def add_notification(self, message):
        """알림 목록에 메시지 추가 (최대 100개 유지)"""
        self._notifications.append({
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        })
        # 최대 100개만 유지하도록 제한
        if len(self._notifications) > 100:
            self._notifications = self._notifications[-100:]
        self.notification_added.emit(message)
        logger.info(f"알림 추가: {message}")
    
    def update_server_connection_status(self, connected):
        """서버 연결 상태 업데이트"""
        if self._server_connected != connected:
            self._server_connected = connected
            self.server_connection_changed.emit(connected)
        logger.info(f"서버 연결 상태 업데이트: {'연결됨' if connected else '연결 끊김'}")
    
    def shutdown(self):
        """애플리케이션 종료 시 호출"""
        self._running = False
        
        # 스레드 종료 대기
        if hasattr(self, 'polling_thread') and self.polling_thread.is_alive():
            self.polling_thread.join(1.0)
            
        logger.info("DataManager 종료 완료")

    def pause_sorter(self):
        # ...
        # 자동 정지 타이머 취소 (일시정지 상태에서는 타임아웃 방지)
        self._cancel_auto_stop_timer()
        # ...