#!/usr/bin/env bash
echo "🚧 Starting Celery Worker..."
exec celery -A core worker --loglevel=info --concurrency=4 --pool=prefork
