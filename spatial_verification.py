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
verify_date = datetime.utcnow() - timedelta(days=1)
date_str = verify_date.strftime("%Y-%m-%d")

def fetch_and_process_data():
    """
    Fetches NBM and URMA data using Herbie.
    """
    print(f"Fetching data for {date_str}...")
    
    try:
        # 1. Fetch URMA (The Observation/Truth)
        H_urma = Herbie(date_str, model='urma', product='2dvaranl', fxx=0)
        ds_urma = H_urma.xarray('TMP:2 m above ground') 
        
        # 2. Fetch NBM (The Forecast)
        forecast_date = verify_date - timedelta(days=1)
        H_nbm = Herbie(forecast_date.strftime("%Y-%m-%d"), model='nbm', product='co', fxx=24)
        ds_nbm = H_nbm.xarray('TMP:2 m above ground')

        # Calculate the Delta (Bias)
        # Note: In a production environment, you may need to regrid one of the 
        # datasets here if their native grid coordinates do not align perfectly.
        try:
            ds_delta = ds_nbm - ds_urma
        except Exception as e:
            print(f"Grid math error (likely grid mismatch): {e}")
            ds_delta = None
            
        return ds_nbm, ds_urma, ds_delta
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None, None, None

def plot_map(data_array, title, filename, cmap='coolwarm', vmin=None, vmax=None):
    """
    Generates a Cartopy map and saves it as a PNG.
    """
    print(f"Generating map: {filename}...")
    
    projection = ccrs.LambertConformal(central_longitude=-97.5, central_latitude=38.5)
    fig, ax = plt.subplots(figsize=(12, 8), subplot_kw={'projection': projection})
    
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linewidth=0.8)
    ax.add_feature(cfeature.STATES, linewidth=0.2)
    ax.set_extent([-120, -70, 20, 50], crs=ccrs.PlateCarree())

    # We use x and y coordinates from the GRIB file
    mesh = ax.pcolormesh(
        data_array.longitude, data_array.latitude, data_array,
        transform=ccrs.PlateCarree(),
        cmap=cmap, vmin=vmin, vmax=vmax, shading='auto'
    )
    
    cbar = plt.colorbar(mesh, ax=ax, orientation='horizontal', pad=0.05, aspect=50)
    cbar.set_label('Temperature (°C)')
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved {filepath}")

if __name__ == "__main__":
    print("Starting verification processing...")
    
    # Actually execute the data fetching function
    ds_nbm, ds_urma, ds_delta = fetch_and_process_data()
    
    if ds_nbm is not None and ds_urma is not None and ds_delta is not None:
        print("Data fetched successfully! Generating maps...")
        plot_map(ds_nbm, "NBM Forecast", "nbm_maxt_forecast.png", cmap='YlOrRd')
        plot_map(ds_urma, "URMA Analysis", "urma_maxt.png", cmap='YlOrRd')
        plot_map(ds_delta, "NBM Bias (Forecast - URMA)", "nbm_maxt_delta.png", cmap='coolwarm', vmin=-10, vmax=10)
        
        # Placeholder for NDFD until we build the specific NDFD fetch logic
        plot_map(ds_nbm, "NDFD Forecast (Placeholder)", "ndfd_maxt_forecast.png", cmap='YlOrRd')
        plot_map(ds_delta, "NDFD Bias (Placeholder)", "ndfd_maxt_delta.png", cmap='coolwarm', vmin=-10, vmax=10)
    else:
        print("Failed to fetch real GRIB data or calculate delta. Generating fallback placeholder maps...")
        import numpy as np
        lons = np.linspace(-120, -70, 100)
        lats = np.linspace(20, 50, 100)
        dummy_data = np.zeros((100, 100))
        dummy_da = xr.DataArray(dummy_data, coords={'latitude': lats, 'longitude': lons}, dims=["latitude", "longitude"])
        
        plot_map(dummy_da, "Data Unavailable", "nbm_maxt_forecast.png", cmap='Greys')
        plot_map(dummy_da, "Data Unavailable", "nbm_maxt_delta.png", cmap='Greys')
        plot_map(dummy_da, "Data Unavailable", "urma_maxt.png", cmap='Greys')
        plot_map(dummy_da, "Data Unavailable", "ndfd_maxt_forecast.png", cmap='Greys')
        plot_map(dummy_da, "Data Unavailable", "ndfd_maxt_delta.png", cmap='Greys')
        
    print("Processing complete!")
