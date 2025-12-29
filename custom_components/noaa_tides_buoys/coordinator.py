"""Data coordinator for NOAA Tides and Buoys integration."""
from datetime import timedelta
import logging
from typing import Any
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_DATA_SOURCE,
    CONF_STATION_ID,
    DATA_SOURCE_TIDES,
    UPDATE_INTERVAL,
    TIDES_PRODUCTS,
    BUOY_DATA_TYPES,
    BUOY_DATA_TYPE_MAP,
)
from .tides_api import TidesApiClient
from .buoy_api import BuoyApiClient

_LOGGER = logging.getLogger(__name__)


class NOAADataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching NOAA data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_data: dict[str, Any],
    ) -> None:
        """Initialize the coordinator."""
        self.data_source = config_entry_data[CONF_DATA_SOURCE]
        self.station_id = config_entry_data[CONF_STATION_ID]
        
        session = async_get_clientsession(hass)
        
        if self.data_source == DATA_SOURCE_TIDES:
            self.client = TidesApiClient(session)
        else:
            self.client = BuoyApiClient(session)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.station_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            if self.data_source == DATA_SOURCE_TIDES:
                # Fetch all available data types for tides in parallel
                async def fetch_tide_data(data_type: str) -> tuple[str, Any]:
                    try:
                        data = await self.client.get_data(self.station_id, data_type)
                        return (data_type, data)
                    except Exception as err:
                        _LOGGER.debug("Could not fetch %s for station %s: %s", data_type, self.station_id, err)
                        return (data_type, None)
                
                results = await asyncio.gather(
                    *[fetch_tide_data(data_type) for data_type in TIDES_PRODUCTS.keys()]
                )
                return dict(results)
            else:
                # Fetch all available data types for buoys in parallel
                async def fetch_buoy_data(data_type: str, file_ext: str) -> tuple[str, Any]:
                    try:
                        data = await self.client.get_data(self.station_id, file_ext)
                        return (data_type, data)
                    except Exception as err:
                        _LOGGER.debug("Could not fetch %s for station %s: %s", data_type, self.station_id, err)
                        return (data_type, None)
                
                results = await asyncio.gather(
                    *[fetch_buoy_data(data_type, file_ext) for data_type, file_ext in BUOY_DATA_TYPE_MAP.items()]
                )
                return dict(results)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
