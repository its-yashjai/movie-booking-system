#!/bin/sh
set -e

echo "🗄️  Running migrations..."
python manage.py migrate --noinput

echo "🗃️  Creating cache table..."
python manage.py createcachetable
echo "✅ Cache table ready."

echo "🚀 Starting gunicorn..."
exec gunicorn moviebooking.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout 120 \
    --workers 3
