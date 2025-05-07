#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "🔥 BUILD SCRIPT STARTED"

pip install -r requirements.txt
python manage.py migrate
celery -A core worker -l info

echo "✅ BUILD SCRIPT FINISHED"