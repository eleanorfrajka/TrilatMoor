"""Plotting functions for trilateration visualization.

Based on MATLAB f_run_anchor.m plotting functionality.
"""

import matplotlib.pyplot as plt
import numpy as np
import os
from typing import Dict, List, Optional, Tuple, Union

from .utilities import vincenty_forward


def query_depth_at_position(
    netcdf_path: str, lat: float, lon: float
) -> Optional[float]:
    """Query bathymetric depth at a specific lat/lon from a NetCDF file.

    Uses xarray lazy loading and nearest-neighbour selection. Reads only the
    coordinate arrays and a single grid cell, so it is efficient even for
    large global files such as GEBCO.

    Parameters
    ----------
    netcdf_path : str
        Path to NetCDF bathymetry file (e.g. GEBCO_2025.nc)
    lat : float
        Latitude in decimal degrees
    lon : float
        Longitude in decimal degrees

    Returns
    -------
    float or None
        Water depth in metres (positive = below sea surface), or None if the
        lookup fails (bad path, land point, NaN, out-of-bounds, etc.)

    """
    try:
        import xarray as xr
    except ImportError:
        return None

    try:
        ds = xr.open_dataset(netcdf_path)

        lon_vars = ["lon", "longitude", "x", "nav_lon"]
        lat_vars = ["lat", "latitude", "y", "nav_lat"]
        depth_vars = ["depth", "elevation", "z", "bathymetry", "topo"]

        lon_var = next((v for v in lon_vars if v in ds.variables), None)
        lat_var = next((v for v in lat_vars if v in ds.variables), None)
        depth_var = next((v for v in depth_vars if v in ds.variables), None)

        if lon_var is None or lat_var is None or depth_var is None:
            ds.close()
            return None

        try:
            value = (
                ds[depth_var]
                .sel({lat_var: lat, lon_var: lon}, method="nearest")
                .values.item()
            )
        finally:
            ds.close()

        if np.isnan(value):
            return None

        # elevation/topo/z: positive-up (GEBCO convention). Negative = ocean.
        if depth_var in {"elevation", "topo", "z"}:
            return None if value >= 0 else float(-value)
        # depth/bathymetry: positive-down. Non-positive = land or invalid.
        return float(value) if value > 0 else None

    except Exception:
        return None


def _extract_depth_from_dict(
    bathymetry: dict, lat: float, lon: float
) -> Optional[float]:
    """Nearest-neighbour depth lookup from an already-loaded bathymetry dict."""
    lat_arr = bathymetry["lat"]
    lon_arr = bathymetry["lon"]
    depth_arr = bathymetry["depth"]

    if len(lat_arr) == 0 or len(lon_arr) == 0:
        return None

    lat_idx = int(np.argmin(np.abs(lat_arr - lat)))
    lon_idx = int(np.argmin(np.abs(lon_arr - lon)))
    value = float(depth_arr[lat_idx, lon_idx])
    return None if (np.isnan(value) or value <= 0) else value


def load_bathymetry_netcdf_subsampled(
    netcdf_path: str, lon_bounds: tuple, lat_bounds: tuple, subsample: int = 5
) -> dict:
    """Load bathymetry data from NetCDF file with regional clipping and subsampling.

    Parameters
    ----------
    netcdf_path : str
        Path to NetCDF bathymetry file
    lon_bounds : tuple
        (min_lon, max_lon) longitude bounds
    lat_bounds : tuple
        (min_lat, max_lat) latitude bounds
    subsample : int
        Subsampling factor (e.g., 5 means every 5th point)

    Returns
    -------
    dict
        Bathymetry data with 'lat', 'lon', 'depth' keys

    """
    try:
        import xarray as xr
    except ImportError:
        raise ImportError(
            "xarray is required to load NetCDF bathymetry files. Install with: pip install xarray"
        )

    # Load NetCDF file
    ds = xr.open_dataset(netcdf_path)

    # Try common variable names for coordinates and depth
    # Common coordinate names
    lon_vars = ["lon", "longitude", "x", "nav_lon"]
    lat_vars = ["lat", "latitude", "y", "nav_lat"]
    depth_vars = ["depth", "elevation", "z", "bathymetry", "topo"]

    # Find coordinate variables
    lon_var = None
    for var in lon_vars:
        if var in ds.variables:
            lon_var = var
            break

    lat_var = None
    for var in lat_vars:
        if var in ds.variables:
            lat_var = var
            break

    depth_var = None
    for var in depth_vars:
        if var in ds.variables:
            depth_var = var
            break

    if lon_var is None or lat_var is None or depth_var is None:
        raise ValueError(
            f"Could not find coordinate/depth variables in NetCDF file. "
            f"Available variables: {list(ds.variables.keys())}"
        )

    # Extract coordinate data first to determine indices
    lon_full = ds[lon_var].values
    lat_full = ds[lat_var].values

    # Handle 1D vs 2D coordinates
    if lon_full.ndim == 1 and lat_full.ndim == 1:
        # Regular grid
        lon_1d = lon_full
        lat_1d = lat_full
    elif lon_full.ndim == 2 and lat_full.ndim == 2:
        # Curvilinear grid - use first row/column for 1D coordinates
        lon_1d = lon_full[0, :]
        lat_1d = lat_full[:, 0]
    else:
        raise ValueError("Unexpected coordinate dimensions")

    # Find indices within bounds
    lon_mask = (lon_1d >= lon_bounds[0]) & (lon_1d <= lon_bounds[1])
    lat_mask = (lat_1d >= lat_bounds[0]) & (lat_1d <= lat_bounds[1])

    lon_indices = np.where(lon_mask)[0]
    lat_indices = np.where(lat_mask)[0]

    if len(lon_indices) == 0 or len(lat_indices) == 0:
        # Return empty dataset if no data in region
        return {"lon": np.array([]), "lat": np.array([]), "depth": np.array([])}

    # Apply subsampling to the indices
    lon_indices_sub = lon_indices[::subsample]
    lat_indices_sub = lat_indices[::subsample]

    # Extract subsampled coordinates
    lon = lon_1d[lon_indices_sub]
    lat = lat_1d[lat_indices_sub]

    # Extract subsampled depth data
    depth_full = ds[depth_var].values
    depth = depth_full[np.ix_(lat_indices_sub, lon_indices_sub)]

    # Ensure depth is positive (bathymetry convention)
    if np.nanmean(depth) < 0:
        depth = -depth

    ds.close()

    return {"lon": lon, "lat": lat, "depth": depth}


def load_bathymetry_netcdf(
    netcdf_path: str,
    lon_bounds: Optional[Tuple[float, float]] = None,
    lat_bounds: Optional[Tuple[float, float]] = None,
) -> dict:
    """Load bathymetry data from NetCDF file.

    Parameters
    ----------
    netcdf_path : str
        Path to NetCDF bathymetry file
    lon_bounds : tuple, optional
        (min_lon, max_lon) to load only a regional subset. Strongly recommended
        for large global files such as GEBCO to avoid reading the full file.
    lat_bounds : tuple, optional
        (min_lat, max_lat) to load only a regional subset.

    Returns
    -------
    dict
        Bathymetry data with 'lat', 'lon', 'depth' keys

    """
    try:
        import xarray as xr
    except ImportError:
        raise ImportError(
            "xarray is required to load NetCDF bathymetry files. Install with: pip install xarray"
        )

    # Load NetCDF file
    ds = xr.open_dataset(netcdf_path)

    # Try common variable names for coordinates and depth
    # Common coordinate names
    lon_vars = ["lon", "longitude", "x", "nav_lon"]
    lat_vars = ["lat", "latitude", "y", "nav_lat"]
    depth_vars = ["depth", "elevation", "z", "bathymetry", "topo"]

    # Find coordinate variables
    lon_var = None
    for var in lon_vars:
        if var in ds.variables:
            lon_var = var
            break

    lat_var = None
    for var in lat_vars:
        if var in ds.variables:
            lat_var = var
            break

    depth_var = None
    for var in depth_vars:
        if var in ds.variables:
            depth_var = var
            break

    if lon_var is None or lat_var is None or depth_var is None:
        raise ValueError(
            f"Could not find coordinate/depth variables in NetCDF file. "
            f"Available variables: {list(ds.variables.keys())}"
        )

    # Subset to region before loading into memory — critical for large global files.
    # Only possible for 1-D coordinate axes (regular grids). Curvilinear grids
    # (nav_lat/nav_lon are 2-D) are loaded in full and clipped after extraction.
    if lon_bounds is not None and lat_bounds is not None:
        lat_vals = ds[lat_var].values
        lon_vals = ds[lon_var].values
        if lat_vals.ndim == 1 and lon_vals.ndim == 1:
            # Some files store lat descending (90→−90); slice() must match axis order.
            lat_desc = len(lat_vals) > 1 and float(lat_vals[0]) > float(lat_vals[-1])
            lon_desc = len(lon_vals) > 1 and float(lon_vals[0]) > float(lon_vals[-1])
            lat_slice = (
                slice(lat_bounds[1], lat_bounds[0])
                if lat_desc
                else slice(lat_bounds[0], lat_bounds[1])
            )
            lon_slice = (
                slice(lon_bounds[1], lon_bounds[0])
                if lon_desc
                else slice(lon_bounds[0], lon_bounds[1])
            )
            ds = ds.sel({lon_var: lon_slice, lat_var: lat_slice})

    # Extract data
    lon = ds[lon_var].values
    lat = ds[lat_var].values
    depth = ds[depth_var].values

    # Handle 1D vs 2D coordinates
    if lon.ndim == 1 and lat.ndim == 1:
        # Regular grid - meshgrid not needed, depth should be 2D
        pass
    elif lon.ndim == 2 and lat.ndim == 2:
        # Curvilinear grid - use first row/column for 1D coordinates
        lon = lon[0, :]
        lat = lat[:, 0]
    else:
        raise ValueError("Unexpected coordinate dimensions")

    # Ensure depth is positive (bathymetry convention)
    if np.nanmean(depth) < 0:
        depth = -depth

    ds.close()

    return {"lon": lon, "lat": lat, "depth": depth}


def load_ship_track_netcdf(
    netcdf_path: str, subsample_minutes: int = 1, time_start=None, time_end=None
) -> dict:
    """Load ship track data from NetCDF file with optional temporal subsampling and filtering.

    Parameters
    ----------
    netcdf_path : str
        Path to NetCDF file containing ship position data
    subsample_minutes : int, optional
        Temporal subsampling interval in minutes. Default is 1 minute.
        Set to 0 to disable subsampling (use all data).
    time_start : datetime-like, optional
        Start time for filtering ship track data
    time_end : datetime-like, optional
        End time for filtering ship track data

    Returns
    -------
    dict
        Ship track data with 'lat', 'lon', and optionally 'time' keys

    """
    try:
        import xarray as xr
    except ImportError:
        raise ImportError(
            "xarray is required to load NetCDF ship track files. Install with: pip install xarray"
        )

    # Load NetCDF file
    ds = xr.open_dataset(netcdf_path)

    # Try common variable names for coordinates
    lat_vars = ["lat", "latitude", "Latitude", "ship_latitude"]
    lon_vars = ["lon", "longitude", "Longitude", "ship_longitude"]
    time_vars = ["time", "Time", "datetime"]

    # Find coordinate variables
    lat_var = None
    for var in lat_vars:
        if var in ds.variables:
            lat_var = var
            break

    lon_var = None
    for var in lon_vars:
        if var in ds.variables:
            lon_var = var
            break

    time_var = None
    for var in time_vars:
        if var in ds.variables:
            time_var = var
            break

    if lat_var is None or lon_var is None:
        available_vars = list(ds.variables.keys())
        raise ValueError(
            f"Could not find latitude/longitude variables in NetCDF file. "
            f"Available variables: {available_vars}"
        )

    # Apply time filtering if requested
    if (time_start is not None or time_end is not None) and time_var is not None:
        try:
            if time_start is not None and time_end is not None:
                ds = ds.sel({time_var: slice(time_start, time_end)})
            elif time_start is not None:
                ds = ds.sel({time_var: slice(time_start, None)})
            elif time_end is not None:
                ds = ds.sel({time_var: slice(None, time_end)})
        except Exception as e:
            print(f"Warning: Time filtering failed: {e}. Loading full dataset.")

    # Apply temporal subsampling if requested
    if subsample_minutes > 0 and time_var is not None:
        # Resample to specified interval (use 'min' for minutes)
        ds_resampled = ds.resample({time_var: f"{subsample_minutes}min"}).first()

        # Extract position data from resampled dataset
        ship_track = {
            "lat": ds_resampled[lat_var].values,
            "lon": ds_resampled[lon_var].values,
            "time": ds_resampled[time_var].values,
        }

        # Remove NaN values that may result from resampling
        import numpy as np

        valid_mask = ~np.isnan(ship_track["lat"]) & ~np.isnan(ship_track["lon"])
        ship_track["lat"] = ship_track["lat"][valid_mask]
        ship_track["lon"] = ship_track["lon"][valid_mask]
        ship_track["time"] = ship_track["time"][valid_mask]

    else:
        # Extract position data without subsampling
        ship_track = {"lat": ds[lat_var].values, "lon": ds[lon_var].values}

        # Add time data if available
        if time_var is not None:
            ship_track["time"] = ds[time_var].values

    # Close dataset
    ds.close()

    return ship_track


def extract_survey_time_range(triang_data: dict):
    """Extract start and end times from survey data.

    Parameters
    ----------
    triang_data : dict
        Trilateration data containing 'times' key

    Returns
    -------
    tuple
        (start_time, end_time) as datetime objects

    """
    if "times" not in triang_data or len(triang_data["times"]) == 0:
        return None, None

    times = triang_data["times"]
    min_time = min(times)
    max_time = max(times)

    # Convert to datetime objects if they are strings
    if isinstance(min_time, str):
        from datetime import datetime

        try:
            min_time = datetime.strptime(min_time, "%Y/%m/%d %H:%M:%S")
            max_time = datetime.strptime(max_time, "%Y/%m/%d %H:%M:%S")
        except ValueError:
            # Try alternative format
            try:
                min_time = datetime.strptime(min_time, "%Y-%m-%d %H:%M:%S")
                max_time = datetime.strptime(max_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None, None

    return min_time, max_time


def plot_trilateration_survey(
    triang_data: dict,
    solution: dict,
    ship_track: Optional[dict] = None,
    bathymetry: Optional[Union[dict, str]] = None,
    save_figure: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 8),
    no_title: bool = False,
    no_legend: bool = False,
) -> plt.Figure:
    """Create trilateration survey plot showing ship positions, range circles, and solution.

    Based on the plotting functionality in MATLAB f_run_anchor.m.

    Parameters
    ----------
    triang_data : dict
        Trilateration survey data
    solution : dict
        Anchor position solution
    ship_track : dict, optional
        Ship track data with 'lat', 'lon' keys for plotting ship path
    bathymetry : dict or str, optional
        Bathymetry data with 'lat', 'lon', 'depth' keys, or path to NetCDF file
    save_figure : str, optional
        Filename to save figure (e.g., 'trilateration.png')

    Returns
    -------
    plt.Figure
        Matplotlib figure object

    """
    # Extract data
    anchor_lat = solution["anchor_lat"]
    anchor_lon = solution["anchor_lon"]
    deploy_lat = triang_data["latitudes"][0]
    deploy_lon = triang_data["longitudes"][0]

    # Calculate plot bounds first — needed to load only the regional bathymetry subset
    from .utilities import horizontal_range
    import numpy as np

    max_range = 0
    for i, range_val in enumerate(triang_data["ranges"]):
        if range_val > 0:
            h_range = horizontal_range(
                range_val,
                triang_data["water_depth_anchor_launch"],
                triang_data["release_height"],
                triang_data["transducer_depth"],
            )
            max_range = max(max_range, h_range)

    if max_range > 0:
        range_deg_lat = max_range / 111320
        range_deg_lon = max_range / (111320 * np.cos(np.radians(anchor_lat)))
        margin_factor = 1.2
        lat_margin = range_deg_lat * margin_factor
        lon_margin = range_deg_lon * margin_factor
        west = anchor_lon - lon_margin
        east = anchor_lon + lon_margin
        south = anchor_lat - lat_margin
        north = anchor_lat + lat_margin
    else:
        all_lons = triang_data["longitudes"] + [anchor_lon, deploy_lon]
        all_lats = triang_data["latitudes"] + [anchor_lat, deploy_lat]
        lat_range = max(all_lats) - min(all_lats)
        lon_range = max(all_lons) - min(all_lons)
        margin = max(lat_range, lon_range, 0.01) * 2
        west = min(all_lons) - margin
        east = max(all_lons) + margin
        south = min(all_lats) - margin
        north = max(all_lats) + margin

    # Expand bounds to fill figsize with geographically correct proportions so
    # that set_aspect(adjustable='box') fills the axes without shrinking it.
    _center_lon = (west + east) / 2
    _center_lat = (south + north) / 2
    _cos_lat = np.cos(np.radians(_center_lat))
    _lon_half = (east - west) / 2
    _lat_half = (north - south) / 2
    _fig_w, _fig_h = figsize if figsize else (10, 8)
    _fig_aspect = _fig_w / _fig_h
    _geo_aspect = (_lon_half * _cos_lat) / _lat_half
    if _geo_aspect < _fig_aspect:
        _lon_half = _lat_half * _fig_aspect / _cos_lat
    else:
        _lat_half = _lon_half * _cos_lat / _fig_aspect
    west = _center_lon - _lon_half
    east = _center_lon + _lon_half
    south = _center_lat - _lat_half
    north = _center_lat + _lat_half

    # Handle bathymetry parameter — load only the regional subset for efficiency.
    # Use a generous margin so contour lines that originate outside the plot area
    # are computed fully and then clipped cleanly at the axes boundary.
    gebco_depth = None
    _bathy_margin = 0.5  # degrees beyond plot bounds
    if isinstance(bathymetry, str):
        gebco_depth = query_depth_at_position(bathymetry, anchor_lat, anchor_lon)
        bathymetry = load_bathymetry_netcdf(
            bathymetry,
            lon_bounds=(west - _bathy_margin, east + _bathy_margin),
            lat_bounds=(south - _bathy_margin, north + _bathy_margin),
        )
    elif isinstance(bathymetry, dict):
        gebco_depth = _extract_depth_from_dict(bathymetry, anchor_lat, anchor_lon)

    # Create figure with constrained layout so decorations (title, labels,
    # legend) are handled before the axes size is determined, which lets
    # set_aspect work correctly without shrinking the axes to a tiny square.
    fig, ax = plt.subplots(figsize=figsize, layout="constrained")

    # Compute contours over a region slightly wider than the tight display so
    # the marching-squares path is complete and clips cleanly at the axes limits.
    # Using the full _bathy_margin (0.5°) makes the isobath a multi-thousand-vertex
    # global path whose tight-area segment can vanish; a modest margin (0.05°, ≈5km)
    # gives ~12 extra GEBCO cells per side — enough for well-formed paths without
    # changing the isobath topology relative to the display area.
    _contour_margin = 0.05
    if bathymetry is not None:
        _anchor_depth = triang_data.get("water_depth_anchor_launch")
        _plot_bathymetry(
            ax,
            bathymetry,
            [west - _contour_margin, east + _contour_margin],
            [south - _contour_margin, north + _contour_margin],
            anchor_depth=_anchor_depth,
        )

    # Plot ship track if provided (only the portion visible in current bounds)
    if ship_track is not None:
        # Filter ship track to only show points within plot bounds for performance
        import numpy as np

        track_lons = np.array(ship_track["lon"])
        track_lats = np.array(ship_track["lat"])

        # Find points within plot bounds
        in_bounds = (
            (track_lons >= west)
            & (track_lons <= east)
            & (track_lats >= south)
            & (track_lats <= north)
        )

        if np.any(in_bounds):
            # Get visible track points
            visible_lons = track_lons[in_bounds]
            visible_lats = track_lats[in_bounds]

            # Subsample if still too many points
            if len(visible_lons) > 500:
                step = max(1, len(visible_lons) // 500)
                visible_lons = visible_lons[::step]
                visible_lats = visible_lats[::step]

            ax.plot(
                visible_lons,
                visible_lats,
                "k-",
                alpha=0.5,
                linewidth=0.8,
                label=f"Ship track ({len(visible_lons)} pts)",
            )
        else:
            # No track points in view - just add a note
            ax.text(
                0.02,
                0.98,
                "Ship track outside view",
                transform=ax.transAxes,
                fontsize=8,
                alpha=0.7,
                verticalalignment="top",
            )

    # Plot range circles and ship positions
    _plot_range_circles(ax, triang_data, solution)

    # Plot anchor positions
    ax.plot(
        deploy_lon,
        deploy_lat,
        "go",
        markersize=8,
        markeredgecolor="green",
        markerfacecolor="lightgreen",
        label="Anchor deployment",
    )
    ax.plot(
        anchor_lon,
        anchor_lat,
        "ro",
        markersize=8,
        markeredgecolor="red",
        markerfacecolor="red",
        label="Calculated anchor position",
    )

    # Plot fallback line
    ax.plot(
        [deploy_lon, anchor_lon],
        [deploy_lat, anchor_lat],
        "m:",
        linewidth=2,
        label=f"Fallback: {solution['fallback_distance']:.0f}m",
    )

    # Add position labels
    _add_position_labels(ax, triang_data, solution)

    # Formatting
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    ax.set_aspect(1.0 / np.cos(np.radians(anchor_lat)))
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    if not no_legend:
        ax.legend(loc="lower right")

    if not no_title:
        loc_name = triang_data["loc_name"]
        water_depth = triang_data["water_depth_anchor_launch"]
        release_height = triang_data["release_height"]
        transducer_depth = triang_data["transducer_depth"]
        title1 = f"Trilateration: {loc_name}"
        if gebco_depth is not None:
            title2 = (
                f"Launch depth: {water_depth:.0f}m, GEBCO: {gebco_depth:.0f}m, "
                f"Release height: {release_height:.0f}m, Transducer: {transducer_depth:.0f}m"
            )
        else:
            title2 = f"Water depth: {water_depth:.0f}m, Release height: {release_height:.0f}m, Transducer: {transducer_depth:.0f}m"
        title3 = f"Max error: {solution['max_residual']:.1f}m, RMS error: {solution['rms_residual']:.1f}m"
        ax.set_title(f"{title1}\n{title2}\n{title3}", pad=20)

    # Format axis ticks to degrees/minutes
    _format_coordinate_ticks(ax)

    # Save if requested
    if save_figure:
        plt.savefig(save_figure, dpi=300, bbox_inches="tight")
        print(f"Figure saved: {save_figure}")

    return fig


def _plot_bathymetry(
    ax,
    bathymetry: dict,
    lon_lim: List[float],
    lat_lim: List[float],
    anchor_depth: Optional[float] = None,
):
    """Plot bathymetry contours."""
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

        depth_min = np.nanmin(depth_subset)
        depth_max = np.nanmax(depth_subset)

        # Build isobath levels: coarse coverage of the full loaded region plus
        # 50 m-spaced levels around the anchor depth so the nearest isobath to
        # the deployment site is always included.
        coarse = list(range(200, 6001, 200))
        if anchor_depth is not None:
            centre = round(anchor_depth / 50) * 50
            fine = list(range(max(50, centre - 200), centre + 251, 50))
        else:
            fine = []
        isobath_levels = sorted(set(coarse + fine))

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
            ax.clabel(cs, inline=True, fontsize=8, fmt="%0.0fm", inline_spacing=10)


def _plot_range_circles(ax, triang_data: dict, solution: dict):
    """Plot range circles around ship positions."""
    from .utilities import horizontal_range

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
        color = "blue" if i < 3 else "red"
        ax.plot(lon, lat, "+", color=color, markersize=8, markeredgewidth=2)
        ax.text(lon, lat, f" {i + 1}", fontsize=10, color=color)

        # Range circle
        circle_lons, circle_lats = _generate_range_circle(lon, lat, h_range)
        ax.plot(circle_lons, circle_lats, color=color, linewidth=1, alpha=0.7)


def _generate_range_circle(
    center_lon: float, center_lat: float, radius: float, num_points: int = 360
) -> Tuple[List[float], List[float]]:
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


def _add_position_labels(ax, triang_data: dict, solution: dict):
    """Add position labels to the plot."""
    from .utilities import dec2deg

    # Anchor position label
    anchor_lat = solution["anchor_lat"]
    anchor_lon = solution["anchor_lon"]

    _, _, lat_str = dec2deg(anchor_lat)
    _, _, lon_str = dec2deg(anchor_lon)

    # Determine hemispheres
    lat_hemisphere = "N" if anchor_lat >= 0 else "S"
    lon_hemisphere = "E" if anchor_lon >= 0 else "W"

    position_text = f"{lat_str}{lat_hemisphere}\n{lon_str}{lon_hemisphere}"

    # Place label offset from anchor position
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_offset = (xlim[1] - xlim[0]) * 0.02
    y_offset = (ylim[1] - ylim[0]) * 0.02

    ax.text(
        anchor_lon + x_offset,
        anchor_lat + y_offset,
        position_text,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
        fontsize=9,
        verticalalignment="bottom",
    )


def _format_coordinate_ticks(ax, max_xticks: int = 5, max_yticks: int = 6):
    """Format axis ticks as degrees/minutes with hemisphere labels.

    Limits tick count via MaxNLocator to prevent label overlap, and rotates
    x-axis labels 30° because longitude strings are wider than plain numbers.
    """
    from .utilities import dec2deg
    from matplotlib.ticker import MaxNLocator

    def _coord_label(value: float, is_lon: bool) -> str:
        if value == 0:
            return "0°"
        _, _, deg_str = dec2deg(abs(value))
        if is_lon:
            hemi = "E" if value >= 0 else "W"
        else:
            hemi = "N" if value >= 0 else "S"
        return f"{deg_str}{hemi}"

    # Latitude (y): limit tick count, keep labels horizontal
    ax.yaxis.set_major_locator(MaxNLocator(nbins=max_yticks, prune="both"))
    ylim = ax.get_ylim()
    yticks = [t for t in ax.get_yticks() if ylim[0] <= t <= ylim[1]]
    ax.set_yticks(yticks)
    ax.set_yticklabels([_coord_label(t, is_lon=False) for t in yticks])

    # Longitude (x): limit tick count, rotate to avoid overlap
    ax.xaxis.set_major_locator(MaxNLocator(nbins=max_xticks, prune="both"))
    xlim = ax.get_xlim()
    xticks = [t for t in ax.get_xticks() if xlim[0] <= t <= xlim[1]]
    ax.set_xticks(xticks)
    ax.set_xticklabels(
        [_coord_label(t, is_lon=True) for t in xticks],
        rotation=30,
        ha="right",
    )


def save_cropped_figure(fig: plt.Figure, filename: str, margin: int = 10):
    """Save figure with cropped whitespace, mimicking MATLAB crop() function.

    Parameters
    ----------
    fig : plt.Figure
        Figure to save
    filename : str
        Output filename
    margin : int
        Margin in pixels around content

    """
    fig.savefig(filename, dpi=300, bbox_inches="tight", pad_inches=0.1)
    print(f"Figure saved: {filename}")


# Multi-survey plotting functions
def parse_survey_file(file_path: str) -> Tuple[Dict, List]:
    """Parse a survey data file and return survey parameters and data.

    Parameters
    ----------
    file_path : str
        Path to the survey data file

    Returns
    -------
    params : dict
        Survey parameters (release_height, transducer_depth, etc.)
    survey_data : list
        List of survey data points [date_time, lat_deg, lat_min, lon_deg, lon_min, range]

    """
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


def process_survey_file(
    file_path: str, sound_speed: Optional[float] = None
) -> Tuple[Dict, Dict]:
    """Process a survey data file and solve trilateration.

    Parameters
    ----------
    file_path : str
        Path to the survey data file
    sound_speed : float, optional
        Override sound speed from file

    Returns
    -------
    triang_data : dict
        Processed triangulation data
    solution : dict
        Trilateration solution

    """
    from .solve_anchor import solve_anchor_position

    params, survey_data = parse_survey_file(file_path)

    # Use provided sound speed or default
    if sound_speed is None:
        sound_speed = params.get("sound_speed", 1500)  # Default sound speed

    # Convert to decimal degrees
    latitudes = []
    longitudes = []
    ranges = []
    times = []

    def convert_to_decimal_degrees(deg, min_val):
        """Convert degrees and decimal minutes to decimal degrees."""
        return deg + min_val / 60

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
    solution = solve_anchor_position(triang_data, true_sound_speed=sound_speed)

    return triang_data, solution


def plot_multiple_solutions(
    solutions: List[Tuple[str, Dict, Dict]],
    bathymetry_path: Optional[str] = None,
    ship_track_path: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 8),
    colors: Optional[List[str]] = None,
    no_title: bool = False,
    no_legend: bool = False,
) -> plt.Figure:
    """Plot multiple trilateration solutions on a single figure.

    Parameters
    ----------
    solutions : list of tuple
        List of (loc_name, triang_data, solution) tuples
    bathymetry_path : str, optional
        Path to bathymetry NetCDF file
    figsize : tuple, optional
        Figure size (width, height)
    colors : list of str, optional
        Colors for each survey. If None, uses default colors

    Returns
    -------
    fig : matplotlib.figure.Figure
        The figure object

    """
    if colors is None:
        colors = ["red", "blue", "green", "orange", "purple", "brown"]

    if not solutions:
        raise ValueError("No solutions provided")

    # Set up the plot
    fig, ax = plt.subplots(figsize=figsize)

    # Calculate plot bounds
    all_lons = []
    all_lats = []

    for loc_name, triang_data, solution in solutions:
        # Add all ship positions and anchor position
        all_lons.extend(triang_data["longitudes"])
        all_lats.extend(triang_data["latitudes"])
        all_lons.append(solution["anchor_lon"])
        all_lats.append(solution["anchor_lat"])

    # Set plot bounds with margin
    lat_range = max(all_lats) - min(all_lats)
    lon_range = max(all_lons) - min(all_lons)

    margin_factor = 0.1
    lat_margin = lat_range * margin_factor if lat_range > 0 else 0.01
    lon_margin = lon_range * margin_factor if lon_range > 0 else 0.01

    west = min(all_lons) - lon_margin
    east = max(all_lons) + lon_margin
    south = min(all_lats) - lat_margin
    north = max(all_lats) + lat_margin

    # Load and plot bathymetry if available
    if bathymetry_path and os.path.exists(bathymetry_path):
        try:
            bathy = load_bathymetry_netcdf_subsampled(
                bathymetry_path,
                lon_bounds=(west - 1, east + 1),
                lat_bounds=(south - 1, north + 1),
                subsample=2,
            )
            # Plot isobaths
            if len(bathy["lon"]) > 0 and len(bathy["lat"]) > 0:
                lon_grid, lat_grid = np.meshgrid(bathy["lon"], bathy["lat"])
                isobath_levels = [600, 700, 800, 900, 1000, 1100]
                depth_min = np.nanmin(bathy["depth"])
                depth_max = np.nanmax(bathy["depth"])
                valid_levels = [
                    level for level in isobath_levels if depth_min <= level <= depth_max
                ]

                if valid_levels:
                    cs = ax.contour(
                        lon_grid,
                        lat_grid,
                        bathy["depth"],
                        levels=valid_levels,
                        colors="black",
                        alpha=0.7,
                        linewidths=1.0,
                    )
                    ax.clabel(cs, inline=True, fontsize=9, fmt="%0.0fm")
        except Exception as e:
            print(f"Could not load bathymetry: {e}")

    # Load and plot ship track if available
    if ship_track_path and os.path.exists(ship_track_path):
        try:
            ship_track = load_ship_track_netcdf(ship_track_path, subsample_minutes=1)
            # Filter ship track to plot bounds for performance
            track_lons = np.array(ship_track["lon"])
            track_lats = np.array(ship_track["lat"])

            # Find points within expanded plot bounds
            in_bounds = (
                (track_lons >= west - 1)
                & (track_lons <= east + 1)
                & (track_lats >= south - 1)
                & (track_lats <= north + 1)
            )

            if np.any(in_bounds):
                visible_lons = track_lons[in_bounds]
                visible_lats = track_lats[in_bounds]

                # Subsample if too many points
                if len(visible_lons) > 1000:
                    step = max(1, len(visible_lons) // 1000)
                    visible_lons = visible_lons[::step]
                    visible_lats = visible_lats[::step]

                ax.plot(
                    visible_lons,
                    visible_lats,
                    "k-",
                    alpha=0.4,
                    linewidth=0.6,
                    label=f"Ship track ({len(visible_lons)} pts)",
                )
        except Exception as e:
            print(f"Could not load ship track: {e}")

    # Plot all surveys
    for i, (loc_name, triang_data, solution) in enumerate(solutions):
        color = colors[i % len(colors)]

        # Plot range circles and ship positions
        _plot_multi_range_circles(ax, triang_data, color)

        # Plot deployment location
        deploy_lat = triang_data["latitudes"][0]
        deploy_lon = triang_data["longitudes"][0]
        ax.plot(
            deploy_lon,
            deploy_lat,
            "s",
            color=color,
            markersize=8,
            markeredgecolor="black",
            markeredgewidth=1,
            label=f"{loc_name} - Deployment",
        )

        # Plot final anchor position
        anchor_lat = solution["anchor_lat"]
        anchor_lon = solution["anchor_lon"]
        ax.plot(
            anchor_lon,
            anchor_lat,
            "*",
            color=color,
            markersize=12,
            markeredgecolor="black",
            markeredgewidth=1,
            label=f"{loc_name} - Anchor",
        )

        # Plot fallback line
        ax.plot(
            [deploy_lon, anchor_lon],
            [deploy_lat, anchor_lat],
            "--",
            color=color,
            linewidth=2,
            alpha=0.8,
        )

    # Set plot limits and formatting
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)

    # Set aspect ratio for correct circles at high latitudes
    center_lat = (south + north) / 2
    lat_lon_ratio = 1.0 / np.cos(np.radians(center_lat))
    ax.set_aspect(lat_lon_ratio)

    if not no_title:
        ax.set_title(
            "Multi-Survey Trilateration Results\n"
            "Range circles (○), deployment positions (□), anchor positions (★)",
            fontsize=12,
            fontweight="bold",
            pad=20,
        )

    _format_coordinate_ticks(ax)
    if not no_legend:
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()

    return fig


def plot_survey_grid(
    solutions: List[Tuple[str, Dict, Dict]],
    bathymetry_path: Optional[str] = None,
    figsize: Optional[Tuple[int, int]] = None,
    colors: Optional[List[str]] = None,
    no_title: bool = False,
    no_legend: bool = False,
) -> plt.Figure:
    """Create a grid figure with an overview map on top and per-mooring subplots below.

    Parameters
    ----------
    solutions : list of tuple
        List of (loc_name, triang_data, solution) tuples
    bathymetry_path : str, optional
        Path to bathymetry NetCDF file
    figsize : tuple, optional
        Figure size (width, height). Defaults to (20, 6 + 5 * n_subplot_rows).
    colors : list of str, optional
        Colors for each survey. If None, uses default colors.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The figure object

    """
    from matplotlib.gridspec import GridSpec

    if colors is None:
        colors = ["red", "blue", "green", "orange", "purple", "brown"]

    if not solutions:
        raise ValueError("No solutions provided")

    n = len(solutions)
    n_cols = min(n, 3)
    n_subplot_rows = (n + 2) // 3  # ceil(n / 3)
    n_rows = 1 + n_subplot_rows

    if figsize is None:
        figsize = (20, 6 + 5 * n_subplot_rows)

    fig = plt.figure(figsize=figsize)
    gs = GridSpec(n_rows, n_cols, figure=fig, hspace=0.35, wspace=0.3)

    # --- Overview panel (top row, full width) ---
    ax_main = fig.add_subplot(gs[0, :])

    all_lons: List[float] = []
    all_lats: List[float] = []
    for _, triang_data, solution in solutions:
        all_lons.extend(triang_data["longitudes"])
        all_lats.extend(triang_data["latitudes"])
        all_lons.append(solution["anchor_lon"])
        all_lats.append(solution["anchor_lat"])

    lat_range = max(all_lats) - min(all_lats)
    lon_range = max(all_lons) - min(all_lons)
    margin = 0.1
    lat_margin = lat_range * margin if lat_range > 0 else 0.01
    lon_margin = lon_range * margin if lon_range > 0 else 0.01
    west = min(all_lons) - lon_margin
    east = max(all_lons) + lon_margin
    south = min(all_lats) - lat_margin
    north = max(all_lats) + lat_margin

    if bathymetry_path and os.path.exists(bathymetry_path):
        try:
            bathy = load_bathymetry_netcdf_subsampled(
                bathymetry_path,
                lon_bounds=(west - 1, east + 1),
                lat_bounds=(south - 1, north + 1),
                subsample=2,
            )
            if len(bathy["lon"]) > 0 and len(bathy["lat"]) > 0:
                lon_grid, lat_grid = np.meshgrid(bathy["lon"], bathy["lat"])
                depth_min = np.nanmin(bathy["depth"])
                depth_max = np.nanmax(bathy["depth"])
                isobath_levels = [
                    lv
                    for lv in [600, 700, 800, 900, 1000, 1100]
                    if depth_min <= lv <= depth_max
                ]
                if isobath_levels:
                    cs = ax_main.contour(
                        lon_grid,
                        lat_grid,
                        bathy["depth"],
                        levels=isobath_levels,
                        colors="black",
                        alpha=0.7,
                        linewidths=1.0,
                    )
                    ax_main.clabel(cs, inline=True, fontsize=9, fmt="%0.0fm")
        except Exception as e:
            print(f"Could not load bathymetry: {e}")

    for i, (loc_name, triang_data, solution) in enumerate(solutions):
        color = colors[i % len(colors)]
        _plot_multi_range_circles(ax_main, triang_data, color)
        deploy_lat = triang_data["latitudes"][0]
        deploy_lon = triang_data["longitudes"][0]
        ax_main.plot(
            deploy_lon,
            deploy_lat,
            "s",
            color=color,
            markersize=8,
            markeredgecolor="black",
            markeredgewidth=1,
            label=f"{loc_name} - Deployment",
        )
        anchor_lat = solution["anchor_lat"]
        anchor_lon = solution["anchor_lon"]
        ax_main.plot(
            anchor_lon,
            anchor_lat,
            "*",
            color=color,
            markersize=12,
            markeredgecolor="black",
            markeredgewidth=1,
            label=f"{loc_name} - Anchor",
        )
        ax_main.plot(
            [deploy_lon, anchor_lon],
            [deploy_lat, anchor_lat],
            "--",
            color=color,
            linewidth=2,
            alpha=0.8,
        )

    ax_main.set_xlim(west, east)
    ax_main.set_ylim(south, north)
    center_lat = (south + north) / 2
    ax_main.set_aspect(1.0 / np.cos(np.radians(center_lat)))
    ax_main.grid(True, alpha=0.3)
    ax_main.set_xlabel("Longitude", fontsize=12)
    ax_main.set_ylabel("Latitude", fontsize=12)
    if not no_title:
        ax_main.set_title(
            "Trilateration Survey Overview\n"
            "Range circles (○), deployment positions (□), anchor positions (★)",
            fontsize=12,
            fontweight="bold",
            pad=10,
        )
    _format_coordinate_ticks(ax_main)
    if not no_legend:
        ax_main.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)

    # --- Individual per-mooring subplots (bottom rows) ---
    for i, (loc_name, triang_data, solution) in enumerate(solutions):
        row = 1 + i // n_cols
        col = i % n_cols
        ax = fig.add_subplot(gs[row, col])
        color = colors[i % len(colors)]

        _plot_multi_range_circles(ax, triang_data, color)

        deploy_lat = triang_data["latitudes"][0]
        deploy_lon = triang_data["longitudes"][0]
        anchor_lat = solution["anchor_lat"]
        anchor_lon = solution["anchor_lon"]

        ax.plot(
            deploy_lon,
            deploy_lat,
            "s",
            color=color,
            markersize=8,
            markeredgecolor="black",
            markeredgewidth=1,
            label="Deployment",
        )
        ax.plot(
            anchor_lon,
            anchor_lat,
            "*",
            color="black",
            markersize=10,
            markeredgewidth=1,
            label="Anchor",
        )
        ax.plot(
            [deploy_lon, anchor_lon],
            [deploy_lat, anchor_lat],
            "--",
            color=color,
            linewidth=1.5,
            alpha=0.8,
        )

        # Auto-bounds around anchor with margin from max range
        from .utilities import horizontal_range as _horiz_range

        max_h = max(
            (
                _horiz_range(
                    r,
                    triang_data["water_depth_anchor_launch"],
                    triang_data["release_height"],
                    triang_data["transducer_depth"],
                )
                for r in triang_data["ranges"]
                if r > 0
            ),
            default=2000,
        )
        pad_deg_lat = max_h / 111320 * 1.3
        pad_deg_lon = pad_deg_lat / np.cos(np.radians(anchor_lat))
        ax.set_xlim(anchor_lon - pad_deg_lon, anchor_lon + pad_deg_lon)
        ax.set_ylim(anchor_lat - pad_deg_lat, anchor_lat + pad_deg_lat)
        ax.set_aspect(1.0 / np.cos(np.radians(anchor_lat)))

        rms = solution["rms_residual"]
        fallback = solution["fallback_distance"]
        if rms < 10:
            quality = "Excellent"
        elif rms < 50:
            quality = "Good"
        elif rms < 100:
            quality = "Fair"
        else:
            quality = "Poor"
        ax.text(
            0.02,
            0.98,
            f"RMS: {rms:.1f} m\nFallback: {fallback:.0f} m\nQuality: {quality}",
            transform=ax.transAxes,
            verticalalignment="top",
            fontsize=8,
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        )

        if not no_title:
            ax.set_title(loc_name, fontsize=10, fontweight="bold")
        ax.grid(True, alpha=0.3)
        _format_coordinate_ticks(ax)
        if not no_legend:
            ax.legend(fontsize=7, loc="lower right")

    plt.tight_layout()
    return fig


def plot_multiple_surveys(
    survey_files: List[str],
    bathymetry_path: Optional[str] = None,
    ship_track_path: Optional[str] = None,
    sound_speed: Optional[float] = None,
    figsize: Tuple[int, int] = (10, 8),
    colors: Optional[List[str]] = None,
    no_title: bool = False,
    no_legend: bool = False,
) -> Tuple[plt.Figure, List[Tuple]]:
    """Plot multiple trilateration surveys on a single figure (wrapper function).

    This function processes survey files and then calls plot_multiple_solutions.

    Parameters
    ----------
    survey_files : list of str
        List of paths to survey data files.
    bathymetry_path : str, optional
        Path to bathymetry NetCDF file.
    ship_track_path : str, optional
        Path to ship track NetCDF file.
    sound_speed : float, optional
        Override sound speed for all surveys.
    figsize : tuple, optional
        Figure size (width, height).
    colors : list of str, optional
        Colors for each survey. If None, uses default colors.
    no_title : bool
        Omit the figure title.
    no_legend : bool
        Omit the figure legend.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The figure object.
    survey_results : list of tuple
        List of (loc_name, triang_data, solution) for each survey.

    """
    survey_results = []
    for file_path in survey_files:
        try:
            triang_data, solution = process_survey_file(file_path, sound_speed)
            survey_results.append((triang_data["loc_name"], triang_data, solution))
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue

    if not survey_results:
        raise ValueError("No valid survey data processed")

    fig = plot_multiple_solutions(
        survey_results,
        bathymetry_path,
        ship_track_path,
        figsize,
        colors,
        no_title=no_title,
        no_legend=no_legend,
    )

    return fig, survey_results


def _plot_multi_range_circles(ax, triang_data: dict, color: str):
    """Plot range circles around ship positions for one mooring in multi-plot context."""
    from .utilities import horizontal_range

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
        circle_lons, circle_lats = _generate_range_circle(lon, lat, h_range)
        ax.plot(circle_lons, circle_lats, color=color, linewidth=1, alpha=0.4)
