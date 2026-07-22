from pydantic import BaseModel


class RestaurantMetrics(BaseModel):
    restaurant_id: int
    order_count: int
    total_revenue: float
