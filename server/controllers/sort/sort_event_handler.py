import logging
import threading
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ==== 분류기 이벤트 처리 클래스 ====
class SortEventHandler:
    # ==== 이벤트 핸들러 초기화 ====
    def __init__(self, controller, tcp_handler, shelf_manager):
        self.controller = controller
        self.tcp_handler = tcp_handler
        self.shelf_manager = shelf_manager
        
        # 바코드 처리중 상태
        self.processing_barcode = False
        
        # 자동 종료 타이머
        self.auto_stop_timer: Optional[threading.Timer] = None
        
        # 분류 정보
        self.category_map = {
            "1": "A",  # 냉동
            "2": "B",  # 냉장
            "3": "C",  # 상온
            "0": "E"   # 오류물품
        }
    # ==== 이벤트 메시지 처리 ====
    def handle_event(self, message: dict):
        try:
            # 메시지 콘텐츠 확인
            content = message.get('content', '')
            
            # 이벤트 타입별 처리 (ir, bc, ss, as 등)
            if content.startswith('ir'):
                # IR 센서 이벤트
                self._handle_ir_sensor_event(content)
            elif content.startswith('bc'):
                # 바코드 인식 이벤트
                self._handle_barcode_event(content)
            elif content.startswith('ss'):
                # 분류 완료 이벤트
                self._handle_sort_complete_event(content)
            elif content.startswith('as'):
                # 자동 정지 이벤트
                self._handle_auto_stop_event(content)
            else:
                logger.warning(f"알 수 없는 이벤트 콘텐츠: {content}")
        
        except Exception as e:
            logger.error(f"분류기 이벤트 처리 중 오류: {str(e)}")
    
    # ==== 응답 메시지 처리 ====
    def handle_response(self, message: dict):
        try:
            # 응답 콘텐츠 확인
            content = message.get('content', '')
            
            # 응답 타입별 처리
            if content.startswith('ok'):
                # 성공 응답
                self._handle_ok_response(content)
            else:
                logger.warning(f"알 수 없는 응답 콘텐츠: {content}")
        
        except Exception as e:
            logger.error(f"분류기 응답 처리 중 오류: {str(e)}")
    
    # ==== 오류 메시지 처리 ====
    def handle_error(self, message: dict):
        try:
            # 오류 콘텐츠 확인
            content = message.get('content', '')
            
            # 오류 코드 추출
            error_code = content[1:] if len(content) > 1 else "unknown"
            
            logger.warning(f"분류기 오류: {error_code}")
            
            # 오류 이벤트 발송
            self.controller._emit_socketio_event("sorter_error", {
                "error_code": error_code,
                "error_message": f"분류기 오류: {error_code}"
            })
        
        except Exception as e:
            logger.error(f"분류기 오류 처리 중 오류: {str(e)}")
    
    # ==== IR 센서 이벤트 처리 ====
    def _handle_ir_sensor_event(self, content: str):
        """IR 센서 감지 이벤트를 처리합니다."""
        # 값 추출 (ir1 - 1=감지됨)
        try:
            detected = int(content[2:]) if len(content) > 2 else 0
            
            if detected == 1:
                logger.info("입구 IR 센서 물품 감지")
                
                # 분류기 상태가 정지 상태인 경우 작동 시작
                if self.controller.status_manager.state == "stopped":
                    # 상태 업데이트
                    self.controller.status_manager.state = "running"
                    self.controller.status_manager.motor_active = True
                    
                    # 상태 업데이트 이벤트 발송
                    self.controller._update_status()
                
                # 대기 물품 수 증가
                self.controller.status_manager.items_waiting += 1
                
                # 상태 업데이트 이벤트 발송
                self.controller._update_status()
                
                # 자동 정지 타이머 초기화
                self.reset_auto_stop_timer()
        except ValueError:
            logger.error(f"IR 센서 값 파싱 오류: {content}")
    
    # ==== 바코드 인식 이벤트 처리 ====
    def _handle_barcode_event(self, content: str):
        """바코드 인식 이벤트를 처리합니다."""
        # 값 추출 (bcA12123456 - A=구역, 12=물품번호, 123456=유통기한)
        if len(content) < 4:  # 최소 'bcA'
            logger.warning(f"잘못된 바코드 형식: {content}")
            return
        
        # 처리 중인 바코드가 없는지 확인 (중복 방지)
        if self.processing_barcode:
            logger.warning(f"이미 처리 중인 바코드가 있음: {content}")
            return
        
        self.processing_barcode = True
        
        try:
            # 바코드 데이터 추출
            barcode_data = content[2:]  # 'bc' 이후 데이터
            
            # 바코드 형식: 구역(1자리) + 물품번호(2자리) + 유통기한(6자리)
            if len(barcode_data) < 9:  # 9자리(1+2+6) 미만이면 오류
                logger.error(f"잘못된 바코드 데이터 형식: {barcode_data}")
                # 오류물품(E) 분류 명령 전송
                self._send_sort_command("E")
                return
            
            # 바코드 파싱
            category = barcode_data[0]  # 구역 (A, B, C 등)
            item_code = barcode_data[1:3]  # 물품번호
            expiry_date = barcode_data[3:9]  # 유통기한 (YYMMDD)
            
            # 유통기한 형식 변환 (YYMMDD -> YYYY-MM-DD)
            year = f"20{expiry_date[0:2]}"
            month = expiry_date[2:4]
            day = expiry_date[4:6]
            formatted_date = f"{year}-{month}-{day}"
            
            # 구역 결정 (인식된 구역 그대로 사용)
            warehouse = category
            
            # 선반 할당
            shelf = None
            if warehouse != "E":  # 오류물품(E)은 선반 할당 안함
                shelf = self.shelf_manager.assign_shelf(warehouse)
            
            # 분류 명령 전송
            self._send_sort_command(warehouse)
            
            # 항목 정보 생성
            item_info = {
                "barcode": barcode_data,
                "category": warehouse,
                "item_code": item_code,
                "expiry_date": formatted_date,
                "shelf": shelf
            }
            
            # DB에 물품 정보 저장
            if shelf:
                self.shelf_manager.save_item(item_info)
            
            # 웹소켓 이벤트 발송
            self.controller._emit_socketio_event("barcode_scanned", item_info)
            
            # 로그에 분류 정보 추가
            self.controller.add_sort_log(item_info)
            
            # 자동 정지 타이머 초기화 (물품이 인식되었으므로)
            self.reset_auto_stop_timer()
        
        except Exception as e:
            logger.error(f"바코드 처리 중 오류: {str(e)}")
            # 오류 발생 시 오류물품(E)으로 분류
            self._send_sort_command("E")
        
        finally:
            self.processing_barcode = False
    
    # ==== 분류 완료 이벤트 처리 ====
    def _handle_sort_complete_event(self, content: str):
        """분류 완료 이벤트를 처리합니다."""
        if len(content) < 3:  # 최소 'ssA'
            logger.warning(f"잘못된 분류 완료 형식: {content}")
            return
        
        # 구역 추출 (마지막 문자)
        zone = content[2]
        logger.info(f"분류 완료: {zone} 구역")
        
        # 대기 물품 수 감소
        if self.controller.status_manager.items_waiting > 0:
            self.controller.status_manager.items_waiting -= 1
        
        # 처리 물품 수 증가
        self.controller.status_manager.items_processed += 1
        
        # 구역별 카운트 증가
        if zone in self.controller.status_manager.sort_counts:
            self.controller.status_manager.sort_counts[zone] += 1
        
        # 상태 업데이트 이벤트 발송
        self.controller._update_status()
        
        # 대기 물품이 없으면 자동 정지 타이머 시작/갱신
        if self.controller.status_manager.items_waiting == 0:
            self.reset_auto_stop_timer()
    
       # ==== 자동 정지 이벤트 처리 ====
    def _handle_auto_stop_event(self, content: str):
        """자동 정지 이벤트를 처리합니다."""
        logger.info("분류기 자동 정지 발생")
        
        # 상태 업데이트
        self.controller.status_manager.state = "stopped"
        self.controller.status_manager.motor_active = False
        
        # 자동 정지 타이머 취소
        self.cancel_auto_stop_timer()
        
        # 상태 업데이트 이벤트 발송
        self.controller._update_status()
        
        # Socket.IO 이벤트 발송
        self.controller._emit_socketio_event("auto_stopped", {
            "reason": "no_items_timeout",
            "status": self.controller.status_manager.state
        })
    
    # ==== 성공 응답 처리 ====
    def _handle_ok_response(self, content: str):
        """성공 응답을 처리합니다."""
        # 성공 응답은 단순히 로그만 기록
        logger.debug(f"분류기 성공 응답: {content}")
    
    # ==== 분류 명령 전송 ====
    def _send_sort_command(self, zone: str):
        """지정된 구역으로 물품을 분류하는 명령을 전송합니다."""
        # 새로운 바이너리 프로토콜에 맞는 형식으로 명령 생성
        # SCsoA\n - 분류기(S)에 명령(C)으로 분류(so) A구역으로 보냄
        command = f"SCso{zone}\n"
        
        success = self.tcp_handler.send_message("S", command)
        if not success:
            logger.error(f"분류 명령 전송 실패: {zone}")
    
    # ==== 자동 정지 타이머 설정 ====
    def reset_auto_stop_timer(self):
        # 기존 타이머 취소
        self.cancel_auto_stop_timer()
        
        # 분류기가 작동 중인 경우에만 타이머 설정
        if self.controller.status_manager.state == "running":
            self.auto_stop_timer = threading.Timer(7.0, self._auto_stop_timeout)
            self.auto_stop_timer.daemon = True
            self.auto_stop_timer.start()
    
    # ==== 자동 정지 타이머 취소 ====
    def cancel_auto_stop_timer(self):
        if self.auto_stop_timer:
            self.auto_stop_timer.cancel()
            self.auto_stop_timer = None
    
    # ==== 자동 정지 타임아웃 처리 ====
    def _auto_stop_timeout(self):
        """자동 정지 타이머 만료 시 호출됩니다."""
        # 타이머 발생 시 분류기가 여전히 작동 중이고 대기 물품이 없는 경우
        if self.controller.status_manager.state == "running" and self.controller.status_manager.items_waiting == 0:
            logger.info("자동 정지: 7초간 물품 없음")
            
            # 정지 명령 전송
            command = "SCsp\n"  # 분류기(S) 명령(C) 정지(sp)
            
            self.tcp_handler.send_message("S", command)
            
            # 상태 업데이트
            self.controller.status_manager.state = "stopped"
            self.controller.status_manager.motor_active = False
            
            # 상태 업데이트 이벤트 발송
            self.controller._update_status()
            
            # Socket.IO 이벤트 발송
            self.controller._emit_socketio_event("auto_stopped", {
                "reason": "no_items_timeout",
                "status": self.controller.status_manager.state
            })