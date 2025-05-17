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
        self.connection_status_notified = False  # 연결 상태 통지 여부 추적 (중복 알림 방지)
        
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
        
        # 오류 추적을 위한 통계 데이터
        self.error_stats = {
            "connection_errors": 0,
            "api_errors": 0,
            "last_error_time": None,
            "last_error_message": None
        }
    
    def register_socketio_handlers(self):
        """Socket.IO 이벤트 핸들러 등록"""
        @self.sio.event(namespace='/ws')
        def connect():
            logger.info("Socket.IO 연결 성공")
            self.is_connected = True
            self.connection_status_notified = False  # 상태 변경 시 재설정
            self.connectionStatusChanged.emit(True, "서버에 연결되었습니다.")
            
            # 연결 성공 시 오류 통계 초기화
            self.error_stats["connection_errors"] = 0
        
        @self.sio.event(namespace='/ws')
        def connect_error(data):
            logger.error(f"Socket.IO 연결 오류: {data}")
            self.connection_error = f"WebSocket 연결 오류: {data}"
            
            # 이전에 연결되어 있었을 때만 상태 변경 신호 발생 (중복 알림 방지)
            if self.is_connected or not self.connection_status_notified:
                self.is_connected = False
                self.connectionStatusChanged.emit(False, self.connection_error)
                self.connection_status_notified = True
            
            # 연결 오류 통계 업데이트
            self.error_stats["connection_errors"] += 1
            self.error_stats["last_error_time"] = time.time()
            self.error_stats["last_error_message"] = self.connection_error
        
        @self.sio.event(namespace='/ws')
        def disconnect():
            logger.warning("Socket.IO 연결 종료")
            
            # 이전에 연결되어 있었을 때만 상태 변경 신호 발생 (중복 알림 방지)
            if self.is_connected:
                self.is_connected = False
                self.connectionStatusChanged.emit(False, "서버 연결이 종료되었습니다.")
                self.connection_status_notified = True
        
        @self.sio.on('event', namespace='/ws')
        def on_event(data):
            """서버에서 이벤트 수신 시 처리"""
            try:
                # 데이터 타입 검증
                if not isinstance(data, dict):
                    logger.error(f"이벤트 데이터가 딕셔너리가 아닙니다: {type(data).__name__}")
                    return
                
                # 이벤트 데이터 파싱
                category = data.get('category', 'unknown')
                action = data.get('action', 'unknown')
                payload = data.get('payload', {})
                
                # payload가 딕셔너리가 아닌 경우 처리
                if not isinstance(payload, dict):
                    logger.warning(f"이벤트 페이로드가 딕셔너리가 아닙니다: {type(payload).__name__}")
                    payload = {"data": payload}
                
                logger.debug(f"서버 이벤트 수신: {category}/{action}")
                
                # 이벤트 신호 발생
                self.eventReceived.emit(category, action, payload)
            except Exception as e:
                logger.error(f"이벤트 처리 중 오류: {str(e)}")
    
    def connect_to_server(self):
        """서버에 연결 시도"""
        self.reconnect_attempts = 0  # 초기화
        self.connection_status_notified = False  # 상태 통지 플래그 초기화
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
                    self.connection_status_notified = True
                return True
                
            except requests.exceptions.RequestException as e:
                logger.error(f"API 서버 연결 실패: {str(e)}")
                self.connection_error = f"API 서버 연결 실패: {str(e)}"
                
                # 이전에 알림을 보내지 않았거나, 이전에 연결됐었던 경우에만 알림
                if self.is_connected or not self.connection_status_notified:
                    self.is_connected = False
                    self.connectionStatusChanged.emit(False, self.connection_error)
                    self.connection_status_notified = True
                
                # 연결 오류 통계 업데이트
                self.error_stats["connection_errors"] += 1
                self.error_stats["last_error_time"] = time.time()
                self.error_stats["last_error_message"] = self.connection_error
                
                return False
                
        except Exception as e:
            logger.error(f"서버 연결 시 예상치 못한 오류: {str(e)}")
            self.connection_error = str(e)
            
            # 이전에 알림을 보내지 않았거나, 이전에 연결됐었던 경우에만 알림
            if self.is_connected or not self.connection_status_notified:
                self.is_connected = False
                self.connectionStatusChanged.emit(False, f"서버 연결 오류: {str(e)}")
                self.connection_status_notified = True
            
            # 오류 통계 업데이트
            self.error_stats["connection_errors"] += 1
            self.error_stats["last_error_time"] = time.time()
            self.error_stats["last_error_message"] = self.connection_error
            
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
            # 재연결 실패 시 한 번만 알림 (이미 알림을 보낸 경우 중복 방지)
            if not self.connection_status_notified:
                self.connectionStatusChanged.emit(False, "재연결 시도 횟수 초과")
                self.connection_status_notified = True
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
                self.reconnect_timer.setInterval(int(next_delay * 1000))  # 밀리초 단위로 변환
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
        # 슬래시 중복 방지
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
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
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_METHOD",
                        "message": f"지원하지 않는 HTTP 메서드: {method}"
                    }
                }
            
            # 응답 검사
            response.raise_for_status()
            
            # JSON 응답 파싱
            try:
                result = response.json()
                
                # 결과가 딕셔너리인지 확인
                if not isinstance(result, dict):
                    return {
                        "success": False,
                        "error": {
                            "code": "INVALID_RESPONSE_FORMAT",
                            "message": f"서버 응답이 딕셔너리 형식이 아닙니다: {type(result).__name__}",
                            "data": result
                        }
                    }
                    
                # 표준 응답 형식이 아닌 경우 변환
                if "success" not in result:
                    # 응답에 오류 내용이 있으면 실패로 처리
                    if "error" in result:
                        return {
                            "success": False,
                            "error": result["error"]
                        }
                    # 그렇지 않으면 성공으로 처리하고 데이터 필드에 응답 내용 포함
                    else:
                        return {
                            "success": True,
                            "data": result
                        }
                
                return result
                
            except json.JSONDecodeError as e:
                # JSON 파싱 실패 시 문자열 응답 처리
                text_response = response.text
                logger.warning(f"JSON 응답 파싱 실패: {str(e)}, 응답: {text_response[:200]}")
                return {
                        "success": False,
                        "error": {
                            "code": "JSON_PARSE_ERROR",
                            "message": "서버 응답을 JSON으로 파싱할 수 없습니다",
                            "details": str(e),
                            "raw_response": text_response[:200]  # 긴 응답은 잘라서 보여줌
                        }
                    }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 오류 ({url}): {str(e)}")
            # ConnectionError나 Timeout의 경우에만 연결 상태 변경 신호 발생
            if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                # 연결 상태가 바뀌었을 때만 알림 (중복 알림 방지)
                if self.is_connected:
                    self.is_connected = False
                    self.connectionStatusChanged.emit(False, f"서버 요청 오류: {str(e)}")
                    self.connection_status_notified = True
                
                # 연결 문제인 경우 자동 재연결 시도
                self.start_reconnect_timer()
            
            # API 오류 통계 업데이트
            self.error_stats["api_errors"] += 1
            self.error_stats["last_error_time"] = time.time()
            self.error_stats["last_error_message"] = f"API 요청 오류 ({url}): {str(e)}"
            
            # 자세한 오류 정보 반환
            error_response = {
                "success": False,
                "error": {
                    "code": "API_ERROR",
                    "message": str(e),
                    "details": {
                        "url": url,
                        "method": method,
                        "timestamp": time.time()
                    }
                }
            }
            
            # 연결 오류인 경우 추가 정보 설정
            if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                error_response["error"]["code"] = "CONNECTION_ERROR"
                error_response["error"]["details"]["type"] = "connection"
            
            return error_response
            
        except Exception as e:
            logger.error(f"API 요청 중 예상치 못한 오류: {str(e)}")
            
            # API 오류 통계 업데이트
            self.error_stats["api_errors"] += 1
            self.error_stats["last_error_time"] = time.time()
            self.error_stats["last_error_message"] = f"예상치 못한 오류: {str(e)}"
            
            return {
                "success": False,
                "error": {
                    "code": "UNKNOWN_ERROR",
                    "message": f"예상치 못한 오류: {str(e)}",
                    "details": {
                        "url": url,
                        "method": method,
                        "timestamp": time.time()
                    }
                }
            }
    
    # ===== 응답 표준화 헬퍼 메서드 =====
    
    def _standardize_response(self, response, context):
        """응답을 표준 형식으로 변환하는 헬퍼 메서드
        
        Args:
            response: API 응답 (dict 또는 기타 타입)
            context: 오류 메시지에 사용할 컨텍스트 문자열
            
        Returns:
            표준화된 응답 (dict)
        """
        # 응답이 없는 경우
        if response is None:
            return {
                "success": False,
                "error": {
                    "code": "NO_RESPONSE",
                    "message": f"{context}에 실패했습니다."
                }
            }
            
        # 응답이 딕셔너리가 아닌 경우
        if not isinstance(response, dict):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_RESPONSE_TYPE",
                    "message": f"예상치 못한 응답 형식: {type(response).__name__}",
                    "raw_data": str(response)[:200]
                }
            }
            
        # 이미 오류 구조를 가진 경우
        if "error" in response:
            # success 필드가 없으면 추가
            if "success" not in response:
                response["success"] = False
            return response
            
        # 성공 필드가 있는 경우 그대로 반환
        if "success" in response:
            return response
            
        # 그 외의 경우 표준 형식으로 변환하여 반환
        return {
            "success": True,
            "data": response
        }
    
    # ===== 분류기 API =====
    
    def get_sorting_status(self):
        """분류기 상태 조회"""
        response = self._send_request('GET', 'sort/status')
        return self._standardize_response(response, "분류기 상태 조회")
    
    def start_sorting(self):
        """분류기 작동 시작"""
        response = self._send_request('POST', 'sort/control', {'action': 'start'})
        return self._standardize_response(response, "분류기 시작")
    
    def stop_sorting(self):
        """분류기 작동 중지"""
        response = self._send_request('POST', 'sort/control', {'action': 'stop'})
        return self._standardize_response(response, "분류기 중지")
    
    def emergency_stop(self):
        """분류기 긴급 정지"""
        response = self._send_request('POST', 'sort/emergency')
        return self._standardize_response(response, "분류기 긴급 정지")
    
    def get_sorter_status(self):
        """분류기 상태 조회"""
        response = self._send_request('GET', 'sort/status')
        return self._standardize_response(response, "분류기 상태 조회")
    
    # ===== 환경 제어 API =====
    
    def get_environment_status(self):
        """전체 환경 상태 조회"""
        response = self._send_request('GET', 'environment/status')
        standardized = self._standardize_response(response, "환경 상태 조회")
        
        # 응답 데이터가 올바른 구조인지 확인
        if standardized["success"] and "data" in standardized:
            data = standardized["data"]
            # 데이터가 None인 경우
            if data is None:
                return {
                    "success": False,
                    "error": {
                        "code": "EMPTY_DATA",
                        "message": "환경 상태 데이터가 비어 있습니다."
                    }
                }
        
        return standardized
    
    def get_warehouse_status(self, warehouse_id):
        """특정 창고 환경 상태 조회"""
        if not warehouse_id:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "창고 ID는 필수 파라미터입니다."
                }
            }
            
        response = self._send_request('GET', f'environment/warehouse/{warehouse_id}')
        return self._standardize_response(response, f"창고 {warehouse_id} 상태 조회")
    
    def set_target_temperature(self, warehouse_id, target_temp):
        """창고 목표 온도 설정"""
        if not warehouse_id:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "창고 ID는 필수 파라미터입니다."
                }
            }
            
        try:
            # 온도 값 검증
            target_temp = float(target_temp)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_TEMPERATURE",
                    "message": "온도 값이 유효하지 않습니다."
                }
            }
            
        # JSON 키 맞추기 - target_temp 대신 temperature 사용
        data = {
            'warehouse': warehouse_id,
            'temperature': target_temp  # API 규격에 맞게 temperature 키 사용
        }
        response = self._send_request('POST', 'environment/temperature', data)
        
        # 응답 표준화
        standardized = self._standardize_response(response, f"창고 {warehouse_id} 온도 설정")
        
        # 성공 시 메시지 추가
        if standardized["success"]:
            standardized["message"] = f"창고 {warehouse_id}의 온도가 {target_temp}°C로 설정되었습니다."
            
        return standardized
    
    # ===== 재고 관리 API =====
    
    def get_inventory_status(self):
        """재고 상태 조회"""
        response = self._send_request('GET', 'inventory/status')
        return self._standardize_response(response, "재고 상태 조회")
    
    def get_inventory_items(self, category=None, limit=20, offset=0):
        """재고 물품 목록 조회"""
        params = {
            'limit': limit,
            'offset': offset
        }
        if category:
            params['category'] = category
            
        response = self._send_request('GET', 'inventory/items', params)
        standardized = self._standardize_response(response, "재고 물품 목록 조회")
        
        # 데이터 필드 확인 및 추가
        if standardized["success"] and "data" not in standardized:
            # 데이터 필드가 없고 성공인 경우, 빈 목록으로 초기화
            standardized["data"] = []
            standardized["total_count"] = 0
            
        return standardized
    
    def get_inventory_item(self, item_id):
        """재고 물품 상세 조회"""
        if not item_id:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PARAMETER",
                    "message": "물품 ID는 필수 파라미터입니다."
                }
            }
            
        response = self._send_request('GET', f'inventory/items/{item_id}')
        return self._standardize_response(response, f"물품 {item_id} 상세 조회")
    
    # ===== 입고 대기 관련 API =====
    
    def get_waiting_items(self):
        """입고 대기 물품 수량 조회 - 추가된 함수"""
        response = self._send_request('GET', 'inventory/waiting')
        standardized = self._standardize_response(response, "입고 대기 물품 조회")
        
        # 응답에 waiting 필드가 없는 경우 추가
        if standardized["success"]:
            if "waiting" not in standardized and "data" in standardized:
                # data 필드에 waiting 값이 있는지 확인
                if isinstance(standardized["data"], dict) and "waiting" in standardized["data"]:
                    standardized["waiting"] = standardized["data"]["waiting"]
                # data 필드가 숫자인 경우 그 값을 waiting으로 사용
                elif isinstance(standardized["data"], (int, float)):
                    standardized["waiting"] = standardized["data"]
                else:
                    # 적절한 필드를 찾을 수 없으면 기본값 0 사용
                    standardized["waiting"] = 0
            elif "waiting" not in standardized:
                standardized["waiting"] = 0
                
        # 실패 시 waiting 필드 추가
        else:
            standardized["waiting"] = 0
            
        return standardized
    
    # ===== 유통기한 관리 API =====
    
    def get_expiry_alerts(self, days=7):
        """유통기한 임박 물품 조회"""
        params = {'days': days}
        response = self._send_request('GET', 'expiry/alerts', params)
        standardized = self._standardize_response(response, "유통기한 임박 물품 조회")
        
        # 데이터 필드 확인 및 추가
        if standardized["success"]:
            # data 필드가 없는 경우 빈 리스트 추가
            if "data" not in standardized:
                standardized["data"] = []
                
            # total_count 필드가 없는 경우 계산하여 추가
            if "total_count" not in standardized and "data" in standardized:
                standardized["total_count"] = len(standardized["data"])
                
            # days_threshold 필드가 없는 경우 파라미터 값 사용
            if "days_threshold" not in standardized:
                standardized["days_threshold"] = days
        else:
            # 오류 시 기본 데이터 추가
            if "data" not in standardized:
                standardized["data"] = []
            if "total_count" not in standardized:
                standardized["total_count"] = 0
        
        return standardized
    
    def get_expired_items(self):
        """유통기한 경과 물품 조회"""
        response = self._send_request('GET', 'expiry/expired')
        standardized = self._standardize_response(response, "유통기한 경과 물품 조회")
        
        # 데이터 필드 확인 및 추가
        if standardized["success"]:
            # data 필드가 없는 경우 빈 리스트 추가
            if "data" not in standardized:
                standardized["data"] = []
                
            # total_count 필드가 없는 경우 계산하여 추가
            if "total_count" not in standardized and "data" in standardized:
                standardized["total_count"] = len(standardized["data"])
        else:
            # 오류 시 기본 데이터 추가
            if "data" not in standardized:
                standardized["data"] = []
            if "total_count" not in standardized:
                standardized["total_count"] = 0
        
        return standardized
    
    # ===== 출입 관리 API =====
    
    def get_access_logs(self):
        """출입 기록 조회"""
        response = self._send_request('GET', 'access/logs')
        standardized = self._standardize_response(response, "출입 로그 조회")
        
        # 데이터 필드 확인 및 추가
        if standardized["success"]:
            # logs 필드가 없는 경우 추가
            if "logs" not in standardized:
                # data 필드가 있으면 그 값을 logs로 복사
                if "data" in standardized and isinstance(standardized["data"], list):
                    standardized["logs"] = standardized["data"]
                else:
                    standardized["logs"] = []
        else:
            # 오류 시 기본 데이터 추가
            standardized["logs"] = []
        
        return standardized
    
    def open_door(self):
        """출입문 열기"""
        response = self._send_request('POST', 'access/open-door')
        return self._standardize_response(response, "출입문 열기 요청")
    
    def close_door(self):
        """출입문 닫기"""
        response = self._send_request('POST', 'access/close-door')
        return self._standardize_response(response, "출입문 닫기 요청")
    
    # ===== 오류 및 상태 정보 =====
    
    def get_error_stats(self):
        """오류 통계 정보 반환"""
        return self.error_stats
    
    def reset_error_stats(self):
        """오류 통계 초기화"""
        self.error_stats = {
            "connection_errors": 0,
            "api_errors": 0,
            "last_error_time": None,
            "last_error_message": None
        }
    
    def test_connection(self):
        """서버 연결 테스트"""
        try:
            response = self._send_request('GET', 'debug/ping')
            if response and response.get("success", False):
                logger.info("서버 연결 테스트 성공")
                return True, response
            else:
                error_msg = "응답 성공 필드 없음" if response else "응답 없음"
                logger.warning(f"서버 연결 테스트 실패: {error_msg}")
                return False, response
        except Exception as e:
            logger.error(f"연결 테스트 중 오류: {str(e)}")
            return False, {"error": str(e)}
        
    def test_debug_apis(self):
        """디버그 API 테스트"""
        results = {}
        
        # 핑 테스트
        try:
            ping_response = self._send_request('GET', 'debug/ping')
            results["ping"] = ping_response
        except Exception as e:
            results["ping"] = {"error": str(e)}
        
        # 분류기 컨트롤러 디버그
        try:
            sort_debug = self._send_request('GET', 'debug/sort-controller')
            results["sort_controller"] = sort_debug
        except Exception as e:
            results["sort_controller"] = {"error": str(e)}
        
        return results

    def get_temperature_thresholds(self):
        """창고별 온도 임계값 정보 조회"""
        response = self._send_request('GET', 'environment/thresholds')
        standardized = self._standardize_response(response, "온도 임계값 조회")
        
        # 값이 없거나 오류인 경우 기본값 반환
        if not standardized.get("success", False) or "data" not in standardized:
            # 기본값 설정
            default_thresholds = {
                'A': {'min': -30, 'max': -18, 'type': 'freezer'},
                'B': {'min': 0, 'max': 10, 'type': 'refrigerator'},
                'C': {'min': 15, 'max': 25, 'type': 'room_temp'}
            }
            logger.warning("온도 임계값 조회 실패, 기본값 사용")
            return default_thresholds
        
        return standardized.get("data", {})

    def get_temperature_thresholds(self):
        """창고별 온도 임계값 정보 조회"""
        response = self._send_request('GET', 'environment/thresholds')
        standardized = self._standardize_response(response, "온도 임계값 조회")
        
        # 값이 없거나 오류인 경우 기본값 반환
        if not standardized.get("success", False) or "data" not in standardized:
            # 기본값 설정
            default_thresholds = {
                'A': {'min': -30, 'max': -18, 'type': 'freezer'},
                'B': {'min': 0, 'max': 10, 'type': 'refrigerator'},
                'C': {'min': 15, 'max': 25, 'type': 'room_temp'}
            }
            logger.warning("온도 임계값 조회 실패, 기본값 사용")
            return default_thresholds
        
        return standardized.get("data", {})

    # sort 관련 API 호출 메서드에 상세 로깅 추가
    def get_sorter_status(self):
        """분류기 상태 조회"""
        logger.info("분류기 상태 조회 API 호출 시작")
        response = self._send_request('GET', 'sort/status')
        logger.info(f"분류기 상태 조회 API 응답: {response}")
        return self._standardize_response(response, "분류기 상태 조회")