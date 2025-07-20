#!/usr/bin/env bash
# start.sh

# Start Celery in background
celery -A core worker --loglevel=info --concurrency=5 --pool=prefork &

# echo "⏱️ Starting Celery Beat..."
celery -A core beat --loglevel=info &

# Start Django web server
gunicorn core.wsgi:application
