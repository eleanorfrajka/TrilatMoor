"""Sphinx configuration for trilatmoor documentation."""

import sys
import os

# Make trilatmoor importable from the repo root
sys.path.insert(0, os.path.abspath("../.."))

import datetime

year = datetime.datetime.now(tz=datetime.timezone.utc).date().year

project = "trilatmoor"
author = "Eleanor Frajka-Williams"
copyright = f"{year}, {author}"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",
    "myst_parser",
    "nbsphinx",
]

nbsphinx_execute = "never"

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "special-members": "__init__",
}

napoleon_google_docstring = False
napoleon_numpy_docstring = True

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_image",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]
source_suffix = [".rst", ".md"]

html_theme = "sphinx_rtd_theme"
html_logo = "_static/trilatmoor_icon.png"
html_static_path = ["_static"]
html_css_files = ["css/custom.css"]

pygments_style = "sphinx"
nitpick_ignore = []
