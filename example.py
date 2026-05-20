#!/usr/bin/env python3
"""Example script showing how to use the trilaterate_moor package.

This example demonstrates the basic workflow:
1. Parse triangulation data file
2. Solve for anchor position
3. Display results

Based on the MATLAB run_anchors.m workflow.
"""

import sys
import matplotlib.pyplot as plt
from trilatmoor import (
    parse_triangulation_file,
    solve_anchor_position,
    dec2deg,
    plot_trilateration_survey,
)


def main():
    """Main example function showing trilateration workflow."""
    # Real triangulation file from the data directory
    filename = "data/GB3LZ_triangulation.txt"

    try:
        # Step 1: Parse the triangulation data file
        print(f"Reading triangulation file: {filename}")
        triang_data = parse_triangulation_file(filename)

        print(f"Location: {triang_data['loc_name']}")
        print(f"Release height: {triang_data['release_height']} m")
        print(f"Transducer depth: {triang_data['transducer_depth']} m")
        print(
            f"Water depth at anchor launch: {triang_data['water_depth_anchor_launch']} m"
        )

        # Count valid position fixes
        valid_fixes = sum(1 for r in triang_data["ranges"] if r > 0)
        print(f"Number of position fixes: {valid_fixes}")
        print()

        # Step 2: Solve for anchor position
        print("Solving for anchor position...")

        # You can specify different sound speeds if known
        true_sound_speed = 1503  # m/s (typical deep water value)
        measured_sound_speed = 1507  # m/s (transducer default)

        solution = solve_anchor_position(
            triang_data,
            true_sound_speed=true_sound_speed,
            measured_sound_speed=measured_sound_speed,
        )

        # Step 3: Display results
        print("RESULTS:")
        print("=" * 50)

        anchor_lat = solution["anchor_lat"]
        anchor_lon = solution["anchor_lon"]

        print(f"Anchor position: {anchor_lat:.6f}°N, {anchor_lon:.6f}°W")

        # Convert to degrees/minutes format
        _, _, lat_str = dec2deg(anchor_lat)
        _, _, lon_str = dec2deg(abs(anchor_lon))
        print(f"Position (deg/min): {lat_str}N, {lon_str}W")

        print(f"Fallback distance: {solution['fallback_distance']:.0f} m")
        print(f"Max residual error: {solution['max_residual']:.1f} m")
        print(f"RMS residual error: {solution['rms_residual']:.1f} m")

        # Individual residuals
        print(f"Individual residuals: {[f'{r:.1f}' for r in solution['residuals']]}")

        # Deployment position for comparison
        deploy_lat = triang_data["latitudes"][0]
        deploy_lon = triang_data["longitudes"][0]
        print()
        print(f"Original deployment position: {deploy_lat:.6f}°N, {deploy_lon:.6f}°W")

        # Step 4: Create visualization
        print()
        print("Creating visualization...")

        fig = plot_trilateration_survey(
            triang_data,
            solution,
            save_figure=f"figs/triang_{triang_data['loc_name']}.png",
        )

        # Show the plot
        plt.show()

    except FileNotFoundError:
        print(f"Error: Could not find file '{filename}'")
        print("Please ensure the file exists or update the filename in the script.")
        sys.exit(1)

    except Exception as e:
        print(f"Error during processing: {e}")
        sys.exit(1)


def create_example_data_file():
    """Create an example triangulation data file for testing.

    This creates a file with the format expected by parse_triangulation_file().
    """
    example_content = """Release_height (m): 1
Transducer_depth (m): 10
Water_depth_anchor_launch (m): 2690
Loc_name: GB3LZ

# Date (yyyy/mm/dd HH:MM:SS) Range Position (Lat / Lon)
2023/09/30 18:58:05 0      42 42.016 -51 -53.984
2023/09/30 19:22:37 2832   42 42.387 -51 -54.478
2023/09/30 19:40:20 2876   42 42.093 -51 -53.360
2023/09/30 19:55:20 2823   42 41.509 -51 -54.325
"""

    # Create data directory if it doesn't exist
    import os

    os.makedirs("data", exist_ok=True)

    with open("data/GB3LZ_triangulation.txt", "w") as f:
        f.write(example_content)

    print("Created example data file: data/GB3LZ_triangulation.txt")


if __name__ == "__main__":
    # Uncomment the line below to create example data file first
    # create_example_data_file()

    main()
