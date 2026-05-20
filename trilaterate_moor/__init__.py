"""
Trilaterate Moor - Python package for seafloor mooring position determination

This package provides tools for trilateration/triangulation of seafloor moorings
using acoustic ranging from ship positions.
"""

from .solve_anchor import solve_anchor_position
from .utilities import (
    vincenty_distance,
    vincenty_forward, 
    dec2deg,
    deg2dec,
    sound_speed_correction,
    horizontal_range
)
from .read_dship import parse_triangulation_file
from .plotting import plot_trilateration_survey, save_cropped_figure, load_bathymetry_netcdf, load_bathymetry_netcdf_subsampled

__version__ = "0.1.0"
__all__ = [
    "solve_anchor_position",
    "vincenty_distance", 
    "vincenty_forward",
    "dec2deg",
    "deg2dec", 
    "sound_speed_correction",
    "horizontal_range",
    "parse_triangulation_file",
    "plot_trilateration_survey",
    "save_cropped_figure",
    "load_bathymetry_netcdf",
    "load_bathymetry_netcdf_subsampled"
]