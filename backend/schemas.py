from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class ProductBase(BaseModel):
    name: str
    description: str
    price: float = Field(gt=0)
    category: str
    image_url: str = ""
    stock: int = Field(ge=0, default=0)
    options: list[dict[str, Any]] = []


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: int
    created_at: str

    class Config:
        from_attributes = True


class CartItemBase(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, default=1)
    selected_options: dict[str, str] = {}


class CartItemCreate(CartItemBase):
    pass


class CartItem(CartItemBase):
    id: int
    product: Optional[Product] = None

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    session_id: str
    items: list[CartItem]
    total: float


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    price: float


class OrderCreate(BaseModel):
    session_id: str
    customer_name: str
    customer_email: str
    shipping_address: str


class OrderItem(OrderItemBase):
    id: int
    product_name: str
    selected_options: dict[str, str] = {}

    class Config:
        from_attributes = True


class Order(BaseModel):
    id: int
    session_id: str
    customer_name: str
    customer_email: str
    shipping_address: str
    total: float
    status: str
    created_at: str
    items: list[OrderItem] = []

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    response: str
    cart_updated: bool = False
    products_mentioned: list[dict] = []
