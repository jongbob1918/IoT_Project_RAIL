# server/serial_handlers/gate_serial.py

import serial
import serial.tools.list_ports
import threading
import queue
import time
import logging
from typing import Callable, Dict, Any, List, Tuple, Optional

class GateSerialHandler:
    """게이트 컨트롤러와 시리얼 통신을 담당하는 핸들러 클래스"""
    
    def __init__(self, port='/dev/ttyACM0', baudrate=9600, timeout=1):
        """시리얼 통신 핸들러 초기화
        
        Args:
            port: 시리얼 포트 경로 (예: '/dev/ttyUSB0', 'COM3')
            baudrate: 통신 속도 (보드레이트)
            timeout: 읽기 타임아웃 (초)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.is_running = False
        self.read_thread = None
        self.write_thread = None
        self.write_queue = queue.Queue()
        
        # 이벤트 콜백 등록
        self.event_callbacks = {
            'id': None,  # 출입 모드 카드 인식 콜백
            'wr': None   # 등록 모드 카드 인식 콜백
        }
        
        # 응답 콜백 (명령에 대한 응답 처리)
        self.response_callbacks = {
            'ok': None,  # 성공 응답
            'e1': None,  # RFID 인식 오류
            'e2': None   # 카드 쓰기 실패
        }
        
        # 로거 설정
        self.logger = logging.getLogger('gate_serial')
        
        # 수신 버퍼
        self.buffer = bytearray()
    
    @staticmethod
    def list_ports() -> List[Tuple[str, str]]:
        """사용 가능한 시리얼 포트 목록 반환
        
        Returns:
            [(포트경로, 설명), ...] 형식의 포트 목록
        """
        ports = list(serial.tools.list_ports.comports())
        return [(p.device, p.description) for p in ports]
    
    def connect(self) -> bool:
        """시리얼 포트 연결
        
        Returns:
            연결 성공 여부 (True/False)
        """
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self.is_running = True
            self.start_threads()
            self.logger.info(f"게이트 컨트롤러와 시리얼 연결 성공: {self.port}")
            return True
        except Exception as e:
            self.logger.error(f"게이트 컨트롤러 시리얼 연결 실패: {e}")
            return False
    
    def disconnect(self):
        """시리얼 포트 연결 해제"""
        self.is_running = False
        if self.read_thread:
            self.read_thread.join(timeout=1.0)
        if self.write_thread:
            self.write_thread.join(timeout=1.0)
        
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        
        self.logger.info("게이트 컨트롤러 시리얼 연결 해제")
    
    def start_threads(self):
        """읽기/쓰기 스레드 시작"""
        # 읽기 스레드
        self.read_thread = threading.Thread(target=self._read_loop)
        self.read_thread.daemon = True
        self.read_thread.start()
        
        # 쓰기 스레드
        self.write_thread = threading.Thread(target=self._write_loop)
        self.write_thread.daemon = True
        self.write_thread.start()
    
    def _read_loop(self):
        """시리얼 포트에서 데이터 읽기 루프"""
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                # 데이터가 있으면 읽기
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    self.buffer.extend(data)
                    
                    # 메시지 경계(\n) 찾기
                    while b'\n' in self.buffer:
                        # 메시지 추출
                        newline_pos = self.buffer.find(b'\n')
                        message = self.buffer[:newline_pos].decode('utf-8')
                        self.buffer = self.buffer[newline_pos + 1:]
                        
                        # 메시지 처리
                        self._process_message(message)
                
                # CPU 사용량 줄이기 위한 짧은 대기
                time.sleep(0.01)
            except Exception as e:
                self.logger.error(f"시리얼 데이터 읽기 오류: {e}")
                time.sleep(1)  # 오류 발생 시 잠시 대기
    
    def _write_loop(self):
        """시리얼 포트로 데이터 쓰기 루프"""
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                # 쓰기 큐에서 메시지 가져오기
                if not self.write_queue.empty():
                    message = self.write_queue.get()
                    if not message.endswith('\n'):
                        message += '\n'
                    
                    # 메시지 전송
                    self.serial_conn.write(message.encode('utf-8'))
                    self.serial_conn.flush()
                    self.logger.debug(f"전송 메시지: {message.strip()}")
                
                # CPU 사용량 줄이기 위한 짧은 대기
                time.sleep(0.01)
            except Exception as e:
                self.logger.error(f"시리얼 데이터 쓰기 오류: {e}")
                time.sleep(1)  # 오류 발생 시 잠시 대기
    
    def _process_message(self, message):
        """수신된 메시지 처리"""
        if len(message) < 3:
            self.logger.warning(f"잘못된 메시지 형식: {message}")
            return
        
        try:
            # 디바이스 ID와 메시지 타입 확인
            device_id = message[0]
            msg_type = message[1]
            
            # 게이트 컨트롤러(G) 메시지만 처리
            if device_id != 'G':
                self.logger.warning(f"잘못된 디바이스 ID: {device_id}")
                return
            
            if msg_type == 'E':  # 이벤트
                # 이벤트 종류 추출 (3번째와 4번째 문자)
                event_type = message[2:4]
                event_data = message[4:] if len(message) > 4 else ''
                
                # 등록된 콜백 실행
                if event_type in self.event_callbacks and self.event_callbacks[event_type]:
                    self.event_callbacks[event_type](event_data)
                    self.logger.info(f"이벤트 처리: {event_type}, 데이터: {event_data}")
                else:
                    self.logger.warning(f"처리되지 않은 이벤트: {event_type}")
                    
            elif msg_type == 'R' or msg_type == 'X':  # 응답 또는 오류
                # 응답 코드 추출
                response_code = message[2:4]
                
                # 등록된 콜백 실행
                if response_code in self.response_callbacks and self.response_callbacks[response_code]:
                    self.response_callbacks[response_code]()
                    self.logger.info(f"응답 처리: {response_code}")
                else:
                    self.logger.warning(f"처리되지 않은 응답: {response_code}")
            
            else:
                self.logger.warning(f"알 수 없는 메시지 타입: {msg_type}")
                
        except Exception as e:
            self.logger.error(f"메시지 처리 중 오류: {e}, 메시지: {message}")
    
    # === 명령 전송 메서드 ===
    def send_access_command(self, allow: bool) -> bool:
        """출입 허용/거부 명령 전송
        
        Args:
            allow: True=허용, False=거부
            
        Returns:
            명령 전송 성공 여부
        """
        # GCac1\n (1=허용, 0=거부)
        command = f"GCac{1 if allow else 0}"
        self.write_queue.put(command)
        return True
    
    def send_mode_command(self, register_mode: bool) -> bool:
        """출입/등록 모드 설정
        
        Args:
            register_mode: True=등록 모드, False=출입 모드
            
        Returns:
            명령 전송 성공 여부
        """
        # GCmd0\n (0=출입 모드, 1=등록 모드)
        command = f"GCmd{1 if register_mode else 0}"
        self.write_queue.put(command)
        return True
    
    def send_write_card_command(self, employee_id: str) -> bool:
        """카드에 직원 ID 쓰기 (등록)
        
        Args:
            employee_id: 직원 ID (최대 6자리)
            
        Returns:
            명령 전송 성공 여부
        """
        # GCwr000000\n
        # employee_id가 6자리 이하면 앞에 0 채우기
        employee_id = employee_id.zfill(6)[:6]
        command = f"GCwr{employee_id}"
        self.write_queue.put(command)
        return True
    
    def send_raw_command(self, command: str) -> bool:
        """원시 명령어 전송
        
        Args:
            command: 전송할 명령어 문자열
            
        Returns:
            명령 전송 성공 여부
        """
        self.write_queue.put(command)
        return True
    
    # === 콜백 등록 메서드 ===
    def register_id_event_callback(self, callback: Callable[[str], None]):
        """출입 모드 카드 인식 이벤트 콜백 등록
        
        Args:
            callback: 콜백 함수 (파라미터: 인식된 카드 데이터)
        """
        self.event_callbacks['id'] = callback
    
    def register_write_event_callback(self, callback: Callable[[str], None]):
        """등록 모드 카드 인식 이벤트 콜백 등록
        
        Args:
            callback: 콜백 함수 (파라미터: 인식된 카드 데이터)
        """
        self.event_callbacks['wr'] = callback
    
    def register_response_callback(self, response_type: str, callback: Callable[[], None]):
        """응답 콜백 등록
        
        Args:
            response_type: 응답 타입 ('ok', 'e1', 'e2' 등)
            callback: 콜백 함수
        """
        if response_type in self.response_callbacks:
            self.response_callbacks[response_type] = callback


# 콘솔에서 직접 실행 시 간단한 테스트 수행
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 사용 가능한 포트 출력
    print("사용 가능한 시리얼 포트:")
    ports = GateSerialHandler.list_ports()
    for i, (port, desc) in enumerate(ports):
        print(f"{i+1}. {port} - {desc}")
    
    if not ports:
        print("시리얼 포트를 찾을 수 없습니다.")
        exit(1)
    
    # 포트 선택
    choice = input("사용할 포트 번호를 입력하세요 (기본값: 1): ") or "1"
    try:
        port_idx = int(choice) - 1
        if 0 <= port_idx < len(ports):
            selected_port = ports[port_idx][0]
        else:
            print("유효하지 않은 포트 번호입니다.")
            exit(1)
    except ValueError:
        print("숫자를 입력하세요.")
        exit(1)
    
    # 보드레이트 선택
    baudrate_input = input("보드레이트를 입력하세요 (기본값: 9600): ") or "9600"
    try:
        baudrate = int(baudrate_input)
    except ValueError:
        print("유효한 보드레이트를 입력하세요.")
        exit(1)
    
    # 핸들러 생성 및 연결
    handler = GateSerialHandler(port=selected_port, baudrate=baudrate)
    
    # 콜백 함수 정의
    def on_card_detected(data):
        print(f"카드 인식됨: {data}")
        # 데이터 파싱 (UID와 직원ID 분리)
        parts = data.split(';')
        if len(parts) == 2:
            uid, employee_id = parts
            print(f"UID: {uid}, 직원ID: {employee_id}")
            
            # 출입 허용 (예시)
            handler.send_access_command(True)
    
    def on_register_card_detected(data):
        print(f"등록용 카드 인식됨: {data}")
        # 데이터 파싱 (UID와 회사ID 분리)
        parts = data.split(';')
        if len(parts) == 2:
            uid, company_id = parts
            print(f"UID: {uid}, 회사ID: {company_id}")
            
            # 직원 ID 할당 및 카드에 쓰기 (예시)
            new_employee_id = "123456"  # 실제로는 DB에서 가져올 것
            handler.send_write_card_command(new_employee_id)
    
    def on_command_ok():
        print("명령 성공적으로 처리됨")
    
    def on_rfid_error():
        print("RFID 인식 오류 발생")
    
    def on_write_error():
        print("카드 쓰기 실패")
    
    # 콜백 등록
    handler.register_id_event_callback(on_card_detected)
    handler.register_write_event_callback(on_register_card_detected)
    handler.register_response_callback('ok', on_command_ok)
    handler.register_response_callback('e1', on_rfid_error)
    handler.register_response_callback('e2', on_write_error)
    
    # 연결
    if handler.connect():
        print("게이트 컨트롤러에 연결되었습니다.")
        
        try:
            # 출입 모드로 시작
            handler.send_mode_command(register_mode=False)
            print("출입 모드로 설정됨")
            
            # 메인 루프
            print("\n명령어 안내:")
            print("1: 출입 모드")
            print("2: 등록 모드")
            print("allow: 출입 허용")
            print("deny: 출입 거부")
            print("write <직원ID>: 카드에 직원ID 쓰기")
            print("cmd <명령어>: 원시 명령어 전송")
            print("q: 종료")
            
            while True:
                cmd = input("\n명령 입력: ")
                
                if cmd == 'q':
                    break
                elif cmd == '1':
                    handler.send_mode_command(register_mode=False)
                    print("출입 모드로 설정됨")
                elif cmd == '2':
                    handler.send_mode_command(register_mode=True)
                    print("등록 모드로 설정됨")
                elif cmd == 'allow':
                    handler.send_access_command(True)
                    print("출입 허용 명령 전송")
                elif cmd == 'deny':
                    handler.send_access_command(False)
                    print("출입 거부 명령 전송")
                elif cmd.startswith('write '):
                    employee_id = cmd.split(' ')[1]
                    handler.send_write_card_command(employee_id)
                    print(f"카드에 직원ID({employee_id}) 쓰기 명령 전송")
                elif cmd.startswith('cmd '):
                    raw_cmd = cmd[4:]
                    handler.send_raw_command(raw_cmd)
                    print(f"원시 명령어 전송: {raw_cmd}")
                else:
                    print(f"알 수 없는 명령: {cmd}")
        
        finally:
            # 연결 해제
            handler.disconnect()
            print("게이트 컨트롤러 연결 해제됨")
    else:
        print(f"게이트 컨트롤러 연결 실패: {selected_port}")