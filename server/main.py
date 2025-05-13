from flask import Flask, jsonify, request
from flask_cors import CORS
from utils.logging import setup_logger
from flask_socketio import SocketIO
from config import CONFIG, SERVER_HOST, SERVER_PORT, TCP_PORT, DEBUG, SOCKETIO_PING_TIMEOUT, SOCKETIO_PING_INTERVAL, SOCKETIO_ASYNC_MODE
from api.sort_api import bp as sort_bp
from api.inventory_api import bp as inventory_bp
from api.env_api import bp as env_bp
from api.access_api import bp as access_bp
from api.expiry_api import bp as expiry_bp
from controllers.system_controller import get_system_status
from controllers.sort.sort_controller import SortController
from utils.tcp_handler import TCPHandler
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
    async_mode=SOCKETIO_ASYNC_MODE
)

# Socket.IO 라우터 등록 - /ws 경로 추가
@socketio.on('connect', namespace='/ws')
def handle_connect():
    logger.info("클라이언트 WebSocket 연결됨")

@socketio.on('disconnect', namespace='/ws')
def handle_disconnect():
    logger.info("클라이언트 WebSocket 연결 종료됨")

# TCP 핸들러 초기화 및 시작
tcp_handler = TCPHandler(SERVER_HOST, TCP_PORT)
tcp_handler.start()  # TCP 서버 시작 호출 추가

# 컨트롤러 초기화 함수
def init_controllers():
    """모든 컨트롤러를 초기화하고 등록합니다."""
    controllers = {}
    
    # 분류기 컨트롤러 초기화
    sort_controller = SortController(tcp_handler, socketio)
    controllers["sort"] = sort_controller
    register_controller("sort", sort_controller)
    
    # TODO: 인벤토리 컨트롤러 초기화
    # inventory_controller = InventoryController(db_manager)
    # controllers["inventory"] = inventory_controller
    # register_controller("inventory", inventory_controller)
    
    # 환경 컨트롤러 초기화
    from controllers.env_controller import EnvController
    env_controller = EnvController(tcp_handler, socketio, db_manager)
    controllers["environment"] = env_controller
    register_controller("environment", env_controller)
    
    # TODO: 출입 컨트롤러 초기화
    # access_controller = AccessController(tcp_handler)
    # controllers["access"] = access_controller
    # register_controller("access", access_controller)
    
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
    logger.info("==== 서버 종료 ====")

if __name__ == '__main__':
    try:
        socketio.run(app, host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)
    finally:
        shutdown()  # 서버 종료 시 정리 작업 수행