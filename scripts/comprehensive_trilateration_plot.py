#!/usr/bin/env python3
"""
Comprehensive trilateration plotting script that combines all demo notebook functionality
into a single summary plot showing triangulation fixes, anchor drop locations, and final positions.
"""

import os
import glob
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.gridspec import GridSpec
import numpy as np
from datetime import datetime
from trilaterate_moor import solve_anchor_position, dec2deg, plot_trilateration_survey
from trilaterate_moor import load_bathymetry_netcdf_subsampled

def parse_data_file(file_path):
    """Parse a survey data file and return survey parameters and data."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Parse header parameters
    params = {}
    survey_data = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('Release_height'):
            params['release_height'] = float(line.split(':')[1].strip())
        elif line.startswith('Transducer_depth'):
            params['transducer_depth'] = float(line.split(':')[1].strip())
        elif line.startswith('Water_depth_anchor_launch'):
            params['water_depth_anchor_launch'] = float(line.split(':')[1].strip())
        elif line.startswith('Loc_name'):
            params['loc_name'] = line.split(':')[1].strip()
        elif line.startswith('Sound_speed'):
            params['sound_speed'] = float(line.split(':')[1].strip())
        elif line.startswith('#') or not line:
            continue
        else:
            # Parse survey data line
            parts = line.split()
            if len(parts) >= 6:
                date_time = f"{parts[0]} {parts[1]}"
                range_val = float(parts[2])
                lat_deg = float(parts[3])
                lat_min = float(parts[4])
                lon_deg = float(parts[5])
                lon_min = float(parts[6])
                
                survey_data.append([date_time, lat_deg, lat_min, lon_deg, lon_min, range_val])
    
    return params, survey_data

def convert_to_decimal_degrees(deg, min_val):
    """Convert degrees and decimal minutes to decimal degrees."""
    return deg + min_val/60

def process_survey_data(params, survey_data):
    """Process survey data and solve trilateration."""
    # Convert to decimal degrees
    latitudes = []
    longitudes = []
    ranges = []
    times = []
    
    for date_time, lat_deg, lat_min, lon_deg, lon_min, range_val in survey_data:
        lat_decimal = convert_to_decimal_degrees(lat_deg, lat_min)
        lon_decimal = convert_to_decimal_degrees(lon_deg, lon_min)
        
        latitudes.append(lat_decimal)
        longitudes.append(lon_decimal)
        ranges.append(range_val)
        times.append(date_time)
    
    # Create triangulation data structure
    triang_data = {
        'loc_name': params['loc_name'],
        'release_height': params['release_height'],
        'transducer_depth': params['transducer_depth'],
        'water_depth_anchor_launch': params['water_depth_anchor_launch'],
        'times': times,
        'ranges': ranges,
        'latitudes': latitudes,
        'longitudes': longitudes
    }
    
    # Solve trilateration
    solution = solve_anchor_position(triang_data, true_sound_speed=params['sound_speed'])
    
    return triang_data, solution

def create_comprehensive_plot(all_data, bathymetry_path=None):
    """Create a comprehensive plot showing all trilateration surveys."""
    
    # Set up the plot
    fig = plt.figure(figsize=(20, 12))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # Main summary plot
    ax_main = fig.add_subplot(gs[0, :])
    
    # Individual plots for each survey
    axes_individual = []
    for i in range(min(6, len(all_data))):
        row = 1 + i // 3
        col = i % 3
        if row < 2:
            axes_individual.append(fig.add_subplot(gs[row, col]))
    
    # Calculate plot bounds from all survey data
    all_lons = []
    all_lats = []
    
    for loc_name, triang_data, solution in all_data:
        all_lons.extend(triang_data['longitudes'])
        all_lats.extend(triang_data['latitudes'])
        all_lons.append(solution['anchor_lon'])
        all_lats.append(solution['anchor_lat'])
    
    # Add 3 degree margin as specified
    west = min(all_lons) - 3.0
    east = max(all_lons) + 3.0
    south = min(all_lats) - 3.0
    north = max(all_lats) + 3.0
    
    # Load bathymetry if available with subsampling and regional clipping
    bathy = None
    if bathymetry_path and os.path.exists(bathymetry_path):
        try:
            bathy = load_bathymetry_netcdf_subsampled(
                bathymetry_path, 
                lon_bounds=(west, east), 
                lat_bounds=(south, north), 
                subsample=5
            )
        except Exception as e:
            print(f"Could not load bathymetry from {bathymetry_path}: {e}")
    
    # Colors for different surveys
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    
    # Plot all surveys on main plot
    ax_main.set_title('Comprehensive Trilateration Survey Summary', fontsize=16, fontweight='bold')
    
    for i, (loc_name, triang_data, solution) in enumerate(all_data):
        color = colors[i % len(colors)]
        
        # Plot deployment location
        deploy_lat = triang_data['latitudes'][0]
        deploy_lon = triang_data['longitudes'][0]
        ax_main.plot(deploy_lon, deploy_lat, 's', color=color, markersize=8, 
                    label=f'{loc_name} - Deployment')
        
        # Plot final anchor position
        anchor_lat = solution['anchor_lat']
        anchor_lon = solution['anchor_lon']
        ax_main.plot(anchor_lon, anchor_lat, '*', color=color, markersize=12,
                    label=f'{loc_name} - Final Position')
        
        # Plot survey fixes
        for j, (lat, lon, range_val) in enumerate(zip(triang_data['latitudes'][1:], 
                                                     triang_data['longitudes'][1:], 
                                                     triang_data['ranges'][1:])):
            if j == 0:
                ax_main.plot(lon, lat, 'o', color=color, markersize=4,
                           label=f'{loc_name} - Survey Fixes', alpha=0.7)
            else:
                ax_main.plot(lon, lat, 'o', color=color, markersize=4, alpha=0.7)
        
        # Draw line from deployment to final position
        ax_main.plot([deploy_lon, anchor_lon], [deploy_lat, anchor_lat], 
                    '--', color=color, alpha=0.5, linewidth=1)
        
        # Add fallback distance as circle
        circle = patches.Circle((anchor_lon, anchor_lat), 
                              solution['fallback_distance'] / 111000,  # rough conversion to degrees
                              fill=False, linestyle=':', color=color, alpha=0.3)
        ax_main.add_patch(circle)
    
    ax_main.set_xlabel('Longitude (°W)', fontsize=12)
    ax_main.set_ylabel('Latitude (°N)', fontsize=12)
    ax_main.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax_main.grid(True, alpha=0.3)
    
    # Individual plots for each survey
    for i, ((loc_name, triang_data, solution), ax) in enumerate(zip(all_data[:len(axes_individual)], axes_individual)):
        try:
            # Use the existing plot function for individual surveys
            temp_fig = plot_trilateration_survey(triang_data, solution, bathymetry=bathy)
            
            # Copy the plot to our subplot (this is a simplified approach)
            ax.set_title(f'{loc_name} Survey Details', fontsize=10, fontweight='bold')
            
            # Plot the survey data on individual subplot
            color = colors[i % len(colors)]
            
            # Deployment
            ax.plot(triang_data['longitudes'][0], triang_data['latitudes'][0], 
                   's', color='red', markersize=8, label='Deployment')
            
            # Final position
            ax.plot(solution['anchor_lon'], solution['anchor_lat'], 
                   '*', color='black', markersize=10, label='Final Position')
            
            # Survey fixes
            for lat, lon in zip(triang_data['latitudes'][1:], triang_data['longitudes'][1:]):
                ax.plot(lon, lat, 'o', color=color, markersize=4, alpha=0.7)
            
            # Quality info
            quality_text = f"RMS: {solution['rms_residual']:.1f}m\nFallback: {solution['fallback_distance']:.0f}m"
            ax.text(0.02, 0.98, quality_text, transform=ax.transAxes, 
                   verticalalignment='top', fontsize=8, 
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            ax.set_xlabel('Longitude (°W)', fontsize=8)
            ax.set_ylabel('Latitude (°N)', fontsize=8)
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
            
            plt.close(temp_fig)  # Close the temporary figure
            
        except Exception as e:
            print(f"Error plotting {loc_name}: {e}")
            ax.text(0.5, 0.5, f'Error plotting {loc_name}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    return fig

def main():
    """Main function to process all survey data files and create comprehensive plot."""
    
    # Find all survey data files
    data_dir = "data"
    data_files = glob.glob(os.path.join(data_dir, "*survey*.txt")) + glob.glob(os.path.join(data_dir, "*triangulation*.txt"))
    
    if not data_files:
        print("No survey data files found. Please ensure files are in the 'data' directory.")
        return
    
    print(f"Found {len(data_files)} survey data files:")
    for f in data_files:
        print(f"  - {f}")
    
    # Process all data files
    all_data = []
    
    for file_path in data_files:
        try:
            print(f"\nProcessing {file_path}...")
            params, survey_data = parse_data_file(file_path)
            triang_data, solution = process_survey_data(params, survey_data)
            
            print(f"  Location: {params['loc_name']}")
            print(f"  Anchor position: {solution['anchor_lat']:.6f}°N, {solution['anchor_lon']:.6f}°W")
            print(f"  RMS residual: {solution['rms_residual']:.1f}m")
            print(f"  Fallback distance: {solution['fallback_distance']:.0f}m")
            
            all_data.append((params['loc_name'], triang_data, solution))
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    if not all_data:
        print("No valid survey data processed.")
        return
    
    # Look for bathymetry file
    bathymetry_paths = [
        "../../cruiseplan/data/bathymetry/GEBCO_2025.nc",
        "../../cruiseplan/data/bathymetry/msm142_bathyJJ.nc",
        "../bathymetry/GEBCO_2025.nc",
        "bathymetry/GEBCO_2025.nc"
    ]
    
    bathymetry_path = None
    for path in bathymetry_paths:
        if os.path.exists(path):
            bathymetry_path = path
            break
    
    if bathymetry_path:
        print(f"\nUsing bathymetry file: {bathymetry_path}")
    else:
        print("\nNo bathymetry file found, plotting without bathymetry.")
    
    # Create comprehensive plot
    print(f"\nCreating comprehensive plot with {len(all_data)} surveys...")
    fig = create_comprehensive_plot(all_data, bathymetry_path)
    
    # Save the plot
    output_file = "comprehensive_trilateration_summary.png"
    fig.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved as: {output_file}")
    
    # Show the plot
    plt.show()
    
    # Print summary table
    print("\n" + "="*80)
    print("COMPREHENSIVE TRILATERATION SUMMARY")
    print("="*80)
    print(f"{'Location':<12} {'Lat (°N)':<12} {'Lon (°W)':<12} {'RMS (m)':<10} {'Quality':<10}")
    print("-" * 80)
    
    for loc_name, triang_data, solution in all_data:
        lat = solution['anchor_lat']
        lon = abs(solution['anchor_lon'])
        rms = solution['rms_residual']
        
        if rms < 10:
            quality = "Excellent"
        elif rms < 50:
            quality = "Good"
        elif rms < 100:
            quality = "Fair"
        else:
            quality = "Poor"
            
        print(f"{loc_name:<12} {lat:<12.6f} {lon:<12.6f} {rms:<10.1f} {quality:<10}")
    
    print("="*80)

if __name__ == "__main__":
    main()