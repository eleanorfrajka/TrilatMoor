#!/usr/bin/env python3
"""Test trilateration functionality using synthetic dsG1-like data.

Tests the solve_anchor_position function with known survey data
and validates the results against expected values.
"""

import pytest
from datetime import datetime

import trilatmoor


class TestDsG1Survey:
    """Test class for dsG1 survey data processing."""

    @pytest.fixture
    def dsg1_synthetic_data(self):
        """Synthetic dsG1 survey data to avoid file dependencies."""
        return {
            "loc_name": "dsG1",
            "release_height": 7.0,
            "transducer_depth": 7.7,
            "water_depth_anchor_launch": 690.0,
            "times": [
                datetime(2026, 5, 6, 16, 32, 42),
                datetime(2026, 5, 6, 16, 48, 15),
                datetime(2026, 5, 6, 17, 14, 0),
                datetime(2026, 5, 6, 17, 31, 45),
                datetime(2026, 5, 6, 17, 55, 0),
            ],
            "ranges": [0.0, 936.0, 900.0, 755.0, 850.0],
            "latitudes": [65.59070, 65.58771, 65.59428, 65.58891, 65.58814],
            "longitudes": [-29.45783, -29.45074, -29.45878, -29.46696, -29.47094],
        }

    def test_dsg1_anchor_solution(self, dsg1_synthetic_data):
        """Test that dsG1 anchor position solution produces expected results.
        
        Regression test with 0.5m precision (1e-6 degrees ≈ 0.1m at this latitude).
        """
        solution = trilatmoor.solve_anchor_position(dsg1_synthetic_data)

        # Test anchor position - regression test values from synthetic data
        assert abs(solution["anchor_lat"] - 65.58975839) < 1e-6  # 0.5m precision
        assert abs(solution["anchor_lon"] - (-29.46241839)) < 1e-6  # 0.5m precision

        # Test fallback distance
        assert abs(solution["fallback_distance"] - 236.27946684116705) < 0.01

        # Test residual statistics
        assert abs(solution["max_residual"] - 103.240) < 0.01
        assert abs(solution["rms_residual"] - 77.719) < 0.01

        # Test individual residuals
        expected_residuals = [59.34, 59.966, 103.24, 79.908]
        assert len(solution["residuals"]) == 4  # One zero range filtered out
        for computed, expected in zip(solution["residuals"], expected_residuals):
            assert abs(computed - expected) < 0.01

    def test_dsg1_solution_quality(self, dsg1_synthetic_data):
        """Test that dsG1 solution quality metrics are reasonable."""
        solution = trilatmoor.solve_anchor_position(dsg1_synthetic_data)

        # Position should be in reasonable range for North Atlantic
        assert 60 < solution["anchor_lat"] < 70  # North latitude
        assert -35 < solution["anchor_lon"] < -25  # West longitude

        # Should have valid residuals
        assert len(solution["residuals"]) > 0
        assert all(r >= 0 for r in solution["residuals"])

        # RMS should be positive
        assert solution["rms_residual"] > 0
        assert solution["max_residual"] >= solution["rms_residual"]

    def test_dsg1_coordinate_conversion(self, dsg1_synthetic_data):
        """Test coordinate conversion functionality with dsG1 results."""
        solution = trilatmoor.solve_anchor_position(dsg1_synthetic_data)

        # Test degree/minute conversion
        lat_deg, lat_min, lat_str = trilatmoor.dec2deg(solution["anchor_lat"])
        lon_deg, lon_min, lon_str = trilatmoor.dec2deg(abs(solution["anchor_lon"]))

        # Should be valid degree/minute format
        assert isinstance(lat_deg, int)
        assert isinstance(lon_deg, int)
        assert 0 <= lat_min < 60
        assert 0 <= lon_min < 60
        assert isinstance(lat_str, str)
        assert isinstance(lon_str, str)

    def test_algorithm_core_functionality(self, dsg1_synthetic_data):
        """Test core trilateration algorithm functionality."""
        solution = trilatmoor.solve_anchor_position(dsg1_synthetic_data)

        # Verify we got a valid solution
        assert "anchor_lat" in solution
        assert "anchor_lon" in solution
        assert "fallback_distance" in solution
        assert "residuals" in solution
        assert "rms_residual" in solution
        assert "max_residual" in solution

        # Verify solution is reasonable
        assert solution["anchor_lat"] is not None
        assert solution["anchor_lon"] is not None
        assert len(solution["residuals"]) > 0


if __name__ == "__main__":
    # Allow running as script for debugging
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
