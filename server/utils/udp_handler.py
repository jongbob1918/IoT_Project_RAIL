import socket
import threading
import logging
import cv2
import numpy as np
import time

logger = logging.getLogger(__name__)

class UDPBarcodeHandler:
    def __init__(self, host='0.0.0.0', port=9000, callback=None, debug_mode=False):
        """UDP 바코드 핸들러 초기화
        
        Args:
            host (str): 바인딩할 호스트 주소
            port (int): 바인딩할 포트 번호
            callback (callable): 바코드 인식 시 호출할 콜백 함수
            debug_mode (bool): 디버그 모드 활성화 여부 (화면에 이미지 표시)
        """
        self.host = host
        self.port = port
        self.callback = callback
        self.debug_mode = debug_mode
        self.running = False
        self.udp_socket = None
        self.thread = None
        
        # 버퍼 및 상태 관리 변수
        self.buffer = bytearray()
        self.receiving = False
        self.expected_size = 0
        self.last_sent_data = ""  # 중복 전송 방지
        self.last_sent_time = 0   # 마지막 데이터 전송 시간
        self.frame_count = 0      # 프레임 카운터
        self.last_fps_check = time.time()  # FPS 계산용 시간
        
        # QR 코드 감지기 초기화
        try:
            self.qr_detector = cv2.QRCodeDetector()
            logger.info("QR 코드 감지기 초기화 성공")
        except Exception as e:
            logger.error(f"QR 코드 감지기 초기화 실패: {str(e)}")
            self.qr_detector = None
        
        # 성능 모니터링 변수
        self.fps = 0
        self.process_times = []  # 이미지 처리 시간 기록
        
        logger.info(f"UDP 바코드 핸들러 초기화 완료 - {host}:{port}")
    
    def start(self):
        """UDP 바코드 핸들러 시작"""
        if self.running:
            logger.warning("UDP 바코드 핸들러가 이미 실행 중입니다.")
            return False
            
        try:
            # UDP 소켓 설정
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind((self.host, self.port))
            # 타임아웃 감소 - 더 빠른 응답성 위해 0.1초로 설정
            self.udp_socket.settimeout(0.1)
            # 소켓 버퍼 크기 증가 (더 많은 데이터를 빠르게 처리)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
            self.running = True
            
            logger.info(f"UDP 바코드 핸들러 시작됨: {self.host}:{self.port}")
            
            # 수신 스레드 시작
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            
            return True
        except Exception as e:
            logger.error(f"UDP 바코드 핸들러 시작 실패: {str(e)}")
            return False
    
    def stop(self):
        """UDP 바코드 핸들러 종료"""
        logger.info("UDP 바코드 핸들러 종료 중...")
        self.running = False
        
        # 소켓 닫기
        if self.udp_socket:
            try:
                self.udp_socket.close()
                logger.debug("UDP 소켓 닫힘")
            except Exception as e:
                logger.error(f"UDP 소켓 종료 중 오류: {str(e)}")
        
        # 스레드 종료 대기
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                logger.warning("UDP 핸들러 스레드가 2초 내에 종료되지 않았습니다.")
            
        logger.info("UDP 바코드 핸들러 종료됨")
    
    def _receive_loop(self):
        """UDP 데이터 수신 루프"""
        # 패킷 크기 증가 - 더 큰 데이터 청크 처리
        PACKET_SIZE = 4096  # 1024에서 4096으로 증가
        
        # 마지막 프레임 처리 시간 기록
        last_frame_time = 0
        
        logger.info("UDP 데이터 수신 루프 시작")
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(PACKET_SIZE)
                
                # 지나치게 자세한 로그 제거 (성능 향상)
                if data.startswith(b'FRAME_START'):
                    self.buffer = bytearray()  # 새 버퍼 생성 (메모리 재사용)
                    parts = data.decode().strip().split(':')
                    if len(parts) == 2:
                        self.expected_size = int(parts[1])
                        self.receiving = True
                        # 큰 프레임을 미리 예약하여 메모리 할당 최적화
                        self.buffer = bytearray(self.expected_size)
                        self.buffer_position = 0
                
                elif data.startswith(b'FRAME_END'):
                    if self.buffer_position == self.expected_size:
                        # 성능 측정
                        current_time = time.time()
                        if last_frame_time > 0:
                            frame_interval = current_time - last_frame_time
                            instant_fps = 1 / frame_interval if frame_interval > 0 else 0
                            # 평균 FPS 계산 (5프레임 이동 평균)
                            self.frame_count += 1
                            if len(self.process_times) >= 5:
                                self.process_times.pop(0)
                            self.process_times.append(instant_fps)
                            self.fps = sum(self.process_times) / len(self.process_times)
                            
                            # 주기적 FPS 로깅 (5초마다)
                            if current_time - self.last_fps_check > 5:
                                logger.info(f"현재 프레임 처리 속도: {self.fps:.2f} FPS")
                                self.last_fps_check = current_time
                        
                        last_frame_time = current_time
                        # 이미지 처리 (QR 코드 인식)
                        self._process_image()
                    else:
                        logger.warning(f"불완전한 프레임: {self.buffer_position}/{self.expected_size} 바이트")
                    
                    self.receiving = False
                
                elif self.receiving:
                    # 더 효율적인 버퍼 관리
                    data_len = len(data)
                    if self.buffer_position + data_len <= self.expected_size:
                        self.buffer[self.buffer_position:self.buffer_position + data_len] = data
                        self.buffer_position += data_len
            
            except socket.timeout:
                # 타임아웃 - 더 이상 로그 남기지 않음
                continue
            except Exception as e:
                logger.error(f"UDP 데이터 처리 오류: {str(e)}")
                # 오류 발생 시 짧은 대기 후 계속
                time.sleep(0.1)
        
        logger.info("UDP 데이터 수신 루프 종료")
    
    def _process_image(self):
        """수신된 이미지 처리 및 QR 코드 인식"""
        start_time = time.time()
        
        try:
            # 바이트 배열을 이미지로 변환
            jpg = np.frombuffer(bytes(self.buffer[:self.buffer_position]), dtype=np.uint8)
            img = cv2.imdecode(jpg, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.warning("이미지 디코딩 실패")
                return
            
            # 디버그 모드 최적화: 낮은 해상도로 표시
            if self.debug_mode:
                # 이미지 크기 축소 (표시 성능 개선)
                display_img = cv2.resize(img, (640, 480))
                cv2.imshow("QR UDP Stream", display_img)
                cv2.waitKey(1)
            
            if self.qr_detector is None:
                logger.error("QR 코드 감지기가 초기화되지 않았습니다.")
                return
            
            # 매 3번째 프레임에서만 QR 코드 감지 (성능 최적화)
            # 실시간성이 중요하다면 이 부분 제거
            if self.frame_count % 3 != 0 and not self.debug_mode:
                return
                
            # QR 코드 인식
            qr_data, points, _ = self.qr_detector.detectAndDecode(img)
            
            current_time = time.time()
            # 중복 데이터 처리 로직 개선: 같은 코드도 일정 시간 경과 시 다시 처리
            if qr_data:
                # 새로운 데이터이거나 마지막 전송 후 0.3초 이상 경과했을 때만 처리
                if qr_data != self.last_sent_data or (current_time - self.last_sent_time > 0.3):
                    logger.info(f"QR 코드 인식됨: {qr_data}")
                    
                    # 디버그 모드일 때 인식된 QR코드 시각화
                    if self.debug_mode and points is not None and len(points) > 0:
                        try:
                            points = points.astype(int).reshape(-1, 2)
                            cv2.polylines(display_img, [points], True, (0, 255, 0), 2)
                            x, y = points[0]
                            cv2.putText(display_img, qr_data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            cv2.imshow("QR UDP Stream", display_img)
                            cv2.waitKey(1)
                        except Exception as e:
                            # 에러 로그 최소화
                            pass
                    
                    # 콜백 함수 호출하여 바코드 데이터 전달
                    if self.callback:
                        try:
                            self.callback(qr_data)
                        except Exception as e:
                            logger.error(f"바코드 콜백 처리 중 오류: {str(e)}")
                    
                    self.last_sent_data = qr_data
                    self.last_sent_time = current_time
        
        except Exception as e:
            logger.error(f"이미지 처리 중 오류: {str(e)}")
        
        # 이미지 처리 시간 측정
        process_time = time.time() - start_time
        if process_time > 0.1:  # 100ms 이상 걸렸을 때만 로그
            logger.debug(f"이미지 처리 시간: {process_time:.3f}초")