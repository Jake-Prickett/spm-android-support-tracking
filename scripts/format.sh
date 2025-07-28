#!/bin/bash
set -e

echo "Formatting Python code with black..."

if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

if ! command -v black &> /dev/null; then
    echo "Error: black is not installed. Run: pip install black"
    exit 1
fi

black swift_package_analyzer/ swift_analyzer.py
echo "Code formatting complete."