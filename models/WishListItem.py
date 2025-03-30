from pydantic import BaseModel


class WishlistItem(BaseModel):
    name: str
    url: str
    price: float
    image_url: str