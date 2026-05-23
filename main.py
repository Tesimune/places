import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Query, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse # Added for serving static files cleanly
from pydantic import BaseModel, Field
import redis.asyncio as redis
import httpx
import json

app = FastAPI(title="Places Integration API")

# --- Configuration & State ---
# In production, pull these from environment variables
GOOGLE_API_URL = os.getenv("GOOGLE_API_URL", "https://maps.googleapis.com/maps/api")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "PREFERABLY_SET_IN_ENV")
REDIS_LOCATION = os.getenv("REDIS_LOCATION", "redis://redis:6379/1")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "valid-secret-token")

# Async Redis client
redis_client = redis.from_url(REDIS_LOCATION, decode_responses=True)
security = HTTPBearer(auto_error=False)

# --- Pydantic Schemas (Replaces DRF Serializers/Validations) ---
class PlaceResponse(BaseModel):
    name: str
    address: Optional[str] = None
    lat: float
    lng: float

class GeocodeResponse(BaseModel):
    lat: float
    lng: float
    formatted_address: str

class DetailsResponse(PlaceResponse):
    phone: Optional[str] = None
    website: Optional[str] = None

# --- Mock Database Layer ---
# Replacing Django ORM calls for this example. Pair this with Tortoise-ORM or SQLModel if needed!
class MockPlaceDB:
    @staticmethod
    async def filter_by_name(query: str, limit: int) -> List[Dict[str, Any]]:
        # Mock local DB check. Connect your async ORM layer here.
        return []

    @staticmethod
    async def get_or_create(place_id: str, defaults: Dict[str, Any]):
        # Mock saving to DB
        return defaults

class MockTokenDB:
    @staticmethod
    async def token_exists(token: str) -> bool:
        # Check token validity against your database
        return token == SECRET_TOKEN


# --- 🔑 Authentication Dependency (Replaces Middleware) ---
async def verify_token(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    # Check for internal request bypass header (used by your frontend landing page demo)
    if request.headers.get("X-Internal-Request"):
        return

    if not auth:
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    
    # Check token validity against the DB
    is_valid = await MockTokenDB.token_exists(auth.credentials)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# --- ⚡ Helper Function for Async Caching + Google API ---
async def fetch_google_data(redis_key: str, url: str, params: dict, timeout: int = 3600) -> Optional[dict]:
    # Check cache
    cached = await redis_client.get(redis_key)
    if cached:
        print(f"✅ Cache hit for {redis_key}")
        return json.loads(cached)

    # Async HTTP request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                return None
            data = response.json()
            
            # Save cache stringified
            await redis_client.set(redis_key, json.dumps(data), ex=timeout)
            return data
        except httpx.HTTPError:
            return None


# =====================================================================
# --- 🖥️ UI DEV LANDING PAGE ROOT ---
# =====================================================================

@app.get("/", tags=["UI"])
async def serve_landing_page():
    """
    Serves the developer landing interface cleanly out of your /static project directory.
    This separates frontend clutter cleanly away from your main backend endpoints logic loop!
    """
    return FileResponse("static/index.html")
    

# =====================================================================
# --- 📌 API ENDPOINTS ---
# =====================================================================

# --- 1️⃣ Search Places ---
@app.get("/api/search", response_model=List[PlaceResponse], dependencies=[Depends(verify_token)])
async def search(
    query: str = Query(..., description="Search text"),
    limit: int = Query(10, ge=1, le=50)
):
    redis_key = f"search:{query}"
    cached = await redis_client.get(redis_key)
    if cached:
        return json.loads(cached)

    # 1. Check local DB first
    local_places = await MockPlaceDB.filter_by_name(query, limit)
    if local_places:
        await redis_client.set(redis_key, json.dumps(local_places), ex=3600)
        return local_places

    # 2. Fetch from Google Text Search
    url = f"{GOOGLE_API_URL}/place/textsearch/json"
    params = {"query": query, "key": GOOGLE_API_KEY}
    data = await fetch_google_data(redis_key, url, params)

    if not data:
        raise HTTPException(status_code=503, detail="Google API request failed")

    results = []
    for item in data.get("results", [])[:limit]:
        place_data = {
            "name": item["name"],
            "address": item.get("formatted_address"),
            "lat": item["geometry"]["location"]["lat"],
            "lng": item["geometry"]["location"]["lng"],
        }
        # Save locally in background or inline
        await MockPlaceDB.get_or_create(item["place_id"], defaults=place_data)
        results.append(place_data)

    await redis_client.set(redis_key, json.dumps(results), ex=3600)
    return results


# --- 2️⃣ Nearby Places ---
@app.get("/api/nearby", response_model=List[PlaceResponse], dependencies=[Depends(verify_token)])
async def nearby(
    lat: float = Query(..., description="Latitude coordinate"),
    lng: float = Query(..., description="Longitude coordinate"),
    radius: int = Query(1000, description="Search radius in meters")
):
    redis_key = f"nearby:{lat}:{lng}:{radius}"
    cached = await redis_client.get(redis_key)
    if cached:
        return json.loads(cached)

    url = f"{GOOGLE_API_URL}/place/nearbysearch/json"
    params = {"location": f"{lat},{lng}", "radius": radius, "key": GOOGLE_API_KEY}
    data = await fetch_google_data(redis_key, url, params)

    if not data:
        raise HTTPException(status_code=503, detail="Google API request failed")

    results = [
        {
            "name": item["name"],
            "address": item.get("vicinity"),
            "lat": item["geometry"]["location"]["lat"],
            "lng": item["geometry"]["location"]["lng"]
        }
        for item in data.get("results", [])
    ]

    await redis_client.set(redis_key, json.dumps(results), ex=3600)
    return results


# --- 3️⃣ Geocoding ---
@app.get("/api/geocode", response_model=GeocodeResponse, dependencies=[Depends(verify_token)])
async def geocode(
    address: str = Query(..., description="Address to search"),
    country: Optional[str] = Query(None, description="Country filter code")
):
    redis_key = f"geocode:{address}:{country}"
    cached = await redis_client.get(redis_key)
    if cached:
        return json.loads(cached)

    url = f"{GOOGLE_API_URL}/geocode/json"
    params = {"address": address, "key": GOOGLE_API_KEY}
    if country:
        params["region"] = country

    data = await fetch_google_data(redis_key, url, params)
    if not data or not data.get("results"):
        raise HTTPException(status_code=404, detail="No results found")

    first_result = data["results"][0]
    result = {
        "lat": first_result["geometry"]["location"]["lat"],
        "lng": first_result["geometry"]["location"]["lng"],
        "formatted_address": first_result["formatted_address"]
    }

    await redis_client.set(redis_key, json.dumps(result), ex=3600)
    return result


# --- 4️⃣ Place Details ---
@app.get("/api/details", response_model=DetailsResponse, dependencies=[Depends(verify_token)])
async def details(
    place_id: Optional[str] = Query(None, description="Google Place ID"),
    lat: Optional[float] = Query(None, description="Latitude for reverse geocode fallback"),
    lng: Optional[float] = Query(None, description="Longitude for reverse geocode fallback")
):
    if not place_id and (lat is None or lng is None):
        raise HTTPException(status_code=400, detail="place_id OR lat & lng required")

    # Reverse Geocode Fallback
    if not place_id:
        url = f"{GOOGLE_API_URL}/geocode/json"
        params = {"latlng": f"{lat},{lng}", "key": GOOGLE_API_KEY}
        data = await fetch_google_data(f"details:{lat}:{lng}", url, params)

        if not data or not data.get("results"):
            raise HTTPException(status_code=404, detail="No details found")

        return {
            "name": "Reverse Geocoded Location",
            "address": data["results"][0]["formatted_address"],
            "lat": lat,
            "lng": lng
        }

    # Fetch Details by Place ID
    redis_key = f"details:{place_id}"
    cached = await redis_client.get(redis_key)
    if cached:
        return json.loads(cached)

    url = f"{GOOGLE_API_URL}/place/details/json"
    params = {"place_id": place_id, "key": GOOGLE_API_KEY}
    data = await fetch_google_data(redis_key, url, params)

    if not data or "result" not in data:
        raise HTTPException(status_code=404, detail="No details found")

    core_result = data["result"]
    result = {
        "name": core_result.get("name"),
        "address": core_result.get("formatted_address"),
        "lat": core_result["geometry"]["location"]["lat"],
        "lng": core_result["geometry"]["location"]["lng"],
        "phone": core_result.get("formatted_phone_number"),
        "website": core_result.get("website")
    }

    await redis_client.set(redis_key, json.dumps(result), ex=3600)
    return result