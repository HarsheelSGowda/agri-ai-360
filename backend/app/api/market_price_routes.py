from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.market_price_schemas import (
    CurrentPriceResponse,
    MarketComparisonResponse,
    MarketPriceCropsResponse,
    MarketPriceDistrictsResponse,
    MarketPriceMarketsResponse,
    MarketPriceStatesResponse,
    TrendResponse,
)
from app.services import market_price_service as svc

router = APIRouter(prefix="/market-prices", tags=["market-prices"])


@router.get("/crops", response_model=MarketPriceCropsResponse)
def get_crops(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return MarketPriceCropsResponse(crops=svc.list_crops(db))


@router.get("/states", response_model=MarketPriceStatesResponse)
def get_states(crop: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return MarketPriceStatesResponse(states=svc.list_states(db, crop))


@router.get("/districts", response_model=MarketPriceDistrictsResponse)
def get_districts(crop: str, state: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return MarketPriceDistrictsResponse(districts=svc.list_districts(db, crop, state))


@router.get("/markets", response_model=MarketPriceMarketsResponse)
def get_markets(
    crop: str, state: str, district: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    return MarketPriceMarketsResponse(markets=svc.list_markets(db, crop, state, district))


@router.get("", response_model=CurrentPriceResponse)
def get_current(
    crop: str,
    state: str,
    district: str | None = None,
    market: str | None = None,
    variety: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return CurrentPriceResponse(**svc.get_current_price(db, crop, state, district, market, variety))


@router.get("/trend", response_model=TrendResponse)
def get_trend(
    crop: str,
    state: str,
    district: str | None = None,
    market: str | None = None,
    variety: str | None = None,
    days: int = 30,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return TrendResponse(**svc.get_trend(db, crop, state, district, market, variety, days))


@router.get("/comparison", response_model=MarketComparisonResponse)
def get_comparison(
    crop: str, state: str, district: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    return MarketComparisonResponse(**svc.get_market_comparison(db, crop, state, district))
