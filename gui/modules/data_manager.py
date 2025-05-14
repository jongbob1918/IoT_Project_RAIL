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
        
        # 오류 연속 발생 횟수 초기화
        error_count = 0
        
        # 마지막 요청 시간 초기화
        last_request_time = 0
        
        while self._running:
            try:
                # 현재 시간 확인 - 적절한 간격으로 요청 (5초 이상)
                current_time = time.time()
                if (current_time - last_request_time) < 5:
                    # 요청 간격이 너무 짧으면 대기
                    time.sleep(1)
                    continue
                
                # 요청 시간 갱신
                last_request_time = current_time
                
                if self._server_connected and self._server_connection is not None:
                    # 서버 데이터 가져오기
                    self._fetch_all_data()
                    
                    # 연속 오류 발생 횟수 초기화
                    error_count = 0
                else:
                    # 서버 연결 시도
                    self._try_connect_server()
                
                # 요청 간격 유지를 위한 적절한 대기 시간
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"데이터 폴링 중 오류: {str(e)}")
                self._server_connected = False
                
                # 오류 정보 저장
                self._last_error = {
                    "time": datetime.datetime.now(),
                    "type": type(e).__name__,
                    "message": str(e)
                }
                
                # 연속 오류 발생 횟수 증가
                error_count += 1
                
                # 알림 추가 (빈번한 알림 방지 - 처음 발생 시에만)
                if error_count == 1:
                    message = f"서버 데이터 폴링 오류: {str(e)}"
                    self._add_notification_thread_safe(message)
                
                # 연속 오류가 5회 이상 발생하면 대기 시간 증가
                if error_count > 5:
                    error_wait_time = min(30, 5 * error_count)  # 최대 30초
                    logger.warning(f"연속 오류 발생 ({error_count}회). {error_wait_time}초 대기 후 재시도")
                    time.sleep(error_wait_time)
                    continue
                
                # 일반적인 오류 발생 시 대기 시간
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
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
            
            # 일시적인 연결 오류 시 재연결 시도
            if retry and ("연결이 끊어졌습니다" in str(e) or "Connection" in str(e)):
                logger.info("연결 오류 감지, 재연결 시도...")
                if self._try_connect_server():
                    logger.info("재연결 성공, 데이터 다시 가져오기 시도")
                    return self._fetch_data_safely(fetch_function, error_message, retry=False)
            
            # 오류 알림 추가 (한 번만)
            self.add_notification(f"데이터 가져오기 오류: {error_message}")
            return False
    
    def _fetch_all_data(self):
        """모든 서버 데이터 가져오기"""
        try:
            self._fetch_environment_data()
            self._fetch_inventory_data()
            self._fetch_waiting_data()  # 입고 대기 데이터 가져오기 추가
            self._fetch_expiry_data()
            self._fetch_conveyor_status()
            logger.debug("모든 서버 데이터 가져오기 완료")
        except Exception as e:
            logger.error(f"서버 데이터 가져오기 실패: {str(e)}")
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
            
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
                        # JSON 구조에 맞게 데이터 맵핑 (current_temp, target_temp 등 필드명 확인)
                        self._warehouse_data[warehouse_id]["temperature"] = data.get("current_temp", 0.0)
                        self._warehouse_data[warehouse_id]["target_temp"] = data.get("target_temp", 0.0)
                        self._warehouse_data[warehouse_id]["status"] = data.get("status", "알 수 없음")
                        self._warehouse_data[warehouse_id]["used"] = data.get("used", 0)
                        self._warehouse_data[warehouse_id]["capacity"] = data.get("capacity", 16)
                        
                        # usage_percent 계산 - 서버에서 제공하지 않는 경우
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
            
            raise
    
    def _fetch_inventory_data(self):
        """재고 데이터 가져오기"""
        if not self._server_connection:
            return
        
        try:
            # 재고 상태 조회 API 호출
            response = self._server_connection.get_inventory_status()
            
            # 응답 처리 - JSON 데이터 구조에 맞게 수정
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
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
            
            raise
    
    def _fetch_waiting_data(self):
        """입고 대기 데이터 가져오기 - JSON 구조에 맞게 수정"""
        if not self._server_connection:
            return
        
        try:
            # 입고 대기 정보 조회 API 호출
            response = self._server_connection._send_request('GET', 'inventory/waiting')
            
            # 응답 처리 - 'waiting' 필드 사용
            if response and response.get("success", True):
                # 입고 대기 수량 업데이트
                self._waiting_items = response.get("waiting", 0)
                
                # 변경 신호 발생
                self.waiting_data_changed.emit()
                logger.debug(f"입고 대기 데이터 업데이트 완료: {self._waiting_items}개")
            
        except Exception as e:
            logger.error(f"입고 대기 데이터 가져오기 오류: {str(e)}")
            
            # 오류 정보 저장
            self._last_error = {
                "time": datetime.datetime.now(),
                "type": type(e).__name__,
                "message": str(e)
            }
            
            # 이 오류는 필수 데이터가 아니므로 무시하고 계속 진행
            pass
    
    def _fetch_expiry_data(self):
        """유통기한 데이터 가져오기 - JSON 구조에 맞게 수정"""
        if not self._server_connection:
            return
        
        try:
            # 유통기한 만료 항목 조회
            expired_response = self._server_connection.get_expired_items()
            
            # 유통기한 경고 항목 조회 (7일 이내)
            alerts_response = self._server_connection.get_expiry_alerts(days=7)
            
            # 응답 처리 - JSON 구조에 맞게 수정
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
            
            raise
    
    def _fetch_conveyor_status(self):
        """컨베이어 상태 가져오기 - JSON 구조에 맞게 수정"""
        if not self._server_connection:
            return
        
        try:
            # 분류기 상태 조회 API 호출
            response = self._server_connection.get_sorter_status()
            
            # 응답 처리 - JSON 구조에 맞게 수정
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
            
            raise
        
    def control_conveyor(self, action):
        """컨베이어 제어 함수 - JSON 구조에 맞게 수정
        
        Args:
            action: 동작 (start, pause, stop)
            
        Returns:
            응답 데이터
        """
        if not self._server_connection or not self._server_connected:
            logger.warning("서버 연결 없음 - 컨베이어를 제어할 수 없습니다.")
            return {"success": False, "message": "서버 연결 없음"}
            
        try:
            # 서버 API 호출 - 'action' 필드 사용 (PDF의 JSON 구조에 맞게)
            if action == "start":
                # action 필드를 사용하는 JSON 요청
                response = self._server_connection._send_request('POST', 'sort/control', {"action": "start"})
                if response and "status" in response and response["status"] != "error":
                    self._conveyor_status = 1  # 가동중
                    self.conveyor_status_changed.emit()
                    logger.info("컨베이어 시작 요청 성공")
                return {"success": True if response and response.get("status") != "error" else False, 
                        "message": response.get("message", "")}
                    
            elif action == "pause":
                # 서버 API에 pause 기능이 있다면 호출, 없다면 stop과 동일하게 처리
                # sort_api.py에는 pause 메서드가 보이지 않으므로 stop으로 대체
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