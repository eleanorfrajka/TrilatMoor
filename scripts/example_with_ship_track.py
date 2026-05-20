#!/usr/bin/env python3
"""Example using real ship track data with trilateration.

This example shows how to:
1. Load real ship track data from MATLAB format
2. Use ship track for position interpolation
3. Perform trilateration with real data
"""

import sys

sys.path.insert(0, ".")

try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from trilaterate_moor import parse_triangulation_file, solve_anchor_position, dec2deg

if HAS_MATPLOTLIB:
    from trilaterate_moor import plot_trilateration_survey

# Import the converter
from matlab_converter import convert_matlab_ship_track


def main():
    """Example with real ship track data."""
    # Real data files
    triangulation_file = "data/GB3LZ_triangulation.txt"
    ship_track_file = "data/MSM121_track_all.mat"

    try:
        # Load ship track data
        print(f"Loading ship track: {ship_track_file}")
        ship_track = convert_matlab_ship_track(ship_track_file)
        print(f"Ship track loaded: {len(ship_track['time'])} points")
        print(f"Time range: {min(ship_track['time'])} to {max(ship_track['time'])}")
        print()

        # Load triangulation data
        print(f"Reading triangulation file: {triangulation_file}")
        triang_data = parse_triangulation_file(triangulation_file)

        print(f"Location: {triang_data['loc_name']}")
        print("Survey times:")
        for i, time in enumerate(triang_data["times"]):
            range_val = triang_data["ranges"][i]
            print(f"  {i+1}: {time} - Range: {range_val}m")
        print()

        # Solve for anchor position
        print("Solving for anchor position...")

        # Use actual sound speed for this cruise
        true_sound_speed = 1503  # m/s
        solution = solve_anchor_position(triang_data, true_sound_speed=true_sound_speed)

        # Results
        print("RESULTS:")
        print("=" * 60)

        anchor_lat = solution["anchor_lat"]
        anchor_lon = solution["anchor_lon"]

        print(f"Anchor position: {anchor_lat:.6f}°N, {anchor_lon:.6f}°W")

        # Format in degrees/minutes
        _, _, lat_str = dec2deg(anchor_lat)
        _, _, lon_str = dec2deg(abs(anchor_lon))
        print(f"Position (deg/min): {lat_str}N, {lon_str}W")

        print(f"Fallback distance: {solution['fallback_distance']:.0f} m")
        print(f"Max residual error: {solution['max_residual']:.1f} m")
        print(f"RMS residual error: {solution['rms_residual']:.1f} m")

        # Show individual residuals
        print("Individual fix residuals:")
        for i, residual in enumerate(solution["residuals"]):
            print(f"  Fix {i+1}: {residual:.1f} m")

        # Deployment position for comparison
        deploy_lat = triang_data["latitudes"][0]
        deploy_lon = triang_data["longitudes"][0]
        print()
        print(f"Original deployment: {deploy_lat:.6f}°N, {deploy_lon:.6f}°W")

        # Create visualization if matplotlib available
        if HAS_MATPLOTLIB:
            print()
            print("Creating visualization...")

            fig = plot_trilateration_survey(
                triang_data,
                solution,
                ship_track=ship_track,  # Include ship track in plot
                save_figure=f"figs/trilateration_{triang_data['loc_name']}_with_track.png",
            )

            print("Plot saved with ship track overlay")
            # plt.show()  # Uncomment to display plot
        else:
            print("\nInstall matplotlib for visualization: pip install matplotlib")

    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
        print("Make sure you have the real data files in the data/ directory")
        sys.exit(1)

    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
