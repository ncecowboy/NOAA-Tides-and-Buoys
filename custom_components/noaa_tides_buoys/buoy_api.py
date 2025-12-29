"""API client for NOAA NDBC Buoy data."""
import logging
from typing import Any
import re

import aiohttp
import async_timeout

from .const import BUOY_API_BASE

_LOGGER = logging.getLogger(__name__)


class BuoyApiClient:
    """API client for NOAA NDBC Buoy data."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self._session = session

    async def get_data(self, station_id: str, data_type: str = "txt") -> dict[str, Any]:
        """Get data from the NDBC Buoy API."""
        url = f"{BUOY_API_BASE}/{station_id}.{data_type}"
        
        try:
            async with async_timeout.timeout(10):
                async with self._session.get(url) as response:
                    response.raise_for_status()
                    text = await response.text()
                    
                    # Parse the text data
                    parsed_data = self._parse_buoy_data(text, data_type)
                    return parsed_data
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching data from Buoy API: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error fetching data: %s", err)
            raise

    def _parse_buoy_data(self, text: str, data_type: str) -> dict[str, Any]:
        """Parse NDBC buoy data text format."""
        lines = text.strip().split('\n')
        
        if len(lines) < 3:
            raise ValueError("Invalid buoy data format")
        
        # First line is header, second line is units, third line onwards is data
        headers = lines[0].split()
        units_line = lines[1].split()
        
        # Get the most recent data (third line)
        if len(lines) > 2:
            data_line = lines[2].split()
            
            # Create a dictionary of the data
            data = {}
            for i, header in enumerate(headers):
                if i < len(data_line):
                    data[header] = data_line[i]
            
            # Add units information
            data['_units'] = {}
            for i, header in enumerate(headers):
                if i < len(units_line):
                    data['_units'][header] = units_line[i]
            
            return data
        
        raise ValueError("No data available")

    async def validate_station(self, station_id: str) -> bool:
        """Validate that a buoy station ID exists."""
        try:
            # Try to fetch standard meteorological data as a test
            await self.get_data(station_id, "txt")
            return True
        except Exception:
            return False
