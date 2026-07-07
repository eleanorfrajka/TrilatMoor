#!/usr/bin/env python3
"""Example: trilateration with ship track overlay.

Demonstrates loading a survey file, solving for the anchor position,
and producing a plot with the ship track superimposed.

Required files:
  - A triangulation survey file (see data format in README)
  - A ship track NetCDF file with variables: time, lat/latitude, lon/longitude
"""

from trilatmoor import (
    parse_triangulation_file,
    solve_anchor_position,
    plot_trilateration_survey,
    load_ship_track_netcdf,
    dec2deg,
)

# --- Paths: edit these to point to your files ---
SURVEY_FILE = "data/GB3LZ_triangulation.txt"
SHIP_TRACK_FILE = "data/ship_track.nc"
OUTPUT_FIGURE = "figs/trilateration_with_track.png"
# ------------------------------------------------


def main():
    # Parse survey
    triang_data = parse_triangulation_file(SURVEY_FILE)
    print(f"Location: {triang_data['loc_name']}")
    print(f"Water depth: {triang_data['water_depth_anchor_launch']} m")

    # Solve
    solution = solve_anchor_position(triang_data)

    lat = solution["anchor_lat"]
    lon = solution["anchor_lon"]
    _, _, lat_str = dec2deg(abs(lat))
    _, _, lon_str = dec2deg(abs(lon))
    lat_hemi = "N" if lat >= 0 else "S"
    lon_hemi = "E" if lon >= 0 else "W"

    print(f"\nAnchor position: {lat_str}{lat_hemi}, {lon_str}{lon_hemi}")
    print(f"Fallback distance: {solution['fallback_distance']:.0f} m")
    print(f"RMS residual: {solution['rms_residual']:.1f} m")

    # Load ship track
    ship_track = load_ship_track_netcdf(SHIP_TRACK_FILE, subsample_minutes=1)
    print(f"\nShip track loaded: {len(ship_track['lat'])} points")

    # Plot with ship track
    fig = plot_trilateration_survey(
        triang_data,
        solution,
        ship_track=ship_track,
        save_figure=OUTPUT_FIGURE,
    )
    print(f"Plot saved: {OUTPUT_FIGURE}")


if __name__ == "__main__":
    main()
