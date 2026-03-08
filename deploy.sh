#!/bin/bash

# Load .env.deployment if it exists
if [ -f ".env.deployment" ]; then
    source .env.deployment
fi

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
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
    log_success "All dependencies available"
}

deploy_render() {
    log_info "Deploying to Render..."
    
    if [ -z "$RENDER_DEPLOY_HOOK" ]; then
        log_error "RENDER_DEPLOY_HOOK not set"
        log_info "Add to .env.deployment or run: export RENDER_DEPLOY_HOOK='your-hook'"
        return 1
    fi
    
    log_info "Triggering Render deployment..."
    if curl -X POST "$RENDER_DEPLOY_HOOK"; then
        log_success "Render deployment triggered!"
        log_info "Check: https://dashboard.render.com"
        return 0
    else
        log_error "Render deployment failed"
        return 1
    fi
}

deploy_vercel() {
    log_info "Deploying to Vercel..."
    
    if [ -z "$VERCEL_TOKEN" ] || [ -z "$VERCEL_ORG_ID" ] || [ -z "$VERCEL_PROJECT_ID" ]; then
        log_error "Vercel credentials not set"
        log_info "Add to .env.deployment: VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_PROJECT_ID"
        return 1
    fi
    
    log_info "Installing Vercel CLI..."
    npm install -g vercel 2>/dev/null || true
    
    log_info "Building..."
    pip install -r requirements.txt > /dev/null 2>&1
    python manage.py collectstatic --noinput > /dev/null 2>&1
    
    log_info "Deploying to Vercel..."
    vercel deploy --token "$VERCEL_TOKEN" --scope "$VERCEL_ORG_ID" --project-id "$VERCEL_PROJECT_ID" --prod
    
    log_success "Vercel deployment complete!"
}

show_usage() {
    echo ""
    echo -e "${BLUE}Movie Booking System - Deploy${NC}"
    echo "Usage: ./deploy.sh [render|vercel|all]"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh render"
    echo "  ./deploy.sh vercel"
    echo "  ./deploy.sh all"
    echo ""
}

main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    TARGET=$1
    check_dependencies || exit 1
    
    log_info "Git status..."
    if [ -n "$(git status --porcelain)" ]; then
        log_error "Uncommitted changes found. Commit first."
        exit 1
    fi
    log_success "Repository clean"
    
    echo ""
    
    case "$TARGET" in
        render)
            deploy_render
            ;;
        vercel)
            deploy_vercel
            ;;
        all)
            deploy_render && deploy_vercel
            ;;
        *)
            log_error "Unknown target: $TARGET"
            show_usage
            exit 1
            ;;
    esac
    
    echo ""
    log_success "Done!"
}

main "$@"
