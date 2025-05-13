# server/controllers/sort_controller.py
import logging
import time
from typing import Dict
from flask_socketio import SocketIO
from utils.tcp_handler import TCPHandler
from .barcode_parser import BarcodeParser

# ==== 분류기 컨트롤러 클래스 ====
class SortController:
    def __init__(self, socketio: SocketIO, tcp_handler: TCPHandler):
        """분류기 컨트롤러 초기화"""
        self.socketio = socketio
        self.tcp_handler = tcp_handler
        self.logger = logging.getLogger('sort_controller')
        
        # 바코드 파서 초기화
        self.barcode_parser = BarcodeParser()
        
        # 분류기 상태 - 항상 작동 중으로 설정
        self.status = {
            "state": "running",           # 항상 작동 중 상태
            "motor_active": True,         # 모터 작동 중
            "items_waiting": 0,           # 대기 물품 수
            "items_processed": 0,         # 처리된 물품 수
            "sort_counts": {              # 분류별 물품 수
                "A": 0,  # 냉동
                "B": 0,  # 냉장
                "C": 0,  # 상온
                "E": 0   # 오류물품
            },
            "last_updated": time.time()   # 마지막 업데이트 시간
        }
        
        # 분류 로그 (최근 항목 10개)
        self.sort_logs = []
        
        # 이벤트 핸들러 등록
        self._register_handlers()
        
        self.logger.info("분류기 컨트롤러 초기화 완료 - 자동 작동 모드")
    
    # ==== 이벤트 핸들러 등록 ====
    def _register_handlers(self):
        """TCP 핸들러에 이벤트 핸들러 등록"""
        # 분류기 이벤트 핸들러 - 매핑된 이름 'sort_controller' 사용
        self.tcp_handler.register_device_handler('sort_controller', 'evt', self._handle_event)
        # 분류기 응답 핸들러
        self.tcp_handler.register_device_handler('sort_controller', 'res', self._handle_response)
        # 분류기 오류 핸들러
        self.tcp_handler.register_device_handler('sort_controller', 'err', self._handle_error)
        
        # 바코드 이벤트를 위한 별도 등록 ('S' 사용)
        self.tcp_handler.register_device_handler('S', 'evt', self._handle_event)
        self.tcp_handler.register_device_handler('S', 'res', self._handle_response)
        self.tcp_handler.register_device_handler('S', 'err', self._handle_error)
    
    # ==== 이벤트 처리 ====
    def _handle_event(self, message: Dict):
        """분류기 이벤트 처리"""
        content = message.get('content', '')
        
        # 이벤트 타입별 처리
        if content.startswith('ir'):  # IR 센서 감지
            self._handle_ir_event(content)
        elif content.startswith('bc'):  # 바코드 인식
            self._handle_barcode_event(content)
        elif content.startswith('ss'):  # 분류 완료
            self._handle_sort_complete_event(content)
        else:
            self.logger.warning(f"알 수 없는 이벤트: {content}")
    
    # ==== IR 센서 이벤트 처리 ====
    def _handle_ir_event(self, content: str):
        """IR 센서 감지 이벤트 처리"""
        try:
            # 값 추출 (ir1 - 1=감지됨)
            detected = int(content[2:]) if len(content) > 2 else 0
            
            if detected == 1:
                self.logger.info("입구 IR 센서 물품 감지")
                
                # 대기 물품 수 증가
                self.status["items_waiting"] += 1
                self.status["last_updated"] = time.time()
                
                # 상태 변경 이벤트 발송
                self._emit_status_update()
        except ValueError:
            self.logger.error(f"IR 센서 값 파싱 오류: {content}")
    
    # ==== 바코드 이벤트 처리 ====
    def _handle_barcode_event(self, content: str):
        """바코드 인식 이벤트 처리"""
        # 바코드 데이터 추출 (bc 이후, 예: bcA12123456)
        barcode_data = content[2:] if len(content) > 2 else ""
        
        if not barcode_data:
            self.logger.warning("바코드 데이터 없음")
            return
            
        try:
            # BarcodeParser를 사용하여 바코드 파싱
            success, item_info = self.barcode_parser.parse(barcode_data)
            
            if not success:
                self.logger.error(f"바코드 파싱 실패: {barcode_data}")
                # 오류 발생 시 오류물품(E)으로 분류
                self._send_sort_command("E")
                return
                
            # 타임스탬프 추가
            item_info["timestamp"] = time.time()
            
            # 분류 명령 전송 - 항상 파싱된 category 사용
            self._send_sort_command(item_info["category"])
            
            # 로그에 추가
            self.add_sort_log(item_info)
            
            # 바코드 인식 이벤트 발송
            self.socketio.emit('barcode_scanned', item_info)
            
        except Exception as e:
            self.logger.error(f"바코드 처리 중 오류: {e}")
            # 오류 발생 시 오류물품(E)으로 분류
            self._send_sort_command("E")
            
            # 오류 이벤트 발송
            self.socketio.emit('barcode_error', {
                "error": str(e),
                "barcode": barcode_data
            })
    
    # ==== 분류 완료 이벤트 처리 ====
    def _handle_sort_complete_event(self, content: str):
        """분류 완료 이벤트 처리"""
        # 분류 구역 추출 (ssA에서 A)
        zone = content[2] if len(content) > 2 else None
        
        if not zone:
            self.logger.warning("분류 구역 정보 없음")
            return
        
        self.logger.info(f"분류 완료: {zone} 구역")
        
        # 대기 물품 수 감소
        if self.status["items_waiting"] > 0:
            self.status["items_waiting"] -= 1
        
        # 처리 물품 수 증가
        self.status["items_processed"] += 1
        
        # 구역별 카운트 증가
        if zone in self.status["sort_counts"]:
            self.status["sort_counts"][zone] += 1
        
        self.status["last_updated"] = time.time()
        
        # 상태 변경 이벤트 발송
        self._emit_status_update()
    
    # ==== 응답 처리 ====
    def _handle_response(self, message: Dict):
        """분류기 응답 처리"""
        content = message.get('content', '')
        
        if content.startswith('ok'):
            self.logger.debug("명령 성공 응답 수신")
        else:
            self.logger.warning(f"알 수 없는 응답: {content}")
    
    # ==== 오류 처리 ====
    def _handle_error(self, message: Dict):
        """분류기 오류 처리"""
        content = message.get('content', '')
        
        # 오류 코드 추출
        error_code = content[1:] if len(content) > 1 else "unknown"
        
        # 오류 메시지 매핑
        error_messages = {
            "e1": "통신 오류",
            "e2": "센서 오류",
            "unknown": "알 수 없는 오류"
        }
        
        error_message = error_messages.get(error_code, f"오류 코드: {error_code}")
        self.logger.error(f"분류기 오류: {error_message}")
        
        # 오류 이벤트 발송
        self.socketio.emit('sorter_error', {
            "error_code": error_code,
            "error_message": error_message
        })
    
    # ==== 상태 업데이트 이벤트 발송 ====
    def _emit_status_update(self):
        """현재 상태 업데이트 이벤트 발송"""
        self.socketio.emit('sort_status_update', self.status)
    
    # ==== 분류 로그에 추가 ====
    def add_sort_log(self, item_info: Dict):
        """분류 로그에 항목 추가 (최대 10개 유지)"""
        # 타임스탬프 추가
        log_entry = item_info.copy()
        if "timestamp" not in log_entry:
            log_entry["timestamp"] = time.time()
        
        # 로그 앞에 추가
        self.sort_logs.insert(0, log_entry)
        
        # 최대 개수(10개) 유지
        if len(self.sort_logs) > 10:
            self.sort_logs = self.sort_logs[:10]
    
    # ==== 분류 명령 전송 ====
    def _send_sort_command(self, zone: str):
        """특정 구역으로 분류 명령 전송"""
        # SCsoA\n - 분류기(S) 명령(C) 분류(so) A구역으로
        command = f"SCso{zone}"
        
        # 두 가지 방식으로 시도 - 원래 'S'로도 시도하고 매핑된 'sort_controller'로도 시도
        success = self.tcp_handler.send_message("sort_controller", command)
        if not success:
            # 'sort_controller'로 실패하면 'S'로 시도
            success = self.tcp_handler.send_message("S", command)
            if not success:
                self.logger.error(f"분류 명령 전송 실패: {zone}")
        
        return success
    
    # ==== 상태 조회 ====
    def get_status(self):
        """현재 분류기 상태 조회"""
        return {
            "status": self.status,
            "logs": self.sort_logs[:5]  # 최근 5개 로그만 반환
        }
        
    # ==== SocketIO 이벤트 발송 ====
    def _emit_socketio_event(self, event_name: str, data: Dict):
        """Socket.IO 이벤트를 발송합니다"""
        if self.socketio:
            self.socketio.emit(event_name, data)
    
    # ==== 상태 업데이트 ====
    def _update_status(self):
        """상태 업데이트 및 이벤트 발송"""
        self._emit_status_update()