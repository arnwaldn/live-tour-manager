#!/usr/bin/env bash
# =============================================================================
# GigRoute - Build Script (Render.com)
# Installs Python dependencies only. Database migrations run at startup
# via startCommand (free tier has no preDeployCommand or internal networking)
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
echo "  DB migrations will run at startup (startCommand)."
echo "============================================"
