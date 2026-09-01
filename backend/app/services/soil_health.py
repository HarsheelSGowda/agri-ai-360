"""
Rule-based soil health scoring.

Thresholds are general agronomic reference ranges (not a trained model) and are
intentionally documented here so the scoring logic is transparent and reproducible.
Score is 0-100 per nutrient: highest near the center of the optimal band, tapering
to 10 at the "hard" low/high bounds.
"""

from __future__ import annotations

# name -> (hard_low, optimal_low, optimal_high, hard_high)
THRESHOLDS: dict[str, tuple[float, float, float, float]] = {
    "nitrogen": (0, 40, 120, 200),
    "phosphorus": (0, 20, 60, 150),
    "potassium": (0, 30, 80, 200),
    "ph": (3.0, 6.0, 7.5, 10.0),
}

LABELS = {
    "nitrogen": "nitrogen",
    "phosphorus": "phosphorus",
    "potassium": "potassium",
    "ph": "pH",
}


def _score(value: float, hard_low: float, low: float, high: float, hard_high: float) -> int:
    if low <= value <= high:
        center = (low + high) / 2
        span = (high - low) / 2 or 1
        dist = abs(value - center)
        return round(100 - 15 * (dist / span))
    if value < low:
        if value <= hard_low:
            return 10
        return round(10 + 75 * (value - hard_low) / (low - hard_low))
    if value >= hard_high:
        return 10
    return round(10 + 75 * (hard_high - value) / (hard_high - high))


def compute_soil_health(nitrogen: float, phosphorus: float, potassium: float, ph: float) -> dict:
    values = {"nitrogen": nitrogen, "phosphorus": phosphorus, "potassium": potassium, "ph": ph}
    breakdown = {key: _score(values[key], *THRESHOLDS[key]) for key in values}
    overall = round(sum(breakdown.values()) / len(breakdown))

    insights: list[str] = []
    ranked = sorted(breakdown.items(), key=lambda kv: kv[1])
    for key, score in ranked:
        if score < 45:
            insights.append(f"Your {LABELS[key]} level is comparatively low.")
        elif score < 65:
            insights.append(f"Your {LABELS[key]} level is slightly below optimal.")

    if not insights:
        insights.append("All measured soil parameters are within a healthy range.")

    return {"score": overall, "breakdown": breakdown, "insights": insights[:3]}
