from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RestaurantOut(BaseModel):
    id: int
    name: str
    cuisine: str
    address: str
    latitude: float
    longitude: float
    rating: float
    total_seats: int
    open_hours: str
    price_tier: str
    distance_km: float


class MenuItemOut(BaseModel):
    id: int
    restaurant_id: int
    name: str
    category: str
    description: str
    price: float
    calories_kcal: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    dietary_tags: list[str]
    ingredients: list[str] = []
    nutrition_source: str = "pending"
    allergens: list[str] = []
    health_note: str = ""
    is_available: bool


class BookingCreate(BaseModel):
    restaurant_id: int
    booking_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    time_slot: str = Field(min_length=4, max_length=20)
    party_size: int = Field(ge=1, le=20)
    notes: str = Field(default="", max_length=300)


class BookingOut(BaseModel):
    id: int
    booking_code: str
    restaurant_id: int
    restaurant_name: str
    booking_date: str
    time_slot: str
    party_size: int
    status: str
    notes: str
    created_at: str


class SlotAvailabilityOut(BaseModel):
    time_slot: str
    available_seats: int


class HealthRecommendationOut(BaseModel):
    restaurant_id: int
    badge: str
    reason: str
    recommended_dishes: list[str] = []


class BookingDraftOut(BaseModel):
    booking_date: str | None = None
    time_slot: str | None = None
    party_size: int | None = None
    notes: str | None = None


class ChatActionRequest(BaseModel):
    action: str = Field(
        default="message",
        description="show_nearby | recommend_healthy | select_restaurant | toggle_like_item | go_back | start_booking | confirm_booking | decline_booking | restart | message",
    )
    restaurant_id: int | None = None
    item_id: int | None = None
    text: str | None = None
    goal: str | None = None
    lat: float | None = None
    lon: float | None = None
    booking_date: str | None = None
    time_slot: str | None = None
    party_size: int | None = None
    notes: str | None = None


class ChatMessageOut(BaseModel):
    sender: str
    text: str
    timestamp: str


class ChatSessionOut(BaseModel):
    state: str
    selected_restaurant: RestaurantOut | None = None
    liked_item_ids: list[int]
    messages: list[ChatMessageOut]
    nearby_restaurants: list[RestaurantOut] = []
    menu_items: list[MenuItemOut] = []
    slots: list[SlotAvailabilityOut] = []
    latest_booking: BookingOut | None = None
    recommendations: list[HealthRecommendationOut] = []
    health_goal: str | None = None
    booking_draft: BookingDraftOut | None = None
    quick_actions: list[str] = []
    llm_provider: str = "fallback"
