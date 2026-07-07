# Bathymetry

Bathymetry is **optional** — trilatmoor runs without it.  When provided, it
adds isobath contours to the trilateration plot and reports the GEBCO depth at
the solved anchor position.

## Supported datasets

Any NetCDF file that stores a 2-D depth or elevation field on a regular
lat/lon grid is supported.  The code auto-detects the following variable names:

| Role | Accepted names |
|------|---------------|
| Longitude | `lon`, `longitude`, `x`, `nav_lon` |
| Latitude | `lat`, `latitude`, `y`, `nav_lat` |
| Depth / elevation | `depth`, `elevation`, `z`, `bathymetry`, `topo` |

The loader signs depths as **positive downward** (ocean floor positive).  If
the file stores negative elevations (the GEBCO convention, where ocean is
negative), the signs are flipped automatically.

Coordinate axes may be in ascending or descending order — both are handled.

**Recommended source:** [GEBCO 2025](https://www.gebco.net/) global
15-arcsecond bathymetric grid (~2 GB NetCDF file).

## CLI usage

Point to a directory containing the NetCDF file and specify the source name:

```bash
trilatmoor -c survey.txt -o results/ --output dsG1 \
    --bathy-dir /data/bathymetry --bathy-source gebco2025
```

Recognised `--bathy-source` values and the filename patterns they match:

| Source | Filename patterns |
|--------|------------------|
| `gebco2025` | `GEBCO_2025.nc`, `gebco_2025.nc`, `GEBCO2025.nc` |
| `gebco2023` | `GEBCO_2023.nc`, `gebco_2023.nc`, `GEBCO2023.nc` |
| `gebco` | `GEBCO*.nc`, `gebco*.nc` |
| `etopo` | `ETOPO*.nc`, `etopo*.nc` |
| `auto` | first `*.nc` file found |

## Python API usage

Pass the path string directly to `plot_trilateration_survey`; the function
loads only the regional subset needed for the plot:

```python
fig = trilatmoor.plot_trilateration_survey(
    triang_data,
    solution,
    bathymetry="/data/GEBCO_2025.nc",
)
```

Pre-load the regional subset (useful when plotting many surveys from the same
area):

```python
bathy = trilatmoor.load_bathymetry_netcdf(
    "/data/GEBCO_2025.nc",
    lon_bounds=(-30, -28),
    lat_bounds=(65, 67),
)
fig = trilatmoor.plot_trilateration_survey(triang_data, solution, bathymetry=bathy)
```

Query depth at a single point:

```python
depth = trilatmoor.query_depth_at_position(
    "/data/GEBCO_2025.nc",
    lat=65.590,
    lon=-29.462,
)
```

## Memory and performance

Loading a global GEBCO file into memory (~2 GB) is unnecessary and slow.
When a path string is passed, `plot_trilateration_survey` automatically loads
only the regional subset around the survey area (0.5° margin) using xarray
lazy evaluation, so only the relevant data pages are read from disk.

`query_depth_at_position` is even more efficient: it reads only the coordinate
arrays and a single grid cell.

## Isobath levels

Contour levels are chosen automatically based on the anchor water depth.
The code uses coarse 200 m spacing for the full loaded region, supplemented by
finer 50 m spacing within ±200 m of the anchor depth — ensuring that the
nearest isobath to the deployment site is always included in the plot.
