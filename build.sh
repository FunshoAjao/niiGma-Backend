#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "🔥 BUILD SCRIPT STARTED"

pip install -r requirements.txt
python manage.py migrate

echo "✅ BUILD SCRIPT FINISHED"