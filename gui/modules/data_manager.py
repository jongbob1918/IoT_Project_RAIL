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
        
        logger.info("DataManager 초기화 완료")
    
    def set_server_connection(self, server_connection):
        """서버 연결 객체 설정"""
        self._server_connection = server_connection
        logger.info("서버 연결 객체 설정 완료")
        
        # 서버 연결 상태 변경 이벤트 연결
        if hasattr(server_connection, 'connectionStatusChanged'):
            server_connection.connectionStatusChanged.connect(self._handle_server_connection_changed)
    
    def _handle_server_connection_changed(self, connected, message=""):
        """서버 연결 상태 변경 처리"""
        self._server_connected = connected
        self.server_connection_changed.emit(connected)
        
        # 서버 연결 되었을 때 즉시 데이터 갱신
        if connected:
            self._fetch_all_data()
    
    def is_server_connected(self):
        """서버 연결 상태 반환 - 모든 페이지가 이 메서드를 사용해야 함"""
        return self._server_connected and self._server_connection and self._server_connection.is_connected


    def _poll_server_data(self):
        """실시간 이벤트로 업데이트되지 않는 중요 데이터만 주기적으로 폴링"""
        logger.info("데이터 폴링 스레드 시작 - 최소 폴링 모드")
        
        # 데이터 유형별 폴링 주기 설정 (초 단위)
        polling_intervals = {
            "environment": 120,  # 환경 데이터는 온도 이벤트로 실시간 업데이트되므로 거의 폴링 필요 없음
            "inventory": 300,    # 재고 데이터는 5분마다
            "expiry": 600,       # 유통기한 데이터는 10분마다
            "access_logs": 300,  # 출입 로그는 5분마다
            "waiting": 300       # 대기 데이터는 5분마다
        }
        
        # 데이터 유형별 마지막 폴링 시간
        last_poll_time = {k: 0 for k in polling_intervals.keys()}
        
        while self._running:
            try:
                if self.is_server_connected():
                    current_time = time.time()
                    
                    # 환경 데이터(WebSocket으로 실시간 업데이트)
                    if current_time - last_poll_time["environment"] >= polling_intervals["environment"]:
                        self._fetch_environment_data()
                        last_poll_time["environment"] = current_time
                    
                    # 재고 데이터(주기적 업데이트 필요)
                    if current_time - last_poll_time["inventory"] >= polling_intervals["inventory"]:
                        self._fetch_inventory_data()
                        last_poll_time["inventory"] = current_time
                    
                    # 유통기한 데이터(주기적 업데이트 필요)
                    if current_time - last_poll_time["expiry"] >= polling_intervals["expiry"]:
                        self._fetch_expiry_data() 
                        last_poll_time["expiry"] = current_time
                    
                    # 출입 로그(주기적 업데이트)
                    if current_time - last_poll_time["access_logs"] >= polling_intervals["access_logs"]:
                        self._fetch_access_logs()
                        last_poll_time["access_logs"] = current_time
                    
                    # 대기 데이터(주기적 업데이트)
                    if current_time - last_poll_time["waiting"] >= polling_intervals["waiting"]:
                        self._fetch_waiting_data()
                        last_poll_time["waiting"] = current_time
                
                # 15초 간격으로 폴링 확인 (짧은 간격으로 체크하되 실제 데이터는 더 긴 간격으로 가져옴)
                time.sleep(15)
                
            except Exception as e:
                logger.error(f"데이터 폴링 중 오류: {str(e)}")
                
                # 오류 정보 저장
                self._last_error = {
                    "time": datetime.datetime.now(),
                    "type": type(e).__name__,
                    "message": str(e)
                }
                
                # 오류 발생 시 슬립
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
                self._fetch_environment_data()
                
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
    
    def _fetch_environment_data(self):
        """환경 데이터 가져오기"""
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
                        self._warehouse_data[warehouse_id]["used"] = data.get("used", 0)
                        self._warehouse_data[warehouse_id]["capacity"] = data.get("capacity", 100)
                        
                        # usage_percent 계산
                        if "usage_percent" in data:
                            self._warehouse_data[warehouse_id]["usage_percent"] = data.get("usage_percent", 0)
                        elif self._warehouse_data[warehouse_id]["capacity"] > 0:
                            used = self._warehouse_data[warehouse_id]["used"]
                            capacity = self._warehouse_data[warehouse_id]["capacity"]
                            self._warehouse_data[warehouse_id]["usage_percent"] = min(100, int((used / capacity) * 100))
                
                # 변경 신호 발생
                self.warehouse_data_changed.emit()
                logger.debug("환경 데이터 업데이트 완료")
            
        except Exception as e:
            logger.error(f"환경 데이터 가져오기 오류: {str(e)}")
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
    
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
                    elif status == "paused":
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
                response = self._server_connection._send_request('POST', 'sort/control', {"action": "stop"})
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
        """알림 목록에 메시지 추가"""
        self._notifications.append({
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        })
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