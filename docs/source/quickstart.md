# Quickstart

## CLI — single survey

The most common workflow: process one triangulation file, write a plot and a
position text file.

```bash
trilatmoor -c examples/data/dsG1_triangulation.txt -o results/ --output dsG1
```

This creates:

- `results/dsG1.png` — map with range circles, anchor position marker, and
  (optionally) bathymetry isobaths
- `results/dsG1_anchorposition.txt` — anchor position, quality metrics, and
  survey parameters

### Adding bathymetry

Point to a directory containing the GEBCO or ETOPO NetCDF file:

```bash
trilatmoor -c survey.txt -o results/ --output dsG1 \
    --bathy-dir /data/bathymetry --bathy-source gebco2025
```

### Adding a ship track

```bash
trilatmoor -c survey.txt -o results/ --output dsG1 \
    --ship-track /data/merian_track.nc \
    --time-interval-hr -12 12
```

The `--time-interval-hr` window is relative to the survey timestamps in the
survey file; ±12 h is the default.

### All options

| Flag | Default | Description |
|------|---------|-------------|
| `-c / --config` | required | Survey file path |
| `-o / --output-directory` | `.` | Directory for output files |
| `--output` | survey `Loc_name` | Base filename (no extension) |
| `--sound-speed` | — | True sound speed in m/s (overrides file value) |
| `--bathy-dir` | — | Directory containing bathymetry NetCDF files |
| `--bathy-source` | `gebco2025` | `gebco2025`, `gebco2023`, `gebco`, `etopo`, `auto` |
| `--ship-track` | — | Ship track NetCDF file |
| `--time-interval-hr` | `-12 12` | Hours around survey for ship track |
| `--figsize` | matplotlib default | Figure size in inches, e.g. `--figsize 10 8` |
| `--no-title` | false | Suppress the figure title |
| `--no-legend` | false | Suppress the legend |
| `--format` | `all` | `all`, `png`, `grid` (`--multi` only), or `txt` |

## CLI — multiple surveys

```bash
trilatmoor --multi data/dsG1.txt data/dsG2.txt data/dsG3.txt \
    -o results/ --output G_series
```

Generates a single overview map showing all anchor positions and a summary
table (`G_series_summary.txt`).

---

## Python API

### Parse and solve

```python
import trilatmoor

# One-step convenience function
triang_data, solution = trilatmoor.process_survey_file("survey.txt")

print(f"Anchor: {solution['anchor_lat']:.6f}°N, {solution['anchor_lon']:.6f}°W")
print(f"RMS residual: {solution['rms_residual']:.1f} m")
print(f"Fallback distance: {solution['fallback_distance']:.0f} m")
```

### Plot

```python
import matplotlib.pyplot as plt

fig = trilatmoor.plot_trilateration_survey(
    triang_data,
    solution,
    bathymetry="/data/GEBCO_2025.nc",   # optional
    figsize=(8, 6),
)
plt.savefig("survey.png", dpi=300, bbox_inches="tight")
plt.close(fig)
```

### GEBCO depth at the anchor position

```python
depth = trilatmoor.query_depth_at_position(
    "/data/GEBCO_2025.nc",
    solution["anchor_lat"],
    solution["anchor_lon"],
)
print(f"GEBCO depth at anchor: {depth:.0f} m")
```

### Multi-survey overview

```python
files = ["data/dsG1.txt", "data/dsG2.txt", "data/dsG3.txt"]
fig, results = trilatmoor.plot_multiple_surveys(files)
```

### Lower-level pipeline

```python
from trilatmoor import parse_triangulation_file, solve_anchor_position

triang_data = parse_triangulation_file("survey.txt")
solution     = solve_anchor_position(triang_data, true_sound_speed=1500)
```
