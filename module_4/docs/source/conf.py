"""Sphinx configuration for the Grad Cafe analysis service (Module 4)."""

import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC))

# models.py builds a (lazy, unconnected) engine at import time; autodoc never queries it.
os.environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/docs_placeholder")

project = "Grad Cafe Analytics"
author = "Adeolu Ogunnoiki"
release = "4.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autodoc_default_options = {"members": True, "undoc-members": True, "member-order": "bysource"}
autodoc_typehints = "description"

templates_path = []
exclude_patterns = []

html_theme = "sphinx_rtd_theme"
html_static_path = []
