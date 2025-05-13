# server/controllers/sort/barcode_parser.py
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ==== 바코드 파싱 클래스 ====
class BarcodeParser:
    def __init__(self):
        # 분류 코드 매핑 (첫 자리 숫자 → 창고)
        self.category_map = {
            "1": "A",  # 냉동
            "2": "B",  # 냉장
            "3": "C",  # 상온
            "0": "E"   # 오류물품
        }
    
    # ==== 바코드 파싱 메소드 ====
    def parse(self, barcode: str) -> Tuple[bool, Optional[Dict]]:
        """
        바코드 파싱 - 형식: 분류(1자리) + 물품번호(2자리) + 판매자(2자리) + 유통기한(6자리, YYMMDD)
        
        Returns:
            (성공 여부, 파싱 결과 딕셔너리 또는 None)
        """
        try:
            # 바코드 길이 확인
            if len(barcode) < 11:
                logger.error(f"잘못된 바코드 형식 (길이 부족): {barcode}")
                return False, None
            
            # 파싱 수행
            category_code = barcode[0]
            item_code = barcode[1:3]  # 물품번호 2자리
            vendor_code = barcode[3:5]
            
            # 유통기한 파싱 
            try:
                year = int(barcode[5:7])
                month = int(barcode[7:9])
                day = int(barcode[9:11])
                
                # 2000년대인 경우 20XX 형식으로 변환
                full_year = 2000 + year
                
                # 유효한 날짜인지 확인
                datetime(full_year, month, day)
                
                # YYYY-MM-DD 형식
                expiry_date = f"20{barcode[5:7]}-{barcode[7:9]}-{barcode[9:11]}"
            except ValueError:
                logger.error(f"잘못된 유통기한 형식: {barcode[5:11]}")
                return False, None
            
            # 분류 카테고리 결정
            if category_code in self.category_map:
                warehouse = self.category_map[category_code]
            else:
                warehouse = "E"  # 알 수 없는 카테고리는 오류물품으로 분류
            
            # 결과 사전 생성
            result = {
                "barcode": barcode,
                "category": warehouse,
                "item_code": item_code,
                "vendor_code": vendor_code,
                "expiry_date": expiry_date
            }
            
            return True, result
            
        except Exception as e:
            logger.error(f"바코드 파싱 중 오류 발생: {str(e)}")
            return False, None