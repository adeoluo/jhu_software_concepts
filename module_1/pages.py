"""Routes and editable content for the personal developer website.

The dictionary below personalizes the homepage in one place.
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


@pages_blueprint.route("/")
def home():
    """Render the biography homepage at the root URL, ``/``."""
    return render_template("home.html", profile=PROFILE)
