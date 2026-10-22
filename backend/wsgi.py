"""Production entry point: `gunicorn --chdir backend wsgi:app`."""

from smartcity.api import create_app

app = create_app()
