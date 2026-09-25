"""Seed script to populate Firestore with travel destination catalog.

Hardcodes GCP Project ID to prevent project number resolution issues on Agent Platform.
"""

from google.cloud import firestore

# CRITICAL: Hardcode the project ID string, never use google.auth.default() or GOOGLE_CLOUD_PROJECT
PROJECT_ID = "qwiklabs-gcp-04-f382432f53cb"
COLLECTION_NAME = "destinations"

DESTINATIONS = [
    {
        "id": "algarve-portugal",
        "name": "Algarve, Portugal",
        "country": "Portugal",
        "continent": "Europe",
        "best_seasons": ["spring", "summer", "fall"],
        "activities": ["beaches", "hikes", "coastal_walks", "kid_friendly", "surfing"],
        "kid_friendly": True,
        "safety_rating": "Level 1: Normal Precautions (Low Tension)",
        "visa_type": "International (Schengen Area - 90 days visa-free for US/EU/UK)",
        "estimated_daily_spend_usd": 70.0,
        "typical_flight_cost_usd": 750.0,
        "highlights": [
            "Ponta da Piedade sea cliffs",
            "Benagil Cave boat tours",
            "Family-friendly calm beaches",
            "Affordable fresh seafood",
        ],
        "total_cost_notes": "Flight is $700-$800, but daily expenses ($70/day) are so low that a 7-10 day trip is often cheaper than domestic beach resorts.",
    },
    {
        "id": "niseko-japan",
        "name": "Niseko (Hokkaido), Japan",
        "country": "Japan",
        "continent": "Asia",
        "best_seasons": ["winter"],
        "activities": ["skiing", "snowboarding", "hot_springs", "kid_friendly"],
        "kid_friendly": True,
        "safety_rating": "Level 1: Normal Precautions (Exceptionally Safe)",
        "visa_type": "International (Visa-free 90 days for US/EU/Canada/UK)",
        "estimated_daily_spend_usd": 120.0,
        "typical_flight_cost_usd": 950.0,
        "highlights": [
            "Legendary powder snow",
            "Onsen hot springs after ski",
            "Kid-friendly ski schools with English instructors",
        ],
        "total_cost_notes": "Ski passes ($55/day) and dining in Japan cost under half of Colorado/Utah resorts, offsetting the flight for groups.",
    },
    {
        "id": "banff-canada",
        "name": "Banff & Lake Louise, Canada",
        "country": "Canada",
        "continent": "North America",
        "best_seasons": ["summer", "winter", "fall"],
        "activities": ["hikes", "skiing", "lakes", "kid_friendly", "wildlife"],
        "kid_friendly": True,
        "safety_rating": "Level 1: Normal Precautions (Very High Stability)",
        "visa_type": "International / Easy Entry (Visa-free for US citizens)",
        "estimated_daily_spend_usd": 140.0,
        "typical_flight_cost_usd": 450.0,
        "highlights": [
            "Turquoise waters of Lake Louise and Moraine Lake",
            "Plain of Six Glaciers teahouse trail",
            "Banff Sunshine & Lake Louise ski areas",
        ],
        "total_cost_notes": "Accessible flights with favorable currency exchange, moderate overall budget for family mountain trips.",
    },
    {
        "id": "boston-usa",
        "name": "Boston & Cape Cod, USA",
        "country": "USA",
        "continent": "North America",
        "best_seasons": ["summer", "fall"],
        "activities": ["history", "culture", "beaches", "kid_friendly", "food"],
        "kid_friendly": True,
        "safety_rating": "Level 1: Normal Precautions (Domestic Safe)",
        "visa_type": "Domestic (No visa needed for US residents)",
        "estimated_daily_spend_usd": 280.0,
        "typical_flight_cost_usd": 220.0,
        "highlights": [
            "Historic Freedom Trail walk",
            "Boston Children's Museum & Aquarium",
            "Cape Cod National Seashore dunes",
        ],
        "total_cost_notes": "Flights are very cheap ($200-$250), but hotel rates ($300+/night) and dining mean total trip cost can easily exceed international spots.",
    },
    {
        "id": "costa-rica",
        "name": "Manuel Antonio & Arenal, Costa Rica",
        "country": "Costa Rica",
        "continent": "Central America",
        "best_seasons": ["winter", "spring"],
        "activities": ["hikes", "beaches", "wildlife", "kid_friendly", "rainforest"],
        "kid_friendly": True,
        "safety_rating": "Level 1: Normal Precautions (Peaceful Democracy)",
        "visa_type": "International (Visa-free 90 days for US/EU)",
        "estimated_daily_spend_usd": 85.0,
        "typical_flight_cost_usd": 500.0,
        "highlights": [
            "Sloths, monkeys, and toucans in national parks",
            "Warm Pacific beaches safe for children",
            "Arenal volcano hot springs & zip-lines",
        ],
        "total_cost_notes": "Short flight times, reasonable airfare, and affordable ecolodges create strong total trip value.",
    },
    {
        "id": "zermatt-switzerland",
        "name": "Zermatt & Matterhorn, Switzerland",
        "country": "Switzerland",
        "continent": "Europe",
        "best_seasons": ["winter", "summer"],
        "activities": ["skiing", "hikes", "alpine_views"],
        "kid_friendly": False,
        "safety_rating": "Level 1: Normal Precautions (Top Global Stability)",
        "visa_type": "International (Schengen Zone)",
        "estimated_daily_spend_usd": 310.0,
        "typical_flight_cost_usd": 850.0,
        "highlights": [
            "Matterhorn glacier paradise",
            "Year-round glacier skiing and scenic hiking",
            "Gornergrat mountain cog railway",
        ],
        "total_cost_notes": "Premium destination: both flights and daily ground expenses (lodging, mountain passes, fondue dinners) are high.",
    },
    {
        "id": "oaxaca-mexico",
        "name": "Oaxaca Valley, Mexico",
        "country": "Mexico",
        "continent": "North America",
        "best_seasons": ["fall", "winter", "spring"],
        "activities": ["culture", "food", "hikes", "kid_friendly"],
        "kid_friendly": True,
        "safety_rating": "Level 2: Exercise Increased Caution (Oaxaca tourist areas are calm & low tension)",
        "visa_type": "International (Visa-free for US/EU/Canada)",
        "estimated_daily_spend_usd": 55.0,
        "typical_flight_cost_usd": 400.0,
        "highlights": [
            "Zapotec ruins at Monte Albán",
            "Hierve el Agua cliffside calcified springs",
            "World-famous mole and artisanal chocolate markets",
        ],
        "total_cost_notes": "Low airfare combined with exceptional food and stays for ~$55/day make this one of the highest value cultural trips available.",
    },
]


def seed():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection(COLLECTION_NAME)

    for item in DESTINATIONS:
        doc_id = item["id"]
        doc_ref = collection.document(doc_id)
        doc_ref.set(item)
        print(f"  ✓ Seeded destination: {item['name']} ({doc_id})")

    print(f"\n🎉 Successfully seeded {len(DESTINATIONS)} destinations into Firestore collection '{COLLECTION_NAME}'!")


if __name__ == "__main__":
    seed()
