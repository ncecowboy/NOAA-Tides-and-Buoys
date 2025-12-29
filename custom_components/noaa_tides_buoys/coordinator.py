"""Data coordinator for NOAA Tides and Buoys integration."""
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_DATA_SOURCE,
    CONF_STATION_ID,
    CONF_DATA_TYPE,
    DATA_SOURCE_TIDES,
    UPDATE_INTERVAL,
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
        self.data_type = config_entry_data[CONF_DATA_TYPE]
        
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
                data = await self.client.get_data(self.station_id, self.data_type)
            else:
                # For buoy data, map data type to file extension
                data_type_map = {
                    "standard": "txt",
                    "cwind": "cwind",
                    "spec": "spec",
                    "ocean": "ocean",
                }
                file_ext = data_type_map.get(self.data_type, "txt")
                data = await self.client.get_data(self.station_id, file_ext)
            
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
