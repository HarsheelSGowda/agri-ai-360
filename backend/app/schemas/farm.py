from datetime import datetime

from pydantic import BaseModel, Field


class FarmCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)
    area_acres: float = Field(gt=0, le=100000)
    soil_type: str = Field(min_length=1, max_length=100)
    irrigation_available: bool = False


class FarmOut(BaseModel):
    id: int
    name: str
    location: str
    area_acres: float
    soil_type: str
    irrigation_available: bool
    created_at: datetime

    model_config = {"from_attributes": True}
