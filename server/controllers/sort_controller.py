# sort_controller.py
import logging
import time
import threading
from typing import Dict, Tuple, Optional, Any
from datetime import datetime  
from utils.protocol import *  
from db import product_item_repo

logger = logging.getLogger(__name__)

# 자동 정지 타이머 시간 (초)
AUTO_STOP_TIMEOUT = 7.0

class SortController:
    """분류기 컨트롤러 - 통합 통신 프로토콜 적용"""
    
    # 기본 상수 정의
    STATE_STOPPED = "stopped"
    STATE_RUNNING = "running"
    STATE_PAUSED = "pause"  

    def __init__(self, socketio: Any, tcp_handler, db_helper=None):
        """분류기 컨트롤러 초기화"""
        self.socketio = socketio
        self.tcp_handler = tcp_handler
        self.db_helper = db_helper  # DB 헬퍼 설정
        self.logger = logger        # logger 속성 추가
        self.pending_barcodes = {}  # 분류 중인 바코드 정보
        # 상태 정보 초기화
        self.state = self.STATE_STOPPED
        self.motor_active = False
        self.items_waiting = 0
        self.items_processed = 0
        self.sort_counts = {"A": 0, "B": 0, "C": 0, "E": 0}
        self.has_db_access = product_item_repo is not None
        if not self.has_db_access:
            logger.warning("DB 리포지토리에 접근할 수 없습니다. 바코드 데이터 저장이 비활성화됩니다.")

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
        self.tcp_handler.register_device_handler('S', 'C', self.handle_command) 
        
        # 매핑된 디바이스 ID로도 등록
        self.tcp_handler.register_device_handler('sort_controller', 'E', self.handle_event)
        self.tcp_handler.register_device_handler('sort_controller', 'R', self.handle_response)
        self.tcp_handler.register_device_handler('sort_controller', 'X', self.handle_error)
        self.tcp_handler.register_device_handler('sort_controller', 'C', self.handle_command) 
        
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
        
        # IR 센서 이벤트 직접 확인 (parse_message 사용하지 않음)
        if content.startswith(SORT_EVENT_IR):
            # IR 센서 이벤트
            self._handle_ir_sensor(content)
        elif content.startswith(SORT_EVENT_BARCODE):
            # 바코드 인식 이벤트
            self._handle_barcode(content)
        elif content.startswith(SORT_EVENT_SORTED):
            # 분류 완료 이벤트
            self._handle_sort_complete(content)
        else:
            # 메시지 구조가 예상과 다른 경우에만 파싱 시도
            _, _, payload = parse_message(content)
            if payload:
                if payload.startswith(SORT_EVENT_IR):
                    self._handle_ir_sensor(payload)
                elif payload.startswith(SORT_EVENT_BARCODE):
                    self._handle_barcode(payload)
                elif payload.startswith(SORT_EVENT_SORTED):
                    self._handle_sort_complete(payload)
                else:
                    logger.debug(f"처리되지 않은 이벤트: {content}")
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
            self._emit_standardized_event("sort", "error", {
                "error_code": error_code,
                "error_message": f"분류기 오류: {error_code}"
            })
    def _save_completed_item_to_db(self, zone: str, item_info: dict) -> bool:
        """분류 완료된 아이템을 DB에 저장
        
        Args:
            zone: 분류된 존 (A, B, C, E)
            item_info: 바코드 파싱 정보
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # DB 접근 가능 여부 확인
            if not hasattr(self, 'db_helper') or not self.db_helper:
                self.logger.warning("DB 연결 없음 - 아이템 저장 무시됨")
                return False
                
            from db import product_item_repo
            
            # 필요한 정보 추출
            product_id = item_info.get('item_code', '00')
            expiry_date = item_info.get('expiry_date')
            original_barcode = item_info.get('original_barcode', '')
            
            # 현재 시간을 입고 시간으로 사용
            entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # DB에 저장
            item_id = product_item_repo.add_item(
                product_id=product_id,
                warehouse_id=zone,
                exp_date=expiry_date,
                entry_time=entry_time
            )
            
            if item_id:
                self.logger.info(f"제품 정보 저장 완료: ID={item_id}, 창고={zone}, 바코드={original_barcode}")
                
                # 분류 로그에 추가
                self._add_sort_log({
                    "item_id": item_id,
                    "barcode": original_barcode,
                    "warehouse_id": zone,
                    "product_id": product_id,
                    "expiry_date": expiry_date,
                    "timestamp": datetime.now().isoformat()
                })
                
                return True
            else:
                self.logger.error(f"제품 정보 저장 실패: 창고={zone}, 바코드={original_barcode}")
                return False
                
        except Exception as e:
            self.logger.error(f"분류 완료 아이템 저장 중 오류: {str(e)}")
            return False
        
    def _handle_ir_sensor(self, payload):
        """IR 센서 이벤트 처리"""
        try:
            # 원본 페이로드 로깅
            logger.debug(f"IR 센서 원본 메시지: {payload}")
            
            # ir1 형식에서 1만 추출 (숫자 부분만 가져옴)
            detected = 0
            for char in payload:
                if char.isdigit():
                    detected = int(char)
                    break
            
            if detected == 1:
                logger.info("입구 IR 센서 물품 감지")
                
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
            # 존 추출 (예: ssA -> A)
            zone = payload[2:3] if len(payload) > 2 else None
            
            # 분류 존 체크
            if zone not in ["A", "B", "C", "E"]:
                logger.warning(f"알 수 없는 분류 존: {zone}, 'E'로 처리")
                zone = "E"
            
            # 대기 물품 수가 0보다 큰 경우에만 처리
            if self.items_waiting > 0:
                # 1. 해당 존에 대한 대기 바코드 정보가 있는지 확인
                if zone in self.pending_barcodes:
                    # 바코드 정보 가져오기
                    item_info = self.pending_barcodes[zone]
                    
                    # 2. DB에 상품 정보 저장
                    self._save_completed_item_to_db(zone, item_info)
                    
                    # 임시 저장소에서 처리된 바코드 제거
                    del self.pending_barcodes[zone]
                else:
                    self.logger.warning(f"분류 완료 이벤트 (존: {zone}) 수신했으나 대기 바코드 정보 없음")
                
                # 3. 대기 물품 감소
                self.items_waiting -= 1
                # 4. 처리 물품 증가
                self.items_processed += 1
                # 5. 분류 카운트 증가
                self.sort_counts[zone] += 1
                
                self.logger.info(f"물품 분류 완료: 존 {zone}, 남은 대기 물품: {self.items_waiting}")
                
                # 상태 업데이트 이벤트 발송
                self._emit_status_update()
                
                # 자동 정지 타이머 재설정
                self._reset_auto_stop_timer()
            else:
                self.logger.warning("분류 완료 이벤트 수신했으나 대기 물품 수가 0")
                
        except Exception as e:
            self.logger.error(f"분류 완료 이벤트 처리 오류: {str(e)}")
    
    def _process_sort_controller_message(self, message: str) -> None:
        """분류기 메시지 처리"""
        try:
            # 기본 검증
            if len(message) < 3 or not message.startswith("S"):
                return
                
            msg_type = message[1]
            raw_barcode = message[2:].strip()
            
            # 바코드 처리
            if msg_type == "E" and raw_barcode.startswith("bc"):
                barcode = raw_barcode[2:]
                # 바코드 파싱 (1자리 카테고리)
                if len(barcode) >= 1:
                    category = barcode[0]
                    
                # 분류 명령 전송
                self._send_sort_command(category)
                
        except Exception as e:
            logger.error(f"메시지 처리 오류: {str(e)}")

    def _handle_barcode(self, barcode_data):
        try:
            # 바코드 형식 확인 (bc 접두사가 없으면 추가)
            if not barcode_data.startswith("bc"):
                barcode_data = f"bc{barcode_data}"

            # 바코드 추출
            barcode = barcode_data[2:] if barcode_data.startswith("bc") else barcode_data
            
            # 바코드 파싱 - 프로토콜 모듈 사용
            from utils.protocol import parse_barcode
            item_info = parse_barcode(barcode)
            
            if item_info:
                category = item_info.get('category', 'E')
                
                # 임시 저장소에 바코드 정보 보관
                # 현재 시간도 함께 저장 (나중에 일치 여부 확인을 위해)
                item_info['timestamp'] = time.time()
                item_info['original_barcode'] = barcode
                self.pending_barcodes[category] = item_info
                
                self.logger.info(f"바코드 파싱 결과: {item_info}, 분류 카테고리: {category}")
            else:
                self.logger.warning(f"바코드 파싱 실패: {barcode}")
                category = "E"  # 오류 시 E 구역으로 분류
            
            # 분류 명령 전송 로직 (기존 코드)
            message = f"SE{barcode_data}\n"
            self._process_sort_controller_message(message)
            
        except Exception as e:
            self.logger.error(f"바코드 처리 중 오류 발생: {str(e)}")
    
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
        logger.debug(f"클라이언트로 전송하는 상태: '{self.state}'")
        # 표준화된 이벤트 발송
        self._emit_standardized_event("sort", "status_update", status_data)
    
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
        if self.state == self.STATE_STOPPED or self.state == self.STATE_PAUSED:
            self.state = self.STATE_RUNNING
            self.motor_active = True
            
            # 상태 업데이트 이벤트 발송
            self._emit_status_update()
            
            # 프로토콜 형식으로 시작 명령 전송
            command = create_message(DEVICE_SORTER, MSG_COMMAND, SORT_CMD_START)
            
            # 디버그 로그 추가 - 문제 확인용
            logger.info(f"분류기 시작 명령 생성: {command.strip()}")
            
            # 분류기 디바이스 연결 확인
            success = self.tcp_handler.send_message(DEVICE_SORTER, command)
            
            # 연결되지 않았다면 클라이언트 연결 리스트 출력
            if success:
                logger.info("분류기 시작 명령 전송 성공")
            else:
                logger.error("분류기 시작 명령 전송 실패")
            
            return success
        else:
            logger.debug("분류기가 이미 작동 중입니다.")
            return True
    
    def pause_sorter(self):
        """분류기를 일시정지 상태로 설정"""
        # running 상태에서만 일시정지 가능
        if self.state == self.STATE_RUNNING:
            # 자동 정지 타이머 취소 (일시정지 상태에서는 타임아웃 방지)
            self._cancel_auto_stop_timer()
            
            # 프로토콜 형식으로 일시정지 명령 전송
            command = create_message(DEVICE_SORTER, MSG_COMMAND, SORT_CMD_PAUSE)  
            
            # 명령 전송
            success = self.tcp_handler.send_message(DEVICE_SORTER, command)
            
            if success:
                logger.info("분류기 일시정지 명령 전송 성공")
                # 명령 성공 시에만 상태 변경
                self.state = self.STATE_PAUSED
                self.motor_active = False
                
                # 상태 업데이트 이벤트 발송
                self._emit_status_update()
            else:
                logger.error("분류기 일시정지 명령 전송 실패")
            
            return success
        elif self.state == self.STATE_PAUSED:
            logger.debug("분류기가 이미 일시정지 상태입니다.")
            return True
        else:
            logger.debug("작동 중인 분류기만 일시정지할 수 있습니다.")
            return False
            
    def stop_sorter(self):
        """분류기를 정지 상태로 설정"""
        if self.state == self.STATE_RUNNING or self.state == self.STATE_PAUSED:
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