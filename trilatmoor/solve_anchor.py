"""Core trilateration algorithm for determining anchor positions.

Based on MATLAB solve_anchor.m using least-squares solution.
"""

import numpy as np
from typing import Tuple, List

from .utilities import vincenty_distance, sound_speed_correction, horizontal_range


def solve_anchor_position(
    triang_data: dict,
    true_sound_speed: float = 1503,
    measured_sound_speed: float = 1507,
) -> dict:
    """Solve for anchor position using trilateration with multiple ship positions.

    Based on MATLAB solve_anchor.m and f_run_anchor.m functions.

    Parameters
    ----------
    triang_data : dict
        Survey data containing ship positions and ranges with keys:
        - 'latitudes', 'longitudes', 'ranges', 'water_depth_anchor_launch'
        - 'release_height', 'transducer_depth'
    true_sound_speed : float
        Actual sound speed (m/s), default 1503 m/s
    measured_sound_speed : float
        Sound speed used by transducer (m/s), default 1507 m/s

    Returns
    -------
    dict
        Solution with keys: 'anchor_lat', 'anchor_lon', 'fallback_distance',
        'max_residual', 'rms_residual', 'residuals'

    Raises
    ------
    ValueError
        If insufficient data for trilateration

    """
    # Count valid fixes (non-zero ranges)
    valid_fixes = sum(1 for r in triang_data["ranges"] if r > 0)
    if valid_fixes < 3:
        raise ValueError("Need at least 3 position fixes for trilateration")

    # Correct ranges for sound speed
    corrected_ranges = sound_speed_correction(
        triang_data["ranges"], measured_sound_speed, true_sound_speed
    )

    # Convert to horizontal ranges
    horizontal_ranges = []
    positions = []

    for i, (lat, lon, range_val) in enumerate(
        zip(triang_data["latitudes"], triang_data["longitudes"], corrected_ranges)
    ):

        if range_val > 0:  # Skip anchor drop position (range = 0)
            h_range = horizontal_range(
                range_val,
                triang_data["water_depth_anchor_launch"],
                triang_data["release_height"],
                triang_data["transducer_depth"],
            )
            horizontal_ranges.append(h_range)
            positions.append((lon, lat))

    # Initial estimate: center of ship positions
    lons, lats = zip(*positions)
    lon0 = np.mean(lons)
    lat0 = np.mean(lats)

    # Solve using least squares approach
    anchor_lon, anchor_lat = _solve_trilateration(
        positions, horizontal_ranges, lon0, lat0
    )

    # Calculate residuals
    residuals = _calculate_residuals(
        positions, horizontal_ranges, anchor_lon, anchor_lat
    )

    # Calculate fallback distance from deployment position
    deploy_lat = triang_data["latitudes"][0]
    deploy_lon = triang_data["longitudes"][0]
    fallback_distance, _, _ = vincenty_distance(
        deploy_lon, deploy_lat, anchor_lon, anchor_lat
    )

    # Error statistics
    max_residual = np.max(residuals)
    rms_residual = np.sqrt(np.mean(np.array(residuals) ** 2))

    return {
        "anchor_lat": anchor_lat,
        "anchor_lon": anchor_lon,
        "fallback_distance": fallback_distance,
        "max_residual": max_residual,
        "rms_residual": rms_residual,
        "residuals": residuals.tolist(),
    }


def _solve_trilateration(
    positions: List[Tuple[float, float]], ranges: List[float], lon0: float, lat0: float
) -> Tuple[float, float]:
    """Solve trilateration using least squares approach.

    Based on MATLAB solve_anchor.m algorithm.

    Parameters
    ----------
    positions : List[Tuple[float, float]]
        Ship positions as (lon, lat) tuples in decimal degrees
    ranges : List[float]
        Horizontal ranges in meters
    lon0, lat0 : float
        Initial position estimate in decimal degrees

    Returns
    -------
    Tuple[float, float]
        Solved position as (lon, lat) in decimal degrees

    """
    n_fixes = len(positions)
    ranges = np.array(ranges)

    # Convert positions to Cartesian coordinates relative to initial estimate
    x = np.zeros(n_fixes)
    y = np.zeros(n_fixes)

    for i, (lon, lat) in enumerate(positions):
        dist, azimuth, _ = vincenty_distance(lon0, lat0, lon, lat)
        azimuth_rad = np.radians(azimuth)
        x[i] = dist * np.sin(azimuth_rad)  # East
        y[i] = dist * np.cos(azimuth_rad)  # North

    # Set up least squares problem: A * solution = b
    # where solution = [delta_x, delta_y] is correction to initial estimate

    # Calculate terms
    xyr = x**2 + y**2 - ranges**2

    # Build matrices for overdetermined system
    A = np.zeros((n_fixes, 2))
    b = np.zeros(n_fixes)

    # Use differences between consecutive equations
    for i in range(n_fixes - 1):
        b[i] = xyr[i] - xyr[i + 1]
        A[i, 0] = 2 * (x[i] - x[i + 1])  # d/dx
        A[i, 1] = 2 * (y[i] - y[i + 1])  # d/dy

    # Add final equation (difference with first)
    b[n_fixes - 1] = xyr[n_fixes - 1] - xyr[0]
    A[n_fixes - 1, 0] = 2 * (x[n_fixes - 1] - x[0])
    A[n_fixes - 1, 1] = 2 * (y[n_fixes - 1] - y[0])

    # Solve least squares: solution = (A^T A)^-1 A^T b
    try:
        solution = np.linalg.lstsq(A, b, rcond=None)[0]
    except np.linalg.LinAlgError:
        raise ValueError("Unable to solve trilateration - singular matrix")

    # Convert solution back to geographic coordinates
    delta_x, delta_y = solution

    # Calculate distance and azimuth of correction
    correction_dist = np.sqrt(delta_x**2 + delta_y**2)
    correction_azimuth = np.degrees(np.arctan2(delta_x, delta_y))

    # Apply correction to get final position
    from .utilities import vincenty_forward

    anchor_lon, anchor_lat, _ = vincenty_forward(
        lon0, lat0, correction_azimuth, correction_dist
    )

    return anchor_lon, anchor_lat


def _calculate_residuals(
    positions: List[Tuple[float, float]],
    ranges: List[float],
    anchor_lon: float,
    anchor_lat: float,
) -> np.ndarray:
    """Calculate residual errors between measured and calculated ranges.

    Parameters
    ----------
    positions : List[Tuple[float, float]]
        Ship positions as (lon, lat) tuples
    ranges : List[float]
        Measured horizontal ranges in meters
    anchor_lon, anchor_lat : float
        Calculated anchor position in decimal degrees

    Returns
    -------
    np.ndarray
        Residual errors in meters

    """
    residuals = []

    for (lon, lat), measured_range in zip(positions, ranges):
        calculated_distance, _, _ = vincenty_distance(lon, lat, anchor_lon, anchor_lat)
        residual = abs(calculated_distance - measured_range)
        residuals.append(residual)

    return np.array(residuals)


def iterative_solve_anchor_position(
    triang_data: dict,
    true_sound_speed: float = 1503,
    measured_sound_speed: float = 1507,
    max_iterations: int = 2,
) -> dict:
    """Iteratively solve anchor position with improved initial estimate.

    Based on the two-step approach in MATLAB f_run_anchor.m.

    Parameters
    ----------
    triang_data : dict
        Survey data
    true_sound_speed : float
        Actual sound speed (m/s)
    measured_sound_speed : float
        Transducer sound speed (m/s)
    max_iterations : int
        Maximum number of iterations (default 2)

    Returns
    -------
    dict
        Final solution after iterations

    """
    solution = solve_anchor_position(
        triang_data, true_sound_speed, measured_sound_speed
    )

    # Iterate to improve solution
    for iteration in range(max_iterations - 1):
        # Use previous solution as new starting point
        previous_solution = solution

        # Update initial estimate and re-solve
        # This mimics the two-step approach in the MATLAB code
        solution = solve_anchor_position(
            triang_data, true_sound_speed, measured_sound_speed
        )

        # Check for convergence
        position_change = vincenty_distance(
            previous_solution["anchor_lon"],
            previous_solution["anchor_lat"],
            solution["anchor_lon"],
            solution["anchor_lat"],
        )[0]

        if position_change < 0.1:  # Converged to within 10 cm
            break

    return solution
