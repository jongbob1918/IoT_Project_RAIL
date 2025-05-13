# simple_gate_serial_test.py
import serial
import serial.tools.list_ports
import time
import threading
import sys

# ANSI 색상 코드 - 터미널에서 데이터 구분을 위한 색상
RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"

class SimpleGateSerialTester:
    def __init__(self, port='/dev/ttyACM0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_running = False
        self.rx_thread = None
    
    def connect(self):
        """시리얼 포트 연결"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self.is_running = True
            
            # 수신 스레드 시작
            self.rx_thread = threading.Thread(target=self._rx_thread)
            self.rx_thread.daemon = True
            self.rx_thread.start()
            
            print(f"{GREEN}포트 {self.port}에 연결되었습니다. (속도: {self.baudrate} bps){RESET}")
            return True
        except Exception as e:
            print(f"{RED}포트 연결 오류: {e}{RESET}")
            return False
    
    def disconnect(self):
        """시리얼 포트 연결 해제"""
        self.is_running = False
        if self.rx_thread:
            self.rx_thread.join(timeout=1.0)
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print(f"{YELLOW}포트 연결이 해제되었습니다.{RESET}")
    
    def _rx_thread(self):
        """수신 스레드 - 데이터 수신 및 출력"""
        buffer = bytearray()
        
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                # 데이터 있으면 읽기
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    buffer.extend(data)
                    
                    # 메시지 경계(\n) 찾기
                    while b'\n' in buffer:
                        newline_pos = buffer.find(b'\n')
                        message = buffer[:newline_pos].decode('utf-8', errors='replace')
                        buffer = buffer[newline_pos + 1:]
                        
                        # 수신 메시지 출력
                        timestamp = time.strftime("%H:%M:%S", time.localtime())
                        print(f"{BLUE}[{timestamp} RX] {message}{RESET}")
                
                time.sleep(0.01)  # CPU 부하 방지
            except Exception as e:
                print(f"{RED}수신 오류: {e}{RESET}")
                time.sleep(1)
    
    def send_command(self, command):
        """명령 전송"""
        if not self.serial_conn or not self.serial_conn.is_open:
            print(f"{RED}포트가 연결되어 있지 않습니다.{RESET}")
            return False
        
        try:
            # 줄바꿈 추가
            if not command.endswith('\n'):
                command += '\n'
            
            # 전송
            self.serial_conn.write(command.encode('utf-8'))
            self.serial_conn.flush()
            
            # 전송 메시지 출력
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            print(f"{GREEN}[{timestamp} TX] {command.strip()}{RESET}")
            return True
        except Exception as e:
            print(f"{RED}전송 오류: {e}{RESET}")
            return False
    
    def simulate_card_read(self, uid, employee_id="000000", is_register_mode=False):
        """카드 인식 이벤트 시뮬레이션 데이터 생성"""
        event_type = "wr" if is_register_mode else "id"
        message = f"GE{event_type}{uid};{employee_id}"
        return message


def list_ports():
    """시리얼 포트 목록 출력"""
    ports = list(serial.tools.list_ports.comports())
    print(f"\n{CYAN}사용 가능한 시리얼 포트:{RESET}")
    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device} - {port.description}")
    return ports


def print_help():
    """도움말 출력"""
    print(f"\n{CYAN}명령어 도움말:{RESET}")
    print(f"  {YELLOW}r{RESET} - 출입 모드로 설정 (Read mode) -> GCmd0")
    print(f"  {YELLOW}w{RESET} - 등록 모드로 설정 (Write mode) -> GCmd1") 
    print(f"  {YELLOW}a{RESET} - 출입 허용 (Access allow) -> GCac1")
    print(f"  {YELLOW}d{RESET} - 출입 거부 (Access deny) -> GCac0")
    print(f"  {YELLOW}c [직원ID]{RESET} - 카드에 직원ID 쓰기 -> GCwr[직원ID]")
    print(f"  {YELLOW}sr [UID]{RESET} - 등록 모드 카드 인식 시뮬레이션 -> GEwr[UID];000000")
    print(f"  {YELLOW}sa [UID] [직원ID]{RESET} - 출입 모드 카드 인식 시뮬레이션 -> GEid[UID];[직원ID]")
    print(f"  {YELLOW}raw [명령어]{RESET} - 원시 명령어 직접 전송")
    print(f"  {YELLOW}help{RESET} - 도움말 출력")
    print(f"  {YELLOW}q/exit{RESET} - 종료")


def main():
    """메인 함수"""
    print(f"{CYAN}게이트 시리얼 통신 간단 테스트 도구{RESET}")
    print("-" * 40)
    
    # 포트 목록 출력 및 선택
    ports = list_ports()
    if not ports:
        print(f"{RED}사용 가능한 시리얼 포트가 없습니다.{RESET}")
        return
    
    choice = input(f"\n{YELLOW}사용할 포트 번호 선택 (기본값: 1): {RESET}") or "1"
    try:
        port_idx = int(choice) - 1
        if port_idx < 0 or port_idx >= len(ports):
            print(f"{RED}유효하지 않은 포트 번호입니다.{RESET}")
            return
        selected_port = ports[port_idx].device
    except ValueError:
        print(f"{RED}숫자를 입력하세요.{RESET}")
        return
    
    # 통신 속도 설정
    baud_input = input(f"{YELLOW}통신 속도 설정 (기본값: 9600): {RESET}") or "9600"
    try:
        baudrate = int(baud_input)
    except ValueError:
        print(f"{RED}유효한 통신 속도가 아닙니다. 기본값 9600을 사용합니다.{RESET}")
        baudrate = 9600
    
    # 테스터 생성 및 연결
    tester = SimpleGateSerialTester(selected_port, baudrate)
    if not tester.connect():
        return
    
    try:
        print_help()
        
        while True:
            cmd = input(f"\n{MAGENTA}명령 입력 > {RESET}")
            
            if not cmd.strip():
                continue
            
            # 명령어 처리
            if cmd in ['q', 'exit']:
                break
            
            elif cmd == 'help':
                print_help()
            
            elif cmd == 'r':
                # 출입 모드 설정
                tester.send_command("GCmd0")
            
            elif cmd == 'w':
                # 등록 모드 설정
                tester.send_command("GCmd1")
            
            elif cmd == 'a':
                # 출입 허용
                tester.send_command("GCac1")
            
            elif cmd == 'd':
                # 출입 거부
                tester.send_command("GCac0")
            
            elif cmd.startswith('c '):
                # 카드에 직원ID 쓰기
                parts = cmd.split(' ', 1)
                if len(parts) == 2:
                    employee_id = parts[1].strip()
                    # 6자리로 맞추기
                    employee_id = employee_id.zfill(6)[:6]
                    tester.send_command(f"GCwr{employee_id}")
                else:
                    print(f"{RED}형식: c [직원ID] (예: c 123456){RESET}")
            
            elif cmd.startswith('sr '):
                # 등록 모드 카드 인식 시뮬레이션
                parts = cmd.split(' ', 1)
                if len(parts) == 2:
                    uid = parts[1].strip()
                    message = tester.simulate_card_read(uid, "000000", True)
                    print(f"{YELLOW}등록 모드 카드 인식 시뮬레이션: {message}{RESET}")
                    tester.send_command(message)
                else:
                    print(f"{RED}형식: sr [UID] (예: sr 04:A3:BC:22){RESET}")
            
            elif cmd.startswith('sa '):
                # 출입 모드 카드 인식 시뮬레이션
                parts = cmd.split(' ', 2)
                if len(parts) == 3:
                    uid = parts[1].strip()
                    employee_id = parts[2].strip().zfill(6)[:6]
                    message = tester.simulate_card_read(uid, employee_id, False)
                    print(f"{YELLOW}출입 모드 카드 인식 시뮬레이션: {message}{RESET}")
                    tester.send_command(message)
                else:
                    print(f"{RED}형식: sa [UID] [직원ID] (예: sa 04:A3:BC:22 123456){RESET}")
            
            elif cmd.startswith('raw '):
                # 원시 명령어 직접 전송
                raw_cmd = cmd[4:].strip()
                tester.send_command(raw_cmd)
            
            else:
                print(f"{RED}알 수 없는 명령: {cmd}{RESET}")
                print(f"{YELLOW}도움말을 보려면 'help'를 입력하세요.{RESET}")
    
    except KeyboardInterrupt:
        print(f"\n{YELLOW}사용자에 의해 중단되었습니다.{RESET}")
    
    finally:
        tester.disconnect()
        print(f"{CYAN}프로그램이 종료되었습니다.{RESET}")


if __name__ == "__main__":
    main()