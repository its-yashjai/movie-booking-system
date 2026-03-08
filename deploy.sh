#!/bin/bash

###############################################################################
# 🚀 Movie Booking System - Final Unified Deployment Script
# 
# Supports: Render, Vercel, and Docker deployments
# 
# Usage:
#   ./deploy.sh render    - Deploy to Render
#   ./deploy.sh vercel    - Deploy to Vercel
#   ./deploy.sh docker    - Build and run Docker container
#   ./deploy.sh all       - Deploy to both Render and Vercel
#   ./deploy.sh setup     - Initial setup and configuration
#
# Author: Movie Booking System
# Version: 2.0
###############################################################################

set -e

# ==============================================================================
# Configuration & Colors
# ==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="Movie Booking System"
PYTHON_VERSION="3.9"

# Environment variables
RENDER_DEPLOY_HOOK="${RENDER_DEPLOY_HOOK:-}"
VERCEL_TOKEN="${VERCEL_TOKEN:-}"
VERCEL_ORG_ID="${VERCEL_ORG_ID:-}"
VERCEL_PROJECT_ID="${VERCEL_PROJECT_ID:-}"

# ==============================================================================
# Utility Functions
# ==============================================================================

log_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

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

log_step() {
    echo -e "${PURPLE}→${NC} $1"
}

spinner() {
    local pid=$!
    local delay=0.1
    local spinstr='|/-\'
    local temp
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# ==============================================================================
# Pre-flight Checks
# ==============================================================================

check_git_status() {
    log_step "Checking git repository status..."
    
    if [ ! -d ".git" ]; then
        log_error "Not a git repository. Please initialize git first."
        return 1
    fi
    
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "Uncommitted changes detected:"
        git status --short
        log_info "Please commit all changes before deploying:"
        log_info "  git add ."
        log_info "  git commit -m 'Your message'"
        return 1
    fi
    
    log_success "Git repository is clean"
    return 0
}

check_dependencies() {
    local missing=0
    local deps=("git" "curl")
    
    log_step "Checking system dependencies..."
    
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is not installed"
            missing=1
        else
            log_success "$cmd is installed"
        fi
    done
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        log_error "python3 is not installed"
        missing=1
    else
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        log_success "Python $PYTHON_VERSION is installed"
    fi
    
    # Check for Node.js if deploying to Vercel
    if [[ "$1" == "vercel" ]] || [[ "$1" == "all" ]]; then
        if ! command -v npm &> /dev/null; then
            log_warning "npm not found. Attempting to install Node.js..."
            if command -v brew &> /dev/null; then
                brew install node
            else
                log_error "Node.js is required for Vercel deployment"
                missing=1
            fi
        else
            log_success "Node.js is installed"
        fi
    fi
    
    [ $missing -eq 0 ] && return 0 || return 1
}

# ==============================================================================
# Setup Function
# ==============================================================================

setup_environment() {
    log_header "Initial Setup & Configuration"
    
    check_dependencies "all" || exit 1
    
    log_step "Setting up Python environment..."
    
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv .venv
        log_success "Virtual environment created"
    else
        log_success "Virtual environment already exists"
    fi
    
    log_step "Activating virtual environment..."
    source .venv/bin/activate
    
    log_step "Upgrading pip..."
    pip install --upgrade pip setuptools wheel > /dev/null 2>&1
    
    log_step "Installing Python dependencies..."
    pip install -r requirements.txt
    
    log_step "Creating .env file..."
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success ".env file created from .env.example"
            log_warning "Please update .env with your configuration"
        else
            log_warning ".env.example not found. Please create .env manually"
        fi
    else
        log_success ".env file already exists"
    fi
    
    log_step "Running migrations..."
    python manage.py migrate
    
    log_success "Setup completed successfully!"
    log_info "To start development server, run:"
    log_info "  source .venv/bin/activate"
    log_info "  python manage.py runserver"
}

# ==============================================================================
# Render Deployment
# ==============================================================================

deploy_render() {
    log_header "Deploying to Render"
    
    if [ -z "$RENDER_DEPLOY_HOOK" ]; then
        log_error "RENDER_DEPLOY_HOOK environment variable not set"
        log_info "Get your deploy hook from Render dashboard:"
        log_info "  1. Go to https://dashboard.render.com"
        log_info "  2. Select your service"
        log_info "  3. Go to Settings → Deploy Hook"
        log_info "  4. Copy the URL and set: export RENDER_DEPLOY_HOOK='<url>'"
        return 1
    fi
    
    check_git_status || return 1
    
    log_step "Pushing code to repository..."
    git push origin main
    
    log_step "Triggering Render deployment..."
    
    if curl -X POST "$RENDER_DEPLOY_HOOK" 2>/dev/null; then
        echo ""
        log_success "Render deployment triggered successfully!"
        log_info "Check deployment status at:"
        log_info "  https://dashboard.render.com"
        return 0
    else
        log_error "Failed to trigger Render deployment"
        return 1
    fi
}

# ==============================================================================
# Vercel Deployment
# ==============================================================================

deploy_vercel() {
    log_header "Deploying to Vercel"
    
    # Validate credentials
    if [ -z "$VERCEL_TOKEN" ]; then
        log_error "VERCEL_TOKEN environment variable not set"
        log_info "Generate a token from: https://vercel.com/account/tokens"
        log_info "Then set: export VERCEL_TOKEN='<token>'"
        return 1
    fi
    
    if [ -z "$VERCEL_ORG_ID" ]; then
        log_error "VERCEL_ORG_ID environment variable not set"
        log_info "Find your Team ID at: https://vercel.com/account"
        log_info "Then set: export VERCEL_ORG_ID='<id>'"
        return 1
    fi
    
    if [ -z "$VERCEL_PROJECT_ID" ]; then
        log_error "VERCEL_PROJECT_ID environment variable not set"
        log_info "Find your project ID in vercel.json or at vercel.com"
        log_info "Then set: export VERCEL_PROJECT_ID='<id>'"
        return 1
    fi
    
    check_git_status || return 1
    
    log_step "Installing Vercel CLI..."
    npm install -g vercel 2>/dev/null || true
    
    log_step "Installing Python dependencies..."
    pip install -r requirements.txt
    
    log_step "Collecting static files..."
    python manage.py collectstatic --noinput
    
    log_step "Pushing code to repository..."
    git push origin main
    
    log_step "Deploying to Vercel (production)..."
    
    if vercel deploy \
        --token "$VERCEL_TOKEN" \
        --scope "$VERCEL_ORG_ID" \
        --project-id "$VERCEL_PROJECT_ID" \
        --prod; then
        
        echo ""
        log_success "Vercel deployment completed!"
        log_info "Check your deployment at:"
        log_info "  https://vercel.com/dashboard"
        return 0
    else
        log_error "Vercel deployment failed"
        return 1
    fi
}

# ==============================================================================
# Docker Deployment
# ==============================================================================

deploy_docker() {
    log_header "Building & Running Docker Container"
    
    if [ ! -f "Dockerfile" ]; then
        log_error "Dockerfile not found in project root"
        return 1
    fi
    
    local container_name="movie-booking-system"
    local image_name="$container_name:latest"
    
    log_step "Building Docker image..."
    docker build -t "$image_name" .
    log_success "Docker image built successfully"
    
    # Stop existing container if running
    if docker ps -a --format '{{.Names}}' | grep -q "^$container_name$"; then
        log_step "Stopping existing container..."
        docker stop "$container_name" || true
        docker rm "$container_name" || true
    fi
    
    log_step "Running Docker container..."
    docker run -d \
        --name "$container_name" \
        -p 8000:8000 \
        --env-file .env \
        "$image_name"
    
    echo ""
    log_success "Docker container running successfully!"
    log_info "Access the application at: http://localhost:8000"
    log_info "View logs with: docker logs -f $container_name"
}

# ==============================================================================
# Help & Usage
# ==============================================================================

show_usage() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║        🎬 Movie Booking System - Deployment Script          ║${NC}"
    echo -e "${CYAN}║                      Version 2.0                            ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Usage: ./deploy.sh [TARGET]"
    echo ""
    echo "Available Targets:"
    echo "  ${GREEN}render${NC}     Deploy to Render hosting platform"
    echo "  ${GREEN}vercel${NC}     Deploy to Vercel hosting platform"
    echo "  ${GREEN}docker${NC}     Build and run Docker container locally"
    echo "  ${GREEN}all${NC}        Deploy to both Render and Vercel"
    echo "  ${GREEN}setup${NC}      Initial setup and configuration"
    echo "  ${GREEN}help${NC}       Show this help message"
    echo ""
    echo "Environment Variables Required:"
    echo ""
    echo "  For Render:"
    echo "    export RENDER_DEPLOY_HOOK='https://api.render.com/deploy/srv-xxxxx?key=xxxxx'"
    echo ""
    echo "  For Vercel:"
    echo "    export VERCEL_TOKEN='your-token-here'"
    echo "    export VERCEL_ORG_ID='your-org-id'"
    echo "    export VERCEL_PROJECT_ID='your-project-id'"
    echo ""
    echo "Quick Start Examples:"
    echo ""
    echo "  1. Initial setup:"
    echo "     ${CYAN}./deploy.sh setup${NC}"
    echo ""
    echo "  2. Deploy to Render:"
    echo "     ${CYAN}export RENDER_DEPLOY_HOOK='<your-hook>'${NC}"
    echo "     ${CYAN}./deploy.sh render${NC}"
    echo ""
    echo "  3. Deploy to Vercel:"
    echo "     ${CYAN}export VERCEL_TOKEN='<token>'${NC}"
    echo "     ${CYAN}export VERCEL_ORG_ID='<id>'${NC}"
    echo "     ${CYAN}export VERCEL_PROJECT_ID='<id>'${NC}"
    echo "     ${CYAN}./deploy.sh vercel${NC}"
    echo ""
    echo "  4. Test locally with Docker:"
    echo "     ${CYAN}./deploy.sh docker${NC}"
    echo ""
    echo "  5. Deploy to all platforms:"
    echo "     ${CYAN}./deploy.sh all${NC}"
    echo ""
}

# ==============================================================================
# Main Entry Point
# ==============================================================================

main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    TARGET="$1"
    DEPLOY_SUCCESS=true
    
    case "$TARGET" in
        setup)
            setup_environment
            ;;
        render)
            check_dependencies "render" || exit 1
            deploy_render || DEPLOY_SUCCESS=false
            ;;
        vercel)
            check_dependencies "vercel" || exit 1
            deploy_vercel || DEPLOY_SUCCESS=false
            ;;
        docker)
            check_dependencies "docker" || exit 1
            deploy_docker || DEPLOY_SUCCESS=false
            ;;
        all)
            check_dependencies "all" || exit 1
            log_header "Deploying to All Platforms"
            deploy_render || DEPLOY_SUCCESS=false
            echo ""
            deploy_vercel || DEPLOY_SUCCESS=false
            ;;
        help|-h|--help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown target: $TARGET"
            show_usage
            exit 1
            ;;
    esac
    
    echo ""
    if [ "$DEPLOY_SUCCESS" = true ]; then
        log_header "Deployment Summary"
        log_success "All operations completed successfully!"
        log_info "Next steps:"
        log_info "  1. Monitor your deployment on the platform dashboard"
        log_info "  2. Test your application thoroughly"
        log_info "  3. Check logs if any issues arise"
    else
        log_header "Deployment Summary"
        log_error "Some operations failed. Please review the logs above."
        exit 1
    fi
}

# Run main function
main "$@"
