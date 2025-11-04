import requests
from django.conf import settings

def geocode_address(address):
    if not address:
        return None, None

    api_key = settings.GOOGLE_MAPS_API_KEY
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}

    try:
        response = requests.get(url, params=params, timeout=5).json()
        if response.get("results"):
            location = response["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
    except Exception as e:
        print("Geocoding error:", e)

    return None, None
