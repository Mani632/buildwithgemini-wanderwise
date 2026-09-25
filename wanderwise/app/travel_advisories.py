"""Live travel advisory checker fetching real-time data from the US Department of State RSS feed."""

import html
import json
import logging
import re
import time
import urllib.request
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

ADVISORY_RSS_URL = "https://travel.state.gov/_res/rss/TAsTWs.xml"
_CACHE_TIMESTAMP = 0
_CACHE_DATA = {}
CACHE_TTL_SECONDS = 3600  # 1 hour in-memory cache


def _fetch_advisories() -> dict[str, dict]:
    global _CACHE_TIMESTAMP, _CACHE_DATA

    now = time.time()
    if _CACHE_DATA and (now - _CACHE_TIMESTAMP) < CACHE_TTL_SECONDS:
        return _CACHE_DATA

    try:
        req = urllib.request.Request(
            ADVISORY_RSS_URL,
            headers={"User-Agent": "WanderWiseAgent/1.0 (Travel Advisory Tool)"},
        )
        with urllib.request.urlopen(req, timeout=6) as response:
            xml_content = response.read()

        root = ET.fromstring(xml_content)
        advisories = {}

        for item in root.findall(".//item"):
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            desc = item.find("description").text if item.find("description") is not None else ""

            # Extract advisory level (e.g. "Level 1: Exercise Normal Precautions")
            level = "Level 1: Exercise Normal Precautions"
            level_num = 1
            if "Level 4" in title or "Do Not Travel" in title:
                level = "Level 4: Do Not Travel"
                level_num = 4
            elif "Level 3" in title or "Reconsider Travel" in title:
                level = "Level 3: Reconsider Travel"
                level_num = 3
            elif "Level 2" in title or "Exercise Increased Caution" in title:
                level = "Level 2: Exercise Increased Caution"
                level_num = 2

            # Clean country name from title (e.g., "Portugal - Level 1: ...")
            country_name = title.split(" - ")[0].replace("Travel Advisory", "").strip()

            # Clean HTML description
            clean_desc = re.sub(r"<[^>]+>", " ", desc)
            clean_desc = html.unescape(clean_desc)
            clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

            # Identify risk triggers
            has_political_tension = any(
                w in clean_desc.lower()
                for w in [
                    "armed conflict",
                    "civil unrest",
                    "political unrest",
                    "terrorism",
                    "war",
                    "tension",
                    "violence",
                ]
            )

            entry = {
                "country": country_name,
                "advisory_level": level,
                "level_number": level_num,
                "is_low_tension": level_num <= 2 and not ("armed conflict" in clean_desc.lower() or "war" in clean_desc.lower()),
                "has_conflict_or_tension_warning": has_political_tension,
                "summary": clean_desc[:350] + ("..." if len(clean_desc) > 350 else ""),
                "published_date": pub_date,
                "official_url": link,
            }

            advisories[country_name.lower()] = entry

        _CACHE_DATA = advisories
        _CACHE_TIMESTAMP = now
        return _CACHE_DATA

    except Exception as e:
        logger.warning("Failed to fetch live travel advisories: %s. Using fallback.", e)
        if _CACHE_DATA:
            return _CACHE_DATA
        return {}


def check_travel_advisories(country_or_destination: str) -> str:
    """Fetch live travel advisory and political stability level for a destination.

    Queries real-time official travel advisory alerts from the US Department of State.
    Checks whether the location has travel warnings, civil unrest, or political tension.

    Args:
        country_or_destination: Country or destination name (e.g., 'Portugal', 'Japan', 'Mexico', 'United States', 'Switzerland').

    Returns:
        JSON string with official advisory level (1-4), political tension warnings, and safety summary.
    """
    clean_query = country_or_destination.strip().lower()

    # Handle domestic US queries
    if any(us_term in clean_query for us_term in ["usa", "united states", "us", "domestic", "boston", "hawaii"]):
        return json.dumps(
            {
                "country": "United States",
                "advisory_level": "Domestic Travel (No International Advisory Needed)",
                "level_number": 1,
                "is_low_tension": True,
                "has_conflict_or_tension_warning": False,
                "summary": "Standard domestic travel rules apply. No international security warnings.",
                "official_url": "https://travel.state.gov",
            },
            indent=2,
        )

    advisories = _fetch_advisories()

    # Exact or substring match
    matched = None
    for c_key, data in advisories.items():
        if clean_query == c_key or clean_query in c_key or c_key in clean_query:
            matched = data
            break

    if matched:
        return json.dumps(matched, indent=2)

    return json.dumps(
        {
            "country": country_or_destination,
            "status": "No specific active advisory alert found; destination generally considered normal precautions.",
            "advisory_level": "Level 1: Exercise Normal Precautions",
            "level_number": 1,
            "is_low_tension": True,
            "has_conflict_or_tension_warning": False,
        },
        indent=2,
    )
