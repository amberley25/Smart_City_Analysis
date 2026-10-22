"""Flask application factory."""

from __future__ import annotations

import logging

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from .. import __version__
from ..config import Settings
from .routes import bp
from .services import ApiError, ModelStore


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings()
    app = Flask(__name__)
    app.config.update(SETTINGS=settings, MODEL_STORE=ModelStore(settings), JSON_SORT_KEYS=False)
    app.json.sort_keys = False
    CORS(app, resources={r"/api/*": {"origins": settings.cors_origins.split(",")}})
    app.register_blueprint(bp)

    @app.get("/")
    def index():
        return jsonify({"name": "Smart City Analytics API", "version": __version__, "docs": "/api/v1/health"})

    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        return jsonify({"error": {"code": err.code, "message": err.message}}), err.status

    @app.errorhandler(HTTPException)
    def handle_http_error(err: HTTPException):
        return jsonify({"error": {"code": err.name.lower().replace(" ", "_"), "message": err.description}}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        app.logger.exception("Unhandled error")
        return jsonify({"error": {"code": "internal_error", "message": "Unexpected server error"}}), 500

    if not app.debug:
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
    return app
