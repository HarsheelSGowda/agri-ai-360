from pydantic import BaseModel, Field


class SatellitePlannedMetric(BaseModel):
    key: str
    label: str
    description: str


class SatelliteStatusResponse(BaseModel):
    status: str
    configured: bool
    location: str
    planned_metrics: list[SatellitePlannedMetric]
    message: str


class SensorReadingOut(BaseModel):
    id: int
    farm_id: int
    sensor_type: str
    value: float
    unit: str
    source: str
    recorded_at: str


class IoTReadingsResponse(BaseModel):
    farm_id: int
    readings: list[SensorReadingOut]
    has_real_device_data: bool


class IoTIngestRequest(BaseModel):
    farm_id: int
    sensor_type: str
    value: float
    unit: str | None = Field(default=None, max_length=20)
