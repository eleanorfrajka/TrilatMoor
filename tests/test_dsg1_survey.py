#!/usr/bin/env python3
"""Test trilateration functionality using dsG1_survey.txt data.

Tests the solve_anchor_position function with known dsG1 survey data
and validates the results against expected values.
"""

import pytest
import numpy as np
from pathlib import Path

import trilatmoor


class TestDsG1Survey:
    """Test class for dsG1 survey data processing."""

    @pytest.fixture
    def dsg1_data_file(self):
        """Path to dsG1 survey test data."""
        return Path("data/dsG1_survey.txt")

    @pytest.fixture
    def dsg1_expected_results(self):
        """Expected results for dsG1 survey - hard-coded reference values."""
        return {
            "anchor_lat": 65.58977474,
            "anchor_lon": -29.46241174,
            "fallback_distance": 220.20489380718294,
            "max_residual": 87.419,
            "rms_residual": 65.318,
            "expected_residuals": [49.54, 50.116, 87.419, 66.767],
            "num_residuals": 4,  # One zero range is filtered out
        }

    @pytest.fixture
    def dsg1_expected_data(self):
        """Expected survey data for dsG1."""
        return {
            "loc_name": "dsG1",
            "release_height": 7.0,
            "transducer_depth": 7.7,
            "water_depth_anchor_launch": 690.0,
            "ranges": [0.0, 936.0, 900.0, 755.0, 850.0],
            "num_ranges": 5,
        }

    def test_dsg1_data_parsing(self, dsg1_data_file):
        """Test that dsG1 survey file is parsed correctly."""
        triang_data = trilatmoor.parse_triangulation_file(str(dsg1_data_file))
        
        # Hard-coded expected values from dsG1_survey.txt
        assert triang_data["loc_name"] == "dsG1"
        assert triang_data["release_height"] == 7.0
        assert triang_data["transducer_depth"] == 7.7
        assert triang_data["water_depth_anchor_launch"] == 690.0
        assert triang_data["ranges"] == [0.0, 936.0, 900.0, 755.0, 850.0]
        assert len(triang_data["ranges"]) == 5

    def test_dsg1_anchor_solution(self, dsg1_data_file):
        """Test that dsG1 anchor position solution matches hard-coded expected results."""
        triang_data, solution = trilatmoor.process_survey_file(str(dsg1_data_file))
        
        # Test anchor position - exact values from dsG1_survey.txt
        assert abs(solution["anchor_lat"] - 65.58977474) < 1e-6
        assert abs(solution["anchor_lon"] - (-29.46241174)) < 1e-6
        
        # Test fallback distance
        assert abs(solution["fallback_distance"] - 220.20489380718294) < 0.01
        
        # Test residual statistics  
        assert abs(solution["max_residual"] - 87.419) < 0.01
        assert abs(solution["rms_residual"] - 65.318) < 0.01
        
        # Test individual residuals
        expected_residuals = [49.54, 50.116, 87.419, 66.767]
        assert len(solution["residuals"]) == 4  # One zero range filtered out
        for computed, expected in zip(solution["residuals"], expected_residuals):
            assert abs(computed - expected) < 0.01

    def test_dsg1_solution_quality(self, dsg1_data_file):
        """Test that dsG1 solution quality metrics are reasonable."""
        triang_data, solution = trilatmoor.process_survey_file(str(dsg1_data_file))
        
        # Position should be in reasonable range for North Atlantic
        assert 60 < solution["anchor_lat"] < 70  # North latitude
        assert -35 < solution["anchor_lon"] < -25  # West longitude
        
        # Should have valid residuals
        assert len(solution["residuals"]) > 0
        assert all(r >= 0 for r in solution["residuals"])
        
        # RMS should be positive
        assert solution["rms_residual"] > 0
        assert solution["max_residual"] >= solution["rms_residual"]

    def test_dsg1_coordinate_conversion(self, dsg1_data_file):
        """Test coordinate conversion functionality with dsG1 results."""
        triang_data, solution = trilatmoor.process_survey_file(str(dsg1_data_file))
        
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

    def test_dsg1_end_to_end(self, dsg1_data_file):
        """End-to-end test of dsG1 processing workflow."""
        # Parse file
        triang_data = trilatmoor.parse_triangulation_file(str(dsg1_data_file))
        
        # Solve anchor position
        solution = trilatmoor.solve_anchor_position(triang_data)
        
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