#!/usr/bin/env bash
# start.sh

# Start Celery in background
celery -A core worker -l info &

# echo "⏱️ Starting Celery Beat..."
celery -A core beat --loglevel=info &

# Start Django web server
gunicorn core.wsgi:application
