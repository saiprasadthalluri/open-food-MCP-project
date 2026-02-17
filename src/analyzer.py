"""
Shared analyzer module for Supply Chain Resilience Agent.
Fetches price data from Open Prices API and computes volatility-based risk scores.
"""
import statistics
import time
from typing import Optional

import requests

DEFAULT_COMMODITIES = ["rice", "milk", "eggs", "oil", "wheat"]

API_BASE = "https://prices.openfoodfacts.org/api/v1/prices"


def fetch_prices(commodity: str, size: int = 50) -> tuple[list[float], str]:
    """
    Fetch price data from Open Prices API for a commodity.
    Returns (prices, currency). Uses most common currency from items.
    Returns ([], "") on error.
    """
    try:
        resp = requests.get(
            API_BASE,
            params={
                "product_name__like": commodity,
                "size": size,
                "sort": "-date",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items") or []
        if not items:
            return [], ""

        prices: list[float] = []
        currencies: list[str] = []
        for item in items:
            price = item.get("price")
            if price is not None:
                try:
                    prices.append(float(price))
                    cur = item.get("currency") or ""
                    if cur:
                        currencies.append(cur)
                except (TypeError, ValueError):
                    pass

        if not prices:
            return [], ""

        currency = ""
        if currencies:
            currency = max(set(currencies), key=currencies.count)

        return prices, currency
    except Exception:
        return [], ""


def compute_risk(prices: list[float]) -> tuple[Optional[float], str]:
    """
    Compute Coefficient of Variation (CV) as risk score.
    Returns (risk_score, status).
    Status: CRITICAL (>0.5), WARNING (>0.3), STABLE (<=0.3), NO_DATA (empty or single price).
    """
    if len(prices) < 2:
        return None, "NO_DATA"

    try:
        mean_val = statistics.mean(prices)
        if mean_val <= 0:
            return None, "NO_DATA"
        std_val = statistics.stdev(prices)
        cv = std_val / mean_val

        if cv > 0.5:
            return round(cv, 4), "CRITICAL"
        if cv > 0.3:
            return round(cv, 4), "WARNING"
        return round(cv, 4), "STABLE"
    except Exception:
        return None, "NO_DATA"


def analyze_commodity(commodity: str) -> dict:
    """
    Fetch prices for a commodity and compute risk analysis.
    Returns dict with name, mean_price, risk_score, status, currency, sample_size.
    """
    prices, currency = fetch_prices(commodity)
    risk_score, status = compute_risk(prices)

    result: dict = {
        "name": commodity,
        "mean_price": None,
        "risk_score": risk_score,
        "status": status,
        "currency": currency or "N/A",
        "sample_size": len(prices),
    }
    if prices:
        result["mean_price"] = round(statistics.mean(prices), 2)
    return result


def analyze_all() -> list[dict]:
    """
    Run analyze_commodity for each default commodity.
    Adds a short delay between requests to be gentle on the API.
    """
    results: list[dict] = []
    for i, commodity in enumerate(DEFAULT_COMMODITIES):
        if i > 0:
            time.sleep(1)
        results.append(analyze_commodity(commodity))
    return results
