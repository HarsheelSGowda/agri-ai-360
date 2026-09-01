from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.weather import WeatherOut
from app.services.weather_provider import get_weather_provider

router = APIRouter(tags=["weather"])


@router.get("/weather", response_model=WeatherOut)
def get_weather(location: str = "Nagpur, Maharashtra", _: User = Depends(get_current_user)):
    provider = get_weather_provider()
    return provider.get_current(location)
