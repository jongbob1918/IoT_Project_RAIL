import threading
import time
import logging
from simulators.sorter_simulator import SorterSimulator
from simulators.environment_simulator import EnvironmentSimulator
from simulators.access_simulator import AccessSimulator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_simulator(simulator):
    """시뮬레이터 실행 함수"""
    try:
        simulator.connect()
        simulator.run()
    except KeyboardInterrupt:
        logger.info(f"{simulator.__class__.__name__} 종료")
    except Exception as e:
        logger.error(f"{simulator.__class__.__name__} 오류: {str(e)}")
    finally:
        simulator.disconnect()

def main():
    """시뮬레이터 실행"""
    # 시뮬레이터 인스턴스 생성
    simulators = [
        SorterSimulator(device_id="sr_01", update_interval=3.0),
        EnvironmentSimulator(device_id="hs_ab", update_interval=5.0),
        AccessSimulator(device_id="gt_01", update_interval=2.0)
    ]
    
    # 시뮬레이터별 스레드 생성
    threads = []
    for sim in simulators:
        thread = threading.Thread(target=run_simulator, args=(sim,))
        thread.daemon = True
        threads.append(thread)
    
    # 모든 스레드 시작
    for thread in threads:
        thread.start()
        time.sleep(0.5)  # 시작 타이밍 조절
    
    logger.info("모든 시뮬레이터가 시작되었습니다. 종료하려면 Ctrl+C를 누르세요.")
    
    try:
        # 메인 스레드는 계속 실행
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("시뮬레이션 종료 중...")
    
    # 모든 시뮬레이터 종료
    for sim in simulators:
        sim.running = False
    
    # 모든 스레드 종료 대기
    for thread in threads:
        thread.join(timeout=2.0)

if __name__ == "__main__":
    main() 