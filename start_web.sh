#!/usr/bin/env bash
echo "🚀 Starting Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000
