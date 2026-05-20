#!/usr/bin/env python3
"""
Command-line interface for trilatmoor package.

Usage:
    trilatmoor -c survey.txt -o output_name
    trilatmoor --compute survey.txt --output output_name
    trilatmoor --multi survey1.txt survey2.txt -o multi_plot
"""

import argparse
import sys
import os
from typing import List, Optional
from datetime import timedelta
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for CLI
import matplotlib.pyplot as plt

from . import process_survey_file, plot_trilateration_survey, plot_multiple_surveys, dec2deg, load_ship_track_netcdf
from .plotting import extract_survey_time_range


def write_anchor_position_file(output_path: str, loc_name: str, triang_data: dict, solution: dict):
    """Write anchor position results to a text file."""
    
    lat = solution['anchor_lat']
    lon = solution['anchor_lon']
    
    # Convert to degrees/minutes
    _, _, lat_str = dec2deg(lat)
    _, _, lon_str = dec2deg(abs(lon))
    
    with open(output_path, 'w') as f:
        f.write(f"Trilatmoor Anchor Position Results\n")
        f.write(f"=====================================\n\n")
        f.write(f"Location: {loc_name}\n\n")
        
        f.write(f"Final Anchor Position:\n")
        f.write(f"  Decimal degrees: {lat:.6f}°N, {abs(lon):.6f}°W\n")
        f.write(f"  Degrees/minutes: {lat_str}N, {lon_str}W\n\n")
        
        f.write(f"Survey Quality:\n")
        f.write(f"  Fallback distance: {solution['fallback_distance']:.0f} m\n")
        f.write(f"  Max residual error: {solution['max_residual']:.1f} m\n")
        f.write(f"  RMS residual error: {solution['rms_residual']:.1f} m\n\n")
        
        # Quality assessment
        rms = solution['rms_residual']
        if rms < 10:
            quality = "Excellent"
        elif rms < 50:
            quality = "Good"
        elif rms < 100:
            quality = "Fair"
        else:
            quality = "Poor"
        f.write(f"  Overall quality: {quality}\n\n")
        
        f.write(f"Individual Fix Residuals:\n")
        for i, residual in enumerate(solution['residuals']):
            f.write(f"  Fix {i+1}: {residual:.1f} m\n")
        
        f.write(f"\nSurvey Parameters:\n")
        f.write(f"  Water depth: {triang_data['water_depth_anchor_launch']} m\n")
        f.write(f"  Release height: {triang_data['release_height']} m\n")
        f.write(f"  Transducer depth: {triang_data['transducer_depth']} m\n")


def find_bathymetry_file(bathy_dir: str, bathy_source: str) -> Optional[str]:
    """Find bathymetry file based on directory and source."""
    
    if not os.path.exists(bathy_dir):
        print(f"Warning: Bathymetry directory not found: {bathy_dir}")
        return None
    
    # Common bathymetry file patterns
    patterns = {
        'gebco2025': ['GEBCO_2025.nc', 'gebco_2025.nc', 'GEBCO2025.nc'],
        'gebco2023': ['GEBCO_2023.nc', 'gebco_2023.nc', 'GEBCO2023.nc'], 
        'gebco': ['GEBCO*.nc', 'gebco*.nc'],
        'etopo': ['ETOPO*.nc', 'etopo*.nc'],
        'msm142': ['msm142_bathy*.nc', 'MSM142_bathy*.nc'],
        'auto': ['*.nc']  # Search for any NetCDF file
    }
    
    search_patterns = patterns.get(bathy_source.lower(), [f'*{bathy_source}*.nc'])
    
    import glob
    for pattern in search_patterns:
        full_pattern = os.path.join(bathy_dir, pattern)
        matches = glob.glob(full_pattern)
        if matches:
            # Return the first match
            bathy_file = matches[0]
            print(f"Found bathymetry file: {bathy_file}")
            return bathy_file
    
    print(f"Warning: No bathymetry file found for source '{bathy_source}' in {bathy_dir}")
    available_files = glob.glob(os.path.join(bathy_dir, "*.nc"))
    if available_files:
        print(f"Available NetCDF files: {[os.path.basename(f) for f in available_files]}")
    
    return None


def process_single_survey(input_file: str, output_name: str, sound_speed: Optional[float] = None, 
                         bathymetry_path: Optional[str] = None, ship_track_path: Optional[str] = None,
                         time_interval_hr: Optional[List[float]] = None):
    """Process a single survey file and generate outputs."""
    
    try:
        # Process the survey
        print(f"Processing {input_file}...")
        triang_data, solution = process_survey_file(input_file, sound_speed)
        
        # Generate plot
        plot_file = f"{output_name}.png"
        print(f"Creating plot: {plot_file}")
        
        if bathymetry_path:
            print(f"Including bathymetry from: {bathymetry_path}")
        
        # Load ship track if provided
        ship_track = None
        if ship_track_path:
            print(f"Loading ship track from: {ship_track_path}")
            try:
                # Calculate time window for ship track
                time_start, time_end = None, None
                if time_interval_hr is not None:
                    survey_start, survey_end = extract_survey_time_range(triang_data)
                    if survey_start and survey_end:
                        time_start = survey_start + timedelta(hours=time_interval_hr[0])
                        time_end = survey_end + timedelta(hours=time_interval_hr[1])
                        print(f"Time filtering: {time_start} to {time_end} ({time_interval_hr[0]:+.0f} to {time_interval_hr[1]:+.0f} hours)")
                
                ship_track = load_ship_track_netcdf(ship_track_path, subsample_minutes=1, 
                                                   time_start=time_start, time_end=time_end)
                print(f"Ship track loaded: {len(ship_track['lat'])} points")
            except Exception as e:
                print(f"Warning: Failed to load ship track: {e}")
        
        fig = plot_trilateration_survey(triang_data, solution, ship_track=ship_track, bathymetry=bathymetry_path, save_figure=plot_file)
        plt.close(fig)
        
        # Generate position file
        pos_file = f"{output_name}_anchorposition.txt"
        print(f"Writing position data: {pos_file}")
        write_anchor_position_file(pos_file, triang_data['loc_name'], triang_data, solution)
        
        # Print summary
        lat = solution['anchor_lat']
        lon = solution['anchor_lon']
        _, _, lat_str = dec2deg(lat)
        _, _, lon_str = dec2deg(abs(lon))
        
        print(f"\nResults for {triang_data['loc_name']}:")
        print(f"  Position: {lat:.6f}°N, {abs(lon):.6f}°W ({lat_str}N, {lon_str}W)")
        print(f"  Fallback: {solution['fallback_distance']:.0f}m")
        print(f"  RMS residual: {solution['rms_residual']:.1f}m")
        print(f"  Files generated: {plot_file}, {pos_file}")
        
        return True
        
    except Exception as e:
        print(f"Error processing {input_file}: {e}")
        return False


def process_multiple_surveys(input_files: List[str], output_name: str, sound_speed: Optional[float] = None,
                           bathymetry_path: Optional[str] = None, ship_track_path: Optional[str] = None,
                           time_interval_hr: Optional[List[float]] = None):
    """Process multiple survey files and generate multi-plot."""
    
    try:
        print(f"Processing {len(input_files)} survey files...")
        
        # Generate multi-plot
        plot_file = f"{output_name}.png"
        print(f"Creating multi-survey plot: {plot_file}")
        
        if bathymetry_path:
            print(f"Including bathymetry from: {bathymetry_path}")
        
        # Load ship track info if provided
        if ship_track_path:
            print(f"Including ship track from: {ship_track_path}")
        
        fig, survey_results = plot_multiple_surveys(
            input_files,
            bathymetry_path=bathymetry_path,
            ship_track_path=ship_track_path,
            sound_speed=sound_speed,
            figsize=(12, 8)
        )
        fig.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        # Generate summary file
        summary_file = f"{output_name}_summary.txt"
        print(f"Writing summary: {summary_file}")
        
        with open(summary_file, 'w') as f:
            f.write(f"Trilatmoor Multi-Survey Results\n")
            f.write(f"===============================\n\n")
            f.write(f"Processed {len(survey_results)} surveys:\n\n")
            
            f.write(f"{'Location':<8} {'Decimal Degrees':<22} {'Degrees/Minutes':<18} {'Fallback':<9} {'RMS':<6} {'Quality':<9}\n")
            f.write(f"{'-'*80}\n")
            
            for loc_name, triang_data, solution in survey_results:
                lat = solution['anchor_lat']
                lon = abs(solution['anchor_lon'])
                fallback = solution['fallback_distance']
                rms = solution['rms_residual']
                
                _, _, lat_str = dec2deg(lat)
                _, _, lon_str = dec2deg(lon)
                
                if rms < 10:
                    quality = "Excellent"
                elif rms < 50:
                    quality = "Good"
                elif rms < 100:
                    quality = "Fair"
                else:
                    quality = "Poor"
                
                decimal_str = f"{lat:.4f}°N, {lon:.4f}°W"
                degmin_str = f"{lat_str}N, {lon_str}W"
                
                f.write(f"{loc_name:<8} {decimal_str:<22} {degmin_str:<18} {fallback:<9.0f} {rms:<6.1f} {quality:<9}\n")
        
        print(f"Files generated: {plot_file}, {summary_file}")
        return True
        
    except Exception as e:
        print(f"Error processing multiple surveys: {e}")
        return False


def main():
    """Main CLI entry point."""
    
    parser = argparse.ArgumentParser(
        description="Process acoustic trilateration survey data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  trilatmoor -c survey.txt -o FC1_results
  trilatmoor --config survey.txt --output FC1_results
  trilatmoor --multi survey1.txt survey2.txt -o multi_results
  trilatmoor -c survey.txt -o results --sound-speed 1480
  trilatmoor -c survey.txt -o results --bathy-dir data/bathymetry --bathy-source gebco2025
  trilatmoor -c survey.txt -o results --bathy-file /path/to/GEBCO_2025.nc
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', '--config', 
                      help='Process a single survey file')
    group.add_argument('--multi', nargs='+', 
                      help='Process multiple survey files for multi-plot')
    
    parser.add_argument('-o', '--output', required=True,
                       help='Output file base name (without extension)')
    
    parser.add_argument('--sound-speed', type=float,
                       help='Override sound speed in m/s (default: use file value or 1500)')
    
    parser.add_argument('--bathy-dir', 
                       help='Directory containing bathymetry files')
    
    parser.add_argument('--bathy-source', default='auto',
                       choices=['gebco2025', 'gebco2023', 'gebco', 'etopo', 'msm142', 'auto'],
                       help='Bathymetry data source (default: auto - find any .nc file)')
    
    parser.add_argument('--bathy-file',
                       help='Specific bathymetry file path (overrides --bathy-dir/--bathy-source)')
    
    parser.add_argument('--ship-track',
                       help='Ship track NetCDF file to overlay on plots')
    
    parser.add_argument('--time-interval-hr', nargs=2, type=float, default=[-12, 12],
                       metavar=('START_HR', 'END_HR'),
                       help='Time interval around survey (hours before/after). Default: -12 12')
    
    args = parser.parse_args()
    
    # Validate input files exist
    input_files = []
    if args.config:
        input_files = [args.config]
    elif args.multi:
        input_files = args.multi
    
    for file_path in input_files:
        if not os.path.exists(file_path):
            print(f"Error: Input file not found: {file_path}")
            sys.exit(1)
    
    # Handle bathymetry options
    bathymetry_path = None
    if args.bathy_file:
        # Specific file provided
        if os.path.exists(args.bathy_file):
            bathymetry_path = args.bathy_file
        else:
            print(f"Warning: Bathymetry file not found: {args.bathy_file}")
    elif args.bathy_dir:
        # Search for file in directory based on source
        bathymetry_path = find_bathymetry_file(args.bathy_dir, args.bathy_source)
    
    # Process based on mode
    success = False
    if args.config:
        success = process_single_survey(args.config, args.output, args.sound_speed, bathymetry_path, 
                                       args.ship_track, args.time_interval_hr)
    elif args.multi:
        success = process_multiple_surveys(args.multi, args.output, args.sound_speed, bathymetry_path, 
                                          args.ship_track, args.time_interval_hr)
    
    if success:
        print("\nProcessing completed successfully!")
        sys.exit(0)
    else:
        print("\nProcessing failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()