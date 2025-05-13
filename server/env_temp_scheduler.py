#!/usr/bin/env python3
# server/env_temp_scheduler.py
"""
환경 제어 온도 설정 스케줄러
config.py에 정의된 온도 설정을 10초마다 환경 제어 디바이스에 전송
"""

import time
import logging
import threading
from utils.tcp_handler import TCPHandler
from config import WAREHOUSES, HARDWARE_IP, TCP_PORT

logger = logging.getLogger('env_temp_scheduler')

class EnvTempScheduler:
    def __init__(self, tcp_handler: TCPHandler):
        """환경 제어 온도 설정 스케줄러 초기화"""
        self.tcp_handler = tcp_handler
        self.running = False
        self.thread = None
        self.interval = 10  # 명령 전송 간격 (초)
        
        # 창고별 목표 온도 설정 - config.py의 중간값 사용
        self.target_temps = {
            "A": int((WAREHOUSES["A"]["temp_min"] + WAREHOUSES["A"]["temp_max"]) / 2),  # 냉동 약 -24°C
            "B": int((WAREHOUSES["B"]["temp_min"] + WAREHOUSES["B"]["temp_max"]) / 2),  # 냉장 약 5°C
            "C": int((WAREHOUSES["C"]["temp_min"] + WAREHOUSES["C"]["temp_max"]) / 2)   # 상온 약 20°C
        }
        
        logger.info(f"환경 제어 온도 스케줄러 초기화 완료, 목표 온도: {self.target_temps}")
    
    def start(self):
        """스케줄러 시작"""
        if self.running:
            logger.warning("이미 실행 중인 스케줄러입니다.")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        logger.info(f"환경 제어 온도 스케줄러 시작 (간격: {self.interval}초)")
        
        # 즉시 한 번 명령 전송 (시작 시)
        self._send_temperature_commands()
    
    def stop(self):
        """스케줄러 정지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            logger.info("환경 제어 온도 스케줄러 정지")
    
    def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        while self.running:
            try:
                self._send_temperature_commands()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"온도 명령 전송 중 오류: {str(e)}")
                # 오류 발생 시에도 계속 실행
                time.sleep(self.interval)
    
    def _send_temperature_commands(self):
        """모든 창고에 온도 설정 명령 전송"""
        for warehouse, temp in self.target_temps.items():
            command = f"HCp{warehouse}{temp}"
            
            # TCP 핸들러로 메시지 전송
            success = self.tcp_handler.send_message("env_controller", command)
            if success:
                logger.debug(f"온도 설정 명령 전송 성공: {warehouse}={temp}°C")
            else:
                # 'env_controller' 매핑으로 실패하면 'H'로 시도
                success = self.tcp_handler.send_message("H", command)
                if success:
                    logger.debug(f"온도 설정 명령 전송 성공(H): {warehouse}={temp}°C")
                else:
                    logger.error(f"온도 설정 명령 전송 실패: {warehouse}={temp}°C")
    
    def update_target_temp(self, warehouse, temperature):
        """특정 창고의 목표 온도 업데이트"""
        if warehouse in self.target_temps:
            self.target_temps[warehouse] = temperature
            logger.info(f"{warehouse} 창고 목표 온도 변경: {temperature}°C")
            
            # 즉시 업데이트된 명령 전송
            command = f"HCp{warehouse}{temperature}"
            success = self.tcp_handler.send_message("env_controller", command) or \
                     self.tcp_handler.send_message("H", command)
            
            if not success:
                logger.error(f"온도 설정 명령 전송 실패: {warehouse}={temperature}°C")
            
            return True
        else:
            logger.warning(f"알 수 없는 창고 ID: {warehouse}")
            return False 