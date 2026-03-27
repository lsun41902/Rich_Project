from dataclasses import dataclass,field
from typing import Optional
import services.ui_helper as helper

@dataclass
class GoldDTO:
    type: int
    code: str
    name: str
    raw_price: Optional[float] = field(init=False,default=None)
    today_usd: float

    def get_price_per_g(self, exchange_rate: float = 1350.0) -> float:
        """어떤 단위든 1g당 원화 가격으로 통일해서 반환"""
        if 0 == self.type:  # 국제 선물 (oz -> g)
            return (self.raw_price * exchange_rate) / 31.1035
        else:  # 국내 종목 (지수 -> g)
            return self.raw_price * 10

    def get_price_per_don(self) -> float:
        """사용자용 '돈' 단위 출력"""
        return self.get_price_per_g(self.today_usd) * 3.75