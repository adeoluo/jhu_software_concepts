"""Run the personal website on the required course port.

This is the file the assignment requires users to run with ``python run.py``.
"""

# The application factory assembles the Flask site.
from app import create_app


# This module-level application instance supports Flask tools and tests.
app = create_app()


if __name__ == "__main__":
    # The assignment requires port 8080 and access through localhost.
    app.run(host="0.0.0.0", port=8080, debug=True)
