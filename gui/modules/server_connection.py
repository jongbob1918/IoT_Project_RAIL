import socketio
import requests
from PyQt6.QtCore import QObject, pyqtSignal
import logging

logger = logging.getLogger(__name__)

class ServerConnection(QObject):
    """서버 연결 및 통신을 관리하는 클래스"""
    
    # 시그널 정의
    connectionStatusChanged = pyqtSignal(bool, str)  # 연결 상태 변경 (성공 여부, 메시지)
    eventReceived = pyqtSignal(str, str, dict)  # 이벤트 수신 (카테고리, 액션, 페이로드)
    
    def __init__(self, server_host="localhost", server_port=8000):
        super().__init__()
        
        # 서버 설정
        self.server_host = server_host
        self.server_port = server_port
        self.api_base_url = f"http://{server_host}:{server_port}/api"
        self.websocket_url = f"http://{server_host}:{server_port}"
        
        # 상태 변수
        self.is_connected = False
        self.connection_error = None
        
        # Socket.IO 클라이언트 설정
        self.sio = socketio.Client()
        self.setup_socketio_events()
        
        # DataManager 참조 (나중에 설정)
        self.data_manager = None
    
    def set_data_manager(self, data_manager):
        """DataManager 참조 설정"""
        self.data_manager = data_manager
        # 데이터 매니저에도 서버 연결 객체 설정
        if self.data_manager:
            self.data_manager.set_server_connection(self)
    
    def setup_socketio_events(self):
        """Socket.IO 이벤트 핸들러 설정"""
        
        @self.sio.event
        def connect():
            print(f"Socket.IO 서버에 연결됨: {self.websocket_url}")
            self.is_connected = True
            self.connectionStatusChanged.emit(True, "서버에 연결되었습니다.")
            
            # 데이터 매니저에 연결 상태 업데이트
            if self.data_manager:
                self.data_manager.update_server_connection_status(True)
                # 즉시 컨베이어 상태 변경 이벤트 발생
                self.data_manager.conveyor_status_changed.emit()
        
        @self.sio.event
        def connect_error(data):
            print(f"Socket.IO 연결 오류: {data}")
            self.is_connected = False
            self.connection_error = str(data)
            self.connectionStatusChanged.emit(False, f"서버 연결 오류: {data}")
            
            # 데이터 매니저에 연결 상태 업데이트
            if self.data_manager:
                self.data_manager.update_server_connection_status(False)
                # 즉시 컨베이어 상태 변경 이벤트 발생
                self.data_manager.conveyor_status_changed.emit()
        
        @self.sio.event
        def disconnect():
            print("Socket.IO 서버와 연결이 끊어졌습니다.")
            self.is_connected = False
            self.connectionStatusChanged.emit(False, "서버와 연결이 끊어졌습니다.")
            
            # 데이터 매니저에 연결 상태 업데이트
            if self.data_manager:
                self.data_manager.update_server_connection_status(False)
                # 즉시 컨베이어 상태 변경 이벤트 발생
                self.data_manager.conveyor_status_changed.emit()
        
        @self.sio.on("event", namespace="/ws")
        def on_event(data):
            print(f"이벤트 수신: {data}")
            
            if isinstance(data, dict):
                category = data.get("category", "unknown")
                action = data.get("action", "unknown")
                payload = data.get("payload", {})
                
                # 이벤트 시그널 발생
                self.eventReceived.emit(category, action, payload)
                
                # 데이터 매니저에 직접 데이터 업데이트 (특정 이벤트)
                if self.data_manager and category == "environment" and action == "temperature_update":
                    warehouse_id = payload.get("warehouse_id")
                    temperature = payload.get("temperature")
                    if warehouse_id in self.data_manager._warehouse_data and temperature is not None:
                        self.data_manager._warehouse_data[warehouse_id]["temperature"] = temperature
                        # 상태 업데이트
                        min_temp = self.data_manager.temp_thresholds[warehouse_id]["min"]
                        max_temp = self.data_manager.temp_thresholds[warehouse_id]["max"]
                        if min_temp <= temperature <= max_temp:
                            self.data_manager._warehouse_data[warehouse_id]["status"] = "정상"
                        else:
                            self.data_manager._warehouse_data[warehouse_id]["status"] = "주의" 
                        self.data_manager.warehouse_data_changed.emit()
                
                # 컨베이어 상태 업데이트
                if self.data_manager and category == "sorter" and action == "status_update":
                    is_running = payload.get("is_running")
                    if is_running is not None:
                        self.data_manager._conveyor_status = 1 if is_running else 0
                        self.data_manager.conveyor_status_changed.emit()
                
        # 바코드 스캔 이벤트 처리
        @self.sio.on("barcode_scanned", namespace="/ws")
        def on_barcode_scanned(data):
            print(f"바코드 스캔 이벤트 수신: {data}")
            # 데이터가 올바른 형식인지 확인
            if isinstance(data, dict) and "barcode" in data and "category" in data:
                # sorter 카테고리, barcode_scanned 액션으로 표준화된 이벤트 형식으로 변환
                self.eventReceived.emit("sorter", "barcode_scanned", data)
    
    def connect_to_server(self):
        """서버에 연결 시도"""
        try:
            # REST API 연결 테스트
            response = requests.get(f"{self.api_base_url}/status", timeout=5)
            response.raise_for_status()
            
            # 새로운 Socket.IO 클라이언트 생성
            self.sio = socketio.Client(
                logger=False,
                engineio_logger=False,
                reconnection=True,
                reconnection_attempts=3,
                reconnection_delay=1,
                reconnection_delay_max=5,
                wait_timeout=5
            )
            
            # 이벤트 핸들러 재설정
            self.setup_socketio_events()
            
            # WebSocket 연결
            if not self.is_connected:
                self.sio.connect(self.websocket_url, namespaces=["/ws"])
                
                # 연결 후 즉시 상태 업데이트
                if self.data_manager:
                    self.data_manager.update_server_connection_status(True)
                    self.data_manager.conveyor_status_changed.emit()
            
            return True
        except Exception as e:
            self.connection_error = str(e)
            self.is_connected = False
            self.connectionStatusChanged.emit(False, f"서버 연결 실패: {str(e)}")
            print(f"서버 연결 실패: {str(e)}")
            
            # 데이터 매니저에 연결 상태 업데이트
            if self.data_manager:
                self.data_manager.update_server_connection_status(False)
                self.data_manager.conveyor_status_changed.emit()
            
            return False
    
    def disconnect_from_server(self):
        """서버 연결 종료"""
        if self.is_connected:
            try:
                self.sio.disconnect()
                self.is_connected = False
                print("서버 연결이 종료되었습니다.")
                
                # 데이터 매니저에 연결 상태 업데이트
                if self.data_manager:
                    self.data_manager.update_server_connection_status(False)
                
            except Exception as e:
                print(f"서버 연결 종료 오류: {str(e)}")
                
    def check_connection(self):
        """서버 연결 상태 확인"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        return True
    
    # ==== API 호출 메서드 ====
    def get_environment_data(self):
        """환경 데이터 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            response = requests.get(f"{self.api_base_url}/environment/status", timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"환경 데이터 가져오기 실패: {str(e)}")
            raise
    
    def get_inventory_data(self):
        """재고 데이터 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            response = requests.get(f"{self.api_base_url}/inventory/status", timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"재고 데이터 가져오기 실패: {str(e)}")
            raise
    
    def get_expiry_data(self):
        """유통기한 데이터 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            response_over = requests.get(f"{self.api_base_url}/expiry/expired", timeout=3)
            response_soon = requests.get(f"{self.api_base_url}/expiry/alerts", timeout=3)
            response_over.raise_for_status()
            response_soon.raise_for_status()
            return {
                "over": len(response_over.json()),
                "soon": len(response_soon.json())
            }
        except Exception as e:
            print(f"유통기한 데이터 가져오기 실패: {str(e)}")
            raise
    
    def get_conveyor_status(self):
        """컨베이어 상태 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            response = requests.get(f"{self.api_base_url}/sort/inbound/status", timeout=3)
            response.raise_for_status()
            data = response.json()
            return 1 if data.get("is_running", False) else 0
        except Exception as e:
            print(f"컨베이어 상태 가져오기 실패: {str(e)}")
            raise
    
    def get_today_input(self):
        """오늘 입고 현황 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            response = requests.get(f"{self.api_base_url}/inventory/today_input", timeout=3)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"오늘 입고 현황 가져오기 실패: {str(e)}")
            raise
            
    def get_error_count(self):
        """오류 건수 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            response = requests.get(f"{self.api_base_url}/sort/status", timeout=3)
            response.raise_for_status()
            data = response.json()
            # 분류기 상태 데이터에서 E 카테고리 건수 추출
            sort_counts = data.get("status", {}).get("sort_counts", {})
            return sort_counts.get("E", 0)
        except Exception as e:
            print(f"오류 건수 가져오기 실패: {str(e)}")
            return 0  # 오류 시 기본값 반환
            
    def get_waiting_count(self):
        """대기 건수 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            response = requests.get(f"{self.api_base_url}/sort/status", timeout=3)
            response.raise_for_status()
            data = response.json()
            # 분류기 상태 데이터에서 대기 건수 추출
            return data.get("status", {}).get("items_waiting", 0)
        except Exception as e:
            print(f"대기 건수 가져오기 실패: {str(e)}")
            return 0  # 오류 시 기본값 반환
            
    def get_total_processed(self):
        """총 처리 건수 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            response = requests.get(f"{self.api_base_url}/sort/status", timeout=3)
            response.raise_for_status()
            data = response.json()
            # 분류기 상태 데이터에서 총 처리 건수 추출
            return data.get("status", {}).get("items_processed", 0)
        except Exception as e:
            print(f"총 처리 건수 가져오기 실패: {str(e)}")
            return 0  # 오류 시 기본값 반환