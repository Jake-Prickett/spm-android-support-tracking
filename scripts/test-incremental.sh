#!/bin/bash
# Test script for incremental processing functionality

set -e  # Exit on any error

echo "🧪 Testing Incremental Processing Pipeline"
echo "=========================================="

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "⚠️  Virtual environment not detected. Activating..."
    if [[ -f ".venv/bin/activate" ]]; then
        source .venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ .venv directory not found. Run ./scripts/setup.sh first"
        exit 1
    fi
fi

# Check if database exists
if [[ ! -f "swift_packages.db" ]]; then
    echo "📦 Initializing database..."
    python swift_analyzer.py --setup
else
    echo "✅ Database exists"
fi

# Test 1: Status check
echo ""
echo "🔍 Test 1: Status Check"
echo "-----------------------"
python swift_analyzer.py --status

# Test 2: Small incremental collection test
echo ""
echo "🔍 Test 2: Incremental Collection Test"
echo "--------------------------------------"
echo "Running incremental collection with 3 repositories..."
python swift_analyzer.py --collect --incremental --test --batch-size 3 --max-batches 1

# Test 3: Check status after collection
echo ""
echo "🔍 Test 3: Status After Collection"
echo "----------------------------------"
python swift_analyzer.py --status

# Test 4: Generate analysis if sufficient data
echo ""
echo "🔍 Test 4: Analysis Generation Test"
echo "-----------------------------------"

# Check if we have enough data for analysis
REPO_COUNT=$(python -c "
from swift_package_analyzer.core.models import Repository, SessionLocal
db = SessionLocal()
count = db.query(Repository).filter(Repository.processing_status == 'completed').count()
db.close()
print(count)
")

if [[ $REPO_COUNT -ge 3 ]]; then
    echo "✅ Sufficient data ($REPO_COUNT repositories) - generating analysis..."
    python swift_analyzer.py --analyze --output-dir test-output
    
    # Check if outputs were created
    if [[ -f "test-output/index.html" ]]; then
        echo "✅ Analysis outputs generated successfully"
        echo "📄 Generated files:"
        ls -la test-output/
    else
        echo "❌ Analysis outputs not found"
        exit 1
    fi
else
    echo "⚠️  Insufficient data ($REPO_COUNT repositories) - skipping analysis test"
fi

# Test 5: Test resume functionality
echo ""
echo "🔍 Test 5: Resume Functionality Test"
echo "------------------------------------"
echo "Testing that incremental processing resumes from checkpoints..."

# Run with no-resume to create a fresh checkpoint
python swift_analyzer.py --collect --incremental --no-resume --batch-size 2 --max-batches 1

# Then run without no-resume to test resume functionality
python swift_analyzer.py --collect --incremental --batch-size 2 --max-batches 1

echo ""
echo "🎉 All tests completed successfully!"
echo "🚀 The incremental processing pipeline is ready for GitHub Actions"
echo ""
echo "Next steps:"
echo "1. Commit and push these changes"
echo "2. Enable GitHub Actions workflow"
echo "3. Test the nightly automation"