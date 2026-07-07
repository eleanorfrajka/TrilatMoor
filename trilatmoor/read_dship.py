"""Reader functions for DShip and triangulation data files.

Based on MATLAB f_parse_triangl.m for reading triangulation files.
"""

import re
from datetime import datetime
from typing import List, Dict, Any
import numpy as np


def parse_triangulation_file(filename: str) -> dict:
    """Parse triangulation data file in the format expected by the MATLAB code.

    Based on MATLAB f_parse_triangl.m function.

    File format:
    ```
    Release_height (m): 1
    Transducer_depth (m): 10
    Water_depth_anchor_launch (m): 2690
    Loc_name: GB2LZ

    # Date (yyyy/mm/dd HH:MM:SS) Range Position (Lat / Lon)
    2023/09/30 18:58:05 0      42 42.016 -51 -53.984
    2023/09/30 19:22:37 2832   42 42.387 -51 -54.478
    2023/09/30 19:40:20 2876   42 42.093 -51 -53.360
    2023/09/30 19:55:20 2823   42 41.509 -51 -54.325
    ```

    Parameters
    ----------
    filename : str
        Path to triangulation file

    Returns
    -------
    dict
        Parsed triangulation data with keys: 'loc_name', 'release_height',
        'transducer_depth', 'water_depth_anchor_launch', 'times', 'ranges',
        'latitudes', 'longitudes'

    Raises
    ------
    FileNotFoundError
        If file doesn't exist
    ValueError
        If file format is invalid

    """
    # Initialize data containers
    header_data = {}
    times = []
    ranges = []
    latitudes = []
    longitudes = []

    with open(filename, "r") as f:
        lines = f.readlines()

    # Parse header section
    header_complete = False
    line_idx = 0

    while line_idx < len(lines) and not header_complete:
        line = lines[line_idx].strip()

        # Check for start of data section
        if line.startswith("#"):
            header_complete = True
            line_idx += 1
            break

        # Parse numeric fields
        for field in [
            "Release_height",
            "Transducer_depth",
            "Water_depth_anchor_launch",
        ]:
            if field in line:
                match = re.search(f"{field}.*?:\\s*([\\d.-]+)", line)
                if match:
                    header_data[field] = float(match.group(1))

        # Parse string fields
        if "Loc_name" in line:
            match = re.search(r"Loc_name:\s*(.+)", line)
            if match:
                header_data["Loc_name"] = match.group(1).strip()

        line_idx += 1

    # Validate required header fields
    required_fields = [
        "Release_height",
        "Transducer_depth",
        "Water_depth_anchor_launch",
        "Loc_name",
    ]
    missing_fields = [f for f in required_fields if f not in header_data]
    if missing_fields:
        raise ValueError(f"Missing required header fields: {missing_fields}")

    # Parse data section
    while line_idx < len(lines):
        line = lines[line_idx].strip()

        if not line or line.startswith("#"):
            line_idx += 1
            continue

        # Parse data line: date time range lat_deg lat_min lon_deg lon_min
        parts = line.split()
        if len(parts) >= 7:
            try:
                # Parse datetime
                date_str = parts[0]
                time_str = parts[1]
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
                times.append(dt)

                # Parse range
                range_val = float(parts[2])
                ranges.append(range_val)

                # Parse position (degrees + decimal minutes to decimal degrees)
                lat_deg = float(parts[3])
                lat_min = float(parts[4])
                lon_deg = float(parts[5])
                lon_min = float(parts[6])

                # Convert to decimal degrees
                lat_decimal = lat_deg + lat_min / 60
                lon_decimal = lon_deg + lon_min / 60

                latitudes.append(lat_decimal)
                longitudes.append(lon_decimal)

            except (ValueError, IndexError) as e:
                raise ValueError(
                    f"Error parsing data line {line_idx + 1}: '{line}'. {str(e)}"
                )
        else:
            raise ValueError(
                f"Insufficient data fields in line {line_idx + 1}: '{line}'"
            )

        line_idx += 1

    if not times:
        raise ValueError("No data lines found in file")

    return {
        "loc_name": header_data["Loc_name"],
        "release_height": header_data["Release_height"],
        "transducer_depth": header_data["Transducer_depth"],
        "water_depth_anchor_launch": header_data["Water_depth_anchor_launch"],
        "times": times,
        "ranges": ranges,
        "latitudes": latitudes,
        "longitudes": longitudes,
    }


def interpolate_ship_position(
    ship_track: Dict[str, Any], target_times: List[datetime]
) -> List[tuple]:
    """Interpolate ship position from track data at specified times.

    Based on the ship position interpolation in MATLAB run_anchors.m.

    Parameters
    ----------
    ship_track : dict
        Dictionary with keys 'time', 'lat', 'lon' containing track data
        Times should be datetime objects or matlab datenum values
    target_times : List[datetime]
        Times at which to interpolate positions

    Returns
    -------
    List[tuple]
        List of (lat, lon) tuples for each target time

    """
    # Convert target times to timestamps for interpolation
    target_timestamps = [t.timestamp() for t in target_times]

    # Handle ship track time format (could be datetime or matlab datenum)
    if hasattr(ship_track["time"][0], "timestamp"):
        track_timestamps = [t.timestamp() for t in ship_track["time"]]
    else:
        # Assume matlab datenum (days since year 0)
        # Convert to unix timestamp
        track_timestamps = [(t - 719163) * 86400 for t in ship_track["time"]]

    # Interpolate positions
    interp_lats = np.interp(target_timestamps, track_timestamps, ship_track["lat"])
    interp_lons = np.interp(target_timestamps, track_timestamps, ship_track["lon"])

    return list(zip(interp_lats, interp_lons))


def update_triangulation_with_ship_track(
    triang_data: dict, ship_track: Dict[str, Any]
) -> dict:
    """Update triangulation data positions using interpolated ship track.

    Parameters
    ----------
    triang_data : dict
        Original triangulation data
    ship_track : dict
        Ship track data with 'time', 'lat', 'lon' keys

    Returns
    -------
    dict
        Updated triangulation data with interpolated positions

    """
    # Interpolate ship positions at triangulation times
    interp_positions = interpolate_ship_position(ship_track, triang_data["times"])

    # Update latitudes and longitudes
    updated_lats = [pos[0] for pos in interp_positions]
    updated_lons = [pos[1] for pos in interp_positions]

    # Create new dict with updated positions
    return {
        "loc_name": triang_data["loc_name"],
        "release_height": triang_data["release_height"],
        "transducer_depth": triang_data["transducer_depth"],
        "water_depth_anchor_launch": triang_data["water_depth_anchor_launch"],
        "times": triang_data["times"].copy(),
        "ranges": triang_data["ranges"].copy(),
        "latitudes": updated_lats,
        "longitudes": updated_lons,
    }
