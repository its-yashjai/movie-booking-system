#!/bin/bash

# CapRover Deployment Script for Django Movie Booking System
# This script handles complete deployment and admin user creation

echo "=================================================="
echo "  Django Movie Booking - CapRover Deployment"
echo "=================================================="
echo ""

# Get CapRover details
read -p "Enter your CapRover domain (e.g., captain.yourdomain.com): " CAPROVER_URL
read -p "Enter your CapRover app name: " APP_NAME
read -s -p "Enter your CapRover password: " CAPROVER_PASSWORD
echo ""
echo ""

# Get admin credentials
echo "🔐 Admin User Setup"
read -p "Enter admin username (default: admin): " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}

read -p "Enter admin email (default: admin@example.com): " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@example.com}

read -s -p "Enter admin password (default: admin123): " ADMIN_PASS
echo ""
ADMIN_PASS=${ADMIN_PASS:-admin123}

echo ""
echo "=================================================="
echo "  Creating captain-definition file..."
echo "=================================================="

# Create captain-definition file
cat > captain-definition <<EOF
{
  "schemaVersion": 2,
  "dockerfilePath": "./Dockerfile"
}
EOF

echo "✅ captain-definition created"
echo ""

echo "=================================================="
echo "  Deploying to CapRover..."
echo "=================================================="

# Initialize git if not already
if [ ! -d .git ]; then
    git init
    git add .
    git commit -m "Initial commit for CapRover"
fi

# Deploy to CapRover
echo "$CAPROVER_PASSWORD" | caprover deploy -h "$CAPROVER_URL" -p "$CAPROVER_PASSWORD" -b main -a "$APP_NAME"

echo ""
echo "=================================================="
echo "  Running post-deployment commands..."
echo "=================================================="

# Run migrations
caprover run -h "$CAPROVER_URL" -p "$CAPROVER_PASSWORD" -a "$APP_NAME" -- python manage.py migrate

# Create admin user
caprover run -h "$CAPROVER_URL" -p "$CAPROVER_PASSWORD" -a "$APP_NAME" -- python manage.py create_admin --username "$ADMIN_USER" --email "$ADMIN_EMAIL" --password "$ADMIN_PASS" --reset

# Collect static files
caprover run -h "$CAPROVER_URL" -p "$CAPROVER_PASSWORD" -a "$APP_NAME" -- python manage.py collectstatic --noinput

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=================================================="
echo ""
echo "Admin Credentials:"
echo "  Username: $ADMIN_USER"
echo "  Password: ********"
echo ""
echo "Access your app at:"
echo "  https://$APP_NAME.$CAPROVER_URL"
echo ""
echo "Admin panels:"
echo "  Django Admin:  /admin/"
echo "  Custom Admin:  /custom-admin/"
echo ""
echo "=================================================="
echo ""
echo "📝 Next steps:"
echo "1. Go to CapRover dashboard"
echo "2. Enable HTTPS for your app"
echo "3. Add PostgreSQL database if needed"
echo "4. Set environment variables in CapRover"
echo ""
