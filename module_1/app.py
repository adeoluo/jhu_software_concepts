"""Flask application factory for the Module 1 website.

An application factory keeps setup in one function, making the app easy to
start, import in tests, and expand as later modules add features.
"""

# Flask provides the web application object.
from flask import Flask
# The blueprint contains the routes for all website pages.
from pages import pages_blueprint


def create_app() -> Flask:
    """Create, configure, and return the Flask application instance."""
    # Flask uses this module location to find the templates and static folders.
    app = Flask(__name__)
    # This registers the site's page routes.
    app.register_blueprint(pages_blueprint)
    return app
