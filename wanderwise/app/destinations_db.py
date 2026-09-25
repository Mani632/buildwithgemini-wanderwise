"""Firestore integration for WanderWise destination catalog.

CRITICAL: Hardcodes project ID 'qwiklabs-gcp-04-f382432f53cb' to avoid
Agent Platform project number resolution failure.
"""

import json
import re
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-f382432f53cb"
COLLECTION_NAME = "destinations"

_db = None


def get_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def search_destinations(
    season: str = "",
    activity: str = "",
    max_daily_budget_usd: float = 0.0,
    kid_friendly: bool = False,
    continent: str = "",
) -> str:
    """Search and filter travel destinations in the Firestore catalog.

    Args:
        season: Preferred season of travel, e.g., 'summer', 'winter', 'spring', 'fall'. Leave empty to match all.
        activity: Interest/activity to match, e.g., 'hikes', 'skiing', 'beaches', 'culture', 'wildlife'. Leave empty to match all.
        max_daily_budget_usd: Maximum daily spend per person on the ground (lodging + food + transit). 0 means no limit.
        kid_friendly: Set to True if travel party requires kid-friendly spots.
        continent: Region/continent filter, e.g., 'Europe', 'North America', 'Asia', 'Central America'. Leave empty for all.

    Returns:
        JSON string containing list of matching destinations with summary details.
    """
    db = get_db()
    docs = db.collection(COLLECTION_NAME).stream()

    results = []
    season_clean = season.strip().lower()
    activity_clean = activity.strip().lower()
    continent_clean = continent.strip().lower()

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        # Season filter
        if season_clean:
            seasons = [s.lower() for s in data.get("best_seasons", [])]
            if season_clean not in seasons:
                continue

        # Activity filter
        if activity_clean:
            acts = [a.lower() for a in data.get("activities", [])]
            # Match substring or exact
            if not any(activity_clean in a or a in activity_clean for a in acts):
                continue

        # Kid friendly filter
        if kid_friendly and not data.get("kid_friendly", False):
            continue

        # Daily budget filter
        daily_spend = float(data.get("estimated_daily_spend_usd", 0.0))
        if max_daily_budget_usd > 0 and daily_spend > max_daily_budget_usd:
            continue

        # Continent filter
        if continent_clean and continent_clean not in data.get("continent", "").lower():
            continue

        results.append(data)

    if not results:
        return f"No destinations matched the criteria: season='{season}', activity='{activity}', kid_friendly={kid_friendly}, max_budget={max_daily_budget_usd}."

    return json.dumps(results, indent=2)


def get_destination_details(destination_id_or_name: str) -> str:
    """Fetch complete details of a specific destination from Firestore.

    Args:
        destination_id_or_name: The destination ID (e.g., 'algarve-portugal', 'niseko-japan', 'boston-usa') or city/country name.

    Returns:
        JSON string containing the complete destination record.
    """
    db = get_db()
    collection = db.collection(COLLECTION_NAME)

    clean_id = destination_id_or_name.strip().lower().replace(" ", "-")
    doc = collection.document(clean_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return json.dumps(data, indent=2)

    # Search by partial match on name or ID if direct lookup fails
    docs = collection.stream()
    search_term = destination_id_or_name.strip().lower()
    for d in docs:
        data = d.to_dict()
        if (
            search_term in d.id.lower()
            or search_term in data.get("name", "").lower()
            or search_term in data.get("country", "").lower()
        ):
            data["id"] = d.id
            return json.dumps(data, indent=2)

    return f"Destination '{destination_id_or_name}' not found in the catalog."


def add_destination(
    name: str,
    country: str,
    continent: str,
    best_seasons: list[str],
    activities: list[str],
    kid_friendly: bool,
    safety_rating: str,
    visa_type: str,
    estimated_daily_spend_usd: float,
    typical_flight_cost_usd: float,
    highlights: list[str],
    total_cost_notes: str,
) -> str:
    """Add a new destination to the Firestore catalog.

    Args:
        name: Name of destination (e.g. 'Phuket, Thailand')
        country: Country name
        continent: Continent or region
        best_seasons: List of best travel seasons, e.g., ['winter', 'spring']
        activities: List of activities, e.g., ['beaches', 'kid_friendly']
        kid_friendly: True if suitable for children/families
        safety_rating: Safety level, e.g., 'Level 1: Normal Precautions'
        visa_type: Visa info, e.g., 'International (Visa on arrival / 30-day visa-free)'
        estimated_daily_spend_usd: Estimated daily ground spend per person
        typical_flight_cost_usd: Estimated typical round-trip flight cost from US
        highlights: Key attractions/experiences
        total_cost_notes: Explanation of flight vs ground cost dynamics

    Returns:
        Confirmation string with the new destination ID.
    """
    db = get_db()
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    doc_ref = db.collection(COLLECTION_NAME).document(slug)

    payload = {
        "id": slug,
        "name": name,
        "country": country,
        "continent": continent,
        "best_seasons": best_seasons,
        "activities": activities,
        "kid_friendly": kid_friendly,
        "safety_rating": safety_rating,
        "visa_type": visa_type,
        "estimated_daily_spend_usd": float(estimated_daily_spend_usd),
        "typical_flight_cost_usd": float(typical_flight_cost_usd),
        "highlights": highlights,
        "total_cost_notes": total_cost_notes,
    }

    doc_ref.set(payload)
    return f"Successfully added destination '{name}' to Firestore with ID '{slug}'."


def calculate_total_trip_cost(
    destination_id_or_name: str,
    days: int = 7,
    travelers: int = 1,
) -> str:
    """Calculate the comprehensive Total Cost of Trip (TCO) for a destination.

    Factors flights + daily ground spend (lodging, dining, activities) across travelers and duration.

    Args:
        destination_id_or_name: ID or name of destination (e.g. 'algarve-portugal', 'boston-usa')
        days: Trip duration in days (default 7)
        travelers: Number of travelers (default 1)

    Returns:
        Itemized cost breakdown comparing airfare vs on-the-ground expenses.
    """
    details_str = get_destination_details(destination_id_or_name)
    if "not found" in details_str:
        return details_str

    data = json.loads(details_str)
    flight_per_person = float(data.get("typical_flight_cost_usd", 0.0))
    daily_per_person = float(data.get("estimated_daily_spend_usd", 0.0))

    total_flights = flight_per_person * travelers
    total_ground = daily_per_person * days * travelers
    total_trip_cost = total_flights + total_ground

    result = {
        "destination": data.get("name"),
        "duration_days": days,
        "travelers": travelers,
        "airfare": {
            "per_person_estimate": flight_per_person,
            "total_airfare": total_flights,
        },
        "ground_expenses": {
            "daily_per_person_estimate": daily_per_person,
            "total_ground_cost": total_ground,
        },
        "total_trip_cost": total_trip_cost,
        "average_cost_per_person": round(total_trip_cost / travelers, 2) if travelers else 0,
        "average_cost_per_day": round(total_trip_cost / days, 2) if days else 0,
        "cost_insight": data.get("total_cost_notes", ""),
    }

    return json.dumps(result, indent=2)
