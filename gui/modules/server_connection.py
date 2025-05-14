import logging
import requests
import json
import time
import socketio
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# 로깅 설정
logger = logging.getLogger(__name__)

class ServerConnection(QObject):
    """서버 연결 관리 클래스
    
    이 클래스는 GUI 클라이언트와 백엔드 서버 간의 통신을 담당합니다.
    REST API와 Socket.IO WebSocket 연결을 모두 관리합니다.
    """
    
    # 신호 정의
    connectionStatusChanged = pyqtSignal(bool, str)  # 연결 상태 변경 신호 (연결됨, 메시지)
    eventReceived = pyqtSignal(str, str, dict)  # 서버 이벤트 수신 신호 (카테고리, 액션, 페이로드)
    
    def __init__(self, server_host="localhost", server_port=8000):
        """생성자
        
        Args:
            server_host: 서버 호스트 (기본값: localhost)
            server_port: 서버 포트 (기본값: 8000)
        """
        super().__init__()
        
        # 서버 연결 정보
        self.server_host = server_host
        self.server_port = server_port
        self.api_base_url = f"http://{server_host}:{server_port}/api"
        self.websocket_url = f"http://{server_host}:{server_port}"
        
        # 연결 상태
        self.is_connected = False
        self.connection_error = None
        
        # Socket.IO 클라이언트 설정
        self.sio = socketio.Client(logger=logger, engineio_logger=False)
        
        # Socket.IO 이벤트 핸들러 등록
        self.register_socketio_handlers()
        
        # 재연결 관련 설정
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2  # 초 단위
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self.attempt_reconnect)
    
    def register_socketio_handlers(self):
        """Socket.IO 이벤트 핸들러 등록"""
        @self.sio.event(namespace='/ws')
        def connect():
            logger.info("Socket.IO 연결 성공")
            self.is_connected = True
            self.connectionStatusChanged.emit(True, "서버에 연결되었습니다.")
        
        @self.sio.event(namespace='/ws')
        def connect_error(data):
            logger.error(f"Socket.IO 연결 오류: {data}")
            self.connection_error = f"WebSocket 연결 오류: {data}"
            self.is_connected = False
            self.connectionStatusChanged.emit(False, self.connection_error)
        
        @self.sio.event(namespace='/ws')
        def disconnect():
            logger.warning("Socket.IO 연결 종료")
            self.is_connected = False
            self.connectionStatusChanged.emit(False, "서버 연결이 종료되었습니다.")
        
        @self.sio.on('event', namespace='/ws')
        def on_event(data):
            """서버에서 이벤트 수신 시 처리"""
            try:
                # 이벤트 데이터 파싱
                category = data.get('category', 'unknown')
                action = data.get('action', 'unknown')
                payload = data.get('payload', {})
                
                logger.debug(f"서버 이벤트 수신: {category}/{action}")
                
                # 이벤트 신호 발생
                self.eventReceived.emit(category, action, payload)
            except Exception as e:
                logger.error(f"이벤트 처리 중 오류: {str(e)}")
    
    def connect_to_server(self):
        """서버에 연결 시도"""
        self.reconnect_attempts = 0  # 초기화
        return self._attempt_connection()
    
    def _attempt_connection(self):
        """내부 연결 시도 함수"""
        try:
            # REST API 연결 테스트
            try:
                response = requests.get(f"{self.api_base_url}/status", timeout=5)
                response.raise_for_status()
                
                # 연결 성공 시 WebSocket 연결
                if not self.sio.connected:
                    self.sio.connect(self.websocket_url, namespaces=["/ws"])
                
                self.is_connected = True
                self.connectionStatusChanged.emit(True, "서버에 연결되었습니다.")
                return True
                
            except requests.exceptions.RequestException as e:
                logger.error(f"API 서버 연결 실패: {str(e)}")
                self.connection_error = f"API 서버 연결 실패: {str(e)}"
                self.is_connected = False
                self.connectionStatusChanged.emit(False, self.connection_error)
                return False
                
        except Exception as e:
            logger.error(f"서버 연결 시 예상치 못한 오류: {str(e)}")
            self.connection_error = str(e)
            self.is_connected = False
            self.connectionStatusChanged.emit(False, f"서버 연결 오류: {str(e)}")
            return False
    
    def disconnect_from_server(self):
        """서버 연결 종료"""
        try:
            if self.sio.connected:
                self.sio.disconnect()
            
            self.is_connected = False
            logger.info("서버 연결 종료")
            return True
        except Exception as e:
            logger.error(f"서버 연결 종료 중 오류: {str(e)}")
            return False
    
    def attempt_reconnect(self):
        """재연결 시도 함수"""
        if self.is_connected:
            self.reconnect_timer.stop()
            return
            
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.warning(f"최대 재연결 시도 횟수({self.max_reconnect_attempts}회)에 도달했습니다.")
            self.reconnect_timer.stop()
            self.connectionStatusChanged.emit(False, "재연결 시도 횟수 초과")
            return
            
        logger.info(f"서버 재연결 시도 중... ({self.reconnect_attempts + 1}/{self.max_reconnect_attempts})")
        self.reconnect_attempts += 1
        
        # 오류 발생 방지를 위해 try-except로 감싸기
        try:
            if self._attempt_connection():
                logger.info("서버 재연결 성공")
                self.reconnect_timer.stop()
            else:
                # 다음 재시도까지 대기 시간 증가 (지수 백오프)
                next_delay = min(30, self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)))
                logger.info(f"다음 재연결 시도까지 {next_delay}초 대기")
                self.reconnect_timer.setInterval(next_delay * 1000)  # 밀리초 단위로 변환
        except Exception as e:
            logger.error(f"재연결 시도 중 예외 발생: {str(e)}")
            # 다음 재시도 일정 계속 유지
            next_delay = min(30, self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)))
            self.reconnect_timer.setInterval(next_delay * 1000)
                                                 
    def start_reconnect_timer(self):
        """재연결 타이머 시작"""
        if not self.reconnect_timer.isActive():
            self.reconnect_attempts = 0
            self.reconnect_timer.start(self.reconnect_delay * 1000)
    
    # ===== API 요청 메서드 =====
    
    def _send_request(self, method, endpoint, data=None, timeout=10):
        """API 요청을 보내는 공통 메서드
        
        Args:
            method: HTTP 메서드 ('GET', 'POST', 'PUT', 'DELETE')
            endpoint: API 엔드포인트 (base_url 이후 경로)
            data: 요청 데이터 (dict)
            timeout: 요청 타임아웃 (초)
            
        Returns:
            응답 데이터 (dict) 또는 None (오류 시)
        """
        url = f"{self.api_base_url}/{endpoint}"
        
        try:
            headers = {'Content-Type': 'application/json'}
            
            if method == 'GET':
                response = requests.get(url, params=data, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, json=data, headers=headers, timeout=timeout)
            else:
                logger.error(f"지원하지 않는 HTTP 메서드: {method}")
                return None
            
            # 응답 검사
            response.raise_for_status()
            
            # JSON 응답 파싱
            result = response.json()
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 오류 ({url}): {str(e)}")
            self.connectionStatusChanged.emit(False, f"서버 요청 오류: {str(e)}")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"응답 JSON 파싱 오류: {str(e)}")
            return None
            
        except Exception as e:
            logger.error(f"예상치 못한 오류: {str(e)}")
            return None
    
    # ===== 분류기 API =====
    
    def start_sorting(self):
        """분류기 작동 시작"""
        return self._send_request('POST', 'sort/inbound/start')
    
    def stop_sorting(self):
        """분류기 작동 중지"""
        return self._send_request('POST', 'sort/inbound/stop')
    
    def emergency_stop(self):
        """분류기 긴급 정지"""
        return self._send_request('POST', 'sort/emergency/stop')
    
    def get_sorter_status(self):
        """분류기 상태 조회"""
        return self._send_request('GET', 'sort/inbound/status')
    
    # ===== 환경 제어 API =====
    
    def get_environment_status(self):
        """전체 환경 상태 조회"""
        response = self._send_request('GET', 'environment/environment/status')
        if response:
            # 기본 성공 응답 구조 추가
            return {
                "success": True,
                "data": response
            }
        return {"success": False}
    
    def get_warehouse_status(self, warehouse_id):
        """특정 창고 환경 상태 조회"""
        return self._send_request('GET', f'environment/environment/warehouse/{warehouse_id}')
    
    def set_target_temperature(self, warehouse_id, target_temp):
        """창고 목표 온도 설정"""
        data = {
            'warehouse': warehouse_id,
            'target_temp': float(target_temp)  # 숫자형 보장
        }
        return self._send_request('PUT', 'environment/environment/control', data)
    
    # ===== 재고 관리 API =====
    
    def get_inventory_status(self):
        """재고 상태 조회"""
        return self._send_request('GET', 'inventory/status')
    
    def get_inventory_items(self, category=None, limit=20, offset=0):
        """재고 물품 목록 조회"""
        params = {
            'limit': limit,
            'offset': offset
        }
        if category:
            params['category'] = category
            
        return self._send_request('GET', 'inventory/items', params)
    
    def get_inventory_item(self, item_id):
        """재고 물품 상세 조회"""
        return self._send_request('GET', f'inventory/items/{item_id}')
    
    # ===== 유통기한 관리 API =====
    
    def get_expiry_alerts(self, days=7):
        """유통기한 임박 물품 조회"""
        params = {'days': days}
        return self._send_request('GET', 'expiry/alerts', params)
    
    def get_expired_items(self):
        """유통기한 경과 물품 조회"""
        return self._send_request('GET', 'expiry/expired')
    
    # ===== 출입 관리 API =====
    
    def get_access_logs(self):
        """출입 기록 조회"""
        return self._send_request('GET', 'access/logs')
    
    def open_door(self):
        """출입문 열기"""
        return self._send_request('POST', 'access/open-door')
    
    def close_door(self):
        """출입문 닫기"""
        return self._send_request('POST', 'access/close-door')