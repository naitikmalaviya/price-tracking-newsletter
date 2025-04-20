from pydantic import BaseModel

class ScrapedProductData(BaseModel):
    name: str
    url: str
    price: float
    discount: float
    image_url: str