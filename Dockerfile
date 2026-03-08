# Use Python 3.11 slim image (better psycopg2 compatibility)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create staticfiles directory
RUN mkdir -p staticfiles media

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Run migrations on startup, then start server
# Note: Superuser creation and admin verification only happen if needed (via management commands with safety checks)
CMD ["sh", "-c", "python manage.py migrate && gunicorn moviebooking.wsgi:application --bind 0.0.0.0:${PORT:-8000} --timeout 120 --workers 3"]
