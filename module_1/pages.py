"""Routes and editable content for the personal developer website.

The dictionaries below personalize every webpage in one place.
"""

# Blueprint groups the page routes; render_template produces HTML responses.
from flask import Blueprint, render_template


# Routes for the site's pages.
pages_blueprint = Blueprint("pages", __name__)

# Shared profile information for website templates.
PROFILE = {
    "name": "Adeolu Ogunnoiki",
    "position": "Data Scientist and Johns Hopkins Student",
    "bio": (
        "I enjoy learning, building impactful software, "
        "and playing football."
    ),
}

# Module 1 project information for the Projects page.
MODULE_ONE_PROJECT = {
    "title": "Module 1: Website",
    "details": (
        "A website created with Flask that introduces me, "
        "provides professional contact links, and will grow to "
        "showcase my Python projects during the course."
    ),
    "github_url": (
        "https://github.com/adeoluo/jhu_software_concepts/tree/main/module_1"
    ),
}


@pages_blueprint.route("/")
def home():
    """Render the biography homepage at the root URL, ``/``."""
    return render_template("home.html", profile=PROFILE, active_page="home")


@pages_blueprint.route("/projects")
def projects():
    """Render the project portfolio page at ``/projects``."""
    return render_template(
        "projects.html",
        profile=PROFILE,
        project=MODULE_ONE_PROJECT,
        active_page="projects",
    )
