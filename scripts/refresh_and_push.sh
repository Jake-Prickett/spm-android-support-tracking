#!/bin/bash

# Simple script to refresh data and push to remote
set -e

echo "🔄 Refreshing Swift package data..."

# Collect latest data
python swift_analyzer.py collect

# Generate reports
python swift_analyzer.py analyze

# Add changes and commit
git add docs/ swift_packages.db
git commit -m "📊 Update Swift package analysis data"

# Push to remote
git push

echo "✅ Data refreshed and pushed to remote!"