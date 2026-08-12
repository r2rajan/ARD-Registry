"""Mock currency tools for the Currency Exchange agent.

Simulates live exchange rates with deterministic but realistic values.
No external forex API required.
"""

import hashlib
import json
import random
from datetime import datetime

from strands import tool

# Base rates relative to USD (approximate real-world values)
BASE_RATES = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 154.50, "CAD": 1.36,
    "AUD": 1.53, "CHF": 0.88, "CNY": 7.24, "INR": 83.40, "MXN": 17.15,
    "BRL": 4.97, "KRW": 1320.0, "SGD": 1.34, "HKD": 7.82, "SEK": 10.45,
    "NOK": 10.62, "DKK": 6.87, "NZD": 1.65, "THB": 35.80, "TWD": 31.50,
    "AED": 3.67, "SAR": 3.75, "ZAR": 18.60, "TRY": 32.10, "PLN": 3.98,
}


def _seed_from(*args) -> int:
    raw = "|".join(str(a) for a in args)
    return int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)


def _get_rate(from_currency: str, to_currency: str) -> float:
    """Get exchange rate with slight randomization for realism."""
    from_c = from_currency.upper()
    to_c = to_currency.upper()

    if from_c not in BASE_RATES or to_c not in BASE_RATES:
        return 0.0

    # Convert through USD
    from_usd = BASE_RATES[from_c]
    to_usd = BASE_RATES[to_c]
    base_rate = to_usd / from_usd

    # Add slight daily variance (seeded by date for consistency within a day)
    seed = _seed_from(from_c, to_c, datetime.now().strftime("%Y-%m-%d"))
    rng = random.Random(seed)
    variance = rng.uniform(-0.005, 0.005)

    return round(base_rate * (1 + variance), 6)


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount from one currency to another.

    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., "USD", "EUR", "JPY")
        to_currency: Target currency code (e.g., "JPY", "GBP", "EUR")

    Returns:
        JSON string with conversion result including rate, converted amount,
        and timestamp.
    """
    from_c = from_currency.upper()
    to_c = to_currency.upper()
    rate = _get_rate(from_c, to_c)

    if rate == 0.0:
        return json.dumps({
            "error": f"Unsupported currency pair: {from_c}/{to_c}",
            "supported_currencies": sorted(BASE_RATES.keys()),
        })

    converted = round(amount * rate, 2)

    result = {
        "from": {"amount": amount, "currency": from_c},
        "to": {"amount": converted, "currency": to_c},
        "rate": rate,
        "inverse_rate": round(1 / rate, 6),
        "timestamp": datetime.now().isoformat(),
        "source": "market_mid_rate",
    }
    return json.dumps(result, indent=2)


@tool
def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """Get the current exchange rate between two currencies.

    Args:
        from_currency: Source currency code (e.g., "USD", "EUR")
        to_currency: Target currency code (e.g., "JPY", "GBP")

    Returns:
        JSON string with current rate, inverse rate, and supported currencies.
    """
    from_c = from_currency.upper()
    to_c = to_currency.upper()
    rate = _get_rate(from_c, to_c)

    if rate == 0.0:
        return json.dumps({
            "error": f"Unsupported currency pair: {from_c}/{to_c}",
            "supported_currencies": sorted(BASE_RATES.keys()),
        })

    result = {
        "pair": f"{from_c}/{to_c}",
        "rate": rate,
        "inverse_rate": round(1 / rate, 6),
        "timestamp": datetime.now().isoformat(),
        "source": "market_mid_rate",
    }
    return json.dumps(result, indent=2)
