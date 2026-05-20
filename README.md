# trilatmoor

Python package for seafloor mooring trilateration using acoustic ranging.

📘 Repository:
👉 https://github.com/eleanorfrajka/TrilatMoor

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/eleanorfrajka/TrilatMoor.git
cd TrilatMoor
pip install -e .
```

### Command Line Usage

```bash
# Process a single survey (replace with your survey file path)
trilatmoor -c path/to/survey.txt -o survey_results

# Process multiple surveys matching a pattern
trilatmoor --multi path/to/surveys/dsG*.txt -o G_series_results

# With bathymetry data
trilatmoor -c path/to/survey.txt -o results --bathy-dir bathymetry --bathy-source gebco2025
```

### Python API Usage

```python
import trilatmoor

# Process single survey file
triang_data, solution = trilatmoor.process_survey_file("survey.txt")
print(f"Anchor position: {solution['anchor_lat']:.6f}°N, {solution['anchor_lon']:.6f}°W")

# Plot multiple surveys
fig, results = trilatmoor.plot_multiple_surveys(["survey1.txt", "survey2.txt"])
```

---

## 📋 Command Line Interface

The `trilatmoor` command provides a complete CLI for processing survey data:

### Single Survey Processing
```bash
trilatmoor -c SURVEY_FILE -o OUTPUT_NAME [OPTIONS]
trilatmoor --config SURVEY_FILE --output OUTPUT_NAME [OPTIONS]
```

**Generates:**
- `OUTPUT_NAME.png` - Plot with range circles and anchor position
- `OUTPUT_NAME_anchorposition.txt` - Detailed position results

**Example:**
```bash
trilatmoor -c examples/data/FC1_triangulation.txt -o FC1_results
```

### Multi-Survey Processing
```bash
trilatmoor --multi SURVEY_FILE1 SURVEY_FILE2 ... -o OUTPUT_NAME [OPTIONS]
```

**Generates:**
- `OUTPUT_NAME.png` - Multi-survey plot
- `OUTPUT_NAME_summary.txt` - Summary table with all positions

**Example:**
```bash
trilatmoor --multi data/dsG1_survey.txt data/dsG2_survey.txt -o G_series
```

### Options

| Option | Description |
|--------|-------------|
| `--sound-speed SPEED` | Override sound speed (m/s) |
| `--bathy-dir DIR` | Directory containing bathymetry files |
| `--bathy-source SOURCE` | Bathymetry source: `gebco2025`, `gebco2023`, `etopo`, `auto` |
| `--bathy-file FILE` | Specific bathymetry NetCDF file |
| `--ship-track FILE` | Ship track NetCDF file to overlay on plots |
| `--time-interval-hr START END` | Time window around survey (hours). Default: `-12 12` |

### Examples with Options
```bash
# Custom sound speed
trilatmoor -c survey.txt -o results --sound-speed 1480

# With GEBCO bathymetry  
trilatmoor -c survey.txt -o results --bathy-dir bathymetry --bathy-source gebco2025

# With ship track (±12 hours around survey)
trilatmoor -c survey.txt -o results --ship-track ship_data.nc

# Custom time window (±2 hours around survey)
trilatmoor -c survey.txt -o results --ship-track ship_data.nc --time-interval-hr -2 2

# Complete example with all options
trilatmoor -c survey.txt -o results --bathy-file GEBCO_2025.nc --ship-track ship_data.nc --sound-speed 1485
```

---

## 🐍 Python API

### Core Functions

#### Single Survey Processing
```python
import trilatmoor

# Process survey file
triang_data, solution = trilatmoor.process_survey_file("survey.txt", sound_speed=1500)

# Manual processing
params, raw_data = trilatmoor.parse_survey_file("survey.txt") 
solution = trilatmoor.solve_anchor_position(triang_data, true_sound_speed=1500)
```

#### Plotting Functions
```python
# Single survey plot
fig = trilatmoor.plot_trilateration_survey(triang_data, solution)

# Multiple surveys (from files)
fig, results = trilatmoor.plot_multiple_surveys(["survey1.txt", "survey2.txt"])

# Multiple surveys (from computed results)
solutions = [(name1, data1, sol1), (name2, data2, sol2)]
fig = trilatmoor.plot_multiple_solutions(solutions)
```

#### Ship Track Functions
```python
# Load ship track with 1-minute subsampling
ship_track = trilatmoor.load_ship_track_netcdf("ship_data.nc", subsample_minutes=1)

# Load ship track with time filtering
from datetime import datetime, timedelta
survey_time = datetime(2026, 5, 6, 17, 0)  # Survey time
start_time = survey_time - timedelta(hours=12)
end_time = survey_time + timedelta(hours=12)
ship_track = trilatmoor.load_ship_track_netcdf("ship_data.nc", 
                                              time_start=start_time, 
                                              time_end=end_time)

# Plot with ship track
fig = trilatmoor.plot_trilateration_survey(triang_data, solution, ship_track=ship_track)
```

### Complete Example
```python
import trilatmoor
import matplotlib.pyplot as plt

# Process survey
triang_data, solution = trilatmoor.process_survey_file("survey.txt")

# Print results
print(f"Location: {triang_data['loc_name']}")
print(f"Position: {solution['anchor_lat']:.6f}°N, {solution['anchor_lon']:.6f}°W")
print(f"Fallback: {solution['fallback_distance']:.0f}m")
print(f"RMS residual: {solution['rms_residual']:.1f}m")

# Load ship track data
ship_track = trilatmoor.load_ship_track_netcdf("ship_data.nc", subsample_minutes=1)

# Create plot with bathymetry and ship track
fig = trilatmoor.plot_trilateration_survey(
    triang_data, 
    solution, 
    ship_track=ship_track,
    bathymetry="bathymetry/GEBCO_2025.nc"
)
plt.show()
```

### Data Processing Workflow
```python
# Step 1: Parse survey file
params, raw_data = trilatmoor.parse_survey_file("survey.txt")

# Step 2: Process into trilateration format  
triang_data, solution = trilatmoor.process_survey_file("survey.txt")

# Step 3: Plot results
fig = trilatmoor.plot_trilateration_survey(triang_data, solution)

# Step 4: Multi-survey analysis
all_results = []
for file in survey_files:
    data, sol = trilatmoor.process_survey_file(file)
    all_results.append((data['loc_name'], data, sol))

fig = trilatmoor.plot_multiple_solutions(all_results)
```

---

## 📁 Project Structure

```
TrilatMoor/
├── examples/                   # Usage examples and sample data
│   ├── data/                   # Example survey files
│   ├── multi_survey_example.py # API examples
│   └── process_ds_surveys.py   # Processing script
├── scripts/                    # Dataset-specific processing scripts  
├── trilatmoor/                 # Main Python package
│   ├── __init__.py             # Package interface
│   ├── cli.py                  # Command-line interface
│   ├── plotting.py             # Plotting functions
│   ├── read_dship.py           # Data reading utilities
│   ├── solve_anchor.py         # Core trilateration algorithms
│   └── utilities.py            # Utility functions
├── tests/                      # Test suite
├── LICENSE                     # MIT license
├── README.md                   # This file
├── pyproject.toml              # Package configuration
└── requirements.txt            # Dependencies
```

---

## 🔧 Development Setup

Install in development mode:

```bash
git clone https://github.com/eleanorfrajka/TrilatMoor.git
cd TrilatMoor
pip install -r requirements-dev.txt
pip install -e .
```

Run tests:

```bash
pytest
```

---

## 📊 Survey Data Format

Survey data files should contain:

```
Release_height (m): 15
Transducer_depth (m): 10
Water_depth_anchor_launch (m): 880
Loc_name: FC1
Sound_speed (m/s): 1500

# Date (yyyy/mm/dd HH:MM:SS) Range Position (Lat / Lon)
2023/10/09 20:39:38 0      48 32.747 -44 -59.991
2023/10/09 20:51:07 1434   48 33.298 -44 -59.956
2023/10/09 20:00:00 2971   48 25.000 -45 -00.287
```

**Format:**
- Header with survey parameters
- Data lines: `date time range latitude_deg latitude_min longitude_deg longitude_min`
- Range = 0 indicates deployment position
- Coordinates in degrees and decimal minutes

---

## 🌊 Bathymetry Support

The package supports bathymetry visualization from NetCDF files:

**Supported sources:**
- GEBCO 2025/2023
- ETOPO datasets  
- Custom NetCDF files

**CLI usage:**
```bash
trilatmoor -c survey.txt -o results --bathy-dir bathymetry --bathy-source gebco2025
```

**API usage:**
```python
fig = trilatmoor.plot_trilateration_survey(
    triang_data, solution, 
    bathymetry="bathymetry/GEBCO_2025.nc"
)
```

---

## 🎯 Algorithm

The package implements acoustic trilateration using algorithms originally developed in MATLAB:

1. **Range correction**: Converts slant ranges to horizontal distances
2. **Least squares optimization**: Solves for anchor position
3. **Quality metrics**: RMS residuals and fallback distance
4. **Fallback positioning**: Uses deployment position when trilateration fails

**Core equation solved:**
For each survey position (xi, yi) with corrected horizontal range ri, find anchor position (x, y) that minimizes:

```
Σ [(√((x-xi)² + (y-yi)²) - ri)²]
```

The Python implementation maintains compatibility with the original MATLAB workflows while providing modern API and CLI interfaces.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---

## 🎓 Citation

If you use this package in your research, please cite:

```bibtex
@software{trilatmoor,
  title = {trilatmoor: Python package for seafloor mooring trilateration},
  author = {Frajka-Williams, Eleanor},
  url = {https://github.com/eleanorfrajka/TrilatMoor},
  year = {2024},
  note = {Python implementation of MATLAB algorithms developed for the RAPID 26°N array}
}
```

The Python package is based on original MATLAB code for mooring trilateration developed for RAPID operations, where the RAPID 26°N array uses moored and auxiliary datasets (Argo, satellite, Florida Cable, hydrographic, reanalysis wind) to make continuous estimates of the Atlantic meridional overturning circulation. 

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

