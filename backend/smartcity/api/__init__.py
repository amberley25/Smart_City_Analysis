"""Flask application factory."""

from __future__ import annotations

import hmac
import logging
import threading
import time
from collections import defaultdict, deque

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from .. import __version__
from ..config import Settings
from .routes import bp
from .services import ApiError, ModelStore

MAX_BODY_BYTES = 64 * 1024
OPEN_PATHS = {"/", "/api/v1/health"}


class RateLimiter:
    """Sliding-window limiter keyed by client address (per process)."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        if self.per_minute <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            hits = self._hits[client]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                return False
            hits.append(now)
            return True


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings()
    app = Flask(__name__)
    app.config.update(SETTINGS=settings, MODEL_STORE=ModelStore(settings), MAX_CONTENT_LENGTH=MAX_BODY_BYTES)
    app.json.sort_keys = False
    if settings.trust_proxy:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    limiter = RateLimiter(settings.rate_limit_per_minute)
    CORS(app, resources={r"/api/*": {"origins": settings.cors_origins.split(",")}})
    app.register_blueprint(bp)

    @app.before_request
    def guard():
        """Optional API key for the whole API (except health) and a rate limit on compute endpoints."""
        if request.method == "OPTIONS" or request.path in OPEN_PATHS:
            return None
        if settings.api_key:
            supplied = request.headers.get("X-API-Key", "")
            if not hmac.compare_digest(supplied.encode(), settings.api_key.encode()):
                raise ApiError(401, "unauthorized", "A valid X-API-Key header is required")
        if request.method == "POST" and not limiter.allow(request.remote_addr or "unknown"):
            raise ApiError(429, "rate_limited", f"Limit is {settings.rate_limit_per_minute} requests per minute")
        return None

    @app.after_request
    def harden(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

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
