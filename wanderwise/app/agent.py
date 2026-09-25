# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from google import genai
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types

MODEL = "gemini-3.6-flash"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"
PROJECT_ID = "qwiklabs-gcp-04-f382432f53cb"
STORAGE_BUCKET_NAME = "wanderwise-destinations-qwiklabs-gcp-04-f382432f53cb"

# -----------------------------------------------------------------------------
# Function Tools
# -----------------------------------------------------------------------------


def get_destination_details(destination: str) -> dict:
    """Fetch details for a destination from the Firestore catalog.

    Args:
        destination: Name or ID of the destination (e.g., 'algarve-portugal', 'niseko-japan', 'boston-usa').

    Returns:
        Destination details including budget, activities, visa, and safety.
    """
    db = firestore.Client(project=PROJECT_ID)
    slug = re.sub(r"[^a-z0-9]+", "-", destination.strip().lower()).strip("-")
    doc = db.collection("destinations").document(slug).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    # Partial match search if direct ID lookup fails
    for d in db.collection("destinations").stream():
        data = d.to_dict()
        name = data.get("name", "").lower()
        country = data.get("country", "").lower()
        query = destination.strip().lower()
        if query in name or query in country or query in d.id.lower():
            data["id"] = d.id
            return data

    return {"error": f"Destination '{destination}' not found in catalog."}


_ADVISORY_CACHE: dict[str, dict] = {}


def check_travel_advisories(country_or_destination: str) -> dict:
    """Fetch live official travel advisory and political stability rating.

    Queries the U.S. Department of State official travel advisories.

    Args:
        country_or_destination: Country or destination name (e.g. 'Portugal', 'Japan', 'Mexico', 'United States').

    Returns:
        Official advisory level (Level 1-4), safety summary, and tension warnings.
    """
    clean = country_or_destination.strip().lower()

    if any(us in clean for us in ["usa", "united states", "us", "domestic", "boston", "hawaii"]):
        return {
            "country": "United States",
            "advisory_level": "Level 1: Normal Precautions",
            "status": "Domestic travel. Standard precautions apply.",
            "is_safe": True,
            "has_conflict_warning": False,
        }

    global _ADVISORY_CACHE
    if not _ADVISORY_CACHE:
        try:
            req = urllib.request.Request(
                "https://travel.state.gov/_res/rss/TAsTWs.xml",
                headers={"User-Agent": "WanderWiseAgent/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                root = ET.fromstring(resp.read())
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                desc = item.findtext("description", "")
                link = item.findtext("link", "")
                country_key = title.split(" - ")[0].replace("Travel Advisory", "").strip().lower()
                clean_desc = re.sub(r"<[^>]+>", " ", desc)
                clean_desc = html.unescape(clean_desc).strip()

                level = "Level 1: Exercise Normal Precautions"
                if "Level 4" in title or "Do Not Travel" in title:
                    level = "Level 4: Do Not Travel"
                elif "Level 3" in title or "Reconsider" in title:
                    level = "Level 3: Reconsider Travel"
                elif "Level 2" in title or "Caution" in title:
                    level = "Level 2: Exercise Increased Caution"

                has_conflict = any(w in clean_desc.lower() for w in ["armed conflict", "civil unrest", "war", "terrorism"])

                _ADVISORY_CACHE[country_key] = {
                    "country": title.split(" - ")[0].strip(),
                    "advisory_level": level,
                    "summary": clean_desc[:250] + ("..." if len(clean_desc) > 250 else ""),
                    "is_safe": "Level 4" not in level and "Level 3" not in level,
                    "has_conflict_warning": has_conflict,
                    "official_url": link,
                }
        except Exception:
            pass

    for k, v in _ADVISORY_CACHE.items():
        if clean in k or k in clean:
            return v

    return {
        "country": country_or_destination,
        "advisory_level": "Level 1: Exercise Normal Precautions",
        "summary": "No active travel warnings found.",
        "is_safe": True,
        "has_conflict_warning": False,
    }


def search_destinations(season: str = "", activity: str = "", kid_friendly: bool = False) -> list[dict]:
    """Search travel destinations in the Firestore catalog.

    Args:
        season: Travel season ('spring', 'summer', 'fall', 'winter').
        activity: Interest/activity ('beaches', 'hikes', 'skiing', 'culture').
        kid_friendly: Filter for kid-friendly destinations.
    """
    db = firestore.Client(project=PROJECT_ID)
    results = []
    for doc in db.collection("destinations").stream():
        data = doc.to_dict()
        data["id"] = doc.id
        if season and season.lower() not in [s.lower() for s in data.get("best_seasons", [])]:
            continue
        if activity and not any(activity.lower() in a.lower() for a in data.get("activities", [])):
            continue
        if kid_friendly and not data.get("kid_friendly", False):
            continue
        results.append(data)
    return results


WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    51: "Light drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    85: "Snow showers",
    95: "Thunderstorm",
}


def get_destination_weather(destination: str) -> dict:
    """Fetch current real-time weather and forecast for a destination using Open-Meteo public API.

    From the public-apis directory (https://open-meteo.com).
    Reads optional OPEN_METEO_API_KEY from environment if configured.

    Args:
        destination: City or destination name (e.g., 'Algarve', 'Faro', 'Niseko', 'Boston', 'Banff', 'Zermatt').

    Returns:
        Current temperature (°C and °F), weather conditions, and forecast.
    """
    city_aliases = {"algarve": "Faro", "costa rica": "San Jose"}
    clean_name = destination.lower().split(",")[0].strip()
    query_city = city_aliases.get(clean_name, clean_name)

    api_key = os.getenv("OPEN_METEO_API_KEY", "")
    key_param = f"&apikey={api_key}" if api_key else ""

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(query_city)}&count=1&language=en&format=json{key_param}"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "WanderWiseAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode())

        results = geo_data.get("results")
        if not results:
            return {"error": f"Could not locate destination '{destination}' for weather."}

        loc = results[0]
        lat, lon = loc["latitude"], loc["longitude"]

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
            f"&daily=temperature_2m_max,temperature_2m_min&timezone=auto{key_param}"
        )
        wreq = urllib.request.Request(weather_url, headers={"User-Agent": "WanderWiseAgent/1.0"})
        with urllib.request.urlopen(wreq, timeout=5) as wresp:
            weather_data = json.loads(wresp.read().decode())

        current = weather_data.get("current", {})
        daily = weather_data.get("daily", {})
        temp_c = current.get("temperature_2m", 0.0)
        temp_f = round(temp_c * 9 / 5 + 32, 1)
        code = current.get("weather_code", 0)
        condition = WMO_WEATHER_CODES.get(code, "Variable conditions")

        return {
            "destination": loc.get("name"),
            "country": loc.get("country"),
            "current_temperature_c": temp_c,
            "current_temperature_f": temp_f,
            "condition": condition,
            "high_temp_f": round(daily.get("temperature_2m_max", [temp_c])[0] * 9 / 5 + 32, 1),
            "low_temp_f": round(daily.get("temperature_2m_min", [temp_c])[0] * 9 / 5 + 32, 1),
            "precipitation_mm": current.get("precipitation", 0.0),
        }
    except Exception as e:
        return {"error": f"Failed to fetch weather: {e}"}


async def generate_destination_image(
    destination: str,
    description: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Generate a high-quality photo for a travel destination and save as an artifact and public image.

    Uses gemini-3.1-flash-lite-image in the global region.
    Saves image with tool_context.save_artifact for Playground Artifacts, and uploads
    in-memory bytes to the public Cloud Storage bucket returning its public HTTPS URL.

    Args:
        destination: Name of the destination (e.g. 'Algarve, Portugal', 'Niseko, Japan', 'Banff, Canada').
        description: Optional details for the scene (e.g. 'golden cliffs at sunset', 'powder snow skiing').

    Returns:
        Public HTTPS URL and artifact filename of the generated image.
    """
    prompt = f"Stunning, vibrant, high quality travel photograph of {destination}."
    if description:
        prompt += f" {description}"

    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    image_bytes = None
    mime_type = "image/jpeg"
    for part in response.parts:
        if part.inline_data:
            image_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or "image/jpeg"
            break

    if not image_bytes:
        return {"error": f"Failed to generate image for {destination}."}

    slug = re.sub(r"[^a-z0-9]+", "-", destination.strip().lower()).strip("-")
    timestamp = int(time.time())
    ext = "jpg" if "jpeg" in mime_type else "png"
    filename = f"{slug}_{timestamp}.{ext}"

    # 1. Save artifact for Playground's Artifacts panel
    if tool_context is not None:
        try:
            artifact_part = types.Part(inline_data=types.Blob(mime_type=mime_type, data=image_bytes))
            await tool_context.save_artifact(filename, artifact_part)
        except Exception:
            pass

    # 2. Upload image bytes directly in-memory to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{filename}"

    return {
        "status": "success",
        "destination": destination,
        "public_image_url": public_url,
        "artifact_filename": filename,
        "message": f"Generated image for {destination}. Public URL: {public_url}",
    }


# -----------------------------------------------------------------------------
# Agent Definition
# -----------------------------------------------------------------------------

WANDERWISE_INSTRUCTION = """You are WanderWise, an intelligent travel destination curator.
Your mission is to help travelers discover, evaluate, and budget ideal travel destinations based on:
1. Time of year / season: Call `get_destination_weather` to check live temperatures and conditions.
2. Interests & activities (hikes, skiing, beaches, kid-friendly)
3. Travel party (solo, couples, families with kids)
4. Visa and origin (domestic vs. international)
5. Safety and political stability: ALWAYS call `check_travel_advisories` to ensure destinations are safe and avoid political tension or conflict zones.
6. Total Cost of Trip (TCO): Evaluate airfare + lodging + daily food + activities. Never reject a destination based on flights alone if ground costs are low.
7. Visuals: When users ask to see or generate a photo/image of a destination, use `generate_destination_image` to create and share the public image.

CRITICAL BEHAVIOR:
- If a user asks for recommendations without enough details (season, activities, traveling party, visa), ask 1-2 friendly clarifying questions first.
- Always call `check_travel_advisories`, `get_destination_details`, and `get_destination_weather` to verify safety, seasonal weather, and ground data.
- When generating images, display the resulting public image markdown link `![Destination](url)`.
"""

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=WANDERWISE_INSTRUCTION,
    tools=[
        check_travel_advisories,
        get_destination_details,
        search_destinations,
        get_destination_weather,
        generate_destination_image,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
