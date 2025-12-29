"""Sensor platform for NOAA Tides and Buoys integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_DATA_SOURCE,
    CONF_STATION_ID,
    CONF_DATA_TYPE,
    DATA_SOURCE_TIDES,
    TIDES_PRODUCTS,
    BUOY_DATA_TYPES,
)
from .coordinator import NOAADataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NOAA sensor based on a config entry."""
    coordinator: NOAADataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    data_source = entry.data[CONF_DATA_SOURCE]
    
    if data_source == DATA_SOURCE_TIDES:
        entities = _create_tides_sensors(coordinator, entry)
    else:
        entities = _create_buoy_sensors(coordinator, entry)
    
    async_add_entities(entities)


def _create_tides_sensors(
    coordinator: NOAADataUpdateCoordinator,
    entry: ConfigEntry,
) -> list[NOAATidesSensor]:
    """Create sensor entities for tides data."""
    sensors = []
    data_type = entry.data[CONF_DATA_TYPE]
    
    # Create primary sensor for the selected data type
    sensors.append(
        NOAATidesSensor(
            coordinator,
            entry,
            data_type,
            TIDES_PRODUCTS.get(data_type, data_type),
        )
    )
    
    return sensors


def _create_buoy_sensors(
    coordinator: NOAADataUpdateCoordinator,
    entry: ConfigEntry,
) -> list[NOAABuoySensor]:
    """Create sensor entities for buoy data."""
    sensors = []
    data_type = entry.data[CONF_DATA_TYPE]
    
    # Create sensors for various buoy measurements
    sensors.append(
        NOAABuoySensor(
            coordinator,
            entry,
            data_type,
            BUOY_DATA_TYPES.get(data_type, data_type),
        )
    )
    
    return sensors


class NOAATidesSensor(CoordinatorEntity, SensorEntity):
    """Representation of a NOAA Tides sensor."""

    def __init__(
        self,
        coordinator: NOAADataUpdateCoordinator,
        entry: ConfigEntry,
        data_key: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._data_key = data_key
        self._attr_name = f"NOAA {entry.data[CONF_STATION_ID]} {name}"
        self._attr_unique_id = f"{entry.entry_id}_{data_key}"
        self._station_id = entry.data[CONF_STATION_ID]

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        data = self.coordinator.data
        
        # Handle different data structures from the API
        if "data" in data and isinstance(data["data"], list) and data["data"]:
            latest = data["data"][0]
            
            # Extract value based on data type
            if "v" in latest:  # value field
                return latest["v"]
            elif "s" in latest:  # speed field for currents/wind
                return latest["s"]
            elif "t" in latest:  # time field
                return latest.get("v", latest.get("s"))
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}
        
        attrs = {
            "station_id": self._station_id,
            "data_type": self._data_key,
        }
        
        data = self.coordinator.data
        
        if "data" in data and isinstance(data["data"], list) and data["data"]:
            latest = data["data"][0]
            
            # Add timestamp if available
            if "t" in latest:
                attrs["timestamp"] = latest["t"]
            
            # Add quality flag if available
            if "f" in latest:
                attrs["quality"] = latest["f"]
            
            # Add direction for wind/currents
            if "d" in latest:
                attrs["direction"] = latest["d"]
        
        # Add metadata if available
        if "metadata" in data:
            metadata = data["metadata"]
            if "name" in metadata:
                attrs["station_name"] = metadata["name"]
            if "lat" in metadata and "lon" in metadata:
                attrs["latitude"] = metadata["lat"]
                attrs["longitude"] = metadata["lon"]
        
        return attrs


class NOAABuoySensor(CoordinatorEntity, SensorEntity):
    """Representation of a NOAA Buoy sensor."""

    def __init__(
        self,
        coordinator: NOAADataUpdateCoordinator,
        entry: ConfigEntry,
        data_key: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._data_key = data_key
        self._attr_name = f"NOAA Buoy {entry.data[CONF_STATION_ID]} {name}"
        self._attr_unique_id = f"{entry.entry_id}_{data_key}"
        self._station_id = entry.data[CONF_STATION_ID]

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        data = self.coordinator.data
        
        # For standard meteorological data, return wave height as primary value
        if "WVHT" in data:
            return data["WVHT"]
        elif "WSPD" in data:
            return data["WSPD"]
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}
        
        attrs = {
            "station_id": self._station_id,
            "data_type": self._data_key,
        }
        
        # Add all available data as attributes
        for key, value in self.coordinator.data.items():
            if key != "_units" and not key.startswith("_"):
                attrs[key.lower()] = value
        
        # Add units information
        if "_units" in self.coordinator.data:
            attrs["units"] = self.coordinator.data["_units"]
        
        return attrs
