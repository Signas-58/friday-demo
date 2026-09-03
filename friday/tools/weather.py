import json
import urllib.request
import urllib.parse
from typing import Dict, Any

# Map standard WMO weather codes to human-readable text and emojis
WMO_CODE_MAP = {
    0: ("Clear Sky", "☀️"),
    1: ("Mainly Clear", "🌤️"),
    2: ("Partly Cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing Rime Fog", "🌫️"),
    51: ("Light Drizzle", "🌧️"),
    53: ("Moderate Drizzle", "🌧️"),
    55: ("Dense Drizzle", "🌧️"),
    56: ("Light Freezing Drizzle", "🌨️"),
    57: ("Dense Freezing Drizzle", "🌨️"),
    61: ("Slight Rain", "🌧️"),
    63: ("Moderate Rain", "🌧️"),
    65: ("Heavy Rain", "🌧️"),
    66: ("Light Freezing Rain", "🌧️"),
    67: ("Heavy Freezing Rain", "🌧️"),
    71: ("Slight Snow", "❄️"),
    73: ("Moderate Snow", "❄️"),
    75: ("Heavy Snow", "❄️"),
    77: ("Snow Grains", "❄️"),
    80: ("Slight Rain Showers", "🌦️"),
    81: ("Moderate Rain Showers", "🌦️"),
    82: ("Violent Rain Showers", "🌧️"),
    85: ("Slight Snow Showers", "🌨️"),
    86: ("Heavy Snow Showers", "🌨️"),
    95: ("Thunderstorm", "🌩️"),
    96: ("Thunderstorm with Slight Hail", "🌩️"),
    99: ("Thunderstorm with Heavy Hail", "🌩️")
}

def get_weather(location: str = "Harare") -> str:
    """
    Fetch current weather and daily forecast for any city/location using Open-Meteo APIs (100% free, no API keys).
    
    Args:
        location: City or location name (e.g. 'Harare', 'London', 'Johannesburg', 'New York').
    """
    try:
        # 1. Geocode location name to latitude & longitude
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1&language=en&format=json"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "FRIDAY-Assistant/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            geo_data = json.loads(resp.read().decode())
        
        if not geo_data.get("results"):
            return f"Error: Could not locate city or place named '{location}'."
        
        place = geo_data["results"][0]
        lat = place["latitude"]
        lon = place["longitude"]
        city_name = place.get("name", location)
        country = place.get("country", "")
        location_display = f"{city_name}, {country}" if country else city_name

        # 2. Fetch current weather and daily forecast
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m&"
            f"daily=weather_code,temperature_2m_max,temperature_2m_min&"
            f"timezone=auto"
        )
        w_req = urllib.request.Request(weather_url, headers={"User-Agent": "FRIDAY-Assistant/1.0"})
        with urllib.request.urlopen(w_req, timeout=10) as resp:
            w_data = json.loads(resp.read().decode())
        
        current = w_data.get("current", {})
        daily = w_data.get("daily", {})
        
        temp = current.get("temperature_2m", "N/A")
        feels_like = current.get("apparent_temperature", "N/A")
        humidity = current.get("relative_humidity_2m", "N/A")
        wind_speed = current.get("wind_speed_10m", "N/A")
        w_code = current.get("weather_code", 0)
        
        temp_max = daily.get("temperature_2m_max", ["N/A"])[0]
        temp_min = daily.get("temperature_2m_min", ["N/A"])[0]
        
        desc, emoji = WMO_CODE_MAP.get(w_code, ("Variable", "☁️"))
        
        report = (
            f"🌤️ **Weather Update for {location_display}:**\n"
            f"- **Condition:** {desc} {emoji}\n"
            f"- **Current Temp:** {temp}°C (Feels like {feels_like}°C)\n"
            f"- **Today's High / Low:** {temp_max}°C / {temp_min}°C\n"
            f"- **Relative Humidity:** {humidity}%\n"
            f"- **Wind Speed:** {wind_speed} km/h"
        )
        return report
    except Exception as e:
        return f"Error fetching weather for '{location}': {str(e)}"

def register(mcp):
    """Register weather tools on the FastMCP server."""
    mcp.tool()(get_weather)
