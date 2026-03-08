#!/bin/sh
set -e

echo "🗄️  Running migrations..."
python manage.py migrate --noinput

echo "🗃️  Creating cache table..."
python manage.py createcachetable
echo "✅ Cache table ready."

# Auto-create admin if DJANGO_ADMIN_USERNAME + DJANGO_ADMIN_PASSWORD env vars are set
if [ -n "$DJANGO_ADMIN_USERNAME" ] && [ -n "$DJANGO_ADMIN_PASSWORD" ]; then
    echo "👤 Creating/resetting admin user: $DJANGO_ADMIN_USERNAME"
    python manage.py create_admin \
        --username "$DJANGO_ADMIN_USERNAME" \
        --email "${DJANGO_ADMIN_EMAIL:-admin@moviebooking.com}" \
        --password "$DJANGO_ADMIN_PASSWORD" \
        --reset
    echo "✅ Admin user ready."
fi

echo "🚀 Starting gunicorn..."
exec gunicorn moviebooking.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout 120 \
    --workers 3
