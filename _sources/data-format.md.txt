# Survey file format

Triangulation survey files are plain text with a metadata header block
followed by a table of timestamped acoustic fixes.

## Example

```
Release_height (m): 6
Transducer_depth (m): 10
Water_depth_anchor_launch (m): 690
Loc_name: dsG1

# Date (yyyy/mm/dd HH:MM:SS) Range Position (Lat / Lon)
2026/05/06 16:32:42 0        65 35.42   -29 -27.47
2026/05/06 16:48:31 936      65 35.2656 -29 -27.0447
2026/05/06 17:15:10 900      65 35.6567 -29 -27.5268
2026/05/06 17:33:20 755      65 35.3346 -29 -28.0173
2026/05/06 17:54:08 849      65 35.2882 -29 -28.2560
```

## Header fields

| Field | Required | Description |
|-------|----------|-------------|
| `Release_height (m)` | yes | Height of acoustic release above the seafloor (m) |
| `Transducer_depth (m)` | yes | Depth of the ship's transducer below the sea surface (m) |
| `Water_depth_anchor_launch (m)` | yes | Water depth at the anchor deployment site (m). Used for slant-to-horizontal range conversion. |
| `Loc_name` | yes | Mooring identifier string; used as the output file base name |
| `Sound_speed (m/s)` | no | Override for the measured sound speed used by the ship's acoustic system |

Header lines are parsed with a colon delimiter and can appear in any order
before the `#` comment line that marks the start of the data section.

## Data lines

Each non-blank, non-comment line after the `#` header contains seven
space-separated fields:

```
YYYY/MM/DD HH:MM:SS  RANGE  LAT_DEG  LAT_MIN  LON_DEG  LON_MIN
```

| Field | Description |
|-------|-------------|
| `YYYY/MM/DD HH:MM:SS` | UTC timestamp of the acoustic fix |
| `RANGE` | Two-way slant range from ship transducer to acoustic release (m). **0 = deployment position** (no acoustic return; see below). |
| `LAT_DEG` | Whole degrees of latitude. Positive = North. |
| `LAT_MIN` | Decimal minutes of latitude, same sign as `LAT_DEG`. |
| `LON_DEG` | Whole degrees of longitude. **Negative = West.** |
| `LON_MIN` | Decimal minutes of longitude, same sign as `LON_DEG`. |

The sign convention for the degrees field carries the hemisphere:
`-29 -27.47` means 29°27.47′W.  Eastern hemisphere longitudes use a positive
degrees field: `15 30.00` = 15°30.00′E.

### Range = 0 — deployment fix

The first data line conventionally has `range = 0`.  It records the ship
position at the moment of anchor deployment (the "anchor drop" fix).  This
line is excluded from the range-based trilateration calculation because there
is no acoustic return; it is used as the deployment position for computing the
*fallback distance* (see [Interpreting results](interpreting-results.md)).

### Minimum valid fixes

At least **three** non-zero range fixes are required for a well-constrained
solution.  The geometry is best when the fixes are spread widely around the
anchor (azimuthal coverage ≥ 180°, ideally ≥ 270°).

## Optional header field: `Sound_speed`

```
Sound_speed (m/s): 1500
```

If present, this value is used as the *measured* sound speed (the speed
assumed by the ship's acoustic ranging system).  The *true* sound speed used
to correct the ranges is set separately via `--sound-speed` on the command
line or the `true_sound_speed` argument in the Python API.
