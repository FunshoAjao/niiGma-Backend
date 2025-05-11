#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "📦 Starting Celery Worker"
celery -A core worker -l info
