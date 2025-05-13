# server/utils/tcp_handler.py
import socket
import threading
import logging
import time
from typing import Dict, Callable, Any, Optional, List

logger = logging.getLogger(__name__)

# ==== TCP 소켓 통신을 관리하는 핸들러 클래스 ====
class TCPHandler:
    # TCP 핸들러 장치 ID 매핑 (필요한 경우)
    DEVICE_ID_MAPPING = {
        'S': 'sort_controller',  # 분류기 - 첫 문자가 S인 메시지
        'H': 'env_controller',   # 환경 제어 - 첫 문자가 H인 메시지
        'G': 'access_controller' # 출입 제어 - 첫 문자가 G인 메시지
    }
    
    # ==== TCP 핸들러 초기화 ====
    def __init__(self, host: str = '192.168.0.10', port: int = 9000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # 클라이언트 소켓 저장 (클라이언트 ID: 정보)
        self.client_lock = threading.Lock()
        self.running = False
        
        # 메시지 버퍼 (클라이언트 ID를 키로 사용)
        self.message_buffers = {}
        
        # 디바이스별 메시지 타입 핸들러 (디바이스 ID: {메시지 타입: 핸들러 함수})
        self.device_handlers = {}
        
        # 헬스체크 주기 (초)
        self.health_check_interval = 60
        self.health_check_thread = None
        
        logger.info("TCP 핸들러 초기화 완료")

        
    # ==== 서버 시작 ====
    def start(self):
        if self.running:
            logger.warning("TCP 서버가 이미 실행 중입니다.")
            return True
        
        try:
            # 소켓 생성
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"TCP 서버가 {self.host}:{self.port}에서 시작되었습니다.")
            
            # 클라이언트 연결 수신 스레드 시작
            threading.Thread(target=self._accept_connections, daemon=True).start()
            
            # 헬스체크 스레드 시작
            self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            self.health_check_thread.start()
            
            return True
        
        except Exception as e:
            logger.error(f"TCP 서버 시작 실패: {str(e)}")
            self.running = False
            return False
    
    # ==== 서버 종료 ====
    def stop(self):
        self.running = False
        
        # 모든 클라이언트 연결 종료
        with self.client_lock:
            for client_id, client_info in list(self.clients.items()):
                try:
                    client_info['socket'].close()
                except Exception as e:
                    logger.error(f"클라이언트 {client_id} 연결 종료 실패: {str(e)}")
            
            self.clients.clear()
            self.message_buffers.clear()
        
        # 서버 소켓 종료
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"서버 소켓 종료 실패: {str(e)}")
        
        logger.info("TCP 서버가 종료되었습니다.")
    
    # ==== 클라이언트 연결 수락 ====
    def _accept_connections(self):
        logger.info("클라이언트 연결 대기 중...")
        
        while self.running:
            try:
                # 클라이언트 연결 수락
                client_socket, address = self.server_socket.accept()
                client_id = f"{address[0]}:{address[1]}"
                
                logger.info(f"새 클라이언트 연결: {client_id}")
                
                # 클라이언트 정보 저장
                with self.client_lock:
                    self.clients[client_id] = {
                        'socket': client_socket,
                        'address': address,
                        'device_id': None,
                        'last_activity': time.time()
                    }
                    # 메시지 버퍼 초기화
                    self.message_buffers[client_id] = b""
                
                # 클라이언트 수신 스레드 시작
                threading.Thread(target=self._handle_client, args=(client_id,), daemon=True).start()
            
            except socket.timeout:
                # 타임아웃은 정상 - 주기적으로 실행 상태 확인을 위함
                pass
            except Exception as e:
                if self.running:  # 정상 종료가 아닌 경우만 로그
                    logger.error(f"클라이언트 연결 수락 실패: {str(e)}")
                    time.sleep(1)  # 연속 오류 방지
    
    # ==== 클라이언트 처리 ====
    def _handle_client(self, client_id: str):
        """클라이언트 데이터 수신 및 처리"""
        if client_id not in self.clients:
            return
        
        client_socket = self.clients[client_id]['socket']
        client_socket.settimeout(5.0)  # 5초 타임아웃
        
        while self.running:
            try:
                # 데이터 수신
                data = client_socket.recv(4096)
                
                if not data:
                    # 연결 종료
                    logger.info(f"클라이언트 {client_id} 연결 종료")
                    self._remove_client(client_id)
                    break
                
                # 마지막 활동 시간 업데이트
                with self.client_lock:
                    if client_id in self.clients:
                        self.clients[client_id]['last_activity'] = time.time()
                
                # 데이터 처리
                self._process_data(client_id, data)
            
            except socket.timeout:
                # 타임아웃은 정상 - 주기적으로 실행 상태 확인을 위함
                continue
            except ConnectionResetError:
                logger.warning(f"클라이언트 {client_id} 연결 리셋됨")
                self._remove_client(client_id)
                break
            except Exception as e:
                logger.error(f"클라이언트 {client_id} 처리 중 오류: {str(e)}")
                self._remove_client(client_id)
                break
    
    # ==== 데이터 처리 ====
    def _process_data(self, client_id: str, data: bytes):
        """수신한 데이터를 처리하고 완전한 메시지를 파싱합니다."""
        # 버퍼에 데이터 추가
        with self.client_lock:
            if client_id not in self.message_buffers:
                self.message_buffers[client_id] = b""
            
            self.message_buffers[client_id] += data
            
            # 완전한 메시지 처리
            buffer = self.message_buffers[client_id]
            messages = []
            
            while b'\n' in buffer:
                # 개행 문자로 메시지 분리
                message, buffer = buffer.split(b'\n', 1)
                if message:  # 빈 메시지가 아닌 경우만 처리
                    messages.append(message)
            
            # 버퍼 업데이트
            self.message_buffers[client_id] = buffer
        
        # 메시지 처리
        for message in messages:
            try:
                # 메시지 디코딩
                decoded_message = message.decode('utf-8')
                
                # 첫 번째 문자는 디바이스 식별자(S, H, G), 두 번째 문자는 메시지 타입(E, C, R, X)
                if len(decoded_message) < 2:
                    logger.warning(f"잘못된 메시지 형식(길이 부족): {decoded_message}")
                    continue
                
                device_type = decoded_message[0]  # 디바이스 타입(S, H, G)
                message_type = decoded_message[1]  # 메시지 타입(E=이벤트, C=명령, R=응답, X=오류)
                message_content = decoded_message[2:]  # 메시지 내용
                
                # 디바이스 ID 매핑
                mapped_device_id = self.DEVICE_ID_MAPPING.get(device_type, device_type)
                
                # 클라이언트-디바이스 매핑 업데이트
                with self.client_lock:
                    if client_id in self.clients:
                        if self.clients[client_id]['device_id'] is None:
                            self.clients[client_id]['device_id'] = device_type
                            logger.info(f"디바이스 등록: {device_type} (클라이언트: {client_id})")
                
                # 메시지 타입 매핑
                if message_type == 'E':  # 이벤트
                    handler_type = 'evt'
                elif message_type == 'R':  # 응답
                    handler_type = 'res'
                elif message_type == 'X':  # 오류
                    handler_type = 'err'
                else:
                    handler_type = message_type  # 그 외 타입은 그대로 사용
                
                # 메시지 처리
                self._process_message(mapped_device_id, handler_type, device_type, message_content)
            
            except Exception as e:
                logger.error(f"메시지 처리 오류: {str(e)}")
    
    # ==== 메시지 처리 ====
    def _process_message(self, device_id: str, message_type: str, raw_device_id: str, content: str):
        """메시지를 적절한 핸들러로 전달합니다."""
        try:
            # 디바이스별 핸들러 호출
            if device_id in self.device_handlers and message_type in self.device_handlers[device_id]:
                logger.debug(f"메시지 수신 ({raw_device_id}): {content}")
                
                # 메시지 파싱 및 핸들러 호출
                self.device_handlers[device_id][message_type]({
                    'device_type': raw_device_id,
                    'message_type': message_type,
                    'content': content
                })
            else:
                logger.warning(f"핸들러 없음: 디바이스={device_id}, 타입={message_type}")
        
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {str(e)}")
    
    # ==== 메시지 전송 ====
    def send_message(self, device_id: str, command: str) -> bool:
        """지정된 디바이스에 커맨드 메시지를 전송합니다."""
        # 디바이스 ID에 해당하는 클라이언트 찾기
        client_id = self._find_client_by_device(device_id)
        
        if not client_id:
            logger.warning(f"연결된 디바이스 없음: {device_id}")
            return False
        
        try:
            with self.client_lock:
                if client_id not in self.clients:
                    return False
                
                client_socket = self.clients[client_id]['socket']
                
                # 명령어에 개행 문자 추가
                command_str = command + '\n'
                
                # 전송
                client_socket.sendall(command_str.encode('utf-8'))
                
                # 활동 시간 업데이트
                self.clients[client_id]['last_activity'] = time.time()
                
                logger.debug(f"메시지 전송 ({device_id}): {command}")
                return True
        
        except Exception as e:
            logger.error(f"메시지 전송 오류 ({device_id}): {str(e)}")
            self._remove_client(client_id)
            return False
    
    # ==== 디바이스 핸들러 등록 ====
    def register_device_handler(self, device_id: str, message_type: str, handler: Callable):
        """디바이스별 메시지 타입 핸들러를 등록합니다."""
        if device_id not in self.device_handlers:
            self.device_handlers[device_id] = {}
        
        self.device_handlers[device_id][message_type] = handler
        logger.debug(f"디바이스 핸들러 등록: {device_id}, {message_type}")
    
    # ==== 클라이언트 제거 ====
    def _remove_client(self, client_id: str):
        """클라이언트 연결을 종료하고 목록에서 제거합니다."""
        with self.client_lock:
            if client_id not in self.clients:
                return
            
            try:
                device_id = self.clients[client_id].get('device_id')
                self.clients[client_id]['socket'].close()
                del self.clients[client_id]
                
                # 메시지 버퍼 제거
                if client_id in self.message_buffers:
                    del self.message_buffers[client_id]
                
                if device_id:
                    logger.info(f"디바이스 {device_id} 연결 종료됨")
            
            except Exception as e:
                logger.error(f"클라이언트 종료 오류: {str(e)}")
    
    # ==== 디바이스 ID로 클라이언트 찾기 ====
    def _find_client_by_device(self, device_id: str) -> Optional[str]:
        """디바이스 ID에 해당하는 클라이언트 ID를 찾습니다."""
        with self.client_lock:
            for client_id, client_info in self.clients.items():
                if client_info.get('device_id') == device_id:
                    return client_id
        
        return None
    
    # ==== 헬스체크 루프 ====
    def _health_check_loop(self):
        """주기적으로 연결 상태를 확인하고 비활성 클라이언트를 정리합니다."""
        while self.running:
            try:
                # 비활성 클라이언트 정리
                self._cleanup_inactive_clients()
                
                # 다음 체크까지 대기
                time.sleep(self.health_check_interval)
            
            except Exception as e:
                logger.error(f"헬스체크 중 오류: {str(e)}")
    
    # ==== 비활성 클라이언트 정리 ====
    def _cleanup_inactive_clients(self, timeout: int = 300):
        """지정 시간 동안 활동이 없는 클라이언트를 제거합니다."""
        current_time = time.time()
        inactive_clients = []
        
        # 비활성 클라이언트 식별
        with self.client_lock:
            for client_id, client_info in self.clients.items():
                last_activity = client_info['last_activity']
                if current_time - last_activity > timeout:
                    inactive_clients.append(client_id)
        
        # 비활성 클라이언트 제거
        for client_id in inactive_clients:
            logger.info(f"비활성 클라이언트 제거: {client_id}")
            self._remove_client(client_id)
    
    # ==== 연결된 디바이스 목록 반환 ====
    def get_connected_devices(self) -> List[str]:
        """현재 연결된 디바이스 ID 목록을 반환합니다."""
        connected_devices = []
        
        with self.client_lock:
            for client_info in self.clients.values():
                device_id = client_info.get('device_id')
                if device_id:
                    connected_devices.append(device_id)
        
        return connected_devices
    
    # ==== 디바이스 연결 상태 확인 ====
    def is_device_connected(self, device_id: str) -> bool:
        """특정 디바이스의 연결 상태를 확인합니다."""
        return self._find_client_by_device(device_id) is not None