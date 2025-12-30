"""Sensor platform for NOAA Tides and Buoys integration."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
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

# Priority data types to check for metadata (most common first)
METADATA_PRIORITY_DATA_TYPES = ["water_level", "predictions", "predictions_hilo"]


def _find_next_tide(predictions_data: dict[str, Any]) -> dict[str, Any] | None:
    """Find the next tide event from predictions data.
    
    Args:
        predictions_data: The predictions_hilo data from coordinator
        
    Returns:
        Dictionary with time, height, and type of next tide, or None if not found
    """
    if not predictions_data or "predictions" not in predictions_data:
        return None
    
    if not isinstance(predictions_data["predictions"], list):
        return None
    
    now = datetime.now(timezone.utc)
    
    for tide in predictions_data["predictions"]:
        if "t" not in tide or "v" not in tide or "type" not in tide:
            continue
        
        try:
            # Parse tide time as UTC (GMT from API)
            tide_time = datetime.strptime(tide["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            
            if tide_time > now:
                # This is the next tide
                return {
                    "time": tide["t"],
                    "height": float(tide["v"]),
                    "type": tide["type"]
                }
        except (ValueError, TypeError):
            continue
    
    return None


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
) -> list[SensorEntity]:
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
    
    # Create station metadata entities
    sensors.extend([
        NOAAStationMetadataSensor(coordinator, entry, "name", "Station Name"),
        NOAAStationMetadataSensor(coordinator, entry, "lat", "Latitude"),
        NOAAStationMetadataSensor(coordinator, entry, "lon", "Longitude"),
    ])
    
    # Create additional entities for tide predictions
    sensors.extend([
        NOAATidePredictionSensor(coordinator, entry, "next_tide_time", "Next Tide Time"),
        NOAATidePredictionSensor(coordinator, entry, "next_tide_height", "Next Tide Height"),
        NOAATidePredictionSensor(coordinator, entry, "next_tide_type", "Next Tide Type"),
    ])
    
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
                # API returns GMT times when time_zone=gmt
                now = datetime.now(timezone.utc)
                for tide in data["predictions"]:
                    if "t" in tide and "v" in tide:
                        try:
                            # Parse tide time as UTC (GMT from API)
                            tide_time = datetime.strptime(tide["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
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
                # API returns GMT times when time_zone=gmt
                now = datetime.now(timezone.utc)
                for current in data["current_predictions"]:
                    if "t" in current and "v" in current:
                        try:
                            # Parse current time as UTC (GMT from API)
                            current_time = datetime.strptime(current["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
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
                # MLLW is the standard datum used for tide predictions and charts
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
            # API returns GMT times when time_zone=gmt
            now = datetime.now(timezone.utc)
            
            # Use helper to find next tide
            next_tide = _find_next_tide(data)
            
            if "predictions" in data and isinstance(data["predictions"], list):
                prior_highs = []
                prior_lows = []
                future_highs = []
                future_lows = []
                
                for tide in data["predictions"]:
                    if "t" not in tide or "v" not in tide or "type" not in tide:
                        continue
                    
                    try:
                        # Parse tide time as UTC (GMT from API)
                        tide_time = datetime.strptime(tide["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
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
                            if tide["type"] == "H":
                                future_highs.append(tide_event)
                            else:
                                future_lows.append(tide_event)
                    except (ValueError, TypeError):
                        continue
                
                # Add attributes using the helper function result
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
            # API returns GMT times when time_zone=gmt
            now = datetime.now(timezone.utc)
            
            if "current_predictions" in data and isinstance(data["current_predictions"], list):
                future_currents = []
                next_current = None
                
                for current in data["current_predictions"]:
                    if "t" not in current or "v" not in current:
                        continue
                    
                    try:
                        # Parse current time as UTC (GMT from API)
                        current_time = datetime.strptime(current["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                        current_event = {
                            "time": current["t"],
                            "speed": float(current["v"]),
                            "direction": current.get("d", "")  # Direction is compass bearing (e.g., "NE", "180")
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
                            # Sanitize datum name for use as attribute key
                            # Replace spaces and special characters with underscores
                            datum_name = re.sub(r'[^a-zA-Z0-9]', '_', datum["n"].lower())
                            # Remove consecutive underscores and leading/trailing underscores
                            datum_name = re.sub(r'_+', '_', datum_name).strip('_')
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
        
        return attrs


class NOAAStationMetadataSensor(CoordinatorEntity, SensorEntity):
    """Representation of a NOAA Station metadata sensor."""

    def __init__(
        self,
        coordinator: NOAADataUpdateCoordinator,
        entry: ConfigEntry,
        metadata_key: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._metadata_key = metadata_key
        self._attr_name = f"NOAA {entry.data[CONF_STATION_ID]} {name}"
        self._attr_unique_id = f"{entry.entry_id}_metadata_{metadata_key}"
        self._station_id = entry.data[CONF_STATION_ID]
        
        # Set device info - same device as other sensors
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
        
        # Check common data types first for better performance
        for data_type in METADATA_PRIORITY_DATA_TYPES:
            if data_type in self.coordinator.data:
                data_type_data = self.coordinator.data[data_type]
                if data_type_data and "metadata" in data_type_data:
                    metadata = data_type_data["metadata"]
                    if self._metadata_key in metadata:
                        return metadata[self._metadata_key]
        
        # Fallback: check all data types if not found in priority types
        for data_type_data in self.coordinator.data.values():
            if data_type_data and "metadata" in data_type_data:
                metadata = data_type_data["metadata"]
                if self._metadata_key in metadata:
                    return metadata[self._metadata_key]
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "station_id": self._station_id,
            "metadata_type": self._metadata_key,
        }


class NOAATidePredictionSensor(CoordinatorEntity, SensorEntity):
    """Representation of a NOAA Tide prediction detail sensor."""

    def __init__(
        self,
        coordinator: NOAADataUpdateCoordinator,
        entry: ConfigEntry,
        prediction_key: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._prediction_key = prediction_key
        self._attr_name = f"NOAA {entry.data[CONF_STATION_ID]} {name}"
        self._attr_unique_id = f"{entry.entry_id}_prediction_{prediction_key}"
        self._station_id = entry.data[CONF_STATION_ID]
        
        # Set device info - same device as other sensors
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
        
        # Get data from predictions_hilo
        data = self.coordinator.data.get("predictions_hilo")
        next_tide = _find_next_tide(data)
        
        if not next_tide:
            return None
        
        # Map prediction keys to their corresponding values
        if self._prediction_key == "next_tide_time":
            return next_tide["time"]
        elif self._prediction_key == "next_tide_height":
            return next_tide["height"]
        elif self._prediction_key == "next_tide_type":
            return "High" if next_tide["type"] == "H" else "Low"
        
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        # Only tide height has a unit
        if self._prediction_key == "next_tide_height":
            return TIDES_UNITS.get("predictions_hilo", "ft")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "station_id": self._station_id,
            "prediction_type": self._prediction_key,
        }


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
                year = str(data["YY"])
                if len(year) == 2:
                    # NOAA real-time data uses current century for 2-digit years
                    year = "20" + year
                
                # Format each component with zero-padding
                month = str(int(data["MM"])).zfill(2)
                day = str(int(data["DD"])).zfill(2)
                hour = str(int(data["hh"])).zfill(2)
                minute = str(int(data["mm"])).zfill(2)
                
                timestamp = f"{year}-{month}-{day} {hour}:{minute}"
                attrs["timestamp"] = timestamp
            except (ValueError, KeyError, AttributeError, TypeError):
                pass
        
        # Add all available data as attributes
        for key, value in data.items():
            if key != "_units" and not key.startswith("_"):
                attrs[key.lower()] = value
        
        # Add units information
        if "_units" in data:
            attrs["units"] = data["_units"]
        
        return attrs
