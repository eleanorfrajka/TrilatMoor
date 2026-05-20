#!/usr/bin/env python3
"""
Process all FC triangulation sites and generate plots.
"""

import sys
import os
sys.path.insert(0, '.')

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

from trilaterate_moor import (
    parse_triangulation_file,
    solve_anchor_position,
    plot_trilateration_survey,
    dec2deg
)
from matlab_converter import convert_matlab_ship_track


def process_site(site_name, ship_track=None):
    """Process a single triangulation site."""
    
    filename = f"data/{site_name}_triangulation.txt"
    
    try:
        print(f"\n{'='*60}")
        print(f"PROCESSING SITE: {site_name}")
        print(f"{'='*60}")
        
        # Parse triangulation data
        print(f"Reading: {filename}")
        triang_data = parse_triangulation_file(filename)
        
        # Show survey info
        print(f"Location: {triang_data['loc_name']}")
        print(f"Water depth: {triang_data['water_depth_anchor_launch']:.0f}m")
        print(f"Release height: {triang_data['release_height']:.0f}m")
        
        # Count valid fixes
        valid_fixes = sum(1 for r in triang_data['ranges'] if r > 0)
        print(f"Position fixes: {valid_fixes}")
        
        # Show survey times and ranges
        print("Survey data:")
        for i, (time, range_val, lat, lon) in enumerate(zip(
            triang_data['times'], triang_data['ranges'], 
            triang_data['latitudes'], triang_data['longitudes'])):
            
            if range_val == 0:
                print(f"  Deployment: {time} at {lat:.5f}°N, {lon:.5f}°W")
            else:
                print(f"  Fix {i}: {time} - Range: {range_val:.0f}m")
        
        # Solve for anchor position  
        print("\nSolving trilateration...")
        
        # Use correct sound speed for FC sites (from MATLAB code)
        if site_name == 'FC3':
            true_sound_speed = 1495  # m/s (as per MATLAB code)
        else:
            true_sound_speed = 1503  # m/s
            
        solution = solve_anchor_position(
            triang_data,
            true_sound_speed=true_sound_speed
        )
        
        # Results
        print(f"\nRESULTS FOR {site_name}:")
        print("-" * 40)
        
        anchor_lat = solution['anchor_lat']
        anchor_lon = solution['anchor_lon']
        
        print(f"Anchor position: {anchor_lat:.6f}°N, {anchor_lon:.6f}°W")
        
        # Format in degrees/minutes
        _, _, lat_str = dec2deg(anchor_lat)
        _, _, lon_str = dec2deg(abs(anchor_lon))
        print(f"Position (deg/min): {lat_str}N, {lon_str}W")
        
        print(f"Fallback distance: {solution['fallback_distance']:.0f} m")
        print(f"Max residual error: {solution['max_residual']:.1f} m")
        print(f"RMS residual error: {solution['rms_residual']:.1f} m")
        
        # Individual residuals
        print("Individual fix residuals:")
        for i, residual in enumerate(solution['residuals']):
            print(f"  Fix {i+1}: {residual:.1f} m")
        
        # Create plot
        print(f"\nCreating plot: triangpy_{site_name}.png")
        
        fig = plot_trilateration_survey(
            triang_data,
            solution,
            ship_track=ship_track,
            save_figure=f"figs/triangpy_{site_name}.png"
        )
        
        plt.close(fig)
        print(f"✅ {site_name} completed successfully!")
        
        return solution
        
    except Exception as e:
        print(f"❌ Error processing {site_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Process all FC sites."""
    
    # Load ship track once
    print("Loading ship track data...")
    try:
        ship_track = convert_matlab_ship_track('data/MSM121_track_all.mat')
        print(f"Ship track loaded: {len(ship_track['time'])} points")
        print(f"Time range: {min(ship_track['time'])} to {max(ship_track['time'])}")
    except Exception as e:
        print(f"Warning: Could not load ship track: {e}")
        ship_track = None
    
    # Process all FC sites
    fc_sites = ['FC1', 'FC3', 'FC4']
    results = {}
    
    for site_name in fc_sites:
        if os.path.exists(f"data/{site_name}_triangulation.txt"):
            results[site_name] = process_site(site_name, ship_track)
        else:
            print(f"Warning: {site_name}_triangulation.txt not found")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY OF ALL SITES")
    print(f"{'='*60}")
    
    for site_name, solution in results.items():
        if solution:
            print(f"{site_name}: {solution['anchor_lat']:.5f}°N, {solution['anchor_lon']:.5f}°W "
                  f"(fallback: {solution['fallback_distance']:.0f}m, "
                  f"RMS error: {solution['rms_residual']:.1f}m)")
        else:
            print(f"{site_name}: FAILED")
    
    print(f"\nPlots saved in figs/ directory as triangpy_*.png")
    print(f"✅ Processing complete!")


if __name__ == "__main__":
    main()