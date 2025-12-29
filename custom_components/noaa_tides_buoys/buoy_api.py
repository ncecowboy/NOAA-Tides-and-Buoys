"""API client for NOAA NDBC Buoy data."""
import logging
from typing import Any
import re

import aiohttp
import async_timeout

from .const import BUOY_API_BASE

_LOGGER = logging.getLogger(__name__)

# Regex patterns for parsing station names from HTML
# Pattern matches: <h1 id="station">COLUMBIA RIVER BAR</h1>
_STATION_H1_PATTERN = r'<h1[^>]*id="station"[^>]*>([^<]+)</h1>'
# Pattern matches: <title>Station 46029 - COLUMBIA RIVER BAR - Recent Data</title>
_STATION_TITLE_PATTERN = r'<title>([^-]+)-'


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

    async def get_station_name(self, station_id: str) -> str | None:
        """Get the name of the buoy station.
        
        Fetches the station name by parsing the NDBC station page HTML.
        """
        url = f"https://www.ndbc.noaa.gov/station_page.php?station={station_id}"
        
        try:
            async with async_timeout.timeout(10):
                async with self._session.get(url) as response:
                    response.raise_for_status()
                    html = await response.text()
                    
                    # Parse the station name from the HTML
                    # The station name is in the <h1> tag with id="station"
                    match = re.search(_STATION_H1_PATTERN, html)
                    if match:
                        return self._clean_station_name(match.group(1))
                    
                    # Fallback: try to find station name in title tag
                    match = re.search(_STATION_TITLE_PATTERN, html)
                    if match:
                        return self._clean_station_name(match.group(1))
                    
                    return None
        except Exception as err:
            _LOGGER.debug("Could not fetch station name for %s: %s", station_id, err)
            return None
    
    def _clean_station_name(self, name: str) -> str:
        """Clean station name by removing common prefixes."""
        name = name.strip()
        name = name.removeprefix("Station ")
        return name
