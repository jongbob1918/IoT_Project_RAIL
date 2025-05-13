from flask import Flask, jsonify, request
from flask_cors import CORS
from utils.logging import setup_logger
from flask_socketio import SocketIO
import datetime  # 타임스탬프 생성용 추가
from config import CONFIG, SERVER_HOST, SERVER_PORT, TCP_PORT, DEBUG, SOCKETIO_PING_TIMEOUT, SOCKETIO_PING_INTERVAL, SOCKETIO_ASYNC_MODE, MULTI_PORT_MODE, TCP_PORTS, HARDWARE_IP
from api.sort_api import sort_bp
from api.inventory_api import bp as inventory_bp
from api.env_api import bp as env_bp
from api.access_api import bp as access_bp
from api.expiry_api import bp as expiry_bp
from controllers.system_controller import get_system_status
from controllers.sort.sort_controller import SortController
from utils.tcp_handler import TCPHandler
from utils.multi_tcp_handler import MultiTCPHandler
from env_temp_scheduler import EnvTempScheduler  # 환경 제어 온도 스케줄러 임포트
from api import set_controller, register_controller  # 컨트롤러 관리 함수 임포트
try:
    from utils.tcp_debug_helper import *
    print("디버깅 모드가 활성화되었습니다.")
except ImportError as e:
    pass  # 디버그 헬퍼가 없으면 무시\

# logger 초기화 전에 로그 디렉토리 확인
import os
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# 로거는 한 번만 설정
logger = setup_logger("server")
logger.info("==== 서버 시작 ====")

# 데이터베이스 모듈 import 및 초기화
try:
    from db import init_database, db_manager
    
    # 데이터베이스 초기화
    try:
        init_database()
        db_status = db_manager.get_connection_status()
        if db_status["connected"]:
            logger.info(f"데이터베이스 '{db_status['database']}' 연결 성공")
        else:
            logger.warning("DB 연결 없음 - 기본 선반 목록 생성")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류: {str(e)}")
        logger.warning("DB 연결 없음 - 기본 선반 목록 생성")
except ImportError as e:
    logger.warning(f"MySQL 관련 모듈을 import할 수 없습니다. DB 기능 없이 진행합니다. 오류: {e}")

app = Flask(__name__)
CORS(app)

# socketio 설정 개선
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    ping_timeout=SOCKETIO_PING_TIMEOUT,
    ping_interval=SOCKETIO_PING_INTERVAL,
    async_mode=SOCKETIO_ASYNC_MODE,
    logger=False,  # SocketIO 로깅 비활성화
    engineio_logger=False,  # Engine.IO 로깅 비활성화
    allowEIO3=True  # Engine.IO 프로토콜 버전 3 허용
)

# Socket.IO 라우터 등록 - /ws 경로 추가
@socketio.on('connect', namespace='/ws')
def handle_connect():
    logger.info("클라이언트 WebSocket 연결됨")
    
    # 클라이언트에게 초기 설정값 전송
    config_data = {
        "type": "event",
        "category": "system",
        "action": "init_config",
        "payload": {
            "version": "1.0.0",
            "warehouses": CONFIG["WAREHOUSES"],
            "server": {
                "websocket_url": f"ws://{CONFIG['SERVER_HOST']}:{CONFIG['SERVER_PORT']}/ws",
                "api_base_url": f"http://{CONFIG['SERVER_HOST']}:{CONFIG['SERVER_PORT']}/api"
            }
        },
        "timestamp": int(datetime.datetime.now().timestamp())
    }
    socketio.emit("event", config_data, namespace='/ws')

@socketio.on('disconnect', namespace='/ws')
def handle_disconnect():
    logger.info("클라이언트 WebSocket 연결 종료됨")

# TCP 핸들러 초기화 및 시작
if MULTI_PORT_MODE:
    # 멀티포트 모드: 각 디바이스별로 별도 포트 사용
    logger.info("멀티포트 모드로 TCP 핸들러 초기화")
    devices_config = {}
    for device_id, port in TCP_PORTS.items():
        devices_config[device_id] = {
            'host': SERVER_HOST,
            'port': port
        }
    tcp_handler = MultiTCPHandler(devices_config)
else:
    # 단일 포트 모드: 모든 디바이스가 동일 포트 사용
    logger.info("단일 포트 모드로 TCP 핸들러 초기화")
    tcp_handler = TCPHandler(SERVER_HOST, TCP_PORT)

# TCP 서버 시작
tcp_handler.start()

# 환경 제어 온도 스케줄러 초기화 및 시작
env_temp_scheduler = EnvTempScheduler(tcp_handler)
env_temp_scheduler.start()
logger.info("환경 제어 온도 스케줄러 시작됨 - 10초마다 온도 설정 명령 전송")

# API에 스케줄러 등록
from api.env_api import register_temp_scheduler
register_temp_scheduler(env_temp_scheduler)
logger.info("API에 환경 제어 온도 스케줄러 등록됨")

# 컨트롤러 초기화 함수
def init_controllers():
    """모든 컨트롤러를 초기화하고 등록합니다."""
    controllers = {}
    
    # 분류기 컨트롤러 초기화
    sort_controller = SortController(socketio, tcp_handler)
    controllers["sort"] = sort_controller
    register_controller("sort", sort_controller)
    
    # 인벤토리 컨트롤러 초기화
    from controllers.inventory_controller import InventoryController
    inventory_controller = InventoryController(tcp_handler, socketio, db_manager)
    controllers["inventory"] = inventory_controller
    register_controller("inventory", inventory_controller)
    
    # 환경 컨트롤러 초기화
    from controllers.env_controller import EnvController
    env_controller = EnvController(tcp_handler, socketio, db_manager)
    controllers["environment"] = env_controller
    register_controller("environment", env_controller)
    
    # 출입 컨트롤러 초기화
    from controllers.gate.gate_controller import GateController
    access_controller = GateController(tcp_handler, socketio, db_manager)
    controllers["access"] = access_controller
    register_controller("access", access_controller)
    
    # 유통기한 관리 컨트롤러 초기화
    from controllers.expiry_controller import ExpiryController
    expiry_controller = ExpiryController(tcp_handler, socketio, db_manager)
    controllers["expiry"] = expiry_controller
    register_controller("expiry", expiry_controller)
    
    return controllers

# 모든 컨트롤러 초기화
controllers = init_controllers()

# 이전 버전 호환성을 위한 설정
sort_controller = controllers.get("sort")
set_controller(sort_controller)  # API에 기본 컨트롤러 등록

# 기능별로 분리된 API 모듈을 등록
app.register_blueprint(sort_bp, url_prefix='/api/sort')
app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
app.register_blueprint(env_bp, url_prefix='/api/environment')
app.register_blueprint(access_bp, url_prefix='/api/access')
app.register_blueprint(expiry_bp, url_prefix='/api/expiry')

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(get_system_status())

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"status": "error", "message": "리소스를 찾을 수 없습니다"}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error('서버 오류: %s', str(error))
    return jsonify({"status": "error", "message": "서버 내부 오류가 발생했습니다"}), 500

# 종료 함수 추가
def shutdown():
    """서버 종료 시 정리 작업"""
    tcp_handler.stop()
    env_temp_scheduler.stop()  # 온도 스케줄러 정지
    logger.info("==== 서버 종료 ====")

if __name__ == '__main__':
    try:
        socketio.run(app, host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)
    finally:
        shutdown()  # 서버 종료 시 정리 작업 수행