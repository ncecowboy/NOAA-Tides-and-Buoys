"""API client for NOAA Tides and Currents data."""
import asyncio
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
    
    # Products to try for validation, in order of preference.
    # Predictions are more commonly available than real-time measurements.
    _VALIDATION_PRODUCTS = ["predictions", "water_level"]

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
        interval: str | None = None,
        range_hours: int | None = None,
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
        
        # Add optional parameters if provided
        if interval:
            params["interval"] = interval
        if range_hours:
            params["range"] = range_hours

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
        """Validate that a station ID exists.
        
        Tries multiple products to validate the station, as not all stations
        support all products. Predictions are tried first as they are more
        commonly available than real-time water level measurements.
        """
        for product in self._VALIDATION_PRODUCTS:
            try:
                await self.get_data(station_id, product)
                return True
            except (ValueError, aiohttp.ClientError, asyncio.TimeoutError):
                # Product not available, network issue, or timeout - try the next product.
                # Station is only invalid if ALL products fail.
                continue
        
        # Station is invalid if none of the products work
        return False

    async def get_station_name(self, station_id: str) -> str | None:
        """Get the name of the station.
        
        Tries multiple products to get station metadata. Predictions are tried
        first as they are more commonly available than real-time measurements.
        
        Note: This fetches data from the API to extract metadata.
        When called after validate_station(), this results in a duplicate API call.
        Future optimization: Consider caching or combining validation with name retrieval.
        """
        for product in self._VALIDATION_PRODUCTS:
            try:
                # Fetch data to get metadata which includes station name
                data = await self.get_data(station_id, product)
                
                # Extract station name from metadata
                if "metadata" in data and "name" in data["metadata"]:
                    return data["metadata"]["name"]
            except (ValueError, aiohttp.ClientError, asyncio.TimeoutError):
                # Product not available, network issue, or timeout - try the next product.
                continue
        
        _LOGGER.debug("Could not fetch station name for %s", station_id)
        return None
