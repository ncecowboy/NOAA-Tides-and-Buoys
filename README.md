# NOAA Tides and Buoys Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

This custom integration for Home Assistant provides real-time data from NOAA (National Oceanic and Atmospheric Administration) sources:

- **Tides and Currents** - Water levels, tide predictions, water temperature, air temperature, wind, air pressure, and current data from NOAA CO-OPS stations
- **Buoy Data** - Real-time oceanographic and meteorological data from NOAA NDBC buoys

## Features

- ✅ UI-based configuration flow - no YAML editing required
- ✅ Support for both Tides/Currents and Buoy data sources
- ✅ Multiple data products/types available
- ✅ Automatic hourly data updates
- ✅ Station validation during setup
- ✅ HACS compatible
- ✅ Semantic versioning for easy updates

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/ncecowboy/NOAA-Tides-and-Buoys`
6. Select category "Integration"
7. Click "Add"
8. Find "NOAA Tides and Buoys" in the integration list and click "Download"
9. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/noaa_tides_buoys` directory from this repository
2. Copy it to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "NOAA Tides and Buoys"
4. Select your data source:
   - **Tides and Currents** - For water level and weather data from coastal stations
   - **Buoy Data** - For oceanographic data from offshore buoys
5. Enter your station ID:
   - For Tides/Currents: 7-digit station ID (e.g., `9439040` for Bellingham, WA)
   - For Buoys: Station ID (e.g., `46029` for Columbia River Bar)
6. Select the data type you want to monitor
7. Click **Submit**

### Finding Station IDs

**Tides and Currents Stations:**
- Visit the [NOAA Tides & Currents Station Map](https://tidesandcurrents.noaa.gov/map/)
- Click on a station to see its ID and available data products

**Buoy Stations:**
- Visit the [NOAA NDBC Station Map](https://www.ndbc.noaa.gov/)
- Click on a buoy to see its ID and available data

## Available Data Products

### Tides and Currents
- Water Level
- Tide Predictions
- High/Low Tide Predictions
- Air Temperature
- Water Temperature
- Wind
- Air Pressure
- Currents
- Conductivity
- Salinity
- Humidity
- Visibility
- Air Gap
- One Minute Water Level
- Hourly Height
- High/Low Water Level
- Daily Mean Water Level
- Monthly Mean Water Level

### Buoy Data
- Standard Meteorological Data (wave height, wind speed, etc.)
- Continuous Winds
- Spectral Wave Summary
- Oceanographic Data

## Data Sources

This integration retrieves data from:
- [NOAA CO-OPS API](https://api.tidesandcurrents.noaa.gov/api/prod/) for Tides and Currents
- [NOAA NDBC Real-time Data](https://www.ndbc.noaa.gov/faq/rt_data_access.shtml) for Buoy information

## Sensors

Each configured station creates sensor entities with:
- Primary measurement value as the state
- Additional data points as attributes
- Station metadata (location, name, etc.)
- Data quality flags when available

## Support

For issues, feature requests, or questions:
- [Open an issue](https://github.com/ncecowboy/NOAA-Tides-and-Buoys/issues)
- [View documentation](https://github.com/ncecowboy/NOAA-Tides-and-Buoys)

## Version Management

This integration uses semantic versioning. Updates are managed automatically through HACS when you create GitHub releases with version tags (e.g., `v1.0.0`, `v1.1.0`).

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Disclaimer

This integration is not affiliated with or endorsed by NOAA. Data is provided by NOAA's public APIs and is subject to their terms of use and availability.
