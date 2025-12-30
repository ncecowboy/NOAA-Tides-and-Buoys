"""Sensor platform for NOAA Tides and Buoys integration."""
from __future__ import annotations

from datetime import datetime
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
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    CONF_DATA_SOURCE,
    CONF_STATION_ID,
    DATA_SOURCE_TIDES,
    TIDES_PRODUCTS,
    TIDES_UNITS,
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
    
    # Create a sensor for each available data type
    for data_type, name in TIDES_PRODUCTS.items():
        sensors.append(
            NOAATidesSensor(
                coordinator,
                entry,
                data_type,
                name,
            )
        )
    
    return sensors


def _create_buoy_sensors(
    coordinator: NOAADataUpdateCoordinator,
    entry: ConfigEntry,
) -> list[NOAABuoySensor]:
    """Create sensor entities for buoy data."""
    sensors = []
    
    # Create a sensor for each available data type
    for data_type, name in BUOY_DATA_TYPES.items():
        sensors.append(
            NOAABuoySensor(
                coordinator,
                entry,
                data_type,
                name,
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
        self._entry_id = entry.entry_id
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.data[CONF_DATA_SOURCE]}_{self._station_id}")},
            name=f"NOAA Station {self._station_id}",
            manufacturer="NOAA",
            model=entry.data[CONF_DATA_SOURCE].replace("_", " ").title(),
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        # Get data for this specific data type
        data = self.coordinator.data.get(self._data_key)
        if not data:
            return None
        
        # Special handling for high/low tide predictions
        if self._data_key == "predictions_hilo":
            # Return the next tide event value
            if "predictions" in data and isinstance(data["predictions"], list) and data["predictions"]:
                # Find the next tide (first future event)
                # Use naive datetime since API returns local station time (lst_ldt)
                now = datetime.now()
                for tide in data["predictions"]:
                    if "t" in tide and "v" in tide:
                        try:
                            # Parse tide time as naive datetime (local station time)
                            tide_time = datetime.strptime(tide["t"], "%Y-%m-%d %H:%M")
                            if tide_time > now:
                                # Return as float to avoid "unknown" state
                                return float(tide["v"])
                        except (ValueError, TypeError):
                            continue
            return None
        
        # Special handling for current predictions
        if self._data_key == "currents_predictions":
            # Return the next current prediction value
            if "current_predictions" in data and isinstance(data["current_predictions"], list) and data["current_predictions"]:
                # Use naive datetime since API returns local station time (lst_ldt)
                now = datetime.now()
                for current in data["current_predictions"]:
                    if "t" in current and "v" in current:
                        try:
                            # Parse current time as naive datetime (local station time)
                            current_time = datetime.strptime(current["t"], "%Y-%m-%d %H:%M")
                            if current_time > now:
                                # Return as float to avoid "unknown" state
                                return float(current["v"])
                        except (ValueError, TypeError):
                            continue
            return None
        
        # Special handling for datums (these are static reference values)
        if self._data_key == "datums":
            # Datums data has a different structure
            if "datums" in data and isinstance(data["datums"], list) and data["datums"]:
                # Return MLLW (Mean Lower Low Water) as the primary value if available
                for datum in data["datums"]:
                    if datum.get("n") == "MLLW" and "v" in datum:
                        try:
                            return float(datum["v"])
                        except (ValueError, TypeError):
                            continue
            return None
        
        # Handle different data structures from the API
        if "data" in data and isinstance(data["data"], list) and data["data"]:
            latest = data["data"][0]
            
            # Extract value based on data type
            if "v" in latest:  # value field
                try:
                    return float(latest["v"])
                except (ValueError, TypeError):
                    return None
            elif "s" in latest:  # speed field for currents/wind
                try:
                    return float(latest["s"])
                except (ValueError, TypeError):
                    return None
            elif "t" in latest:  # time field
                value = latest.get("v", latest.get("s"))
                if value is not None:
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return None
        
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return TIDES_UNITS.get(self._data_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}
        
        attrs = {
            "station_id": self._station_id,
            "data_type": self._data_key,
        }
        
        # Get data for this specific data type
        data = self.coordinator.data.get(self._data_key)
        if not data:
            return attrs
        
        # Special handling for high/low tide predictions
        if self._data_key == "predictions_hilo":
            # Use naive datetime since API returns local station time (lst_ldt)
            now = datetime.now()
            
            if "predictions" in data and isinstance(data["predictions"], list):
                prior_highs = []
                prior_lows = []
                future_highs = []
                future_lows = []
                next_tide = None
                
                for tide in data["predictions"]:
                    if "t" not in tide or "v" not in tide or "type" not in tide:
                        continue
                    
                    try:
                        # Parse tide time as naive datetime (local station time)
                        tide_time = datetime.strptime(tide["t"], "%Y-%m-%d %H:%M")
                        tide_event = {
                            "time": tide["t"],
                            "height": float(tide["v"]),  # Ensure float for proper display
                            "type": tide["type"]
                        }
                        
                        if tide_time < now:
                            # Prior tide
                            if tide["type"] == "H":
                                prior_highs.append(tide_event)
                            else:
                                prior_lows.append(tide_event)
                        else:
                            # Future tide
                            if next_tide is None:
                                next_tide = tide_event
                            
                            if tide["type"] == "H":
                                future_highs.append(tide_event)
                            else:
                                future_lows.append(tide_event)
                    except (ValueError, TypeError):
                        continue
                
                # Add attributes
                if next_tide:
                    attrs["next_tide_time"] = next_tide["time"]
                    attrs["next_tide_height"] = next_tide["height"]
                    attrs["next_tide_type"] = "High" if next_tide["type"] == "H" else "Low"
                
                # Keep most recent prior tides (last 3 of each)
                if prior_highs:
                    attrs["prior_high_tides"] = prior_highs[-3:]
                if prior_lows:
                    attrs["prior_low_tides"] = prior_lows[-3:]
                
                # Keep upcoming future tides (next 3 of each)
                if future_highs:
                    attrs["future_high_tides"] = future_highs[:3]
                if future_lows:
                    attrs["future_low_tides"] = future_lows[:3]
        
        # Special handling for current predictions
        if self._data_key == "currents_predictions":
            # Use naive datetime since API returns local station time (lst_ldt)
            now = datetime.now()
            
            if "current_predictions" in data and isinstance(data["current_predictions"], list):
                future_currents = []
                next_current = None
                
                for current in data["current_predictions"]:
                    if "t" not in current or "v" not in current:
                        continue
                    
                    try:
                        # Parse current time as naive datetime (local station time)
                        current_time = datetime.strptime(current["t"], "%Y-%m-%d %H:%M")
                        current_event = {
                            "time": current["t"],
                            "speed": float(current["v"]),
                            "direction": current.get("d", "")
                        }
                        
                        if current_time > now:
                            if next_current is None:
                                next_current = current_event
                            future_currents.append(current_event)
                    except (ValueError, TypeError):
                        continue
                
                # Add attributes
                if next_current:
                    attrs["next_current_time"] = next_current["time"]
                    attrs["next_current_speed"] = next_current["speed"]
                    if next_current.get("direction"):
                        attrs["next_current_direction"] = next_current["direction"]
                
                # Keep upcoming currents (next 6)
                if future_currents:
                    attrs["future_currents"] = future_currents[:6]
        
        # Special handling for datums (static reference data)
        if self._data_key == "datums":
            if "datums" in data and isinstance(data["datums"], list):
                # Add all datums as separate attributes
                for datum in data["datums"]:
                    if "n" in datum and "v" in datum:
                        try:
                            datum_name = datum["n"].lower().replace(" ", "_")
                            attrs[f"datum_{datum_name}"] = float(datum["v"])
                        except (ValueError, TypeError):
                            continue
        
        # Regular data handling
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
            
            # Add gust data for wind
            if self._data_key == "wind" and "g" in latest:
                attrs["gust"] = latest["g"]
        
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
        self._entry_id = entry.entry_id
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.data[CONF_DATA_SOURCE]}_{self._station_id}")},
            name=f"NOAA Buoy {self._station_id}",
            manufacturer="NOAA",
            model=entry.data[CONF_DATA_SOURCE].replace("_", " ").title(),
        )

    def _get_primary_measurement_key(self) -> str | None:
        """Get the key for the primary measurement based on available data."""
        if not self.coordinator.data:
            return None
        
        # Get data for this specific data type
        data = self.coordinator.data.get(self._data_key)
        if not data:
            return None
        
        # For standard meteorological data, prioritize wave height, then wind speed
        if "WVHT" in data:
            return "WVHT"
        elif "WSPD" in data:
            return "WSPD"
        
        return None

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        key = self._get_primary_measurement_key()
        if key:
            return self.coordinator.data[key]
        
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if not self.coordinator.data:
            return None
        
        key = self._get_primary_measurement_key()
        if key and "_units" in self.coordinator.data:
            units = self.coordinator.data["_units"]
            return units.get(key)
        
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
        
        # Get data for this specific data type
        data = self.coordinator.data.get(self._data_key)
        if not data:
            return attrs
        
        # Add all available data as attributes
        for key, value in data.items():
            if key != "_units" and not key.startswith("_"):
                attrs[key.lower()] = value
        
        # Add units information
        if "_units" in data:
            attrs["units"] = data["_units"]
        
        return attrs
