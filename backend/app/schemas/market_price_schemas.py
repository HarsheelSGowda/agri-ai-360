from pydantic import BaseModel


class MarketPriceCropsResponse(BaseModel):
    crops: list[str]


class MarketPriceStatesResponse(BaseModel):
    states: list[str]


class MarketPriceDistrictsResponse(BaseModel):
    districts: list[str]


class MarketPriceMarketsResponse(BaseModel):
    markets: list[str]


class CurrentPriceResponse(BaseModel):
    found: bool
    crop: str | None = None
    state: str | None = None
    district: str | None = None
    market: str | None = None
    variety: str | None = None
    as_of_date: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    modal_price: float | None = None
    markets_reporting: int | None = None
    source: str | None = None
    is_live: bool | None = None
    reason: str | None = None


class TrendPoint(BaseModel):
    date: str
    min_price: float
    max_price: float
    modal_price: float


class TrendResponse(BaseModel):
    found: bool
    points: list[TrendPoint]
    trend_direction: str | None = None
    change_pct: float | None = None
    source: str | None = None
    is_live: bool | None = None
    reason: str | None = None


class MarketComparisonItem(BaseModel):
    market: str
    district: str
    min_price: float
    max_price: float
    modal_price: float
    arrivals_tonnes: float | None = None


class MarketComparisonResponse(BaseModel):
    found: bool
    as_of_date: str | None = None
    markets: list[MarketComparisonItem]
    best_market: MarketComparisonItem | None = None
    source: str | None = None
    is_live: bool | None = None
    reason: str | None = None
