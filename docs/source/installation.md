# Installation

## Requirements

- Python ≥ 3.9
- `numpy`
- `scipy`
- `matplotlib`
- `xarray` — optional; required for loading NetCDF bathymetry and ship-track files

## From source (recommended)

```bash
git clone https://github.com/eleanorfrajka/TrilatMoor.git
cd TrilatMoor
pip install -e .
```

## PyPI

```bash
pip install trilatmoor
```

## Development install

```bash
git clone https://github.com/eleanorfrajka/TrilatMoor.git
cd TrilatMoor
pip install -r requirements-dev.txt
pip install -e .
```

The development requirements add `pytest`, `black`, `ruff`, and `codespell`.

## Verifying the install

```bash
trilatmoor --help
pytest
```

All four tests should pass within a few seconds.
