FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SMARTCITY_HOME=/app

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY backend ./backend
RUN pip install .

COPY dataset ./dataset
COPY docker-entrypoint.sh ./
RUN useradd --system --home /app smartcity \
    && mkdir -p var docs/figures \
    && chown -R smartcity /app/var /app/docs \
    && chmod +x docker-entrypoint.sh
USER smartcity

VOLUME ["/app/var"]
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/api/v1/health').status == 200 else 1)"

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "--access-logfile", "-", "smartcity.api:create_app()"]
