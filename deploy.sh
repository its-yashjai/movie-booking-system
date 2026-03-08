#!/bin/bash

###############################################################################
# Unified Deployment Script for Render & Vercel
# 
# Usage:
#   ./deploy.sh render    - Deploy to Render
#   ./deploy.sh vercel    - Deploy to Vercel
#   ./deploy.sh all       - Deploy to both Render and Vercel
#
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Environment variables
RENDER_DEPLOY_HOOK="${RENDER_DEPLOY_HOOK:-}"
VERCEL_TOKEN="${VERCEL_TOKEN:-}"
VERCEL_ORG_ID="${VERCEL_ORG_ID:-}"
VERCEL_PROJECT_ID="${VERCEL_PROJECT_ID:-}"

###############################################################################
# Utility Functions
###############################################################################

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

check_dependencies() {
    local deps=("git" "curl")
    
    for cmd in "${deps[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            log_error "$cmd is not installed"
            return 1
        fi
    done
    
    # Check for vercel CLI if deploying to Vercel
    if [[ "$1" == "vercel" ]] || [[ "$1" == "all" ]]; then
        if ! command -v vercel &> /dev/null; then
            log_warning "Vercel CLI not found. Installing..."
            npm install -g vercel
        fi
    fi
    
    log_success "All dependencies are available"
}

###############################################################################
# Render Deployment
###############################################################################

deploy_render() {
    log_info "Deploying to Render..."
    
    if [ -z "$RENDER_DEPLOY_HOOK" ]; then
        log_error "RENDER_DEPLOY_HOOK environment variable not set"
        log_info "Set it with: export RENDER_DEPLOY_HOOK='your-hook-url'"
        return 1
    fi
    
    log_info "Triggering Render deployment hook..."
    
    if curl -X POST "$RENDER_DEPLOY_HOOK"; then
        log_success "Render deployment triggered successfully!"
        log_info "Check deployment status at: https://dashboard.render.com"
        return 0
    else
        log_error "Failed to trigger Render deployment"
        return 1
    fi
}

###############################################################################
# Vercel Deployment
###############################################################################

deploy_vercel() {
    log_info "Deploying to Vercel..."
    
    # Check for Vercel credentials
    if [ -z "$VERCEL_TOKEN" ]; then
        log_error "VERCEL_TOKEN environment variable not set"
        log_info "Set it with: export VERCEL_TOKEN='your-token'"
        return 1
    fi
    
    if [ -z "$VERCEL_ORG_ID" ]; then
        log_error "VERCEL_ORG_ID environment variable not set"
        log_info "Get it from: https://vercel.com/account"
        return 1
    fi
    
    if [ -z "$VERCEL_PROJECT_ID" ]; then
        log_error "VERCEL_PROJECT_ID environment variable not set"
        log_info "Get it from your project settings"
        return 1
    fi
    
    log_info "Installing Vercel CLI..."
    npm install -g vercel 2>/dev/null || true
    
    log_info "Running build command..."
    pip install -r requirements.txt
    python manage.py collectstatic --noinput
    
    log_info "Deploying to Vercel..."
    vercel deploy \
        --token "$VERCEL_TOKEN" \
        --scope "$VERCEL_ORG_ID" \
        --project-id "$VERCEL_PROJECT_ID" \
        --prod
    
    log_success "Vercel deployment completed!"
    log_info "Check your deployment at: https://vercel.com/dashboard"
}

###############################################################################
# Main Logic
###############################################################################

show_usage() {
    echo ""
    echo -e "${BLUE}Movie Booking System - Unified Deployment Script${NC}"
    echo ""
    echo "Usage: ./deploy.sh [TARGET]"
    echo ""
    echo "Targets:"
    echo "  render    Deploy to Render platform"
    echo "  vercel    Deploy to Vercel platform"
    echo "  all       Deploy to both Render and Vercel"
    echo ""
    echo "Environment Variables Required:"
    echo "  RENDER_DEPLOY_HOOK    - Render deployment webhook URL"
    echo "  VERCEL_TOKEN          - Vercel authentication token"
    echo "  VERCEL_ORG_ID         - Vercel organization ID"
    echo "  VERCEL_PROJECT_ID     - Vercel project ID"
    echo ""
    echo "Example:"
    echo "  export RENDER_DEPLOY_HOOK='https://api.render.com/deploy/srv-xxxxx?key=xxxxx'"
    echo "  export VERCEL_TOKEN='your-token'"
    echo "  export VERCEL_ORG_ID='your-org-id'"
    echo "  export VERCEL_PROJECT_ID='your-project-id'"
    echo "  ./deploy.sh all"
    echo ""
}

main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    TARGET=$1
    DEPLOY_SUCCESS=0
    
    log_info "Starting deployment process..."
    
    # Check dependencies
    check_dependencies "$TARGET" || exit 1
    
    # Verify git status
    log_info "Checking git status..."
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "You have uncommitted changes"
        log_info "Please commit changes before deploying"
        exit 1
    fi
    
    log_success "Git repository is clean"
    
    case "$TARGET" in
        render)
            deploy_render || DEPLOY_SUCCESS=1
            ;;
        vercel)
            deploy_vercel || DEPLOY_SUCCESS=1
            ;;
        all)
            deploy_render || DEPLOY_SUCCESS=1
            echo ""
            deploy_vercel || DEPLOY_SUCCESS=1
            ;;
        *)
            log_error "Unknown target: $TARGET"
            show_usage
            exit 1
            ;;
    esac
    
    echo ""
    if [ $DEPLOY_SUCCESS -eq 0 ]; then
        log_success "Deployment completed successfully!"
    else
        log_error "Deployment failed. Please check the logs above."
        exit 1
    fi
}

# Run main function
main "$@"
