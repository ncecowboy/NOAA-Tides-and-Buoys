"""API client for NOAA Tides and Currents data."""
import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp

from .const import (
    TIDES_API_BASE,
    TIDES_METADATA_API_BASE,
    DEFAULT_DATUM,
    DEFAULT_UNITS,
    DEFAULT_TIME_ZONE,
)

_LOGGER = logging.getLogger(__name__)

# Products that measure absolute currents/direction and don't accept a tidal datum reference.
# monthly_mean is also excluded because the NOAA API rejects the datum parameter for it.
_PRODUCTS_WITHOUT_DATUM = frozenset({"currents", "currents_predictions", "datums", "monthly_mean"})
# Products that don't accept a time_zone parameter.
# daily_mean returns calendar-day averages so time_zone is irrelevant and rejected by the API.
_PRODUCTS_WITHOUT_TIMEZONE = frozenset({"datums", "daily_mean", "monthly_mean"})
# Products that don't accept a units parameter
_PRODUCTS_WITHOUT_UNITS = frozenset({"datums"})
# Products where a 400 response typically means the station doesn't offer the product
# rather than a request configuration error.
_STATION_DEPENDENT_PRODUCTS = frozenset({"currents", "currents_predictions"})


class TidesApiClient:
    """API client for NOAA Tides and Currents."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self._session = session

    async def get_data(
        self,
        station_id: str,
        product: str,
        date: str | None = None,
        begin_date: str | None = None,
        end_date: str | None = None,
        datum: str = DEFAULT_DATUM,
        units: str = DEFAULT_UNITS,
        time_zone: str = DEFAULT_TIME_ZONE,
        interval: str | None = None,
        range_hours: int | None = None,
    ) -> dict[str, Any]:
        """Get data from the Tides and Currents API.
        
        Args:
            station_id: Station identifier
            product: Data product type
            date: Date parameter (e.g., "latest", "today", "recent")
            begin_date: Start date (required for predictions, format: YYYYMMDD or YYYYMMDD HH:MM)
            end_date: End date (required for predictions, format: YYYYMMDD or YYYYMMDD HH:MM)
            datum: Tidal datum reference
            units: Unit system (english or metric)
            time_zone: Time zone for data
            interval: Data interval (e.g., "hilo" for high/low)
            range_hours: Number of hours for data range
        """
        params = {
            "station": station_id,
            "product": product,
            "format": "json",
            "application": "HomeAssistant",
        }

        if product not in _PRODUCTS_WITHOUT_DATUM:
            params["datum"] = datum
        if product not in _PRODUCTS_WITHOUT_UNITS:
            params["units"] = units
        if product not in _PRODUCTS_WITHOUT_TIMEZONE:
            params["time_zone"] = time_zone
        
        # Add date parameters - prefer begin/end dates over date parameter
        if begin_date and end_date:
            params["begin_date"] = begin_date
            params["end_date"] = end_date
        elif date:
            params["date"] = date
        
        # Add optional parameters if provided
        if interval:
            params["interval"] = interval
        if range_hours and not (begin_date and end_date):
            # Per NOAA API docs, range parameter cannot be used with begin_date/end_date
            # Range specifies hours relative to a date, while begin/end define absolute range
            params["range"] = range_hours

        try:
            async with asyncio.timeout(10):
                async with self._session.get(
                    TIDES_API_BASE, params=params
                ) as response:
                    if response.status == 400:
                        # NOAA uses 400 both for "product not available at this station"
                        # and for genuinely invalid requests (bad/missing parameters).
                        # Capture the server-provided details so that misconfigurations
                        # remain diagnosable.
                        try:
                            error_body = (await response.text()).strip()
                        except (aiohttp.ClientError, UnicodeDecodeError) as read_err:
                            _LOGGER.debug("Could not read 400 response body: %s", read_err)
                            error_body = ""

                        # For known station-dependent current products a 400 often
                        # indicates that the product is simply not offered at this
                        # station.  Log at debug to avoid flooding logs.
                        if product in _STATION_DEPENDENT_PRODUCTS:
                            _LOGGER.debug(
                                "NOAA API returned 400 for station %s product %s – "
                                "this product may not be available at this station. "
                                "Response: %s",
                                station_id,
                                product,
                                error_body,
                            )
                        else:
                            # For other products treat 400 as a potential configuration
                            # or request error and log at warning with details.
                            _LOGGER.warning(
                                "NOAA API returned 400 for station %s product %s. "
                                "Response: %s",
                                station_id,
                                product,
                                error_body,
                            )

                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                            message=(
                                "Bad Request from NOAA API"
                                + (f": {error_body}" if error_body else "")
                            ),
                        )
                    response.raise_for_status()
                    data = await response.json()
                    
                    if "error" in data:
                        raise ValueError(f"API error: {data['error']}")
                    
                    return data
        except aiohttp.ClientResponseError as err:
            # 400/404 errors are already logged above; other HTTP errors are unexpected.
            if err.status not in {400, 404}:
                _LOGGER.warning(
                    "HTTP error fetching data from Tides API (station %s, product %s): %s",
                    station_id,
                    product,
                    err,
                )
            raise
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "Timeout fetching data from Tides API (station %s, product %s)",
                station_id,
                product,
            )
            raise
        except aiohttp.ClientError as err:
            _LOGGER.warning(
                "Network error fetching data from Tides API (station %s, product %s): %s",
                station_id,
                product,
                err,
            )
            raise
        except Exception as err:
            _LOGGER.warning("Unexpected error fetching data from Tides API: %s", err)
            raise

    async def get_datums(self, station_id: str) -> dict[str, Any]:
        """Get tidal datums for a station from the CO-OPS Metadata API.

        Returns data in the same structure as the datagetter response so that
        sensors can consume it transparently (a dict with a "datums" list of
        {"n": name, "v": value} objects).
        """
        try:
            async with asyncio.timeout(10):
                async with self._session.get(
                    f"{TIDES_METADATA_API_BASE}/{station_id}/datums.json"
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.debug("Error fetching datums for station %s: %s", station_id, err)
            raise
        except Exception as err:
            _LOGGER.warning("Unexpected error fetching datums for station %s: %s", station_id, err)
            raise

    async def validate_station(self, station_id: str) -> bool:
        """Validate that a station ID exists using the metadata API.

        This is more reliable than checking data products since a station
        may be valid but not currently broadcasting all data products.
        """
        try:
            async with asyncio.timeout(10):
                async with self._session.get(
                    f"{TIDES_METADATA_API_BASE}/{station_id}.json"
                ) as response:
                    if response.status == 404:
                        return False
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Valid station should have basic metadata
                    if "stations" in data and isinstance(data["stations"], list) and data["stations"]:
                        return True
                    
                    return False
        except aiohttp.ClientError as err:
            _LOGGER.error("Error validating station %s: %s", station_id, err)
            return False
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout validating station %s", station_id)
            return False
        except Exception as err:
            _LOGGER.error("Unexpected error validating station %s: %s", station_id, err)
            return False

    async def get_station_name(self, station_id: str) -> str | None:
        """Get the name of the station using the metadata API.
        
        This is more reliable than querying data products.
        """
        try:
            async with asyncio.timeout(10):
                async with self._session.get(
                    f"{TIDES_METADATA_API_BASE}/{station_id}.json"
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Extract station name from metadata
                    if "stations" in data and isinstance(data["stations"], list) and data["stations"]:
                        station = data["stations"][0]
                        if "name" in station:
                            return station["name"]
                    
                    return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Could not fetch station name for %s: %s", station_id, err)
            return None
        except Exception as err:
            _LOGGER.warning("Unexpected error fetching station name for %s: %s", station_id, err)
            return None

    async def get_station_metadata(self, station_id: str) -> dict[str, Any] | None:
        """Get full station metadata including name, lat, lon, etc.
        
        Returns dict with metadata or None if not available.
        """
        try:
            async with asyncio.timeout(10):
                async with self._session.get(
                    f"{TIDES_METADATA_API_BASE}/{station_id}.json"
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Extract station metadata
                    if "stations" in data and isinstance(data["stations"], list) and data["stations"]:
                        station = data["stations"][0]
                        metadata = {}
                        if "name" in station:
                            metadata["name"] = station["name"]
                        if "lat" in station:
                            metadata["lat"] = station["lat"]
                        if "lng" in station:
                            # API uses 'lng' but we'll normalize to 'lon'
                            metadata["lon"] = station["lng"]
                        if "state" in station:
                            metadata["state"] = station["state"]
                        return metadata
                    
                    return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Could not fetch station metadata for %s: %s", station_id, err)
            return None
        except Exception as err:
            _LOGGER.warning("Unexpected error fetching station metadata for %s: %s", station_id, err)
            return None
