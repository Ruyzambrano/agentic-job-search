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
        location = geolocator.geocode(
            user_input, 
            country_codes=api_region, 
            addressdetails=True, 
            language="en",
            extratags=True
        )
        
        if not location:
            return None
        
        address = location.raw.get("address", {})
        postcode = address.get("postcode")

        if not postcode:
            reverse_loc = geolocator.reverse((location.latitude, location.longitude), addressdetails=True)
            if reverse_loc:
                postcode = reverse_loc.raw.get("address", {}).get("postcode")

        
        return LocationData(
            raw_input=user_input,
            city=address.get('city') or address.get('town') or address.get('village') or user_input,
            state_full=address.get('state'),
            country_full=address.get('country', 'United Kingdom'),
            country_code=address.get('country_code', api_region).lower(),
            postcode = postcode
        )
    except (GeocoderTimedOut, Exception) as e:
        return LocationData(raw_input=user_input, city=user_input, country_full=region_hint, country_code=api_region)