import socketio
import requests
from PyQt6.QtCore import QObject, pyqtSignal

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
        
        @self.sio.event
        def connect_error(data):
            print(f"Socket.IO 연결 오류: {data}")
            self.is_connected = False
            self.connection_error = str(data)
            self.connectionStatusChanged.emit(False, f"서버 연결 오류: {data}")
            
            # 데이터 매니저에 연결 상태 업데이트
            if self.data_manager:
                self.data_manager.update_server_connection_status(False)
        
        @self.sio.event
        def disconnect():
            print("Socket.IO 서버와 연결이 끊어졌습니다.")
            self.is_connected = False
            self.connectionStatusChanged.emit(False, "서버와 연결이 끊어졌습니다.")
            
            # 데이터 매니저에 연결 상태 업데이트
            if self.data_manager:
                self.data_manager.update_server_connection_status(False)
        
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
    
    def connect_to_server(self):
        """서버에 연결 시도"""
        try:
            # REST API 연결 테스트
            # 실제 환경에서는 아래 코드 사용
            # response = requests.get(f"{self.api_base_url}/status", timeout=5)
            # response.raise_for_status()
            
            # 테스트용 코드 - 항상 연결 실패
            # 실제 환경에서는 아래 주석 처리
            raise ConnectionError("테스트: 서버 연결 실패")
            
            # WebSocket 연결
            if not self.is_connected:
                self.sio.connect(self.websocket_url, namespaces=["/ws"])
            
            return True
        except Exception as e:
            self.connection_error = str(e)
            self.is_connected = False
            self.connectionStatusChanged.emit(False, f"서버 연결 실패: {str(e)}")
            print(f"서버 연결 실패: {str(e)}")
            
            # 데이터 매니저에 연결 상태 업데이트
            if self.data_manager:
                self.data_manager.update_server_connection_status(False)
            
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
            # 실제 환경에서는 아래 코드 사용
            # response = requests.get(f"{self.api_base_url}/environment/status", timeout=3)
            # response.raise_for_status()
            # return response.json()
            
            # 테스트 데이터
            return {
                "A": {"temperature": -25.0},
                "B": {"temperature": 5.0},
                "C": {"temperature": 20.0}
            }
        except Exception as e:
            print(f"환경 데이터 가져오기 실패: {str(e)}")
            raise
    
    def get_inventory_data(self):
        """재고 데이터 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            # 실제 환경에서는 아래 코드 사용
            # response = requests.get(f"{self.api_base_url}/inventory/status", timeout=3)
            # response.raise_for_status()
            # return response.json()
            
            # 테스트 데이터
            return {
                "A": {"used": 37, "capacity": 100},
                "B": {"used": 93, "capacity": 100},
                "C": {"used": 87, "capacity": 100}
            }
        except Exception as e:
            print(f"재고 데이터 가져오기 실패: {str(e)}")
            raise
    
    def get_expiry_data(self):
        """유통기한 데이터 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            # 실제 환경에서는 아래 코드 사용
            # response_over = requests.get(f"{self.api_base_url}/expiry/expired", timeout=3)
            # response_soon = requests.get(f"{self.api_base_url}/expiry/alerts", timeout=3)
            # response_over.raise_for_status()
            # response_soon.raise_for_status()
            # return {
            #     "over": len(response_over.json()),
            #     "soon": len(response_soon.json())
            # }
            
            # 테스트 데이터
            return {
                "over": 2,
                "soon": 10
            }
        except Exception as e:
            print(f"유통기한 데이터 가져오기 실패: {str(e)}")
            raise
    
    def get_conveyor_status(self):
        """컨베이어 상태 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            # 실제 환경에서는 아래 코드 사용
            # response = requests.get(f"{self.api_base_url}/sort/inbound/status", timeout=3)
            # response.raise_for_status()
            # data = response.json()
            # return 1 if data.get("is_running", False) else 0
            
            # 테스트 데이터
            return 0  # 정지 상태
        except Exception as e:
            print(f"컨베이어 상태 가져오기 실패: {str(e)}")
            raise
    
    def get_today_input(self):
        """오늘 입고 현황 가져오기"""
        if not self.is_connected:
            raise ConnectionError("서버에 연결되어 있지 않습니다.")
        
        try:
            # 실제 환경에서는 아래 코드 사용
            # response = requests.get(f"{self.api_base_url}/inventory/today_input", timeout=3)
            # response.raise_for_status()
            # return response.json()
            
            # 테스트 데이터
            return {
                "total": 25,
                "A": 8,
                "B": 10,
                "C": 7
            }
        except Exception as e:
            print(f"오늘 입고 현황 가져오기 실패: {str(e)}")
            raise