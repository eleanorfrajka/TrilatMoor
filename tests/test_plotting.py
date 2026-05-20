#!/usr/bin/env python3
"""Test the plotting functionality of trilaterate_moor package.
"""

import sys

sys.path.insert(0, ".")

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for testing
import matplotlib.pyplot as plt

from trilaterate_moor import (
    parse_triangulation_file,
    solve_anchor_position,
    plot_trilateration_survey,
)


def main():
    """Test plotting functionality."""
    filename = "data/GB3LZ_triangulation.txt"

    try:
        # Parse and solve
        print(f"Reading triangulation file: {filename}")
        triang_data = parse_triangulation_file(filename)

        print("Solving for anchor position...")
        solution = solve_anchor_position(triang_data)

        print(
            f"Anchor position: {solution['anchor_lat']:.6f}°N, {solution['anchor_lon']:.6f}°W"
        )
        print(f"Fallback distance: {solution['fallback_distance']:.0f} m")

        # Create plot
        print("Creating visualization...")
        fig = plot_trilateration_survey(
            triang_data, solution, save_figure="figs/test_trilateration.png"
        )

        print("✅ Plot created successfully!")
        print("Check figs/test_trilateration.png for the output")

        plt.close(fig)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
