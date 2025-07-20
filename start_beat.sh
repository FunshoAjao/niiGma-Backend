#!/usr/bin/env bash
echo "⏱️ Starting Celery Beat..."
exec celery -A core beat --loglevel=info
