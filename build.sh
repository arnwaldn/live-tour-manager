#!/usr/bin/env bash
# Build script for Render deployment
# This script runs during the build phase

set -e  # Exit on any error

echo "============================================"
echo "  Tour Manager - Build Script"
echo "============================================"

echo ""
echo "=== Step 1: Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Step 2: Running database migrations ==="
flask db upgrade

echo ""
echo "============================================"
echo "  Build completed successfully!"
echo "============================================"
