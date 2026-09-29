"""
Satellite / remote-sensing integration architecture (Phase 2E, Feature 10B).

No satellite/NDVI data provider is configured for this project (see
SATELLITE_API_KEY / SATELLITE_PROVIDER in .env.example - both empty by
default). Per the project's no-fabrication rule, this module NEVER invents a
vegetation-health reading. It documents the intended interface so a real
provider (e.g. Sentinel Hub/Copernicus, Google Earth Engine, Planet) can be
plugged in later, mirroring the same swappable-provider pattern already used
for weather (weather_provider.py) and market prices (market_price_provider.py).

get_satellite_status() returns a "planned/integration-ready" descriptor: what
data would be shown and why it isn't available yet - never a fake number.
"""

from __future__ import annotations

from app.core.config import settings

PLANNED_METRICS = [
    {
        "key": "ndvi",
        "label": "NDVI (Vegetation Index)",
        "description": "Normalized Difference Vegetation Index - a satellite-derived measure of plant greenness/health.",
    },
    {
        "key": "vegetation_health",
        "label": "Vegetation Health",
        "description": "Overall crop canopy vigor derived from multispectral satellite imagery.",
    },
    {
        "key": "crop_stress",
        "label": "Crop Stress Detection",
        "description": "Early water/nutrient stress signals visible from space, often before they're visible on the ground.",
    },
    {
        "key": "field_monitoring",
        "label": "Field Boundary Monitoring",
        "description": "Change detection across growing seasons using historical satellite passes.",
    },
]


def is_configured() -> bool:
    return bool(settings.satellite_api_key) and settings.satellite_provider != "none"


def get_satellite_status(location: str) -> dict:
    # Even if a key is configured, no real provider is implemented yet in this
    # MVP - this module exists to define the contract, not to fake results.
    return {
        "status": "PLANNED",
        "configured": is_configured(),
        "location": location,
        "planned_metrics": PLANNED_METRICS,
        "message": (
            "Satellite monitoring is architected but not yet connected to a live data source. "
            "Connecting a provider (Sentinel Hub/Copernicus, Google Earth Engine, or Planet) would populate "
            "these metrics for this farm's location without changing this API's response shape."
        ),
    }
