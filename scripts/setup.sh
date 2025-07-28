#!/bin/bash
# Setup script for Swift Package Support Data Processing

echo "🚀 Setting up Swift Package Support Data Processing..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.8 or later and try again."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo "📝 Please edit .env and add your GitHub token:"
    echo "   Get token from: https://github.com/settings/tokens"
    echo "   Required scope: public_repo"
fi

# Initialize database
echo "🗄️ Initializing database..."
python swift_analyzer.py setup
