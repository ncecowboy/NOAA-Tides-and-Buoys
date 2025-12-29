# Quick Start Guide

## Installation via HACS

1. **Add Custom Repository**
   - Open HACS in your Home Assistant instance
   - Go to "Integrations"
   - Click the three-dot menu (⋮) in the top right
   - Select "Custom repositories"
   - Add repository URL: `https://github.com/ncecowboy/NOAA-Tides-and-Buoys`
   - Category: "Integration"
   - Click "Add"

2. **Install the Integration**
   - Search for "NOAA Tides and Buoys" in HACS
   - Click "Download"
   - Restart Home Assistant

3. **Configure the Integration**
   - Go to Settings → Devices & Services
   - Click "+ Add Integration"
   - Search for "NOAA Tides and Buoys"
   - Follow the setup wizard:
     - Select data source (Tides/Currents or Buoy)
     - Enter station ID (e.g., 9439040 or 46029)
     - Select data type to monitor

## Example Stations

### Tides and Currents
- **9439040** - Bellingham, WA
- **9414290** - San Francisco, CA
- **8518750** - The Battery, NY

Find more stations: https://tidesandcurrents.noaa.gov/map/

### Buoys
- **46029** - Columbia River Bar, OR
- **46089** - Tilllamook, OR  
- **41002** - South Hatteras, NC

Find more buoys: https://www.ndbc.noaa.gov/

## Available Data Types

### Tides and Currents
- Water Level
- Tide Predictions
- Air Temperature
- Water Temperature
- Wind
- Air Pressure
- Currents

### Buoys
- Standard Meteorological Data
- Continuous Winds
- Spectral Wave Summary
- Oceanographic Data

## Troubleshooting

**Integration doesn't appear after installation:**
- Make sure you restarted Home Assistant
- Clear your browser cache

**Station validation fails:**
- Verify the station ID is correct
- Check that the station supports your selected data type
- Ensure you have internet connectivity

**No data appearing:**
- Check the station is active and reporting
- Review Home Assistant logs for error messages
- Verify the update interval (default: 1 hour)

## Support

For issues and feature requests, visit:
https://github.com/ncecowboy/NOAA-Tides-and-Buoys/issues
