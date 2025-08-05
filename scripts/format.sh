#!/bin/bash
set -e

echo "Formatting Python code with black..."

if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv directory not found. Run ./scripts/setup.sh first"
    exit 1
fi

if ! python -m black --version &> /dev/null; then
    echo "Error: black is not installed. Run: pip install black"
    exit 1
fi

python -m black src/ swift_analyzer.py
echo "Code formatting complete."