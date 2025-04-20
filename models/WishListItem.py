from pydantic import Field
from typing import Optional
from datetime import date

from .ScrapedProductData import ScrapedProductData

class WishlistItem(ScrapedProductData):
    page_id: str
    lowest_price_so_far: Optional[float] = Field(default=None)
    lowest_price_date: Optional[date] = Field(default=None)