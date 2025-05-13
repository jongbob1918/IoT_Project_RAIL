from typing import Dict, Any, Optional

# 컨트롤러 참조 저장소 (각 모듈별 컨트롤러 관리)
controllers: Dict[str, Any] = {}

# 이전 버전 호환성을 위한 변수
controller: Optional[Any] = None

# 컨트롤러 설정 함수
def set_controller(main_controller):
    """이전 버전 호환성을 위해 유지하는 함수"""
    global controller
    controller = main_controller
    # 기본 컨트롤러로도 등록
    controllers['main'] = main_controller

def register_controller(name: str, controller_instance: Any) -> None:
    """컨트롤러를 레지스트리에 등록합니다.
    
    Args:
        name: 컨트롤러의 이름 (예: 'inventory', 'sort', 'access')
        controller_instance: 컨트롤러 인스턴스
    """
    controllers[name] = controller_instance
    
def get_controller(name: str) -> Any:
    """이름으로 컨트롤러를 가져옵니다.
    
    Args:
        name: 컨트롤러의 이름
        
    Returns:
        등록된 컨트롤러 인스턴스 또는 None (등록되지 않은 경우)
    """
    return controllers.get(name)