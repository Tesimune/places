# Places — Location Search API

Developer-friendly location search, geocoding, and place details backed by Google Places, Redis caching, and a small FastAPI service.

**Quick links**
- **Main app:** [main.py](main.py)
- **Dockerfile:** [Dockerfile](Dockerfile)
- **Compose:** [docker-compose.yaml](docker-compose.yaml)
- **Project metadata:** [pyproject.toml](pyproject.toml)
- **Frontend demo:** [static/index.html](static/index.html)

**What this project provides**
- **Search:** Text search for places using Google Places Text Search API.
- **Nearby:** Find nearby places by lat/lng and radius.
- **Geocode:** Forward and reverse geocoding.
- **Details:** Place details (phone, website) by place_id or lat/lng fallback.
- **Caching:** Redis-backed caching to reduce external API usage and improve latency.
- **Simple auth:** HTTP Bearer token check (replace with your own DB-backed token validation).

**Tech stack**
- **Server:** FastAPI
- **HTTP client:** httpx (async)
- **Cache:** redis (async client)
- **Runtime:** uvicorn (used for local runs; Docker image uses `uv` toolchain in the Dockerfile)

**Requirements**
- Python >= 3.13
- Redis (docker-compose will spin one up for you)
- A Google API key with Places / Geocoding access (set via environment variable)

**Environment variables**
Create a `.env` at the project root (referenced by docker-compose) with at least the following values:

```env
SECRET_TOKEN=service_token_here
REDIS_LOCATION=redis://redis:6379/1
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_API_URL=https://maps.googleapis.com/maps/api
# Optional: override defaults
# PORT=8000
```

Configuration notes:
- `GOOGLE_API_URL` defaults to `https://maps.googleapis.com/maps/api`.
- `REDIS_LOCATION` defaults to `redis://redis:6379/1` (compatible with the compose service name).
- `SECRET_TOKEN` is used by the included `MockTokenDB` for demo auth—replace with real token validation.

**Run (Docker Compose)**
This is the recommended quick-start for development and demo (builds the image and starts Redis):

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

**Run locally (venv)**
If you prefer to run without Docker, use a virtualenv and `uvicorn`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install "fastapi[standard]>=0.136.1" httpx redis uvicorn
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**API Overview**
All API endpoints require an Authorization header with a bearer token unless the request includes the `X-Internal-Request` header (used by the demo landing page).

- **Auth header:** `Authorization: Bearer <TOKEN>` (the demo uses `SECRET_TOKEN` from env)

Endpoints (HTTP GET):

- `/api/search` — text search
	- Query params: `query` (required), `limit` (optional, default 10)
	- Example:

```bash
curl -G "http://localhost:8000/api/search" \
	-H "Authorization: Bearer $SECRET_TOKEN" \
	--data-urlencode "query=restaurants in New York" \
	--data-urlencode "limit=5"
```

- `/api/nearby` — nearby places
	- Query params: `lat`, `lng`, `radius` (meters)

```bash
curl -G "http://localhost:8000/api/nearby" \
	-H "Authorization: Bearer $SECRET_TOKEN" \
	--data-urlencode "lat=40.7128" \
	--data-urlencode "lng=-74.0060" \
	--data-urlencode "radius=1000"
```

- `/api/geocode` — forward geocode
	- Query params: `address` (required), `country` (optional)

```bash
curl -G "http://localhost:8000/api/geocode" \
	-H "Authorization: Bearer $SECRET_TOKEN" \
	--data-urlencode "address=1600 Amphitheatre Parkway, Mountain View"
```

- `/api/details` — place details or reverse geocode fallback
	- Query params: `place_id` OR `lat` and `lng`

```bash
curl -G "http://localhost:8000/api/details" \
	-H "Authorization: Bearer $SECRET_TOKEN" \
	--data-urlencode "place_id=PLACE_ID_HERE"
```

Responses use simple JSON shapes defined in `main.py` (see `PlaceResponse`, `GeocodeResponse`, `DetailsResponse`).

**Caching behavior**
- Results from Google are cached in Redis with a default TTL of ~3600s inside the helper `fetch_google_data`. Keys are prefixed by endpoint type (e.g. `search:`, `nearby:`, `geocode:`, `details:`).

**Static demo UI**
- The root path `/` serves `static/index.html` for a developer demo and quick integration examples.

**Docker image & custom runtime notes**
- The Dockerfile installs a small `uv` toolchain and runs the packaged fastapi runner inside the container. For local development you may prefer `uvicorn` as shown above.

**Troubleshooting**
- If `docker compose up` fails with an error:
	- Ensure `.env` exists and contains `GOOGLE_API_KEY` and `SECRET_TOKEN`.
	- Run `docker compose logs app` and `docker compose logs redis` to see container output.
	- Confirm the redis volume has proper permissions and the `redis` service is healthy.

**Security notes**
- The included `MockTokenDB` is a placeholder. Replace `MockTokenDB.token_exists` and `verify_token` with a real authentication/authorization mechanism before production use.
- Never commit real API keys to source control.

**Extending the project**
- Persist places in a real DB (SQLModel, Tortoise, or an RDBMS) instead of `MockPlaceDB`.
- Add rate limiting and per-key quotas.
- Add request logging, structured telemetry, and more robust error handling for external API failures.

**Contributing**
- Open an issue or a PR. Keep changes focused and include tests where applicable.

**License & Contact**
- MIT-style usage is acceptable for demos. Adapt as needed for your organization.
