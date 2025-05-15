import socket
import threading
import logging
import cv2
import numpy as np
import time

logger = logging.getLogger(__name__)

class UDPBarcodeHandler:
    def __init__(self, host='0.0.0.0', port=9000, callback=None):
        """UDP 바코드 핸들러 초기화
        
        Args:
            host (str): 바인딩할 호스트 주소
            port (int): 바인딩할 포트 번호
            callback (callable): 바코드 인식 시 호출할 콜백 함수
        """
        self.host = host
        self.port = port
        self.callback = callback
        self.running = False
        self.udp_socket = None
        self.thread = None
        
        # 버퍼 및 상태 관리 변수
        self.buffer = bytearray()
        self.receiving = False
        self.expected_size = 0
        self.last_sent_data = ""  # 중복 전송 방지
        
        # QR 코드 감지기 초기화
        try:
            self.qr_detector = cv2.QRCodeDetector()
            logger.info("QR 코드 감지기 초기화 성공")
        except Exception as e:
            logger.error(f"QR 코드 감지기 초기화 실패: {str(e)}")
            self.qr_detector = None
        
        logger.info("UDP 바코드 핸들러 초기화 완료")
    
    def start(self):
        """UDP 바코드 핸들러 시작"""
        if self.running:
            logger.warning("UDP 바코드 핸들러가 이미 실행 중입니다.")
            return False
            
        try:
            # UDP 소켓 설정
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind((self.host, self.port))
            self.udp_socket.settimeout(5)
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
        PACKET_SIZE = 1024
        
        logger.info("UDP 데이터 수신 루프 시작")
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(PACKET_SIZE + 50)
                logger.debug(f"UDP 데이터 수신: {len(data)} 바이트 (from {addr})")
                
                if data.startswith(b'FRAME_START'):
                    self.buffer.clear()
                    parts = data.decode().strip().split(':')
                    if len(parts) == 2:
                        self.expected_size = int(parts[1])
                        self.receiving = True
                        logger.debug(f"프레임 수신 시작: {self.expected_size} 바이트")
                
                elif data.startswith(b'FRAME_END'):
                    if len(self.buffer) == self.expected_size:
                        logger.debug(f"프레임 수신 완료: {len(self.buffer)} 바이트")
                        # 이미지 디코딩 및 QR 코드 인식
                        self._process_image()
                    else:
                        logger.warning(f"불완전한 프레임: {len(self.buffer)}/{self.expected_size} 바이트")
                    
                    self.receiving = False
                    self.buffer.clear()
                
                elif self.receiving:
                    self.buffer.extend(data)
            
            except socket.timeout:
                # 타임아웃은 정상적인 동작
                pass
            except Exception as e:
                logger.error(f"UDP 데이터 처리 오류: {str(e)}")
                time.sleep(1)  # 연속 오류 방지
        
        logger.info("UDP 데이터 수신 루프 종료")
    
    def _process_image(self):
        """수신된 이미지 처리 및 QR 코드 인식"""
        try:
            # 바이트 배열을 이미지로 변환
            jpg = np.frombuffer(bytes(self.buffer), dtype=np.uint8)
            img = cv2.imdecode(jpg, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.warning("이미지 디코딩 실패")
                return
            
            if self.qr_detector is None:
                logger.error("QR 코드 감지기가 초기화되지 않았습니다.")
                return
            
            # QR 코드 인식
            qr_data, points, _ = self.qr_detector.detectAndDecode(img)
            
            if qr_data and qr_data != self.last_sent_data:
                logger.info(f"QR 코드 인식됨: {qr_data}")
                
                # 콜백 함수 호출하여 바코드 데이터 전달
                if self.callback:
                    try:
                        self.callback(qr_data)
                        logger.debug(f"바코드 데이터 콜백 처리 성공: {qr_data}")
                    except Exception as e:
                        logger.error(f"바코드 콜백 처리 중 오류: {str(e)}")
                
                self.last_sent_data = qr_data
            elif qr_data:
                logger.debug(f"이미 처리된 QR 코드 무시: {qr_data}")
        
        except Exception as e:
            logger.error(f"이미지 처리 중 오류: {str(e)}")