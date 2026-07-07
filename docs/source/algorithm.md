# Algorithm

trilatmoor determines the seafloor anchor position by least-squares acoustic
trilateration.  The pipeline has three stages: range correction, coordinate
conversion, and optimisation.

## 1. Range corrections

### Sound speed

The ship's acoustic system assumes a fixed sound speed *c̃* (default 1507 m/s).
If the true in-situ speed *c* differs, every measured slant range *s̃ᵢ* must be
rescaled:

$$s_i = \tilde{s}_i \cdot \frac{c}{\tilde{c}}$$

The defaults `true_sound_speed = 1503` m/s and `measured_sound_speed = 1507`
m/s are representative values for the RAPID 26°N array and should be replaced
with CTD-derived estimates when available.

### Slant-to-horizontal range

The acoustic signal travels a slant path from the ship's transducer to the
seafloor release.  The corrected slant range *sᵢ* is converted to a horizontal
range *rᵢ* using the water depth:

$$r_i = \sqrt{s_i^2 - d_v^2}$$

where the vertical separation is:

$$d_v = H - h_r - h_t$$

- *H* — water depth at anchor launch (m), from the survey file header
- *hᵣ* — release height above the seafloor (m)
- *hₜ* — transducer depth below the sea surface (m)

## 2. Geodetic distance

All distances between ship fixes and the candidate anchor position are
computed with **Vincenty's inverse formula** on the WGS-84 ellipsoid.  This
gives sub-metre accuracy at any latitude, including high latitudes (65°N for
the RAPID array) where the Haversine approximation accumulates noticeable
error.

## 3. Least-squares trilateration

Given *n* ship positions (φᵢ, λᵢ) and corrected horizontal ranges *rᵢ*, find
the anchor position (φ, λ) that minimises the sum of squared residuals:

$$\min_{\phi,\,\lambda} \sum_{i=1}^{n} \bigl(d_i(\phi,\lambda) - r_i\bigr)^2$$

where *dᵢ* is the Vincenty distance from the candidate anchor to the *i*-th
ship position.

The algorithm linearises this problem around an initial estimate (the
centroid of all ship positions):

1. Convert each ship fix to Cartesian coordinates *(xᵢ, yᵢ)* relative to the
   initial estimate using the Vincenty forward formula.
2. Build the overdetermined linear system from pairwise differences of the
   range equations, eliminating the quadratic terms.
3. Solve with `numpy.linalg.lstsq` to obtain a Cartesian correction
   *(Δx, Δy)*.
4. Apply the correction back to geographic coordinates with the Vincenty
   forward formula.

## 4. Quality metrics

| Metric | Definition |
|--------|-----------|
| Residual *εᵢ* | \|*dᵢ*(anchor) − *rᵢ*\| for each fix (m) |
| Max residual | max(*εᵢ*) — worst single fix |
| RMS residual | √(mean(*εᵢ²*)) — overall fit quality |
| Fallback distance | Vincenty distance from deployment position to solved anchor (m) |

See [Interpreting results](interpreting-results.md) for guidance on what
these numbers mean in practice.

## 5. Survey geometry

A well-conditioned survey requires:
- At least **three** non-zero range fixes.
- **Broad azimuthal coverage** — fixes spread over ≥ 180° around the anchor.
  Coverage ≥ 270° is strongly preferred; a straight steaming run produces a
  rank-deficient geometry with poorly constrained cross-track position.
- Ranges approximately matching the water depth (within a factor of ~3),
  so the slant-to-horizontal correction is accurate.
