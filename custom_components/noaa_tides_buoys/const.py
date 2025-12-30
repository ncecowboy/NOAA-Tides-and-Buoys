"""Constants for the NOAA Tides and Buoys integration."""

DOMAIN = "noaa_tides_buoys"

# Configuration
CONF_DATA_SOURCE = "data_source"
CONF_STATION_ID = "station_id"

# Data sources
DATA_SOURCE_TIDES = "tides_currents"
DATA_SOURCE_BUOY = "buoy"

# Tides and Currents products
TIDES_PRODUCTS = {
    "water_level": "Water Level",
    "predictions": "Tide Predictions",
    "predictions_hilo": "High/Low Tide Predictions",
    "air_temperature": "Air Temperature",
    "water_temperature": "Water Temperature",
    "wind": "Wind",
    "air_pressure": "Air Pressure",
    "currents": "Currents",
    "currents_predictions": "Current Predictions",
    "conductivity": "Conductivity",
    "salinity": "Salinity",
    "humidity": "Humidity",
    "visibility": "Visibility",
    "air_gap": "Air Gap",
    "one_minute_water_level": "One Minute Water Level",
    "hourly_height": "Hourly Height",
    "high_low": "High/Low Water Level",
    "daily_mean": "Daily Mean Water Level",
    "monthly_mean": "Monthly Mean Water Level",
    "datums": "Tidal Datums",
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
TIDES_METADATA_API_BASE = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"
BUOY_API_BASE = "https://www.ndbc.noaa.gov/data/realtime2"

# Update intervals (in seconds)
UPDATE_INTERVAL = 3600  # 1 hour

# Default settings
DEFAULT_DATUM = "MLLW"
DEFAULT_UNITS = "english"
DEFAULT_TIME_ZONE = "lst_ldt"  # Local Standard/Daylight Time
DEFAULT_RANGE = 24  # hours

# Units for Tides products (based on DEFAULT_UNITS = "english")
TIDES_UNITS = {
    "water_level": "ft",
    "predictions": "ft",
    "predictions_hilo": "ft",
    "air_temperature": "°F",
    "water_temperature": "°F",
    "wind": "kts",
    "air_pressure": "mb",
    "currents": "kts",
    "currents_predictions": "kts",
    "conductivity": "mS/cm",
    "salinity": "PSU",
    "humidity": "%",
    "visibility": "nmi",
    "air_gap": "ft",
    "one_minute_water_level": "ft",
    "hourly_height": "ft",
    "high_low": "ft",
    "daily_mean": "ft",
    "monthly_mean": "ft",
    "datums": "ft",
}
