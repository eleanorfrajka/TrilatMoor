"""
Plotting functions for trilateration visualization.

Based on MATLAB f_run_anchor.m plotting functionality.
"""

import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional, Tuple, Union

from .utilities import vincenty_forward, vincenty_distance


def load_bathymetry_netcdf_subsampled(netcdf_path: str, lon_bounds: tuple, lat_bounds: tuple, subsample: int = 5) -> dict:
    """
    Load bathymetry data from NetCDF file with regional clipping and subsampling.
    
    Parameters:
    -----------
    netcdf_path : str
        Path to NetCDF bathymetry file
    lon_bounds : tuple
        (min_lon, max_lon) longitude bounds
    lat_bounds : tuple
        (min_lat, max_lat) latitude bounds  
    subsample : int
        Subsampling factor (e.g., 5 means every 5th point)
        
    Returns:
    --------
    dict
        Bathymetry data with 'lat', 'lon', 'depth' keys
    """
    try:
        import xarray as xr
    except ImportError:
        raise ImportError("xarray is required to load NetCDF bathymetry files. Install with: pip install xarray")
    
    # Load NetCDF file
    ds = xr.open_dataset(netcdf_path)
    
    # Try common variable names for coordinates and depth
    # Common coordinate names
    lon_vars = ['lon', 'longitude', 'x', 'nav_lon']
    lat_vars = ['lat', 'latitude', 'y', 'nav_lat'] 
    depth_vars = ['depth', 'elevation', 'z', 'bathymetry', 'topo']
    
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
        raise ValueError(f"Could not find coordinate/depth variables in NetCDF file. "
                        f"Available variables: {list(ds.variables.keys())}")
    
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
        return {'lon': np.array([]), 'lat': np.array([]), 'depth': np.array([])}
    
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
    
    return {
        'lon': lon,
        'lat': lat, 
        'depth': depth
    }


def load_bathymetry_netcdf(netcdf_path: str) -> dict:
    """
    Load bathymetry data from NetCDF file.
    
    Parameters:
    -----------
    netcdf_path : str
        Path to NetCDF bathymetry file
        
    Returns:
    --------
    dict
        Bathymetry data with 'lat', 'lon', 'depth' keys
    """
    try:
        import xarray as xr
    except ImportError:
        raise ImportError("xarray is required to load NetCDF bathymetry files. Install with: pip install xarray")
    
    # Load NetCDF file
    ds = xr.open_dataset(netcdf_path)
    
    # Try common variable names for coordinates and depth
    # Common coordinate names
    lon_vars = ['lon', 'longitude', 'x', 'nav_lon']
    lat_vars = ['lat', 'latitude', 'y', 'nav_lat'] 
    depth_vars = ['depth', 'elevation', 'z', 'bathymetry', 'topo']
    
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
        raise ValueError(f"Could not find coordinate/depth variables in NetCDF file. "
                        f"Available variables: {list(ds.variables.keys())}")
    
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
    
    return {
        'lon': lon,
        'lat': lat, 
        'depth': depth
    }


def plot_trilateration_survey(triang_data: dict, solution: dict, 
                            ship_track: Optional[dict] = None,
                            bathymetry: Optional[Union[dict, str]] = None,
                            save_figure: Optional[str] = None) -> plt.Figure:
    """
    Create trilateration survey plot showing ship positions, range circles, and solution.
    
    Based on the plotting functionality in MATLAB f_run_anchor.m.
    
    Parameters:
    -----------
    triang_data : dict
        Triangulation survey data
    solution : dict
        Anchor position solution
    ship_track : dict, optional
        Ship track data with 'lat', 'lon' keys for plotting ship path
    bathymetry : dict or str, optional
        Bathymetry data with 'lat', 'lon', 'depth' keys, or path to NetCDF file
    save_figure : str, optional
        Filename to save figure (e.g., 'trilateration.png')
        
    Returns:
    --------
    plt.Figure
        Matplotlib figure object
    """
    
    # Extract data
    anchor_lat = solution['anchor_lat']
    anchor_lon = solution['anchor_lon']
    deploy_lat = triang_data['latitudes'][0]
    deploy_lon = triang_data['longitudes'][0]
    
    # Handle bathymetry parameter
    if isinstance(bathymetry, str):
        # Load bathymetry from NetCDF file
        bathymetry = load_bathymetry_netcdf(bathymetry)
    
    # Calculate plot bounds based on triangulation area and range circles
    from .utilities import horizontal_range
    import numpy as np
    
    # Get the maximum horizontal range to determine plot scale
    max_range = 0
    for i, range_val in enumerate(triang_data['ranges']):
        if range_val > 0:
            h_range = horizontal_range(
                range_val,
                triang_data['water_depth_anchor_launch'],
                triang_data['release_height'],
                triang_data['transducer_depth']
            )
            max_range = max(max_range, h_range)
    
    # Use range circles to set appropriate bounds
    if max_range > 0:
        # Convert range to approximate degrees (rough approximation)
        range_deg_lat = max_range / 111320  # meters to degrees latitude
        range_deg_lon = max_range / (111320 * np.cos(np.radians(anchor_lat)))  # account for longitude compression
        
        # Set bounds based on anchor position and max range + margin
        margin_factor = 1.2  # 20% margin beyond max range
        lat_margin = range_deg_lat * margin_factor
        lon_margin = range_deg_lon * margin_factor
        
        west = anchor_lon - lon_margin
        east = anchor_lon + lon_margin  
        south = anchor_lat - lat_margin
        north = anchor_lat + lat_margin
    else:
        # Fallback to original method if no ranges
        all_lons = triang_data['longitudes'] + [anchor_lon, deploy_lon]
        all_lats = triang_data['latitudes'] + [anchor_lat, deploy_lat]
        
        lat_range = max(all_lats) - min(all_lats)
        lon_range = max(all_lons) - min(all_lons)
        margin = max(lat_range, lon_range, 0.01) * 2  # Ensure minimum margin
        
        west = min(all_lons) - margin
        east = max(all_lons) + margin  
        south = min(all_lats) - margin
        north = max(all_lats) + margin
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Plot bathymetry if provided
    if bathymetry is not None:
        _plot_bathymetry(ax, bathymetry, [west, east], [south, north])
    
    # Plot ship track if provided (only the portion visible in current bounds)
    if ship_track is not None:
        # Filter ship track to only show points within plot bounds for performance
        import numpy as np
        track_lons = np.array(ship_track['lon'])
        track_lats = np.array(ship_track['lat'])
        
        # Find points within plot bounds
        in_bounds = ((track_lons >= west) & (track_lons <= east) & 
                    (track_lats >= south) & (track_lats <= north))
        
        if np.any(in_bounds):
            # Get visible track points
            visible_lons = track_lons[in_bounds]
            visible_lats = track_lats[in_bounds]
            
            # Subsample if still too many points
            if len(visible_lons) > 500:
                step = max(1, len(visible_lons) // 500)
                visible_lons = visible_lons[::step]
                visible_lats = visible_lats[::step]
            
            ax.plot(visible_lons, visible_lats, 'k-', alpha=0.5, linewidth=0.8, 
                   label=f'Ship track ({len(visible_lons)} pts)')
        else:
            # No track points in view - just add a note
            ax.text(0.02, 0.98, 'Ship track outside view', transform=ax.transAxes, 
                   fontsize=8, alpha=0.7, verticalalignment='top')
    
    # Plot range circles and ship positions
    _plot_range_circles(ax, triang_data, solution)
    
    # Plot anchor positions
    ax.plot(deploy_lon, deploy_lat, 'go', markersize=8, markeredgecolor='green', 
            markerfacecolor='lightgreen', label='Anchor deployment')
    ax.plot(anchor_lon, anchor_lat, 'ro', markersize=8, markeredgecolor='red',
            markerfacecolor='red', label='Calculated anchor position')
    
    # Plot fallback line
    ax.plot([deploy_lon, anchor_lon], [deploy_lat, anchor_lat], 'm:', linewidth=2, 
            label=f'Fallback: {solution["fallback_distance"]:.0f}m')
    
    # Add position labels
    _add_position_labels(ax, triang_data, solution)
    
    # Formatting
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.legend()
    
    # Title with key information
    loc_name = triang_data['loc_name']
    water_depth = triang_data['water_depth_anchor_launch']
    release_height = triang_data['release_height']
    transducer_depth = triang_data['transducer_depth']
    
    title1 = f'Triangulation Survey: {loc_name}'
    title2 = f'Water depth: {water_depth:.0f}m, Release height: {release_height:.0f}m, Transducer: {transducer_depth:.0f}m'
    title3 = f'Max error: {solution["max_residual"]:.1f}m, RMS error: {solution["rms_residual"]:.1f}m'
    
    ax.set_title(f'{title1}\n{title2}\n{title3}', pad=20)
    
    # Format axis ticks to degrees/minutes
    _format_coordinate_ticks(ax)
    
    plt.tight_layout(pad=2.0)
    
    # Save if requested
    if save_figure:
        plt.savefig(save_figure, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {save_figure}")
    
    return fig


def _plot_bathymetry(ax, bathymetry: dict, lon_lim: List[float], lat_lim: List[float]):
    """Plot bathymetry contours."""
    
    # Find indices within plot bounds
    lon_idx = np.where((bathymetry['lon'] >= lon_lim[0]) & (bathymetry['lon'] <= lon_lim[1]))[0]
    lat_idx = np.where((bathymetry['lat'] >= lat_lim[0]) & (bathymetry['lat'] <= lat_lim[1]))[0]
    
    if len(lon_idx) > 0 and len(lat_idx) > 0:
        lon_grid, lat_grid = np.meshgrid(bathymetry['lon'][lon_idx], bathymetry['lat'][lat_idx])
        depth_subset = bathymetry['depth'][np.ix_(lat_idx, lon_idx)]
        
        # Specific isobath levels
        isobath_levels = [600, 700, 800, 900, 1000, 1100]
        
        # Filter levels to only those within the data range
        depth_min = np.nanmin(depth_subset)
        depth_max = np.nanmax(depth_subset)
        valid_levels = [level for level in isobath_levels if depth_min <= level <= depth_max]
        
        if valid_levels:
            cs = ax.contour(lon_grid, lat_grid, depth_subset, levels=valid_levels, 
                           colors='black', alpha=0.7, linewidths=1.0)
            ax.clabel(cs, inline=True, fontsize=8, fmt='%0.0fm', 
                     inline_spacing=10)


def _plot_range_circles(ax, triang_data: dict, solution: dict):
    """Plot range circles around ship positions."""
    
    from .utilities import horizontal_range
    
    # Get corrected horizontal ranges
    corrected_ranges = []
    ship_positions = []
    
    for i, (lat, lon, range_val) in enumerate(zip(
        triang_data['latitudes'], triang_data['longitudes'], triang_data['ranges'])):
        
        if range_val > 0:  # Skip deployment position
            h_range = horizontal_range(
                range_val,
                triang_data['water_depth_anchor_launch'],
                triang_data['release_height'],
                triang_data['transducer_depth']
            )
            corrected_ranges.append(h_range)
            ship_positions.append((lon, lat))
    
    # Plot ship positions and range circles
    for i, ((lon, lat), h_range) in enumerate(zip(ship_positions, corrected_ranges)):
        # Ship position
        color = 'blue' if i < 3 else 'red'
        ax.plot(lon, lat, '+', color=color, markersize=8, markeredgewidth=2)
        ax.text(lon, lat, f' {i+1}', fontsize=10, color=color)
        
        # Range circle
        circle_lons, circle_lats = _generate_range_circle(lon, lat, h_range)
        ax.plot(circle_lons, circle_lats, color=color, linewidth=1, alpha=0.7)


def _generate_range_circle(center_lon: float, center_lat: float, radius: float, 
                          num_points: int = 360) -> Tuple[List[float], List[float]]:
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
    anchor_lat = solution['anchor_lat']
    anchor_lon = solution['anchor_lon']
    
    _, _, lat_str = dec2deg(anchor_lat)
    _, _, lon_str = dec2deg(abs(anchor_lon))
    
    position_text = f'{lat_str}N\n{lon_str}W'
    
    # Place label offset from anchor position
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_offset = (xlim[1] - xlim[0]) * 0.02
    y_offset = (ylim[1] - ylim[0]) * 0.02
    
    ax.text(anchor_lon + x_offset, anchor_lat + y_offset, position_text, 
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
            fontsize=9, verticalalignment='bottom')


def _format_coordinate_ticks(ax):
    """Format axis ticks to show degrees and minutes."""
    
    from .utilities import dec2deg
    
    # Format latitude ticks
    yticks = ax.get_yticks()
    yticklabels = []
    for tick in yticks:
        if tick != 0:
            _, _, deg_str = dec2deg(abs(tick))
            hemisphere = 'N' if tick >= 0 else 'S'
            yticklabels.append(f'{deg_str}{hemisphere}')
        else:
            yticklabels.append('0°')
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels)
    
    # Format longitude ticks  
    xticks = ax.get_xticks()
    xticklabels = []
    for tick in xticks:
        if tick != 0:
            _, _, deg_str = dec2deg(abs(tick))
            hemisphere = 'E' if tick >= 0 else 'W'
            xticklabels.append(f'{deg_str}{hemisphere}')
        else:
            xticklabels.append('0°')
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)


def save_cropped_figure(fig: plt.Figure, filename: str, margin: int = 10):
    """
    Save figure with cropped whitespace, mimicking MATLAB crop() function.
    
    Parameters:
    -----------
    fig : plt.Figure
        Figure to save
    filename : str
        Output filename
    margin : int
        Margin in pixels around content
    """
    fig.savefig(filename, dpi=300, bbox_inches='tight', pad_inches=0.1)
    print(f"Figure saved: {filename}")