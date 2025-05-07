#!/bin/bash
set -e

echo "🔥 BUILD SCRIPT STARTED"

pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

echo "✅ BUILD SCRIPT FINISHED"
