"""Sensor platform for NOAA Tides and Buoys integration."""
from __future__ import annotations

from datetime import datetime, timezone
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
                now = datetime.now(timezone.utc)
                for tide in data["predictions"]:
                    if "t" in tide:
                        # Parse tide time and make it timezone-aware (UTC)
                        tide_time = datetime.strptime(tide["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                        if tide_time > now and "v" in tide:
                            return tide["v"]
            return None
        
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
            now = datetime.now(timezone.utc)
            
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
                        # Parse tide time and make it timezone-aware (UTC)
                        tide_time = datetime.strptime(tide["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                        tide_event = {
                            "time": tide["t"],
                            "height": tide["v"],
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
                    except ValueError:
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
        
        # Helper function to check if a value is a missing data marker
        def is_valid_value(value):
            """Check if value is valid (not a missing data marker)."""
            if value == "MM":
                return False
            # Check numeric missing data markers (as float or string)
            try:
                num_val = float(value)
                return num_val not in [999.0, 99.0, 9999.0]
            except (ValueError, TypeError):
                return True  # If not numeric, assume valid
        
        # Define priority order for different data types
        # For standard meteorological data, prioritize wave height, then wind speed, then air temp
        if self._data_key == "standard":
            for key in ["WVHT", "WSPD", "ATMP", "WTMP", "PRES"]:
                if key in data and is_valid_value(data[key]):
                    return key
        # For continuous winds, prioritize wind speed
        elif self._data_key == "cwind":
            for key in ["WSPD", "WDIR", "GST"]:
                if key in data and is_valid_value(data[key]):
                    return key
        # For spectral wave data, prioritize significant wave height
        elif self._data_key == "spec":
            for key in ["WVHT", "SwH", "SwP", "WWH"]:
                if key in data and is_valid_value(data[key]):
                    return key
        # For ocean data, prioritize water temperature
        elif self._data_key == "ocean":
            for key in ["WTMP", "DEPTH", "OTMP", "SAL"]:
                if key in data and is_valid_value(data[key]):
                    return key
        # For solar radiation
        elif self._data_key == "srad":
            for key in ["SRAD1", "SRAD2", "SRAD3"]:
                if key in data and is_valid_value(data[key]):
                    return key
        # For ADCP data
        elif self._data_key == "adcp":
            for key in ["DIR", "SPD", "DEPTH"]:
                if key in data and is_valid_value(data[key]):
                    return key
        # For supplemental data
        elif self._data_key == "supl":
            for key in ["PRES", "ATMP", "WTMP"]:
                if key in data and is_valid_value(data[key]):
                    return key
        
        # Fallback: return first non-timestamp, non-units key that has valid data
        for key in data:
            if (key not in ["YY", "MM", "DD", "hh", "mm", "_units", "#YY"] 
                and not key.startswith("#")
                and is_valid_value(data[key])):
                return key
        
        return None

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        # Get data for this specific data type
        data = self.coordinator.data.get(self._data_key)
        if not data:
            return None
        
        key = self._get_primary_measurement_key()
        if key:
            return data.get(key)
        
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if not self.coordinator.data:
            return None
        
        # Get data for this specific data type
        data = self.coordinator.data.get(self._data_key)
        if not data:
            return None
        
        key = self._get_primary_measurement_key()
        if key and "_units" in data:
            units = data["_units"]
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
        
        # Create a timestamp from the date/time fields if available
        if all(k in data for k in ["YY", "MM", "DD", "hh", "mm"]):
            try:
                # Handle both 2-digit and 4-digit years
                year = data["YY"]
                if isinstance(year, str) and len(year) == 2:
                    year = "20" + year
                timestamp = f"{year}-{data['MM'].zfill(2) if isinstance(data['MM'], str) else str(int(data['MM'])).zfill(2)}-{data['DD'].zfill(2) if isinstance(data['DD'], str) else str(int(data['DD'])).zfill(2)} {data['hh'].zfill(2) if isinstance(data['hh'], str) else str(int(data['hh'])).zfill(2)}:{data['mm'].zfill(2) if isinstance(data['mm'], str) else str(int(data['mm'])).zfill(2)}"
                attrs["timestamp"] = timestamp
            except (ValueError, KeyError, AttributeError):
                pass
        
        # Add all available data as attributes
        for key, value in data.items():
            if key != "_units" and not key.startswith("_"):
                attrs[key.lower()] = value
        
        # Add units information
        if "_units" in data:
            attrs["units"] = data["_units"]
        
        return attrs
