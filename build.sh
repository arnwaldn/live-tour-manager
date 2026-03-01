#!/usr/bin/env bash
# =============================================================================
# GigRoute - Build Script (Render.com)
# Installs Python dependencies only. Database migrations run via preDeployCommand
# (Render's internal network is not available during build phase)
# =============================================================================
set -o errexit  # Exit on error

echo "============================================"
echo "  GigRoute - Build Script"
echo "============================================"

echo ""
echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "============================================"
echo "  Build completed successfully!"
echo "  DB migrations will run in pre-deploy step."
echo "============================================"
