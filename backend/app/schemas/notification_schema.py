from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    farm_id: int | None
    category: str
    priority: str
    title: str
    message: str
    is_read: bool
    created_at: str


class NotificationGenerateResponse(BaseModel):
    created: int
    notifications: list[NotificationOut]
