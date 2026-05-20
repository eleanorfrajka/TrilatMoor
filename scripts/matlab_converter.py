#!/usr/bin/env python3
"""
Convert MATLAB ship track files (.mat) to Python/NetCDF format.

This script converts the MSM121_track_all.mat file format used in the MATLAB
code to a format compatible with the Python trilaterate_moor package.
"""

import numpy as np
import sys
from datetime import datetime, timedelta
try:
    import scipy.io
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import xarray as xr
    import pandas as pd
    HAS_XARRAY = True
except ImportError:
    HAS_XARRAY = False


def convert_matlab_ship_track(mat_filename: str, output_filename: str = None):
    """
    Convert MATLAB ship track file to NetCDF format.
    
    Parameters:
    -----------
    mat_filename : str
        Path to MATLAB .mat file containing ship track
    output_filename : str, optional
        Output NetCDF filename (defaults to input name with .nc extension)
        
    Returns:
    --------
    dict
        Ship track data with 'time', 'lat', 'lon' keys
    """
    
    if not HAS_SCIPY:
        raise ImportError("scipy required for reading MATLAB files. Install with: pip install scipy")
    
    print(f"Loading MATLAB file: {mat_filename}")
    
    # Load MATLAB file
    try:
        mat_data = scipy.io.loadmat(mat_filename)
    except Exception as e:
        raise ValueError(f"Error reading MATLAB file: {e}")
    
    # Extract ship data structure
    if 'ship' in mat_data:
        ship_struct = mat_data['ship']
        
        # Handle MATLAB structure arrays
        if ship_struct.dtype.names:
            # Structure with fields
            ship_data = {
                'lat': ship_struct['lat'][0,0].flatten(),
                'lon': ship_struct['lon'][0,0].flatten(), 
                'time': ship_struct['time'][0,0].flatten()
            }
        else:
            # Try different extraction methods
            print("Warning: Unexpected MATLAB structure format")
            print("Available keys in mat file:", list(mat_data.keys()))
            return None
            
    else:
        print("Error: No 'ship' variable found in MATLAB file")
        print("Available variables:", [k for k in mat_data.keys() if not k.startswith('_')])
        return None
    
    # Convert MATLAB datenum to Python datetime
    # MATLAB datenum: days since January 0, 0000 (Gregorian)
    # Convert to Python datetime
    
    times = []
    for datenum_val in ship_data['time']:
        try:
            # MATLAB datenum to datetime
            # MATLAB day 1 = January 1, 0001
            # Days between January 1, 0001 and January 1, 1970 = 719529
            dt = datetime(1970, 1, 1) + timedelta(days=float(datenum_val) - 719529)
            times.append(dt)
        except (ValueError, OverflowError) as e:
            print(f"Warning: Could not convert datenum {datenum_val}: {e}")
            continue
    
    # Correct longitude if needed (MATLAB code does this)
    if np.mean(ship_data['lon']) > 0:
        ship_data['lon'] = -ship_data['lon']
    
    # Create final data structure
    track_data = {
        'time': times,
        'lat': ship_data['lat'].tolist(),
        'lon': ship_data['lon'].tolist()
    }
    
    print(f"Loaded {len(times)} track points")
    print(f"Time range: {min(times)} to {max(times)}")
    print(f"Lat range: {np.min(ship_data['lat']):.4f} to {np.max(ship_data['lat']):.4f}")
    print(f"Lon range: {np.min(ship_data['lon']):.4f} to {np.max(ship_data['lon']):.4f}")
    
    # Save to NetCDF if xarray available and output requested
    if output_filename and HAS_XARRAY:
        save_to_netcdf(track_data, output_filename)
    elif output_filename and not HAS_XARRAY:
        print("Warning: xarray not available, cannot save NetCDF. Install with: pip install xarray")
    
    return track_data


def save_to_netcdf(track_data: dict, filename: str):
    """Save track data to NetCDF format."""
    
    # Convert to pandas datetime index for xarray
    time_index = pd.to_datetime(track_data['time'])
    
    # Create xarray dataset
    ds = xr.Dataset({
        'latitude': (['time'], track_data['lat']),
        'longitude': (['time'], track_data['lon'])
    }, coords={
        'time': time_index
    })
    
    # Add attributes
    ds.attrs['title'] = 'Ship track data'
    ds.attrs['source'] = 'Converted from MATLAB format'
    ds.attrs['created'] = datetime.now().isoformat()
    
    ds['latitude'].attrs = {
        'long_name': 'Latitude',
        'units': 'degrees_north',
        'standard_name': 'latitude'
    }
    
    ds['longitude'].attrs = {
        'long_name': 'Longitude', 
        'units': 'degrees_east',
        'standard_name': 'longitude'
    }
    
    # Save to NetCDF
    ds.to_netcdf(filename)
    print(f"Saved track data to NetCDF: {filename}")


def create_example_ship_track():
    """Create example ship track data for testing."""
    
    # Create synthetic ship track around mooring area
    base_lat = 42.70  # Near the example mooring
    base_lon = -51.90
    
    # Generate circular track over 2 hours
    n_points = 120  # 2 hours of 1-minute data
    start_time = datetime(2023, 9, 30, 18, 0, 0)
    
    times = [start_time + timedelta(minutes=i) for i in range(n_points)]
    
    # Circular track with some noise
    angles = np.linspace(0, 2*np.pi, n_points)
    radius = 0.05  # degrees (roughly 5 km)
    noise_level = 0.002  # Small amount of position noise
    
    lats = base_lat + radius * np.cos(angles) + np.random.normal(0, noise_level, n_points)
    lons = base_lon + radius * np.sin(angles) + np.random.normal(0, noise_level, n_points)
    
    track_data = {
        'time': times,
        'lat': lats.tolist(),
        'lon': lons.tolist()
    }
    
    print("Created example ship track with", len(times), "points")
    return track_data


def main():
    """Main function for testing converter."""
    
    if len(sys.argv) > 1:
        mat_filename = sys.argv[1]
        output_filename = sys.argv[2] if len(sys.argv) > 2 else None
        
        try:
            track_data = convert_matlab_ship_track(mat_filename, output_filename)
            print("✅ Conversion successful!")
            
        except Exception as e:
            print(f"❌ Error converting file: {e}")
            sys.exit(1)
    else:
        print("Creating example ship track for testing...")
        track_data = create_example_ship_track()
        
        # Save example track
        if HAS_XARRAY:
            save_to_netcdf(track_data, "data/example_ship_track.nc")
        
        print("Example usage:")
        print("  python matlab_converter.py input.mat [output.nc]")


if __name__ == "__main__":
    main()