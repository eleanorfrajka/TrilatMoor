#!/usr/bin/env python3
"""Comprehensive trilateration single plot script that shows all moorings on one plot
with triangulation radii, final positions, fallback distances and directions.
"""

import os
import glob
import matplotlib.pyplot as plt
import numpy as np
from trilatmoor import (
    solve_anchor_position,
    dec2deg,
    load_bathymetry_netcdf_subsampled,
)
from trilatmoor.utilities import horizontal_range, vincenty_forward


def parse_data_file(file_path):
    """Parse a survey data file and return survey parameters and data."""
    with open(file_path, "r") as f:
        lines = f.readlines()

    # Parse header parameters
    params = {}
    survey_data = []

    for line in lines:
        line = line.strip()
        if line.startswith("Release_height"):
            params["release_height"] = float(line.split(":")[1].strip())
        elif line.startswith("Transducer_depth"):
            params["transducer_depth"] = float(line.split(":")[1].strip())
        elif line.startswith("Water_depth_anchor_launch"):
            params["water_depth_anchor_launch"] = float(line.split(":")[1].strip())
        elif line.startswith("Loc_name"):
            params["loc_name"] = line.split(":")[1].strip()
        elif line.startswith("Sound_speed"):
            params["sound_speed"] = float(line.split(":")[1].strip())
        elif line.startswith("#") or not line:
            continue
        else:
            # Parse survey data line
            parts = line.split()
            if len(parts) >= 7:
                date_time = f"{parts[0]} {parts[1]}"
                range_val = float(parts[2])
                lat_deg = float(parts[3])
                lat_min = float(parts[4])
                lon_deg = float(parts[5])
                lon_min = float(parts[6])

                survey_data.append(
                    [date_time, lat_deg, lat_min, lon_deg, lon_min, range_val]
                )

    return params, survey_data


def convert_to_decimal_degrees(deg, min_val):
    """Convert degrees and decimal minutes to decimal degrees."""
    return deg + min_val / 60


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
        "loc_name": params["loc_name"],
        "release_height": params["release_height"],
        "transducer_depth": params["transducer_depth"],
        "water_depth_anchor_launch": params["water_depth_anchor_launch"],
        "times": times,
        "ranges": ranges,
        "latitudes": latitudes,
        "longitudes": longitudes,
    }

    # Solve trilateration
    solution = solve_anchor_position(
        triang_data, true_sound_speed=params["sound_speed"]
    )

    return triang_data, solution


def generate_range_circle(center_lon, center_lat, radius, num_points=360):
    """Generate points for a range circle around a center point."""
    azimuths = np.linspace(0, 360, num_points, endpoint=False)
    circle_lons = []
    circle_lats = []

    for azimuth in azimuths:
        lon, lat, _ = vincenty_forward(center_lon, center_lat, azimuth, radius)
        circle_lons.append(lon)
        circle_lats.append(lat)

    # Close the circle
    circle_lons.append(circle_lons[0])
    circle_lats.append(circle_lats[0])

    return circle_lons, circle_lats


def plot_range_circles(ax, triang_data, color):
    """Plot range circles around ship positions for one mooring."""
    # Get corrected horizontal ranges
    corrected_ranges = []
    ship_positions = []

    for i, (lat, lon, range_val) in enumerate(
        zip(triang_data["latitudes"], triang_data["longitudes"], triang_data["ranges"])
    ):

        if range_val > 0:  # Skip deployment position
            h_range = horizontal_range(
                range_val,
                triang_data["water_depth_anchor_launch"],
                triang_data["release_height"],
                triang_data["transducer_depth"],
            )
            corrected_ranges.append(h_range)
            ship_positions.append((lon, lat))

    # Plot ship positions and range circles
    for i, ((lon, lat), h_range) in enumerate(zip(ship_positions, corrected_ranges)):
        # Ship position
        ax.plot(lon, lat, "+", color=color, markersize=6, markeredgewidth=2, alpha=0.8)

        # Range circle
        circle_lons, circle_lats = generate_range_circle(lon, lat, h_range)
        ax.plot(circle_lons, circle_lats, color=color, linewidth=1, alpha=0.4)


def plot_bathymetry(ax, bathymetry, lon_lim, lat_lim):
    """Plot bathymetry contours with specific isobaths."""
    # Find indices within plot bounds
    lon_idx = np.where(
        (bathymetry["lon"] >= lon_lim[0]) & (bathymetry["lon"] <= lon_lim[1])
    )[0]
    lat_idx = np.where(
        (bathymetry["lat"] >= lat_lim[0]) & (bathymetry["lat"] <= lat_lim[1])
    )[0]

    if len(lon_idx) > 0 and len(lat_idx) > 0:
        lon_grid, lat_grid = np.meshgrid(
            bathymetry["lon"][lon_idx], bathymetry["lat"][lat_idx]
        )
        depth_subset = bathymetry["depth"][np.ix_(lat_idx, lon_idx)]

        # Specific isobath levels
        isobath_levels = [600, 700, 800, 900, 1000, 1100]

        # Filter levels to only those within the data range
        depth_min = np.nanmin(depth_subset)
        depth_max = np.nanmax(depth_subset)
        valid_levels = [
            level for level in isobath_levels if depth_min <= level <= depth_max
        ]

        if valid_levels:
            cs = ax.contour(
                lon_grid,
                lat_grid,
                depth_subset,
                levels=valid_levels,
                colors="black",
                alpha=0.7,
                linewidths=1.0,
            )
            ax.clabel(
                cs,
                inline=True,
                fontsize=9,
                fmt="%0.0fm",
                inline_spacing=5,
                manual=False,
            )


def create_comprehensive_single_plot(all_data, bathymetry_path=None):
    """Create a single comprehensive plot showing all trilateration surveys."""
    # Set up the plot
    fig, ax = plt.subplots(figsize=(10, 8))

    # Colors for different surveys
    colors = ["red", "blue", "green", "orange", "purple", "brown"]

    # Calculate overall plot bounds including all triangulation points and anchor positions
    all_lons = []
    all_lats = []
    all_range_circle_points = []

    for loc_name, triang_data, solution in all_data:
        # Add all ship positions (triangulation points)
        all_lons.extend(triang_data["longitudes"])
        all_lats.extend(triang_data["latitudes"])

        # Add final anchor position
        all_lons.append(solution["anchor_lon"])
        all_lats.append(solution["anchor_lat"])

        # Calculate range circle extents for each survey position
        for i, (lat, lon, range_val) in enumerate(
            zip(
                triang_data["latitudes"],
                triang_data["longitudes"],
                triang_data["ranges"],
            )
        ):

            if range_val > 0:  # Skip deployment position
                h_range = horizontal_range(
                    range_val,
                    triang_data["water_depth_anchor_launch"],
                    triang_data["release_height"],
                    triang_data["transducer_depth"],
                )

                # Add the extremes of the range circle to bounds calculation
                # North, South, East, West points of the circle
                north_pt = vincenty_forward(lon, lat, 0, h_range)
                south_pt = vincenty_forward(lon, lat, 180, h_range)
                east_pt = vincenty_forward(lon, lat, 90, h_range)
                west_pt = vincenty_forward(lon, lat, 270, h_range)

                all_range_circle_points.extend(
                    [
                        (north_pt[0], north_pt[1]),
                        (south_pt[0], south_pt[1]),
                        (east_pt[0], east_pt[1]),
                        (west_pt[0], west_pt[1]),
                    ]
                )

    # Add range circle extents to the bounds
    if all_range_circle_points:
        circle_lons, circle_lats = zip(*all_range_circle_points)
        all_lons.extend(circle_lons)
        all_lats.extend(circle_lats)

    # Set plot bounds with margin
    lat_range = max(all_lats) - min(all_lats)
    lon_range = max(all_lons) - min(all_lons)

    # Use a smaller margin now that we include range circles
    margin_factor = 0.1  # 10% margin
    lat_margin = lat_range * margin_factor if lat_range > 0 else 0.01
    lon_margin = lon_range * margin_factor if lon_range > 0 else 0.01

    west = min(all_lons) - lon_margin
    east = max(all_lons) + lon_margin
    south = min(all_lats) - lat_margin
    north = max(all_lats) + lat_margin

    # Calculate bathymetry bounds with 3-degree margin
    bathy_west = min(all_lons) - 3.0
    bathy_east = max(all_lons) + 3.0
    bathy_south = min(all_lats) - 3.0
    bathy_north = max(all_lats) + 3.0

    print(
        f"Bathymetry region: {bathy_west:.2f}W to {bathy_east:.2f}W, {bathy_south:.2f}N to {bathy_north:.2f}N"
    )

    # Load and plot bathymetry if available with subsampling and regional clipping
    bathy = None
    if bathymetry_path and os.path.exists(bathymetry_path):
        try:
            bathy = load_bathymetry_netcdf_subsampled(
                bathymetry_path,
                lon_bounds=(bathy_west, bathy_east),
                lat_bounds=(bathy_south, bathy_north),
                subsample=2,
            )
            # Use the full bathymetry bounds for plotting instead of just the smaller plot bounds
            plot_bathymetry(
                ax, bathy, [bathy_west, bathy_east], [bathy_south, bathy_north]
            )
            print(
                f"Loaded bathymetry: {len(bathy['lon'])} x {len(bathy['lat'])} points"
            )
        except Exception as e:
            print(f"Could not load bathymetry: {e}")

    # Plot all surveys
    legend_entries = []

    for i, (loc_name, triang_data, solution) in enumerate(all_data):
        color = colors[i % len(colors)]

        # Plot range circles and ship positions
        plot_range_circles(ax, triang_data, color)

        # Plot deployment location
        deploy_lat = triang_data["latitudes"][0]
        deploy_lon = triang_data["longitudes"][0]
        deploy_marker = ax.plot(
            deploy_lon,
            deploy_lat,
            "s",
            color=color,
            markersize=8,
            markeredgecolor="black",
            markeredgewidth=1,
        )

        # Plot final anchor position
        anchor_lat = solution["anchor_lat"]
        anchor_lon = solution["anchor_lon"]
        anchor_marker = ax.plot(
            anchor_lon,
            anchor_lat,
            "*",
            color=color,
            markersize=12,
            markeredgecolor="black",
            markeredgewidth=1,
        )

        # Plot fallback line
        fallback_line = ax.plot(
            [deploy_lon, anchor_lon],
            [deploy_lat, anchor_lat],
            "--",
            color=color,
            linewidth=2,
            alpha=0.8,
        )

        # Add position label with key metrics
        _, _, lat_str = dec2deg(anchor_lat)
        _, _, lon_str = dec2deg(abs(anchor_lon))

        # Calculate heading from anchor drop to fallback position
        deploy_lat = triang_data["latitudes"][0]
        deploy_lon = triang_data["longitudes"][0]

        # Calculate bearing using simple approximation
        dlat = anchor_lat - deploy_lat
        dlon = anchor_lon - deploy_lon

        # Convert to radians
        dlat_rad = np.radians(dlat)
        dlon_rad = np.radians(dlon)
        lat1_rad = np.radians(deploy_lat)

        # Calculate bearing
        y = np.sin(dlon_rad) * np.cos(np.radians(anchor_lat))
        x = np.cos(lat1_rad) * np.sin(np.radians(anchor_lat)) - np.sin(
            lat1_rad
        ) * np.cos(np.radians(anchor_lat)) * np.cos(dlon_rad)
        bearing_rad = np.arctan2(y, x)
        bearing_deg = np.degrees(bearing_rad)

        # Normalize to 0-360 degrees
        if bearing_deg < 0:
            bearing_deg += 360

        # Append _1_2026 to location name after dsXX part
        display_name = loc_name + "_1_2026"

        label_text = (
            f"{display_name}\n"
            f"{lat_str}N, {lon_str}W\n"
            f'Fallback: {solution["fallback_distance"]:.0f}m\n'
            f"Heading: {bearing_deg:.0f}°"
        )

        # Position annotation boxes at specific latitudes
        # Longitude range: 29°33'W to 29°09'W (-29.55 to -29.15)
        # Latitude range: 65°27.6'N to 65°37.2'N (65.46 to 65.62)

        if "G" in loc_name:  # dsG1, dsG2, dsG3 - bottom edge at 65°36.0'N
            # Calculate x position based on G number for spacing across longitude range
            g_num = int(loc_name[-1]) if loc_name[-1].isdigit() else 1
            lon_range = -29.15 - (-29.55)  # 0.4 degrees
            x_pos = (
                -29.55 + (g_num - 1) * lon_range / 3 + lon_range / 6
            )  # Evenly spaced
            y_pos = 65.6  # 65°36.0'N in decimal degrees
            va = "bottom"
        elif "K" in loc_name:  # dsK1, dsK2, dsK3 - top edge at 65°28.8'N
            # Calculate x position based on K number for spacing across longitude range
            k_num = int(loc_name[-1]) if loc_name[-1].isdigit() else 1
            lon_range = -29.15 - (-29.55)  # 0.4 degrees
            x_pos = (
                -29.55 + (k_num - 1) * lon_range / 3 + lon_range / 6
            )  # Evenly spaced
            y_pos = 65.48  # 65°28.8'N in decimal degrees
            va = "top"
        else:
            # Fallback to anchor position for other moorings
            x_pos = anchor_lon
            y_pos = anchor_lat
            va = "bottom"

        ax.text(
            x_pos,
            y_pos,
            label_text,
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="white",
                alpha=0.9,
                edgecolor=color,
                linewidth=1,
            ),
            fontsize=10,
            verticalalignment=va,
            horizontalalignment="center",
        )

        # Add simple label at final anchor position, offset 1 minute west
        label_lon = anchor_lon - 1.0 / 60.0  # 1 minute west
        ax.text(
            label_lon,
            anchor_lat,
            loc_name,
            fontsize=8,
            fontweight="bold",
            horizontalalignment="center",
            verticalalignment="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8),
        )

        # Add to legend
        legend_entries.append((deploy_marker[0], f"{loc_name} - Deployment"))
        legend_entries.append((anchor_marker[0], f"{loc_name} - Final Position"))

    # Draw connecting lines between moorings in each group
    # Group G moorings (G1, G2, G3)
    g_moorings = {}
    k_moorings = {}

    # Collect positions for each group
    print("All mooring names found:")
    for loc_name, triang_data, solution in all_data:
        print(f"  - {loc_name}")
        if "G" in loc_name:  # dsG1, dsG2, dsG3
            g_moorings[loc_name] = (solution["anchor_lon"], solution["anchor_lat"])
        elif "K" in loc_name:  # dsK1, dsK2, dsK3
            k_moorings[loc_name] = (solution["anchor_lon"], solution["anchor_lat"])

    print(f"G moorings found: {list(g_moorings.keys())}")
    print(f"K moorings found: {list(k_moorings.keys())}")

    # Calculate midpoint of K-series moorings
    if len(k_moorings) >= 3:
        k_lons = [pos[0] for pos in k_moorings.values()]
        k_lats = [pos[1] for pos in k_moorings.values()]

        midpoint_lon = sum(k_lons) / len(k_lons)
        midpoint_lat = sum(k_lats) / len(k_lats)

        print("\nK-series midpoint:")
        print(f"  Decimal degrees: {midpoint_lat:.6f}°N, {abs(midpoint_lon):.6f}°W")

        # Convert to degrees/minutes format
        lat_deg, lat_min, lat_str = dec2deg(midpoint_lat)
        lon_deg, lon_min, lon_str = dec2deg(abs(midpoint_lon))
        print(f"  Degrees/minutes: {lat_str}N, {lon_str}W")
        print("  Individual positions:")
        for name, (lon, lat) in k_moorings.items():
            print(f"    {name}: {lat:.6f}°N, {abs(lon):.6f}°W")

    # Draw lines connecting G1-G2-G3
    if len(g_moorings) >= 3:
        print(f"Drawing G-group connections between {len(g_moorings)} moorings")
        g_names = sorted(g_moorings.keys())  # Sort to get consistent order
        for i in range(len(g_names)):
            for j in range(i + 1, len(g_names)):
                name1, name2 = g_names[i], g_names[j]
                lon1, lat1 = g_moorings[name1]
                lon2, lat2 = g_moorings[name2]
                print(
                    f"Drawing line from {name1} ({lon1:.4f}, {lat1:.4f}) to {name2} ({lon2:.4f}, {lat2:.4f})"
                )
                ax.plot(
                    [lon1, lon2],
                    [lat1, lat2],
                    "b--",
                    alpha=0.8,
                    linewidth=2.0,
                    label="G-Group Connections" if i == 0 and j == 1 else "",
                )

    # Draw lines connecting K1-K2-K3
    if len(k_moorings) >= 3:
        print(f"Drawing K-group connections between {len(k_moorings)} moorings")
        k_names = sorted(k_moorings.keys())  # Sort to get consistent order
        for i in range(len(k_names)):
            for j in range(i + 1, len(k_names)):
                name1, name2 = k_names[i], k_names[j]
                lon1, lat1 = k_moorings[name1]
                lon2, lat2 = k_moorings[name2]
                print(
                    f"Drawing line from {name1} ({lon1:.4f}, {lat1:.4f}) to {name2} ({lon2:.4f}, {lat2:.4f})"
                )
                ax.plot(
                    [lon1, lon2],
                    [lat1, lat2],
                    "b--",
                    alpha=0.8,
                    linewidth=2.0,
                    label="K-Group Connections" if i == 0 and j == 1 else "",
                )

    # Add group labels outside the right margin
    # "Gross" at 65°36.6'N, 29°7'W
    ax.text(
        -29.117,
        65.61,
        "Gross",
        fontsize=12,
        fontweight="bold",
        horizontalalignment="center",
        verticalalignment="center",
    )

    # "Klein" at 65°28.2'N, 29°7'W
    ax.text(
        -29.117,
        65.47,
        "Klein",
        fontsize=12,
        fontweight="bold",
        horizontalalignment="center",
        verticalalignment="center",
    )

    # Set specific plot limits as requested
    # Longitude: 29°33'W to 29°09'W (-29.55 to -29.15)
    # Latitude: 65°27.6'N to 65°37.2'N (65.46 to 65.62)
    ax.set_xlim(-29.55, -29.15)
    ax.set_ylim(65.46, 65.62)
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)

    # Set aspect ratio accounting for latitude - circles should appear circular
    # At high latitudes, longitude degrees are smaller than latitude degrees
    center_lat = (south + north) / 2
    lat_lon_ratio = 1.0 / np.cos(np.radians(center_lat))
    ax.set_aspect(lat_lon_ratio)

    # Format coordinate ticks
    format_coordinate_ticks(ax)

    # Legend removed as requested

    # Title
    ax.set_title(
        "Trilateration Survey - MIXSED array\n"
        "Triangulation circles, deployment positions (□), final anchor positions (★), and fallback distances",
        fontsize=12,
        fontweight="bold",
        pad=20,
    )

    plt.tight_layout()
    return fig


def format_coordinate_ticks(ax):
    """Format axis ticks to show degrees and minutes."""
    # Format latitude ticks (1 decimal place for minutes)
    yticks = ax.get_yticks()
    yticklabels = []
    for tick in yticks:
        if tick != 0:
            degrees, minutes, _ = dec2deg(abs(tick))
            hemisphere = "N" if tick >= 0 else "S"
            yticklabels.append(f"{degrees}°{minutes:.1f}'{hemisphere}")
        else:
            yticklabels.append("0°")
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels, fontsize=10)

    # Format longitude ticks (no decimals for minutes)
    xticks = ax.get_xticks()
    xticklabels = []
    for tick in xticks:
        if tick != 0:
            degrees, minutes, _ = dec2deg(abs(tick))
            hemisphere = "E" if tick >= 0 else "W"
            xticklabels.append(f"{degrees}°{minutes:.0f}'{hemisphere}")
        else:
            xticklabels.append("0°")
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels, fontsize=10)


def main():
    """Main function to process all survey data files and create comprehensive single plot."""
    # Find all survey data files
    data_dir = "data"
    data_files = glob.glob(os.path.join(data_dir, "*survey*.txt")) + glob.glob(
        os.path.join(data_dir, "*triangulation*.txt")
    )

    if not data_files:
        print(
            "No survey data files found. Please ensure files are in the 'data' directory."
        )
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
            print(
                f"  Anchor position: {solution['anchor_lat']:.6f}°N, {solution['anchor_lon']:.6f}°W"
            )
            print(f"  RMS residual: {solution['rms_residual']:.1f}m")
            print(f"  Fallback distance: {solution['fallback_distance']:.0f}m")

            all_data.append((params["loc_name"], triang_data, solution))

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue

    if not all_data:
        print("No valid survey data processed.")
        return

    # Look for bathymetry file
    bathymetry_paths = [
        "../cruiseplan/data/bathymetry/GEBCO_2025.nc",
        "../../cruiseplan/data/bathymetry/GEBCO_2025.nc",
        "../../cruiseplan/data/bathymetry/msm142_bathyJJ.nc",
        "../bathymetry/GEBCO_2025.nc",
        "bathymetry/GEBCO_2025.nc",
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

    # Create comprehensive single plot
    print(f"\nCreating comprehensive single plot with {len(all_data)} surveys...")
    fig = create_comprehensive_single_plot(all_data, bathymetry_path)

    # Save the plot
    os.makedirs("figs", exist_ok=True)
    output_file = "figs/comprehensive_trilateration_single_plot.png"
    fig.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"\nPlot saved as: {output_file}")

    # Show the plot
    plt.show()

    # Print summary table
    print("\n" + "=" * 90)
    print("COMPREHENSIVE TRILATERATION SUMMARY")
    print("=" * 90)
    print(
        f"{'Location':<8} {'Final Position (°N, °W)':<25} {'Fallback':<10} {'RMS':<8} {'Quality':<10}"
    )
    print("-" * 90)

    for loc_name, triang_data, solution in all_data:
        lat = solution["anchor_lat"]
        lon = abs(solution["anchor_lon"])
        fallback = solution["fallback_distance"]
        rms = solution["rms_residual"]

        if rms < 10:
            quality = "Excellent"
        elif rms < 50:
            quality = "Good"
        elif rms < 100:
            quality = "Fair"
        else:
            quality = "Poor"

        pos_str = f"{lat:.4f}°N, {lon:.4f}°W"
        print(
            f"{loc_name:<8} {pos_str:<25} {fallback:<10.0f} {rms:<8.1f} {quality:<10}"
        )

    print("=" * 90)


if __name__ == "__main__":
    main()
