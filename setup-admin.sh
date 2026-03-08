#!/bin/bash

###############################################################################
# Setup Production Admin Account on Render
#
# This script creates a superuser account for production environment
# Run this AFTER your app is deployed and running on Render
#
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@moviebooking.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
RESET_ADMIN="${RESET_ADMIN:-false}"

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

show_usage() {
    echo ""
    echo -e "${BLUE}Movie Booking System - Production Admin Setup${NC}"
    echo ""
    echo "Usage: ./setup-admin.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --username USERNAME     Admin username (default: admin)"
    echo "  --email EMAIL          Admin email (default: admin@moviebooking.com)"
    echo "  --password PASSWORD    Admin password (default: generates random)"
    echo "  --reset                Reset existing admin if found"
    echo ""
    echo "Examples:"
    echo "  # Create default admin with random password:"
    echo "  ./setup-admin.sh"
    echo ""
    echo "  # Create with custom credentials:"
    echo "  ./setup-admin.sh --username admin --email admin@yourdomain.com --password YourSecurePassword123!"
    echo ""
    echo "  # Reset existing admin:"
    echo "  ./setup-admin.sh --reset"
    echo ""
}

main() {
    log_info "Starting admin setup..."
    echo ""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --username)
                ADMIN_USERNAME="$2"
                shift 2
                ;;
            --email)
                ADMIN_EMAIL="$2"
                shift 2
                ;;
            --password)
                ADMIN_PASSWORD="$2"
                shift 2
                ;;
            --reset)
                RESET_ADMIN=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Validate inputs
    if [[ -z "$ADMIN_USERNAME" ]]; then
        log_error "Username cannot be empty"
        exit 1
    fi

    if [[ -z "$ADMIN_EMAIL" ]]; then
        log_error "Email cannot be empty"
        exit 1
    fi

    # Generate password if not provided
    if [[ -z "$ADMIN_PASSWORD" ]]; then
        ADMIN_PASSWORD=$(openssl rand -base64 16)
        log_warning "No password provided. Generated random password."
    fi

    log_info "Admin Account Setup Details:"
    echo "  Username: $ADMIN_USERNAME"
    echo "  Email: $ADMIN_EMAIL"
    echo "  Password: ${ADMIN_PASSWORD:0:3}****${ADMIN_PASSWORD: -3}"
    echo ""

    # Build command
    CMD="python manage.py create_admin"
    CMD="$CMD --username $ADMIN_USERNAME"
    CMD="$CMD --email $ADMIN_EMAIL"
    CMD="$CMD --password $ADMIN_PASSWORD"

    if [[ "$RESET_ADMIN" == "true" ]]; then
        CMD="$CMD --reset"
    fi

    log_info "Running: $CMD"
    echo ""

    # Run the command
    if eval $CMD; then
        log_success "Admin account setup completed!"
        echo ""
        echo -e "${GREEN}=== ADMIN CREDENTIALS ===${NC}"
        echo "Username: $ADMIN_USERNAME"
        echo "Email: $ADMIN_EMAIL"
        echo "Password: $ADMIN_PASSWORD"
        echo ""
        echo -e "${BLUE}Admin URL: https://your-app-url.onrender.com/admin/${NC}"
        echo ""
    else
        log_error "Failed to create admin account"
        exit 1
    fi
}

main "$@"
