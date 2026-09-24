import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

project = "Grad Café Analytics"
author = "JHU Software Concepts"
release = "1.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "alabaster"
html_static_path = ["_static"]

nitpick_ignore = [
    ("py:obj", "orm_declarative_metadata"),
]

master_doc = "index"
