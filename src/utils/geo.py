from typing import Optional

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

from src.schema import LocationData

def resolve_location(user_input: str, region_hint: str) -> Optional[LocationData]:
    """
    Resolves messy input into a Smart LocationData object.
    Handles 'uk' -> 'gb' mapping and full-name expansion.
    """
    if not user_input or len(user_input) < 2:
        return None

    mapping = {"uk": "gb", "united kingdom": "gb", "usa": "us", "canada": "ca"}
    api_region = mapping.get(region_hint.lower(), region_hint.lower())

    geolocator = Nominatim(user_agent="job_agent_2026")
    
    try:
        loc = geolocator.geocode(
            user_input, 
            country_codes=api_region, 
            addressdetails=True, 
            language="en"
        )
        
        if not loc:
            return None

        addr = loc.raw.get('address', {})
        
        return LocationData(
            city=addr.get('city') or addr.get('town') or addr.get('village') or user_input,
            state_full=addr.get('state'),
            country_full=addr.get('country', 'United Kingdom'),
            country_code=addr.get('country_code', api_region).lower()
        )
    except (GeocoderTimedOut, Exception):
        return LocationData(city=user_input, country_full=region_hint, country_code=api_region)