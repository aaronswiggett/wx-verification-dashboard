"""
Spatial Verification Generator for NBM/NDFD vs URMA
Requires: xarray, matplotlib, cartopy, herbie-data, cfgrib

This script is designed to be run via GitHub Actions or locally.
It downloads the required grids, calculates the bias (delta), 
and exports standard PNG maps for the web frontend to display.
"""

import os
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from herbie import Herbie
from datetime import datetime, timedelta

# Configuration
OUTPUT_DIR = "./output_maps"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define the date we want to verify (e.g., yesterday's MaxT)
# In production, this would be dynamically set to yesterday
verify_date = datetime.utcnow() - timedelta(days=1)
date_str = verify_date.strftime("%Y-%m-%d")

def fetch_and_process_data():
    """
    Fetches NBM and URMA data using Herbie.
    Note: NDFD fetching depends on the specific NOMADS directory structure,
    but the logic follows the exact same pattern as the NBM.
    """
    print(f"Fetching data for {date_str}...")
    
    try:
        # 1. Fetch URMA (The Observation/Truth)
        # Assuming we want the 00Z run which contains the 24h Max/Min summary
        H_urma = Herbie(date_str, model='urma', product='2dvaranl', fxx=0)
        # Extract Maximum Temperature at 2m
        ds_urma = H_urma.xarray('TMP:2 m above ground') 
        
        # 2. Fetch NBM (The Forecast)
        # Fetching a forecast made 24 hours prior valid for the verification date
        forecast_date = verify_date - timedelta(days=1)
        H_nbm = Herbie(forecast_date.strftime("%Y-%m-%d"), model='nbm', product='co', fxx=24)
        ds_nbm = H_nbm.xarray('TMP:2 m above ground')

        # NOTE ON GRID ALIGNMENT: 
        # NBM and URMA might be on slightly different grids (e.g., NBM on grid 130, URMA on 227).
        # Before subtracting, you must project them to a common grid.
        # For simplicity in this template, we assume they are regridded or match.
        # Use libraries like `xesmf` or `pyresample` for robust regridding in production.
        
        # Calculate the Delta (Bias)
        # Positive value = NBM Forecast was too warm
        # Negative value = NBM Forecast was too cold
        ds_delta = ds_nbm - ds_urma
        
        return ds_nbm, ds_urma, ds_delta
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None, None, None

def plot_map(data_array, title, filename, cmap='coolwarm', vmin=None, vmax=None):
    """
    Generates a Cartopy map and saves it as a PNG.
    """
    print(f"Generating map: {filename}...")
    
    # Set up the map projection (Lambert Conformal is standard for CONUS)
    projection = ccrs.LambertConformal(central_longitude=-97.5, central_latitude=38.5)
    
    fig, ax = plt.subplots(figsize=(12, 8), subplot_kw={'projection': projection})
    
    # Add map features
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linewidth=0.8)
    ax.add_feature(cfeature.STATES, linewidth=0.2)
    
    # Set map extent for CONUS
    ax.set_extent([-120, -70, 20, 50], crs=ccrs.PlateCarree())

    # Plot the data
    # We use x and y coordinates from the GRIB file
    mesh = ax.pcolormesh(
        data_array.longitude, data_array.latitude, data_array,
        transform=ccrs.PlateCarree(),
        cmap=cmap, vmin=vmin, vmax=vmax, shading='auto'
    )
    
    # Add colorbar and title
    cbar = plt.colorbar(mesh, ax=ax, orientation='horizontal', pad=0.05, aspect=50)
    cbar.set_label('Temperature (°C)')
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    # Save the figure
    filepath = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved {filepath}")

if __name__ == "__main__":
    # In a real scenario, you'd loop through parameters (MaxT, MinT) and models (NBM, NDFD)
    # For this template, we structure the logic.
    
    # ds_nbm, ds_urma, ds_delta = fetch_and_process_data()
    
    print("This script provides the framework for processing the GRIB files.")
    print("To run fully, ensure you have eccodes/cfgrib configured on your system.")
    print("The frontend expects the following files to be generated:")
    print(" - nbm_maxt_forecast.png")
    print(" - nbm_maxt_delta.png")
    print(" - ndfd_maxt_forecast.png")
    print(" - ndfd_maxt_delta.png")
    print(" - urma_maxt.png")