from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.core.cache import cache
from django.conf import settings
from django.shortcuts import render
from .models import Token, Place
import requests


def middleware(request):
    # Token auth unless internal
    if not request.headers.get("X-Internal-Request"):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return Response({"error": "Authorization header missing"}, status=status.HTTP_401_UNAUTHORIZED)

        token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else auth_header
        try:
            Token.objects.get(token=token)
        except Token.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)
    return None

# --- Helper function for caching + Google API ---
def fetch_google_data(redis_key, url, params, timeout=3600):
    cached = cache.get(redis_key)
    if cached:
        print(f'✅ Cache hit for {redis_key}')
        return cached

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None

    data = response.json()
    cache.set(redis_key, data, timeout)
    return data



# --- Home Page ---
def application(request):
    return render(request, "index.html")


# --- 1️⃣ Search Places ---
@api_view(["GET"])
def search(request):
    # Middleware check
    validate = middleware(request)
    if validate:
        return validate

    query = request.query_params.get("query")
    limit = int(request.query_params.get("limit", 10))
    if not query:
        return Response({"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST)

    redis_key = f"search:{query}"
    cached = cache.get(redis_key)
    if cached:
        return Response(cached)

    # Check local DB first
    places = Place.objects.filter(name__icontains=query)[:limit]
    if places.exists():
        result = [
            {"name": p.name, "address": p.address, "lat": p.lat, "lng": p.lng}
            for p in places
        ]
        cache.set(redis_key, result, timeout=3600)
        return Response(result)

    # Fetch from Google Text Search
    url = f"{settings.GOOGLE_API_URL}/place/textsearch/json"
    params = {"query": query, "key": settings.GOOGLE_API_KEY}
    data = fetch_google_data(redis_key, url, params)

    if not data:
        return Response({"error": "Google API request failed"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    results = []
    for item in data.get("results", [])[:limit]:
        place, _ = Place.objects.get_or_create(
            place_id=item["place_id"],
            defaults={
                "name": item["name"],
                "address": item.get("formatted_address"),
                "lat": item["geometry"]["location"]["lat"],
                "lng": item["geometry"]["location"]["lng"],
                "query": query,
            },
        )
        results.append({
            "name": place.name,
            "address": place.address,
            "lat": place.lat,
            "lng": place.lng,
        })

    cache.set(redis_key, results, timeout=3600)
    return Response(results)


# --- 2️⃣ Nearby Places ---
@api_view(["GET"])
def nearby(request):
    # Middleware check
    validate = middleware(request)
    if validate:
        return validate

    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    radius = request.query_params.get('radius', 1000)

    if not lat or not lng:
        return Response({'error': 'lat and lng are required'}, status=status.HTTP_400_BAD_REQUEST)

    redis_key = f'nearby:{lat}:{lng}:{radius}'
    cached = cache.get(redis_key)
    if cached:
        return Response(cached)

    url = f'{settings.GOOGLE_API_URL}/place/nearbysearch/json'
    params = {'location': f'{lat},{lng}', 'radius': radius, 'key': settings.GOOGLE_API_KEY}
    data = fetch_google_data(redis_key, url, params)

    if not data:
        return Response({'error': 'Google API request failed'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    results = [
        {
            'name': item['name'],
            'address': item.get('vicinity'),
            'lat': item['geometry']['location']['lat'],
            'lng': item['geometry']['location']['lng']
        }
        for item in data.get('results', [])
    ]

    cache.set(redis_key, results, timeout=3600)
    return Response(results)


# --- 3️⃣ Geocoding ---
@api_view(["GET"])
def geocode(request):
    # Middleware check
    validate = middleware(request)
    if validate:
        return validate

    address = request.query_params.get('address')
    country = request.query_params.get('country')

    if not address:
        return Response({'error': 'Address is required'}, status=status.HTTP_400_BAD_REQUEST)

    redis_key = f'geocode:{address}:{country}'
    cached = cache.get(redis_key)
    if cached:
        return Response(cached)

    url = f'{settings.GOOGLE_API_URL}/geocode/json'
    params = {'address': address, 'key': settings.GOOGLE_API_KEY}
    if country:
        params['region'] = country

    data = fetch_google_data(redis_key, url, params)
    if not data or not data.get('results'):
        return Response({'error': 'No results found'}, status=status.HTTP_404_NOT_FOUND)

    result = {
        'lat': data['results'][0]['geometry']['location']['lat'],
        'lng': data['results'][0]['geometry']['location']['lng'],
        'formatted_address': data['results'][0]['formatted_address']
    }

    cache.set(redis_key, result, timeout=3600)
    return Response(result)


# --- 4️⃣ Place Details ---
@api_view(["GET"])
def details(request):
    # Middleware check
    validate = middleware(request)
    if validate:
        return validate

    place_id = request.query_params.get('place_id')
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')

    if not place_id and (not lat or not lng):
        return Response({'error': 'place_id OR lat & lng required'}, status=status.HTTP_400_BAD_REQUEST)

    if not place_id:
        # Reverse geocode using lat/lng
        url = f'{settings.GOOGLE_API_URL}/geocode/json'
        params = {'latlng': f'{lat},{lng}', 'key': settings.GOOGLE_API_KEY}
        data = fetch_google_data(f'details:{lat}:{lng}', url, params)

        if not data or not data.get('results'):
            return Response({'error': 'No details found'}, status=status.HTTP_404_NOT_FOUND)

        result = {
            'address': data['results'][0]['formatted_address'],
            'lat': lat,
            'lng': lng
        }
        return Response(result)

    # Place ID details
    redis_key = f'details:{place_id}'
    cached = cache.get(redis_key)
    if cached:
        return Response(cached)

    url = f'{settings.GOOGLE_API_URL}/place/details/json'
    params = {'place_id': place_id, 'key': settings.GOOGLE_API_KEY}
    data = fetch_google_data(redis_key, url, params)

    if not data or 'result' not in data:
        return Response({'error': 'No details found'}, status=status.HTTP_404_NOT_FOUND)

    result = {
        'name': data['result'].get('name'),
        'address': data['result'].get('formatted_address'),
        'lat': data['result']['geometry']['location']['lat'],
        'lng': data['result']['geometry']['location']['lng'],
        'phone': data['result'].get('formatted_phone_number'),
        'website': data['result'].get('website')
    }

    cache.set(redis_key, result, timeout=3600)
    return Response(result)
