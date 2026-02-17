"""
Shared analyzer module for Supply Chain Resilience Agent.
Fetches price data from Open Prices API and computes volatility-based risk scores.
"""
import statistics
import time
from collections import defaultdict
from typing import Optional

import requests

DEFAULT_COMMODITIES = ["rice", "milk", "eggs", "oil", "wheat"]

API_BASE = "https://prices.openfoodfacts.org/api/v1/prices"


def fetch_price_records(commodity: str, size: int = 50) -> list[dict]:
    """
    Fetch raw price records from Open Prices API for a commodity keyword.
    Returns a list of normalized records:
      {price: float, currency: str, country: str, city: str, date: str}
    Returns [] on error.
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
            return []

        records: list[dict] = []
        for item in items:
            price = item.get("price")
            if price is None:
                continue
            try:
                price_f = float(price)
            except (TypeError, ValueError):
                continue

            currency = (item.get("currency") or "").strip()
            location = item.get("location") or {}
            country = (location.get("osm_address_country") or "").strip()
            city = (location.get("osm_address_city") or "").strip()
            date = (item.get("date") or "").strip()

            records.append(
                {
                    "price": price_f,
                    "currency": currency,
                    "country": country or "Unknown",
                    "city": city or "Unknown",
                    "date": date,
                }
            )
        return records
    except Exception:
        return []


def fetch_prices(commodity: str, size: int = 50) -> tuple[list[float], str]:
    """
    Fetch price data from Open Prices API for a commodity.
    Returns (prices, currency). Uses most common currency from items.
    Returns ([], "") on error.
    """
    records = fetch_price_records(commodity=commodity, size=size)
    if not records:
        return [], ""

    prices = [r["price"] for r in records]
    currencies = [r["currency"] for r in records if r.get("currency")]
    currency = max(set(currencies), key=currencies.count) if currencies else ""
    return prices, currency


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


def _region_key_country(record: dict) -> str:
    return record.get("country") or "Unknown"


def _region_key_city(record: dict) -> str:
    country = record.get("country") or "Unknown"
    city = record.get("city") or "Unknown"
    return f"{city}, {country}"


def compute_region_risks(
    records: list[dict], *, level: str = "country", min_samples: int = 5, limit: int = 5
) -> list[dict]:
    """
    Compute volatility (CV) per region and return the most stressed regions.
    level: 'country' or 'city'
    """
    if not records:
        return []

    key_fn = _region_key_country if level == "country" else _region_key_city
    groups: dict[str, list[float]] = defaultdict(list)
    for r in records:
        try:
            groups[key_fn(r)].append(float(r["price"]))
        except Exception:
            pass

    region_rows: list[dict] = []
    for region, prices in groups.items():
        if len(prices) < min_samples:
            continue
        risk_score, status = compute_risk(prices)
        mean_price = round(statistics.mean(prices), 2) if prices else None
        region_rows.append(
            {
                "region": region,
                "mean_price": mean_price,
                "risk_score": risk_score,
                "status": status,
                "sample_size": len(prices),
            }
        )

    # Sort with numeric risks first (descending), NO_DATA/None last
    region_rows.sort(
        key=lambda r: (r["risk_score"] is None, -(r["risk_score"] or 0.0), -r["sample_size"])
    )
    return region_rows[:limit]


def analyze_commodity(commodity: str) -> dict:
    """
    Fetch prices for a commodity and compute risk analysis.
    Returns dict with name, mean_price, risk_score, status, currency, sample_size, regions.
    """
    records = fetch_price_records(commodity)
    prices = [r["price"] for r in records] if records else []
    currencies = [r["currency"] for r in records if r.get("currency")] if records else []
    currency = max(set(currencies), key=currencies.count) if currencies else ""
    risk_score, status = compute_risk(prices)

    result: dict = {
        "name": commodity,
        "mean_price": None,
        "risk_score": risk_score,
        "status": status,
        "currency": currency or "N/A",
        "sample_size": len(prices),
        "regions": {
            "by_country": compute_region_risks(records, level="country"),
            "by_city": compute_region_risks(records, level="city"),
        },
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
