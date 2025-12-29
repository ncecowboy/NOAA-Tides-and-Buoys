"""Constants for the NOAA Tides and Buoys integration."""

DOMAIN = "noaa_tides_buoys"

# Configuration
CONF_DATA_SOURCE = "data_source"
CONF_STATION_ID = "station_id"
CONF_DATA_TYPE = "data_type"

# Data sources
DATA_SOURCE_TIDES = "tides_currents"
DATA_SOURCE_BUOY = "buoy"

# Tides and Currents products
TIDES_PRODUCTS = {
    "water_level": "Water Level",
    "predictions": "Tide Predictions",
    "air_temperature": "Air Temperature",
    "water_temperature": "Water Temperature",
    "wind": "Wind",
    "air_pressure": "Air Pressure",
    "currents": "Currents",
}

# Buoy data types
BUOY_DATA_TYPES = {
    "standard": "Standard Meteorological Data",
    "cwind": "Continuous Winds",
    "spec": "Spectral Wave Summary",
    "ocean": "Oceanographic Data",
}

# Buoy data type to file extension mapping
BUOY_DATA_TYPE_MAP = {
    "standard": "txt",
    "cwind": "cwind",
    "spec": "spec",
    "ocean": "ocean",
}

# API endpoints
TIDES_API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
BUOY_API_BASE = "https://www.ndbc.noaa.gov/data/realtime2"

# Update intervals (in seconds)
UPDATE_INTERVAL = 3600  # 1 hour

# Default settings
DEFAULT_DATUM = "MLLW"
DEFAULT_UNITS = "english"
DEFAULT_TIME_ZONE = "gmt"
DEFAULT_RANGE = 24  # hours
