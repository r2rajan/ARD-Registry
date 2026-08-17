"""Mock travel tools for the Flight & Hotel Specialist agent.

Returns deterministic but realistic mock data using seeded random generation.
No external travel API required.
"""

import hashlib
import json
import random
from datetime import datetime, timedelta

from strands import tool


def _seed_from(*args) -> int:
    """Create a deterministic seed from input arguments."""
    raw = "|".join(str(a) for a in args)
    return int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)


# --- Flight data generators ---

CARRIERS = [
    "ANA", "JAL", "United", "Delta", "Singapore Airlines",
    "Cathay Pacific", "Korean Air", "EVA Air",
]
CABINS = ["Economy", "Premium Economy", "Business"]


def _generate_flight(
    origin: str, destination: str, date: str, seed: int, index: int
) -> dict:
    """Generate a single realistic flight option."""
    rng = random.Random(seed + index)

    carrier = rng.choice(CARRIERS)
    flight_no = f"{carrier[:2].upper()}{rng.randint(100, 999)}"
    depart_hour = rng.randint(6, 22)
    depart_minute = rng.choice([0, 15, 30, 45])
    flight_hours = rng.randint(8, 14)
    stops = rng.choices([0, 1, 2], weights=[50, 35, 15])[0]
    cabin = rng.choice(CABINS)

    base_price = {"Economy": 800,
                  "Premium Economy": 1500, "Business": 3500}[cabin]
    price = round(base_price * rng.uniform(0.7, 1.4), 2)

    depart_dt = datetime.fromisoformat(
        f"{date}T{depart_hour:02d}:{depart_minute:02d}:00")
    arrive_dt = depart_dt + \
        timedelta(hours=flight_hours, minutes=rng.randint(0, 59))

    return {
        "carrier": carrier,
        "flight_no": flight_no,
        "origin": origin.upper(),
        "destination": destination.upper(),
        "depart": depart_dt.isoformat(),
        "arrive": arrive_dt.isoformat(),
        "stops": stops,
        "price_usd": price,
        "cabin": cabin,
    }


@tool
def search_flights(origin: str, destination: str, depart_date: str, return_date: str) -> str:
    """Search for available flights between two cities.

    Args:
        origin: Origin airport code (e.g., "SFO", "LAX", "JFK")
        destination: Destination airport code (e.g., "NRT", "HND", "LHR")
        depart_date: Departure date in YYYY-MM-DD format
        return_date: Return date in YYYY-MM-DD format

    Returns:
        JSON string with outbound and return flight options including carrier,
        flight number, departure/arrival times, stops, price, and cabin class.
    """
    seed = _seed_from(origin, destination, depart_date, return_date)

    outbound_flights = [
        _generate_flight(origin, destination, depart_date, seed, i)
        for i in range(4)
    ]
    return_flights = [
        _generate_flight(destination, origin, return_date, seed + 1000, i)
        for i in range(4)
    ]

    outbound_flights.sort(key=lambda f: f["price_usd"])
    return_flights.sort(key=lambda f: f["price_usd"])

    result = {
        "outbound": outbound_flights,
        "return": return_flights,
        "search_params": {
            "origin": origin.upper(),
            "destination": destination.upper(),
            "depart_date": depart_date,
            "return_date": return_date,
        },
    }
    return json.dumps(result, indent=2)


# --- Hotel data generators ---

HOTEL_CHAINS = [
    "Park Hyatt", "The Ritz-Carlton", "Four Seasons", "Mandarin Oriental",
    "Conrad", "W Hotel", "Hilton", "Marriott", "APA Hotel", "Tokyu Stay",
    "Hotel Gracery", "Mitsui Garden", "Cerulean Tower", "Aman",
]
NEIGHBORHOODS = {
    "NRT": ["Shinjuku", "Shibuya", "Ginza", "Roppongi", "Asakusa", "Akihabara", "Marunouchi"],
    "HND": ["Shinjuku", "Shibuya", "Ginza", "Roppongi", "Asakusa", "Akihabara", "Marunouchi"],
    "LHR": ["Mayfair", "Covent Garden", "South Kensington", "Westminster", "Soho", "The City"],
    "CDG": ["Le Marais", "Saint-Germain", "Champs-Élysées", "Montmartre", "Bastille"],
    "DEFAULT": ["Downtown", "City Center", "Waterfront", "Arts District", "Old Town"],
}


def _generate_hotel(
    destination: str, checkin: str, checkout: str, preferences: str, seed: int, index: int
) -> dict:
    """Generate a single realistic hotel option."""
    rng = random.Random(seed + index + 2000)

    neighborhoods = NEIGHBORHOODS.get(
        destination.upper(), NEIGHBORHOODS["DEFAULT"])
    name = f"{rng.choice(HOTEL_CHAINS)} {rng.choice(neighborhoods)}"
    stars = rng.choices([3, 4, 5], weights=[20, 50, 30])[0]
    neighborhood = rng.choice(neighborhoods)

    base_nightly = {3: 120, 4: 220, 5: 450}[stars]
    if preferences and "budget" in preferences.lower():
        base_nightly *= 0.6
    elif preferences and "luxury" in preferences.lower():
        base_nightly *= 1.5

    nightly_usd = round(base_nightly * rng.uniform(0.8, 1.3), 2)

    try:
        d_in = datetime.fromisoformat(checkin)
        d_out = datetime.fromisoformat(checkout)
        nights = max((d_out - d_in).days, 1)
    except (ValueError, TypeError):
        nights = 3

    total_usd = round(nightly_usd * nights, 2)
    refundable = rng.random() > 0.3

    return {
        "name": name,
        "stars": stars,
        "nightly_usd": nightly_usd,
        "total_usd": total_usd,
        "nights": nights,
        "neighborhood": neighborhood,
        "refundable": refundable,
        "amenities": rng.sample(
            ["WiFi", "Pool", "Gym", "Spa", "Restaurant",
                "Bar", "Concierge", "Breakfast"],
            k=rng.randint(3, 6),
        ),
    }


@tool
def search_hotels(destination: str, checkin: str, checkout: str, preferences: str) -> str:
    """Search for available hotels at a destination.

    Args:
        destination: Destination city or airport code (e.g., "NRT", "Tokyo", "LHR")
        checkin: Check-in date in YYYY-MM-DD format
        checkout: Check-out date in YYYY-MM-DD format
        preferences: Guest preferences (e.g., "mid-range", "luxury", "budget", "near station")

    Returns:
        JSON string with hotel options including name, stars, nightly/total price,
        neighborhood, refund policy, and amenities.
    """
    seed = _seed_from(destination, checkin, checkout, preferences)

    hotels = [
        _generate_hotel(destination, checkin, checkout, preferences, seed, i)
        for i in range(5)
    ]

    hotels.sort(key=lambda h: h["nightly_usd"])

    result = {
        "hotels": hotels,
        "search_params": {
            "destination": destination,
            "checkin": checkin,
            "checkout": checkout,
            "preferences": preferences,
        },
    }
    return json.dumps(result, indent=2)
