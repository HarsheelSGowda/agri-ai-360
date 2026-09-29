from pydantic import BaseModel, Field


class FertilizerRecommendationInput(BaseModel):
    crop: str = Field(min_length=1, max_length=100)
    nitrogen: float = Field(ge=0, le=300)
    phosphorus: float = Field(ge=0, le=300)
    potassium: float = Field(ge=0, le=300)
    ph: float = Field(ge=0, le=14)
    growth_stage: str = Field(min_length=1, max_length=50)
    organic_carbon: float | None = Field(default=None, ge=0, le=100)
    moisture: float | None = Field(default=None, ge=0, le=100)
    farm_area_acres: float | None = Field(default=None, gt=0, le=100_000)
    farm_id: int | None = None


class NutrientStatus(BaseModel):
    nutrient: str
    current_value: float
    optimal_range: str
    status: str
    recommended_category: str | None


class FertilizerRecommendationResponse(BaseModel):
    crop: str
    growth_stage: str
    farm_area_acres: float | None
    deficiencies: list[NutrientStatus]
    organic_matter_guidance: str | None
    application_timing: str
    warnings: list[str]
    disclaimer: str


class FertilizerOptionsResponse(BaseModel):
    growth_stages: list[str]
