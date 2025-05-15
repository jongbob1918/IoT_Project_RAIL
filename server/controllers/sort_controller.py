import logging
import time
import threading
from typing import Dict, Tuple, Optional, Any
from datetime import datetime
from utils.protocol import *  # 프로토콜 정의 임포트

logger = logging.getLogger(__name__)

# 자동 정지 타이머 시간 (초)
AUTO_STOP_TIMEOUT = 7.0

class SortController:
    """분류기 컨트롤러 - 통합 통신 프로토콜 적용"""
    
    # 기본 상수 정의
    STATE_STOPPED = "stopped"
    STATE_RUNNING = "running"
    
    def __init__(self, socketio: Any, tcp_handler, db_helper=None):
        """분류기 컨트롤러 초기화"""
        self.socketio = socketio
        self.tcp_handler = tcp_handler
        self.db_helper = db_helper  # DB 헬퍼 설정
        
        # 상태 정보 초기화
        self.state = self.STATE_STOPPED
        self.motor_active = False
        self.items_waiting = 0
        self.items_processed = 0
        self.sort_counts = {"A": 0, "B": 0, "C": 0, "E": 0}
        
        # 최근 분류 로그 (최대 20개)
        self.sort_logs = []
        
        # 바코드 처리 상태
        self.processing_barcode = False
        
        # 자동 정지 타이머
        self.auto_stop_timer = None
        
        # 이벤트 핸들러 등록
        self._register_handlers()
        
        logger.info("분류기 컨트롤러 초기화 완료")

    def _register_handlers(self):
        """TCP 핸들러에 이벤트 핸들러 등록"""
        # 원본 프로토콜 형식으로 등록 (E, C, R, X)
        self.tcp_handler.register_device_handler('S', 'E', self.handle_event)
        self.tcp_handler.register_device_handler('S', 'R', self.handle_response)
        self.tcp_handler.register_device_handler('S', 'X', self.handle_error)
        self.tcp_handler.register_device_handler('S', 'C', self.handle_command)  # 명령 핸들러 추가
        
        # 매핑된 디바이스 ID로도 등록
        self.tcp_handler.register_device_handler('sort_controller', 'E', self.handle_event)
        self.tcp_handler.register_device_handler('sort_controller', 'R', self.handle_response)
        self.tcp_handler.register_device_handler('sort_controller', 'X', self.handle_error)
        self.tcp_handler.register_device_handler('sort_controller', 'C', self.handle_command)  # 명령 핸들러 추가
        
        # 이전 방식 호환성 유지
        self.tcp_handler.register_device_handler('sort_controller', 'evt', self.handle_event)
        self.tcp_handler.register_device_handler('sort_controller', 'res', self.handle_response)
        self.tcp_handler.register_device_handler('sort_controller', 'err', self.handle_error)
    
    def handle_event(self, message):
        """분류기 이벤트 처리"""
        if 'content' not in message:
            return
            
        content = message['content']
        # 로그 추가
        logger.debug(f"수신된 이벤트: {content}")
        
        # 직접 처리: 바코드 데이터인 경우
        if content.startswith('bc'):
            self._handle_barcode(content)
            return
            
        # 표준 프로토콜로 파싱
        _, _, payload = parse_message(content)
        
        if not payload:
            return
            
        # 이벤트 타입에 따른 처리
        if payload.startswith(SORT_EVENT_IR):
            # IR 센서 이벤트
            self._handle_ir_sensor(payload)
        elif payload.startswith(SORT_EVENT_BARCODE):
            # 바코드 인식 이벤트
            self._handle_barcode(payload)
        elif payload.startswith(SORT_EVENT_SORTED):
            # 분류 완료 이벤트
            self._handle_sort_complete(payload)
        else:
            logger.debug(f"처리되지 않은 이벤트: {content}")
    
    def handle_response(self, message):
        """응답 처리"""
        if 'content' in message:
            content = message['content']
            _, _, payload = parse_message(content)
            
            if payload == RESPONSE_OK:
                logger.debug("명령 실행 성공 응답 수신")
            else:
                logger.debug(f"알 수 없는 응답: {content}")
    
    def handle_command(self, message):
        """명령 메시지 처리 - 'C' 타입 메시지"""
        if 'content' not in message:
            return
        
        content = message['content']
        logger.debug(f"분류기 명령 수신: {content}")
        
        # SC 접두사 제거 (있는 경우)
        if content.startswith('SC'):
            content = content[2:]
        
        # 명령 타입별 처리
        if content.startswith('st'):
            # 시작 명령
            self.start_sorter()
            return True
        
        elif content.startswith('sp'):
            # 정지 명령
            self.stop_sorter()
            return True
        
        elif content.startswith('ps'):
            # 일시정지 명령
            if hasattr(self, 'pause_sorter'):
                self.pause_sorter()
                return True
        
        elif content.startswith('so') and len(content) >= 3:
            # 분류 명령 - 'soA', 'soB', 'soC'
            zone = content[2:3]
            self._send_sort_command(zone)
            return True
        
        # 이 외의 경우 로그로 기록
        logger.debug(f"처리되지 않은 명령: {content}")
        return False
    
    def handle_error(self, message):
        """오류 처리"""
        if 'content' in message:
            content = message['content']
            _, _, payload = parse_message(content)
            
            error_code = payload
            logger.warning(f"분류기 오류: {error_code}")
            
            # 소켓 이벤트 발송
            self._emit_standardized_event("sorter", "error", {
                "error_code": error_code,
                "error_message": f"분류기 오류: {error_code}"
            })
    
    def _handle_ir_sensor(self, payload):
        """IR 센서 이벤트 처리"""
        try:
            # 값 추출 (ir1 - 1=감지됨)
            detected = int(payload[2:]) if len(payload) > 2 else 0
            
            if detected == 1:
                logger.info("입구 IR 센서 물품 감지")
                
                # 분류기가 정지 상태인 경우 작동 시작
                if self.state == self.STATE_STOPPED:
                    self.state = self.STATE_RUNNING
                    self.motor_active = True
                
                # 대기 물품 수 증가
                self.items_waiting += 1
                
                # 자동 정지 타이머 초기화
                self._reset_auto_stop_timer()
                
                # 상태 업데이트 이벤트 발송
                self._emit_status_update()
        except ValueError:
            logger.error(f"IR 센서 값 파싱 오류: {payload}")
    
    def _handle_sort_complete(self, payload):
        """분류 완료 이벤트 처리"""
        try:
            # 기존 코드...
            
            # DB에 분류 완료 로그 저장
            if hasattr(self, 'db_helper') and self.db_helper and zone:
                self.db_helper.update_sort_result(zone)
                
                # 최근 분류된 바코드가 있다면 그 정보도 함께 업데이트
                if self.sort_logs and len(self.sort_logs) > 0:
                    last_item = self.sort_logs[0]
                    barcode = last_item.get("barcode")
                    if barcode:
                        self.db_helper.update_item_location(barcode, zone)
            
            # 이하 기존 코드...
        except Exception as e:
            logger.error(f"분류 완료 이벤트 처리 오류: {str(e)}")
        
    def _handle_sort_complete(self, payload):
        """분류 완료 이벤트 처리"""
        try:
            # 예: ss1 형식 (zone 포함)
            zone = payload[2:3] if len(payload) > 2 else None
            
            # 분류 존 체크
            if zone not in ["A", "B", "C", "E"]:
                logger.warning(f"알 수 없는 분류 존: {zone}, 'E'로 처리")
                zone = "E"
                
            # 대기 물품 수가 0보다 큰 경우에만 처리
            if self.items_waiting > 0:
                # 대기 물품 감소
                self.items_waiting -= 1
                # 처리 물품 증가
                self.items_processed += 1
                # 분류 카운트 증가
                self.sort_counts[zone] += 1
                
                logger.info(f"물품 분류 완료: 존 {zone}, 남은 대기 물품: {self.items_waiting}")
                
                # 상태 업데이트 이벤트 발송
                self._emit_status_update()
                
                # 자동 정지 타이머 재설정
                self._reset_auto_stop_timer()
            else:
                logger.warning("분류 완료 이벤트 수신했으나 대기 물품 수가 0")
                
        except Exception as e:
            logger.error(f"분류 완료 이벤트 처리 오류: {str(e)}")
    
    def _handle_barcode(self, payload):
        """바코드 이벤트 처리"""
        # 처리 중 표시
        if self.processing_barcode:
            logger.warning("이미 처리 중인 바코드가 있음")
            return
            
        self.processing_barcode = True
        
        try:
            # 바코드 데이터 추출 (bc 이후의 문자열)
            barcode_data = payload[2:] if len(payload) > 2 else ""
            
            if not barcode_data:
                logger.warning("바코드 데이터 없음")
                self._send_sort_command("E")  # 오류 분류
                return
            
            # 바코드 파싱
            item_info = parse_barcode(barcode_data)
            
            if not item_info:
                logger.error(f"바코드 파싱 실패: {barcode_data}")
                self._send_sort_command("E")  # 오류 분류
                return
            
            # 타임스탬프 추가
            item_info["timestamp"] = time.time()
            # 분류 명령 전송
            self._send_sort_command(item_info["category"])
            
            # 로그에 추가
            self._add_sort_log(item_info)
            
            # 바코드 인식 이벤트 발송
            self.socketio.emit('barcode_scanned', item_info, namespace="/ws")
            
            # 표준 형식 이벤트도 추가로 발송
            self._emit_standardized_event("sorter", "barcode_scanned", item_info)
            
            # DB에 바코드 스캔 로그만 저장 (선반 할당 없이)
            if hasattr(self, 'db_helper') and self.db_helper:
                self.db_helper.insert_barcode_scan(
                    item_info["barcode"], 
                    item_info["category"],
                    item_info.get("item_code"),
                    item_info.get("expiry_date")
                )
            
        except Exception as e:
            logger.error(f"바코드 처리 오류: {str(e)}")
            self._send_sort_command("E")  # 오류 분류
        finally:
            self.processing_barcode = False
    
    def _send_sort_command(self, zone):
        """분류 명령 전송"""
        # 프로토콜 형식으로 메시지 생성
        command = create_message(DEVICE_SORTER, MSG_COMMAND, f"{SORT_CMD_SORT}{zone}")
        
        success = self.tcp_handler.send_message(DEVICE_SORTER, command)
        if not success:
            logger.error(f"분류 명령 전송 실패: {zone}")
        
        return success
    
    def _add_sort_log(self, item_info):
        """분류 로그 추가"""
        # 타임스탬프 추가
        if "timestamp" not in item_info:
            item_info["timestamp"] = time.time()
        
        # 로그 앞에 추가
        self.sort_logs.insert(0, item_info)
        
        # 최대 10개 유지
        if len(self.sort_logs) > 10:
            self.sort_logs = self.sort_logs[:10]
    
    def _emit_standardized_event(self, category, action, payload):
        """표준화된 소켓 이벤트 발송"""
        if not self.socketio:
            return
            
        event_data = {
            "type": "event",
            "category": category,
            "action": action,
            "payload": payload,
            "timestamp": int(time.time())
        }
        
        self.socketio.emit("event", event_data, namespace="/ws")
    
    def _emit_status_update(self):
        """상태 업데이트 이벤트 발송"""
        status_data = {
            "state": self.state,
            "motor_active": self.motor_active,
            "items_waiting": self.items_waiting,
            "items_processed": self.items_processed,
            "sort_counts": self.sort_counts,
            "last_updated": time.time()
        }
        
        # 표준화된 이벤트 발송
        self._emit_standardized_event("sorter", "status_update", {
            "is_running": self.state == self.STATE_RUNNING,
            "items_waiting": self.items_waiting,
            "items_processed": self.items_processed,
            "sort_counts": self.sort_counts
        })
    
    def _reset_auto_stop_timer(self):
        """자동 정지 타이머 초기화"""
        # 기존 타이머 취소
        self._cancel_auto_stop_timer()
        
        # 작동 중인 경우에만 타이머 설정
        if self.state == self.STATE_RUNNING:
            self.auto_stop_timer = threading.Timer(AUTO_STOP_TIMEOUT, self._auto_stop_timeout)
            self.auto_stop_timer.daemon = True
            self.auto_stop_timer.start()
    
    def _cancel_auto_stop_timer(self):
        """자동 정지 타이머 취소"""
        if self.auto_stop_timer:
            self.auto_stop_timer.cancel()
            self.auto_stop_timer = None
    
    def _auto_stop_timeout(self):
        """자동 정지 타임아웃 처리"""
        # 작동 중이고 대기 물품이 없는 경우에만 처리
        if self.state == self.STATE_RUNNING and self.items_waiting == 0:
            logger.info("자동 정지: 물품 없음")
            
            # 정지 명령 전송
            command = create_message(DEVICE_SORTER, MSG_COMMAND, SORT_CMD_STOP)
            self.tcp_handler.send_message(DEVICE_SORTER, command)
            
            # 상태 업데이트
            self.state = self.STATE_STOPPED
            self.motor_active = False
            
            # 상태 업데이트 이벤트 발송
            self._emit_status_update()
    
    def get_status(self):
        """현재 상태 조회"""
        return {
            "status": {
                "state": self.state,
                "motor_active": self.motor_active,
                "items_waiting": self.items_waiting,
                "items_processed": self.items_processed,
                "sort_counts": self.sort_counts,
                "last_updated": time.time()
            },
            "logs": self.sort_logs[:5]  # 최근 5개 로그만 반환
        }
    
    def start_sorter(self):
        """분류기를 시작 상태로 설정"""
        if self.state == self.STATE_STOPPED:
            self.state = self.STATE_RUNNING
            self.motor_active = True
            
            # 상태 업데이트 이벤트 발송
            self._emit_status_update()
            
            # 프로토콜 형식으로 시작 명령 전송
            command = create_message(DEVICE_SORTER, MSG_COMMAND, SORT_CMD_START)
            
            # 디버그 로그 추가 - 문제 확인용
            logger.info(f"분류기 시작 명령 생성: {command.strip()}")
            
            # 분류기 디바이스 연결 확인
            is_connected = self.tcp_handler.is_device_connected(DEVICE_SORTER)
            logger.info(f"분류기 디바이스 연결 상태: {is_connected}")
            
            # 연결되지 않았다면 클라이언트 연결 리스트 출력
            if not is_connected:
                connected_devices = self.tcp_handler.get_connected_devices()
                logger.info(f"현재 연결된 디바이스 목록: {connected_devices}")
                logger.warning("분류기 디바이스가 연결되어 있지 않습니다. 하드웨어 연결을 확인하세요.")
            
            # 명령 전송
            success = self.tcp_handler.send_message(DEVICE_SORTER, command)
            
            if success:
                logger.info("분류기 시작 명령 전송 성공")
            else:
                logger.error("분류기 시작 명령 전송 실패")
            
            return success
        else:
            logger.debug("분류기가 이미 작동 중입니다.")
            return True
    
    def stop_sorter(self):
        """분류기를 정지 상태로 설정"""
        if self.state == self.STATE_RUNNING:
            self.state = self.STATE_STOPPED
            self.motor_active = False
            
            # 상태 업데이트 이벤트 발송
            self._emit_status_update()
            
            # 프로토콜 형식으로 정지 명령 전송
            command = create_message(DEVICE_SORTER, MSG_COMMAND, SORT_CMD_STOP)
            
            # 명령 전송
            success = self.tcp_handler.send_message(DEVICE_SORTER, command)
            
            if success:
                logger.info("분류기 정지 명령 전송 성공")
            else:
                logger.error("분류기 정지 명령 전송 실패")
            
            return success
        else:
            logger.debug("분류기가 이미 정지 상태입니다.")
            return True
    
    