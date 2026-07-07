# Interpreting results

## Output files

### `_anchorposition.txt`

```
Trilatmoor Anchor Position Results
=====================================

Location: dsG1

Final Anchor Position:
  Decimal degrees: 65.589856°N, 29.462519°W
  Degrees/minutes: 65°35.39'N, 29°27.75'W

Survey Quality:
  Fallback distance: 222 m
  Max residual error: 103.9 m
  RMS residual error: 77.3 m

  Overall quality: Good

Individual Fix Residuals:
  Fix 1: 103.9 m
  Fix 2:  14.4 m
  Fix 3:  97.7 m
  Fix 4:  23.9 m

Survey Parameters:
  Water depth at launch:  690 m
  GEBCO depth at anchor:  695 m
  Release height:           6 m
  Transducer depth:        10 m
```

## RMS residual

The RMS residual measures how consistently the range circles intersect at the
solved anchor position.

| RMS | Assessment |
|-----|------------|
| < 10 m | Excellent — range circles meet almost perfectly |
| 10–50 m | Good — typical for a well-executed survey |
| 50–100 m | Fair — worth inspecting individual residuals |
| > 100 m | Poor — recheck sound speed, water depth, and fix geometry |

Large residuals on individual fixes (visible in the fix-by-fix table) often
point to a position error in that GPS fix rather than a problem with the
acoustics.

## Fallback distance

The fallback distance is the great-circle distance (m) from the **anchor
deployment position** (range = 0 in the survey file) to the **solved anchor
position**.

It is a sanity check, not an error metric.  For a typical slack-moored
deployment the anchor should land within 0–500 m of the deployment position
depending on depth and line scope.  Values much larger than the water depth
may indicate a data entry problem or a ship track error in the deployment fix.

## Launch depth vs GEBCO depth

When a bathymetry file is provided:

- **Launch depth** (`Water_depth_anchor_launch`) — the depth recorded at the
  moment of deployment, usually from the ship's echo sounder or a pre-survey
  CTD.  This value is used to compute the slant-to-horizontal range correction
  and therefore affects the trilaterated position.

- **GEBCO depth at anchor** — the nearest-neighbour depth from the GEBCO grid
  at the *solved* anchor position.  This is a post-hoc check; agreement within
  ~50 m is reassuring.  A large discrepancy suggests either a coarse GEBCO grid
  cell or that the launch depth value in the survey file is inaccurate.

## When to distrust results

- RMS > 100 m with fixes spread across multiple azimuths — check for a
  mis-entered GPS fix (drop the outlier and re-run).
- RMS > 100 m with fixes from a straight steaming run — geometry is
  ill-conditioned; azimuthal coverage is insufficient.
- Fallback distance ≫ water depth — suspect the deployment fix (range = 0
  line in the survey file).
- GEBCO depth and launch depth differ by > 10 % — verify the launch depth
  header value.

## Sound speed sensitivity

A 1 m/s error in sound speed produces a fractional range error of ≈ 0.07 %
(1/1503 × 100 %).  For a 1 000 m range this is ≈ 0.7 m.  At typical RAPID
survey ranges (500–3 000 m), a 5 m/s sound speed error translates to a
position error of roughly 2–10 m — well below the typical RMS residual.
