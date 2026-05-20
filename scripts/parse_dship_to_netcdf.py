#!/usr/bin/env python3

import argparse
from pathlib import Path
from datetime import datetime
from msm142.read_dship import read_dship_dat
from msm142.writers import save_dataset


def main():
    parser = argparse.ArgumentParser(
        description="Convert dship .dat file to NetCDF format"
    )
    parser.add_argument(
        "--input-file", 
        default="data/pos_weather_roll_waves/msm142_pos_weather_roll_waves_2026-04-28_00-07-39/msm142_pos_weather_roll_waves.dat",
        help="Path to input dship .dat file"
    )
    parser.add_argument(
        "--output-dir", 
        default="data/",
        help="Output directory for NetCDF file"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    output_dir = Path(args.output_dir)
    
    # Check if input file exists
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}")
        return 1
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading dship file: {input_path}")
    
    try:
        # Read the dataset
        ds = read_dship_dat(str(input_path))
        
        # Extract end date from dataset for filename
        end_date = ds.attrs['end_date']
        end_date_str = datetime.fromisoformat(end_date).strftime('%Y%m%d')
        
        # Generate output filename
        output_file = output_dir / f"msm142_pos_weather_roll_waves_{end_date_str}.nc"
        
        print(f"Saving dataset to: {output_file}")
        success = save_dataset(ds, str(output_file), delete_existing=True, prompt_user=False)
        
        if success:
            print(f"Successfully created NetCDF file: {output_file}")
            print(f"Dataset contains {len(ds.data_vars)} variables")
            print(f"Time range: {ds.attrs['start_date']} to {ds.attrs['end_date']}")
            print(f"Total time points: {len(ds.time)}")
            return 0
        else:
            print("Failed to create NetCDF file")
            return 1
            
    except Exception as e:
        print(f"Error processing file: {e}")
        return 1


if __name__ == "__main__":
    exit(main())