"""Mock activities tool for the Local Activities Agent.

Returns deterministic but realistic activity recommendations using
seeded random generation. No external API required.
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


# Activity databases by destination
ACTIVITIES = {
    "DEFAULT": {
        "restaurants": [
            ("The Local Kitchen", "Farm-to-table seasonal cuisine"),
            ("Harbor Grill", "Fresh seafood with waterfront views"),
            ("Noodle House", "Handmade noodles and dumplings"),
            ("Bistro Central", "French-inspired comfort food"),
            ("Spice Route", "Pan-Asian fusion"),
        ],
        "tours": [
            ("City Walking Tour", "Guided 3-hour walk through historic districts"),
            ("Food & Market Tour", "Sample local flavors at top markets"),
            ("Architecture Cruise", "Boat tour of iconic buildings"),
            ("Street Art Walk", "Explore vibrant mural districts"),
        ],
        "experiences": [
            ("Cooking Class", "Learn to make local specialties"),
            ("Sunset Viewpoint", "Best panoramic city views at golden hour"),
            ("Night Market", "Evening street food and live music"),
            ("Museum Pass", "Skip-the-line access to top museums"),
        ],
    },
    "TOKYO": {
        "restaurants": [
            ("Ichiran Ramen", "Solo ramen booths, rich tonkotsu broth"),
            ("Sushi Zanmai", "Fresh tsukiji-sourced omakase"),
            ("Gonpachi Nishi-Azabu", "Yakitori and soba, Kill Bill inspiration"),
            ("Afuri Ramen", "Light yuzu shio ramen, modern interior"),
            ("Genki Sushi", "Fun conveyor belt sushi, budget-friendly"),
            ("Narisawa", "Two-Michelin-star innovative Japanese"),
            ("Tsukiji Outer Market stalls", "Street food breakfast paradise"),
        ],
        "tours": [
            ("Tsukiji & Ginza Food Tour", "3-hour guided tasting walk"),
            ("Shibuya & Harajuku Pop Culture Walk", "Explore Tokyo street fashion"),
            ("Imperial Palace Gardens Tour", "Historic grounds and architecture"),
            ("Akihabara Electronics Deep Dive", "Guided tour of otaku culture"),
            ("Yanaka Old Town Walking Tour", "Traditional Tokyo neighborhood"),
        ],
        "experiences": [
            ("teamLab Borderless", "Immersive digital art museum"),
            ("Senso-ji Temple & Asakusa", "Tokyo's oldest temple, Nakamise shopping"),
            ("Robot Restaurant Shinjuku", "Wild robot cabaret show"),
            ("Meiji Shrine & Yoyogi Park", "Peaceful forested shrine in the city"),
            ("Tokyo Tower Night View", "360-degree city panorama after dark"),
            ("Onsen Day Pass", "Traditional hot spring bath experience"),
            ("Sake Tasting in Shimokitazawa", "Craft sake bar hopping"),
        ],
    },
    "LONDON": {
        "restaurants": [
            ("Dishoom", "Bombay-style cafe, legendary bacon naan"),
            ("Borough Market Stalls", "World-class food market grazing"),
            ("The Wolseley", "Grand European cafe on Piccadilly"),
            ("Flat Iron", "Simple, excellent steak for under 15 pounds"),
            ("Padella", "Fresh handmade pasta, long queues worth it"),
        ],
        "tours": [
            ("Tower of London & Crown Jewels", "Medieval history, 2-3 hours"),
            ("Thames River Cruise", "Westminster to Greenwich by boat"),
            ("Harry Potter Studio Tour", "Behind the scenes at Leavesden"),
            ("Jack the Ripper Walking Tour", "Evening tour of Whitechapel"),
        ],
        "experiences": [
            ("British Museum", "Free entry, world-class collection"),
            ("West End Show", "World-class theatre in the evening"),
            ("Sky Garden", "Free rooftop garden with city views"),
            ("Camden Market", "Eclectic shopping and street food"),
            ("Afternoon Tea", "Classic English tradition at a top hotel"),
        ],
    },
}

CATEGORIES = ["restaurants", "tours", "experiences"]
TIME_SLOTS = ["Morning", "Afternoon", "Evening", "Full Day"]
PRICE_RANGES = ["$", "$$", "$$$", "$$$$"]


def _get_activities_db(destination: str) -> dict:
    """Get the activities database for a destination."""
    dest_upper = destination.upper().strip()
    for key in ACTIVITIES:
        if key in dest_upper or dest_upper in key:
            return ACTIVITIES[key]
    # Check common airport codes
    if dest_upper in ("NRT", "HND", "TYO"):
        return ACTIVITIES["TOKYO"]
    if dest_upper in ("LHR", "LGW", "STN"):
        return ACTIVITIES["LONDON"]
    return ACTIVITIES["DEFAULT"]


@tool
def search_activities(destination: str, dates: str, preferences: str) -> str:
    """Search for recommended activities, restaurants, and experiences at a destination.

    Args:
        destination: Destination city or airport code (e.g., "Tokyo", "NRT", "London")
        dates: Trip dates (e.g., "Oct 3-7" or "2025-10-03 to 2025-10-07")
        preferences: Guest preferences (e.g., "mid-range", "foodie", "cultural", "family-friendly")

    Returns:
        JSON string with categorized activity recommendations including name,
        category, price range, time slot, rating, and description.
    """
    seed = _seed_from(destination, dates, preferences)
    rng = random.Random(seed)
    db = _get_activities_db(destination)

    activities = []

    for category in CATEGORIES:
        items = db.get(category, [])
        # Pick 3-4 items per category
        count = min(rng.randint(3, 4), len(items))
        selected = rng.sample(items, count)

        for name, description in selected:
            rating = round(rng.uniform(4.0, 5.0), 1)
            price_range = rng.choice(PRICE_RANGES)
            time_slot = rng.choice(TIME_SLOTS)

            # Adjust price based on preferences
            if preferences and "budget" in preferences.lower():
                price_range = rng.choice(["$", "$$"])
            elif preferences and "luxury" in preferences.lower():
                price_range = rng.choice(["$$$", "$$$$"])

            activities.append({
                "name": name,
                # "restaurants" -> "restaurant"
                "category": category.rstrip("s"),
                "description": description,
                "price_range": price_range,
                "time_slot": time_slot,
                "rating": rating,
                "neighborhood": rng.choice(["Central", "Old Town", "Waterfront", "Arts District", "Downtown"]),
                "bookable": rng.random() > 0.3,
            })

    result = {
        "activities": activities,
        "search_params": {
            "destination": destination,
            "dates": dates,
            "preferences": preferences,
        },
        "total_found": len(activities),
    }
    return json.dumps(result, indent=2)
