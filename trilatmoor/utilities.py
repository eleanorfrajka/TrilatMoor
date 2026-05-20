"""Utilities for trilateration calculations including geodetic functions.

Based on MATLAB m_map functions using Vincenty's algorithms for high accuracy.
"""

import numpy as np
import math


# WGS84 ellipsoid parameters
WGS84_A = 6378137.0  # Semi-major axis (meters)
WGS84_F = 1 / 298.257223563  # Flattening
WGS84_B = WGS84_A * (1 - WGS84_F)  # Semi-minor axis


def vincenty_distance(lon1, lat1, lon2, lat2):
    """Calculate distance between two points using Vincenty's inverse formula.

    Based on MATLAB m_idist.m - highly accurate ellipsoidal distance calculation.

    Parameters
    ----------
    lon1, lat1 : float
        First point coordinates in decimal degrees
    lon2, lat2 : float
        Second point coordinates in decimal degrees

    Returns
    -------
    distance : float
        Distance in meters
    azimuth_forward : float
        Forward azimuth in degrees (from point 1 to point 2)
    azimuth_backward : float
        Backward azimuth in degrees (from point 2 to point 1)

    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    lon2_rad = math.radians(lon2)

    # Handle pole proximity (within 1e-10 degrees)
    if abs(90 - abs(lat1)) < 1e-10:
        lat1_rad = math.copysign(math.radians(90 - 1e-10), lat1_rad)
    if abs(90 - abs(lat2)) < 1e-10:
        lat2_rad = math.copysign(math.radians(90 - 1e-10), lat2_rad)

    a, b, f = WGS84_A, WGS84_B, WGS84_F

    U1 = math.atan((1 - f) * math.tan(lat1_rad))
    U2 = math.atan((1 - f) * math.tan(lat2_rad))

    # Longitude difference (shortest path)
    L = abs((lon2 % 360) - (lon1 % 360)) * math.pi / 180
    if L > math.pi:
        L = 2 * math.pi - L

    lambda_val = L
    lambda_old = 0
    itercount = 0
    # Initialize variables to handle early loop exit
    alpha = 0
    sin_sigma = 0
    cos_sigma = 1
    sigma = 0
    cos2_sigma_m = 0

    while abs(lambda_val - lambda_old) > 1e-12 and itercount < 50:
        itercount += 1

        sin_sigma = math.sqrt(
            (math.cos(U2) * math.sin(lambda_val)) ** 2
            + (
                math.cos(U1) * math.sin(U2)
                - math.sin(U1) * math.cos(U2) * math.cos(lambda_val)
            )
            ** 2
        )
        cos_sigma = math.sin(U1) * math.sin(U2) + math.cos(U1) * math.cos(
            U2
        ) * math.cos(lambda_val)
        sigma = math.atan2(sin_sigma, cos_sigma)

        if sin_sigma == 0:
            alpha = 0  # Points are coincident
        else:
            alpha = math.asin(
                math.cos(U1) * math.cos(U2) * math.sin(lambda_val) / sin_sigma
            )

        cos2_sigma_m = cos_sigma - 2 * math.sin(U1) * math.sin(U2) / (
            math.cos(alpha) ** 2
        )
        C = f / 16 * math.cos(alpha) ** 2 * (4 + f * (4 - 3 * math.cos(alpha) ** 2))

        lambda_old = lambda_val
        lambda_val = L + (1 - C) * f * math.sin(alpha) * (
            sigma
            + C
            * sin_sigma
            * (cos2_sigma_m + C * cos_sigma * (-1 + 2 * cos2_sigma_m**2))
        )

        # Handle antipodal points
        if lambda_val > math.pi:
            lambda_val = math.pi
            break

    u2 = math.cos(alpha) ** 2 * (a**2 - b**2) / b**2
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))

    delta_sigma = (
        B
        * sin_sigma
        * (
            cos2_sigma_m
            + B
            / 4
            * (
                cos_sigma * (-1 + 2 * cos2_sigma_m**2)
                - B
                / 6
                * cos2_sigma_m
                * (-3 + 4 * sin_sigma**2)
                * (-3 + 4 * cos2_sigma_m**2)
            )
        )
    )

    distance = b * A * (sigma - delta_sigma)

    # Calculate azimuths
    if abs(lambda_val) < 1e-12:  # Same point
        azimuth_forward = 0
        azimuth_backward = 180
    else:
        # Correct sign for azimuth calculation
        if math.sin((lon2 - lon1) * math.pi / 180) * math.sin(lambda_val) < 0:
            lambda_val = -lambda_val

        # Forward azimuth
        numer = math.cos(U2) * math.sin(lambda_val)
        denom = math.cos(U1) * math.sin(U2) - math.sin(U1) * math.cos(U2) * math.cos(
            lambda_val
        )
        azimuth_forward = math.degrees(math.atan2(numer, denom)) % 360

        # Backward azimuth
        numer = math.cos(U1) * math.sin(lambda_val)
        denom = math.sin(U1) * math.cos(U2) - math.cos(U1) * math.sin(U2) * math.cos(
            lambda_val
        )
        azimuth_backward = math.degrees(math.atan2(numer, denom)) % 360

    return distance, azimuth_forward, azimuth_backward


def vincenty_forward(lon1, lat1, azimuth, distance):
    """Calculate endpoint given start point, azimuth, and distance using Vincenty's direct formula.

    Based on MATLAB m_fdist.m for high accuracy forward calculations.

    Parameters
    ----------
    lon1, lat1 : float
        Starting point coordinates in decimal degrees
    azimuth : float
        Forward azimuth in degrees (clockwise from north)
    distance : float
        Distance in meters

    Returns
    -------
    lon2, lat2 : float
        Endpoint coordinates in decimal degrees
    azimuth_back : float
        Backward azimuth in degrees

    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    azimuth_rad = math.radians(azimuth)

    # Handle pole proximity
    if abs(90 - abs(lat1)) < 1e-10:
        lat1_rad = math.copysign(math.radians(90 - 1e-10), lat1_rad)

    a, b, f = WGS84_A, WGS84_B, WGS84_F

    U1 = math.atan((1 - f) * math.tan(lat1_rad))
    sigma1 = math.atan2(math.tan(U1), math.cos(azimuth_rad))
    alpha = math.asin(math.cos(U1) * math.sin(azimuth_rad))

    u2 = math.cos(alpha) ** 2 * (a**2 - b**2) / b**2
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))

    sigma = distance / (b * A)
    sigma_old = sigma
    itercount = 0

    while itercount < 50:
        itercount += 1
        sigma_m2 = 2 * sigma1 + sigma
        cos2_sigma_m = math.cos(sigma_m2)

        delta_sigma = (
            B
            * math.sin(sigma)
            * (
                cos2_sigma_m
                + B
                / 4
                * (
                    math.cos(sigma) * (-1 + 2 * cos2_sigma_m**2)
                    - B
                    / 6
                    * cos2_sigma_m
                    * (-3 + 4 * math.sin(sigma) ** 2)
                    * (-3 + 4 * cos2_sigma_m**2)
                )
            )
        )

        sigma_old = sigma
        sigma = distance / (b * A) + delta_sigma

        if abs(sigma - sigma_old) <= 1e-12:
            break

    # Calculate final position
    numer = math.sin(sigma) * math.sin(azimuth_rad)
    denom = math.cos(U1) * math.cos(sigma) - math.sin(U1) * math.sin(sigma) * math.cos(
        azimuth_rad
    )
    lambda_val = math.atan2(numer, denom)

    C = f / 16 * math.cos(alpha) ** 2 * (4 + f * (4 - 3 * math.cos(alpha) ** 2))
    L = lambda_val - (1 - C) * f * math.sin(alpha) * (
        sigma
        + C
        * math.sin(sigma)
        * (cos2_sigma_m + C * math.cos(sigma) * (-1 + 2 * cos2_sigma_m**2))
    )

    lon2 = (lon1 + math.degrees(L)) % 360
    if lon2 > 180:
        lon2 -= 360

    numer = math.sin(U1) * math.cos(sigma) + math.cos(U1) * math.sin(sigma) * math.cos(
        azimuth_rad
    )
    denom = (1 - f) * math.sqrt(
        math.sin(alpha) ** 2
        + (
            math.sin(U1) * math.sin(sigma)
            - math.cos(U1) * math.cos(sigma) * math.cos(azimuth_rad)
        )
        ** 2
    )
    lat2 = math.degrees(math.atan2(numer, denom))

    # Backward azimuth
    azimuth_back = (
        math.degrees(
            math.atan2(
                -math.sin(alpha),
                math.sin(U1) * math.sin(sigma)
                - math.cos(U1) * math.cos(sigma) * math.cos(azimuth_rad),
            )
        )
        % 360
    )

    return lon2, lat2, azimuth_back


def dec2deg(decimal_degrees):
    """Convert decimal degrees to degrees and decimal minutes.

    Based on MATLAB dec2deg.m function.

    Parameters
    ----------
    decimal_degrees : float
        Coordinate in decimal degrees

    Returns
    -------
    degrees : int
        Whole degrees
    minutes : float
        Decimal minutes
    deg_str : str
        Formatted string representation

    """
    if decimal_degrees == 0:
        return 0, 0.0, "0°"

    abs_val = abs(decimal_degrees)
    degrees = int(abs_val)
    minutes = round((abs_val - degrees) * 60 * 100) / 100  # Round to 2 decimals

    if minutes >= 60:
        degrees += 1
        minutes = 0

    if minutes == 0:
        deg_str = f"{degrees}°"
    else:
        deg_str = f"{degrees}°{minutes:.2f}'"

    return degrees, minutes, deg_str


def deg2dec(degrees, minutes):
    """Convert degrees and minutes to decimal degrees.

    Parameters
    ----------
    degrees : int
        Whole degrees
    minutes : float
        Decimal minutes

    Returns
    -------
    decimal_degrees : float
        Coordinate in decimal degrees

    """
    return degrees + minutes / 60


def sound_speed_correction(measured_range, measured_speed=1507, true_speed=1503):
    """Correct acoustic ranges for sound speed differences.

    Parameters
    ----------
    measured_range : float or array
        Measured ranges in meters
    measured_speed : float
        Sound speed used by transducer (m/s), default 1507 m/s
    true_speed : float
        True sound speed (m/s), default 1503 m/s

    Returns
    -------
    corrected_range : float or array
        Range corrected for true sound speed

    """
    return np.array(measured_range) * true_speed / measured_speed


def horizontal_range(slant_range, water_depth, release_height=1, transducer_depth=10):
    """Calculate horizontal range from slant range and water depth.

    Parameters
    ----------
    slant_range : float or array
        Slant range measurements in meters
    water_depth : float
        Water depth at anchor position in meters
    release_height : float
        Height of release above seafloor in meters (default 1m)
    transducer_depth : float
        Depth of ship's transducer below surface in meters (default 10m)

    Returns
    -------
    horizontal_range : float or array
        Horizontal range in meters

    """
    vertical_separation = water_depth - release_height - transducer_depth
    return np.sqrt(np.array(slant_range) ** 2 - vertical_separation**2)


def round_to_n(value, n=100):
    """Round value to nearest 1/n.

    Based on MATLAB r100.m function.

    Parameters
    ----------
    value : float
        Value to round
    n : int
        Rounding factor (default 100 for rounding to hundredths)

    Returns
    -------
    rounded_value : float
        Rounded value

    """
    return round(n * value) / n
