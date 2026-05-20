# trilaterate_moor

Python package for seafloor mooring trilateration using acoustic ranging.

📘 Repository:
👉 https://github.com/eleanorfrajka/trilaterate_moor

---

## Project structure

trilaterate_moor/
├── data/                       # Sample data files
├── figs/                       # Generated figures
├── matlab/                     # MATLAB code and utilities
├── notebooks/                  # Example notebooks
├── tests/                      # Test suite (empty currently)
├── trilaterate_moor/           # Main Python package
│   ├── __init__.py
│   ├── plotting.py            # Plotting functions
│   ├── read_dship.py          # Data reading utilities
│   ├── solve_anchor.py        # Core trilateration algorithms
│   └── utilities.py           # General utility functions
├── CITATION.cff               # Citation information
├── CONTRIBUTING.md            # Contribution guidelines
├── LICENSE                    # MIT license
├── README.md
├── pyproject.toml             # Modern packaging config
├── requirements.txt           # Package requirements
├── requirements-dev.txt       # Development requirements
├── example.py                 # Basic usage example
├── example_with_ship_track.py # Advanced example with ship tracks
└── various processing scripts # Data processing utilities


---

## 🔧 Quickstart

Install in development mode:

```bash
git clone https://github.com/eleanorfrajka/trilaterate_moor.git
cd trilaterate_moor
pip install -r requirements-dev.txt
pip install -e .
```

To run tests:

```bash
pytest
```

To build the documentation locally:

```bash
cd docs
make html
```

