from datetime import datetime
from typing import Dict, List, Optional

# ===== 기본 모델 =====
class BaseResponse:
    """기본 응답 모델"""
    def __init__(self, status, timestamp=None):
        self.status = status
        self.timestamp = timestamp or datetime.now().isoformat()
        
    def to_dict(self):
        return {
            "status": self.status,
            "timestamp": self.timestamp
        }

# ===== 분류기 관련 모델 =====
class SortRequest:
    """분류 작업 요청 모델"""
    def __init__(self, auto_stop=False):
        self.auto_stop = auto_stop
        
    def to_dict(self):
        return {
            "auto_stop": self.auto_stop
        }

class SortResponse(BaseResponse):
    """분류기 응답 모델"""
    def __init__(self, status, message, timestamp=None, auto_dismiss=None):
        super().__init__(status, timestamp)
        self.message = message
        self.auto_dismiss = auto_dismiss
        
    def to_dict(self):
        data = super().to_dict()
        data.update({
            "message": self.message
        })
        if self.auto_dismiss is not None:
            data["auto_dismiss"] = self.auto_dismiss
        return data

class SortStatus(BaseResponse):
    """분류기 상태 응답 모델"""
    def __init__(self, status, current_status, waiting_count, processed_count, timestamp=None):
        super().__init__(status, timestamp)
        self.current_status = current_status
        self.waiting_count = waiting_count
        self.processed_count = processed_count
        
    def to_dict(self):
        data = super().to_dict()
        data.update({
            "current_status": self.current_status,
            "waiting_count": self.waiting_count,
            "processed_count": self.processed_count
        })
        return data

# ===== 환경 제어 관련 모델 =====
class EnvironmentData:
    """환경 데이터 모델"""
    def __init__(self, temperature, humidity, status):
        self.temperature = temperature
        self.humidity = humidity
        self.status = status
        
    def to_dict(self):
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "status": self.status
        }

class EnvironmentStatus(BaseResponse):
    """환경 상태 응답 모델"""
    def __init__(self, status, data, timestamp=None):
        super().__init__(status, timestamp)
        self.data = data
        
    def to_dict(self):
        data = super().to_dict()
        data["data"] = {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.data.items()}
        return data

class TemperatureControl:
    """온도 제어 요청 모델"""
    def __init__(self, warehouse_id, target_temp):
        self.warehouse_id = warehouse_id
        self.target_temp = target_temp
        
    def to_dict(self):
        return {
            "warehouse_id": self.warehouse_id,
            "target_temp": self.target_temp
        }

# ===== 출입 관리 관련 모델 =====
class AccessLog:
    """출입 기록 모델"""
    def __init__(self, employee_id, name, department, status, timestamp=None):
        self.employee_id = employee_id
        self.name = name
        self.department = department
        self.status = status
        self.timestamp = timestamp or datetime.now().isoformat()
        
    def to_dict(self):
        return {
            "employee_id": self.employee_id,
            "name": self.name,
            "department": self.department,
            "status": self.status,
            "timestamp": self.timestamp
        }

class AccessLogResponse(BaseResponse):
    """출입 기록 조회 응답 모델"""
    def __init__(self, status, total_entry, total_exit, current_count, logs, timestamp=None):
        super().__init__(status, timestamp)
        self.total_entry = total_entry
        self.total_exit = total_exit
        self.current_count = current_count
        self.logs = logs
        
    def to_dict(self):
        data = super().to_dict()
        data.update({
            "total_entry": self.total_entry,
            "total_exit": self.total_exit,
            "current_count": self.current_count,
            "logs": [log.to_dict() if hasattr(log, 'to_dict') else log for log in self.logs]
        })
        return data

class Employee:
    """직원 정보 모델"""
    def __init__(self, id, name, department, access, last_access=None):
        self.id = id
        self.name = name
        self.department = department
        self.access = access
        self.last_access = last_access
        
    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
            "department": self.department,
            "access": self.access
        }
        if self.last_access:
            data["last_access"] = self.last_access
        return data

# ===== 재고 관리 관련 모델 =====
class InventoryItem:
    """재고 물품 정보 모델"""
    def __init__(self, item_id, barcode, name, warehouse_id, shelf_id, expiry_date, status, entry_date):
        self.item_id = item_id
        self.barcode = barcode
        self.name = name
        self.warehouse_id = warehouse_id
        self.shelf_id = shelf_id
        self.expiry_date = expiry_date
        self.status = status
        self.entry_date = entry_date
        
    def to_dict(self):
        return {
            "item_id": self.item_id,
            "barcode": self.barcode,
            "name": self.name,
            "warehouse_id": self.warehouse_id,
            "shelf_id": self.shelf_id,
            "expiry_date": self.expiry_date,
            "status": self.status,
            "entry_date": self.entry_date
        }

class ShelfStatus:
    """선반 상태 정보 모델"""
    def __init__(self, shelf_id, warehouse_id, is_occupied, item_id=None):
        self.shelf_id = shelf_id
        self.warehouse_id = warehouse_id
        self.is_occupied = is_occupied
        self.item_id = item_id
        
    def to_dict(self):
        data = {
            "shelf_id": self.shelf_id,
            "warehouse_id": self.warehouse_id,
            "is_occupied": self.is_occupied
        }
        if self.item_id:
            data["item_id"] = self.item_id
        return data

# ===== 유통기한 관리 관련 모델 =====
class ExpiryItem:
    """유통기한 관리 대상 물품 정보 모델"""
    def __init__(self, item_id, barcode, name, warehouse_id, shelf_id, expiry_date, days_remaining, status):
        self.item_id = item_id
        self.barcode = barcode
        self.name = name
        self.warehouse_id = warehouse_id
        self.shelf_id = shelf_id
        self.expiry_date = expiry_date
        self.days_remaining = days_remaining
        self.status = status
        
    def to_dict(self):
        return {
            "item_id": self.item_id,
            "barcode": self.barcode,
            "name": self.name,
            "warehouse_id": self.warehouse_id,
            "shelf_id": self.shelf_id,
            "expiry_date": self.expiry_date,
            "days_remaining": self.days_remaining,
            "status": self.status
        }

class ProcessRequest:
    """유통기한 경과 물품 처리 요청 모델"""
    def __init__(self, item_id, action, description):
        self.item_id = item_id
        self.action = action
        self.description = description
        
    def to_dict(self):
        return {
            "item_id": self.item_id,
            "action": self.action,
            "description": self.description
        } 