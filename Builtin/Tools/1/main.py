from typing import Any
import requests


def get_weather(city: str, temperature_unit: str = "celsius") -> dict[str, Any]:
    """Fetch current weather for a city using Open-Meteo.
    
    Args:
        city: Name of the city (e.g., "Tokyo", "New York").
        temperature_unit: Either "celsius" or "fahrenheit".
    
    Returns:
        Dict with location, temperature, temperature_unit, windspeed, and weather code.
    """
    if temperature_unit not in ("celsius", "fahrenheit"):
        raise ValueError("temperature_unit must be 'celsius' or 'fahrenheit'.")

    # 1. Geocoding — get lat/lon for the city
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_params = {"name": city, "count": 1, "language": "en", "format": "json"}
    geo_response = requests.get(geo_url, params=geo_params, timeout=10).json()

    if not geo_response.get("results"):
        raise ValueError(f"City '{city}' not found.")

    location_data = geo_response["results"][0]
    lat = location_data["latitude"]
    lon = location_data["longitude"]
    resolved_name = location_data.get("name", city)
    country = location_data.get("country", "")

    # 2. Forecast — get current weather
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,weather_code",
        "temperature_unit": temperature_unit,
        "timezone": "auto",
    }
    weather_response = requests.get(weather_url, params=weather_params, timeout=10).json()

    current = weather_response.get("current", {})
    if not current:
        raise ValueError(f"Could not fetch weather for {city}.")

    return {
        "location": f"{resolved_name}, {country}".strip(", "),
        "temperature": current.get("temperature_2m"),
        "temperature_unit": temperature_unit,
        "wind_speed": current.get("wind_speed_10m"),
        "weather_code": current.get("weather_code"),
        "observed_at": current.get("time"),
    }