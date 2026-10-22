#!/bin/sh
# Build the database and models on first start, then hand over to the server.
set -e

if [ ! -f var/smartcity.db ] || [ ! -f var/models/anomaly_detector.joblib ]; then
    echo "First start: ingesting data and training models (takes about a minute)"
    smartcity ingest
    smartcity train
fi

exec "$@"
