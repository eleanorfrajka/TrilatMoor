#!/usr/bin/env python3
"""Example showing the multi-survey plotting API.

This example demonstrates how to:
1. Process multiple survey files
2. Plot them together on a single figure
3. Use the clean trilatmoor API
"""

import os
import glob
import matplotlib.pyplot as plt
from trilatmoor import (
    plot_multiple_surveys,
    plot_multiple_solutions,
    process_survey_file,
)


def main():
    """Run the multi-survey plotting example."""
    # Find example data files
    data_dir = "data"
    if os.path.exists(data_dir):
        survey_files = glob.glob(os.path.join(data_dir, "*.txt"))
    else:
        # Use the single example file we included
        survey_files = ["data/FC1_triangulation.txt"]

    if not survey_files:
        print(
            "No survey data files found. Please add some data files to the data/ directory."
        )
        return

    print(f"Found {len(survey_files)} survey files:")
    for f in survey_files:
        print(f"  - {f}")

    # Example 1: Process a single survey file
    print("\n=== Example 1: Single Survey Processing ===")
    if survey_files:
        triang_data, solution = process_survey_file(survey_files[0])

        print(f"Location: {triang_data['loc_name']}")
        print(
            f"Anchor position: {solution['anchor_lat']:.6f}°N, {solution['anchor_lon']:.6f}°W"
        )
        print(f"RMS residual: {solution['rms_residual']:.1f}m")
        print(f"Fallback distance: {solution['fallback_distance']:.0f}m")

    # Example 2: Multi-survey plot (wrapper function)
    print("\n=== Example 2: Multi-Survey Plot (File-based wrapper) ===")
    try:
        fig, survey_results = plot_multiple_surveys(
            survey_files, figsize=(12, 8), colors=["red", "blue", "green", "orange"]
        )

        # Save the figure
        output_file = "multi_survey_plot.png"
        fig.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Plot saved as: {output_file}")

        # Show summary
        print(f"\nProcessed {len(survey_results)} surveys:")
        for loc_name, triang_data, solution in survey_results:
            print(
                f"  {loc_name}: RMS {solution['rms_residual']:.1f}m, "
                f"Fallback {solution['fallback_distance']:.0f}m"
            )

        # Show the plot
        plt.show()

    except Exception as e:
        print(f"Error creating multi-survey plot: {e}")

    # Example 2b: Multi-survey plot (core function with pre-computed solutions)
    print("\n=== Example 2b: Multi-Survey Plot (Pre-computed solutions) ===")
    try:
        # Process files separately
        solutions = []
        for file_path in survey_files:
            try:
                triang_data, solution = process_survey_file(file_path)
                solutions.append((triang_data["loc_name"], triang_data, solution))
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        if solutions:
            # Plot using pre-computed solutions
            fig = plot_multiple_solutions(
                solutions,
                figsize=(10, 6),
                colors=["cyan", "magenta", "yellow", "black"],
            )

            output_file = "multi_solutions_plot.png"
            fig.savefig(output_file, dpi=300, bbox_inches="tight")
            print(f"Solutions plot saved as: {output_file}")

            plt.show()

    except Exception as e:
        print(f"Error creating solutions plot: {e}")

    # Example 3: Custom sound speed
    print("\n=== Example 3: Custom Sound Speed ===")
    if survey_files:
        # Compare default vs custom sound speed
        triang_data1, solution1 = process_survey_file(survey_files[0])  # Default
        triang_data2, solution2 = process_survey_file(
            survey_files[0], sound_speed=1480
        )  # Custom

        print("Default sound speed:")
        print(
            f"  Position: {solution1['anchor_lat']:.6f}°N, {solution1['anchor_lon']:.6f}°W"
        )
        print(f"  RMS: {solution1['rms_residual']:.1f}m")

        print("Custom sound speed (1480 m/s):")
        print(
            f"  Position: {solution2['anchor_lat']:.6f}°N, {solution2['anchor_lon']:.6f}°W"
        )
        print(f"  RMS: {solution2['rms_residual']:.1f}m")


if __name__ == "__main__":
    main()
