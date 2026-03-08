#!/usr/bin/env bash
# Render build script - runs on every deploy
set -e  # Exit on any error

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "📂 Collecting static files..."
python manage.py collectstatic --noinput

echo "🗄️  Running database migrations..."
python manage.py migrate --noinput

echo "🗃️  Creating cache table (idempotent - safe to run every deploy)..."
python manage.py createcachetable || echo "⚠️  Cache table already exists, skipping."

echo "✅ Build complete!"
