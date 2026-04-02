from dataclasses import dataclass,field
from typing import Optional

@dataclass
class TickerDTO:
    type: int
    code: str
    name: str
    open_price: Optional[float] = field(init=False,default=0)
    close_price: Optional[float] = field(init=False,default=0)
