#!/usr/bin/env python3
"""Basic test of the trilaterate_moor package without matplotlib.

Tests core functionality with the example data.
"""

import sys

sys.path.insert(0, ".")

from trilatmoor import parse_triangulation_file, solve_anchor_position, dec2deg


def main():
    """Test the basic trilateration functionality."""
    filename = "data/GB3LZ_triangulation.txt"

    try:
        # Parse the data
        print(f"Reading triangulation file: {filename}")
        triang_data = parse_triangulation_file(filename)

        print(f"Location: {triang_data['loc_name']}")
        print(f"Release height: {triang_data['release_height']} m")
        print(f"Transducer depth: {triang_data['transducer_depth']} m")
        print(f"Water depth: {triang_data['water_depth_anchor_launch']} m")

        # Count valid fixes
        valid_fixes = sum(1 for r in triang_data["ranges"] if r > 0)
        print(f"Number of position fixes: {valid_fixes}")
        print()

        # Solve for anchor position
        print("Solving for anchor position...")
        solution = solve_anchor_position(triang_data)

        # Results
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
        print(f"Individual residuals: {[f'{r:.1f}' for r in solution['residuals']]}")

        # Deployment position
        deploy_lat = triang_data["latitudes"][0]
        deploy_lon = triang_data["longitudes"][0]
        print()
        print(f"Original deployment position: {deploy_lat:.6f}°N, {deploy_lon:.6f}°W")

        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
