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
    DATA_SOURCE_TIDES,
    UPDATE_INTERVAL,
    TIDES_PRODUCTS,
    BUOY_DATA_TYPES,
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
                # Fetch all available data types for tides
                all_data = {}
                for data_type in TIDES_PRODUCTS.keys():
                    try:
                        data = await self.client.get_data(self.station_id, data_type)
                        all_data[data_type] = data
                    except Exception as err:
                        _LOGGER.debug(f"Could not fetch {data_type} for station {self.station_id}: {err}")
                        # Continue fetching other data types even if one fails
                        all_data[data_type] = None
                return all_data
            else:
                # Fetch all available data types for buoys
                all_data = {}
                data_type_map = {
                    "standard": "txt",
                    "cwind": "cwind",
                    "spec": "spec",
                    "ocean": "ocean",
                }
                for data_type, file_ext in data_type_map.items():
                    try:
                        data = await self.client.get_data(self.station_id, file_ext)
                        all_data[data_type] = data
                    except Exception as err:
                        _LOGGER.debug(f"Could not fetch {data_type} for station {self.station_id}: {err}")
                        # Continue fetching other data types even if one fails
                        all_data[data_type] = None
                return all_data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
