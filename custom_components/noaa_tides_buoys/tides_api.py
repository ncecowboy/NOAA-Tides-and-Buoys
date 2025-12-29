"""API client for NOAA Tides and Currents data."""
import logging
from datetime import datetime
from typing import Any

import aiohttp
import async_timeout

from .const import (
    TIDES_API_BASE,
    DEFAULT_DATUM,
    DEFAULT_UNITS,
    DEFAULT_TIME_ZONE,
)

_LOGGER = logging.getLogger(__name__)


class TidesApiClient:
    """API client for NOAA Tides and Currents."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self._session = session

    async def get_data(
        self,
        station_id: str,
        product: str,
        date: str = "latest",
        datum: str = DEFAULT_DATUM,
        units: str = DEFAULT_UNITS,
        time_zone: str = DEFAULT_TIME_ZONE,
    ) -> dict[str, Any]:
        """Get data from the Tides and Currents API."""
        params = {
            "station": station_id,
            "product": product,
            "date": date,
            "datum": datum,
            "units": units,
            "time_zone": time_zone,
            "format": "json",
            "application": "HomeAssistant",
        }

        try:
            async with async_timeout.timeout(10):
                async with self._session.get(
                    TIDES_API_BASE, params=params
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if "error" in data:
                        raise ValueError(f"API error: {data['error']}")
                    
                    return data
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching data from Tides API: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error fetching data: %s", err)
            raise

    async def validate_station(self, station_id: str) -> bool:
        """Validate that a station ID exists."""
        try:
            # Try to fetch latest water level data as a test
            await self.get_data(station_id, "water_level")
            return True
        except Exception:
            return False

    async def get_station_name(self, station_id: str) -> str | None:
        """Get the name of the station.
        
        Note: This fetches data from the API to extract metadata.
        When called after validate_station(), this results in a duplicate API call.
        Future optimization: Consider caching or combining validation with name retrieval.
        """
        try:
            # Fetch data to get metadata which includes station name
            data = await self.get_data(station_id, "water_level")
            
            # Extract station name from metadata
            if "metadata" in data and "name" in data["metadata"]:
                return data["metadata"]["name"]
            
            return None
        except Exception:
            _LOGGER.debug("Could not fetch station name for %s", station_id)
            return None
