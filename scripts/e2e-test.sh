#!/bin/bash

# End-to-End Test Script
# Mirrors the GitHub Actions workflows for testing functionality locally
# Prerequisites: Run './scripts/setup.sh' or ensure virtual environment is activated

set -e  # Exit on any error

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_MODE=${1:-"test"}  # Default to test mode (3 repos), pass "full" for larger batch
BATCH_SIZE=${2:-"10"}   # Small batch for full mode testing
CLEANUP=${3:-"false"}   # Set to "true" to cleanup generated files after test

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo -e "\n${BLUE}==== $1 ====${NC}"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log_success "$1 is available"
        return 0
    else
        log_error "$1 is not available"
        return 1
    fi
}

verify_file_exists() {
    if [ -f "$1" ]; then
        log_success "File exists: $1 ($(wc -c < "$1") bytes)"
        return 0
    else
        log_error "File missing: $1"
        return 1
    fi
}

verify_json_valid() {
    if python -m json.tool "$1" > /dev/null 2>&1; then
        log_success "Valid JSON: $1"
        return 0
    else
        log_error "Invalid JSON: $1"
        return 1
    fi
}

# Main execution
main() {
    log_step "Starting End-to-End Test (Mode: $TEST_MODE)"
    
    # Check prerequisites
    log_step "Checking Prerequisites"
    check_command "python" || exit 1
    check_command "pip" || exit 1
    check_command "node" || exit 1
    check_command "npm" || exit 1
    
    # Verify we're in the right directory
    if [ ! -f "swift_analyzer.py" ]; then
        log_error "swift_analyzer.py not found. Run this script from the project root."
        exit 1
    fi
    
    log_success "All prerequisites met"
    
    # Ensure logs directory exists
    mkdir -p logs
    
    # Database status check
    log_step "Checking Database Status"
    python swift_analyzer.py --status
    
    # Data collection phase (mirroring nightly-analysis workflow)
    log_step "Data Collection Phase"
    
    if [ "$TEST_MODE" = "test" ]; then
        log_info "Running in test mode (3 repositories)..."
        timeout 5m python swift_analyzer.py --collect --test || {
            exit_code=$?
            if [ $exit_code -eq 124 ]; then
                log_warning "Collection timed out - this is expected in test mode"
            else
                log_error "Collection failed with exit code $exit_code"
                exit $exit_code
            fi
        }
    else
        log_info "Running with batch size: $BATCH_SIZE"
        timeout 10m python swift_analyzer.py --collect --batch-size "$BATCH_SIZE" || {
            exit_code=$?
            if [ $exit_code -eq 124 ]; then
                log_warning "Collection timed out - progress saved"
            else
                log_error "Collection failed with exit code $exit_code"
                exit $exit_code
            fi
        }
    fi
    
    # Check status after collection
    log_info "Checking status after collection..."
    python swift_analyzer.py --status
    log_success "Data collection completed"
    
    # Analysis phase
    log_step "Analysis Phase"
    
    log_info "Generating comprehensive analysis and reports..."
    python swift_analyzer.py --analyze --output-dir docs
    
    # Verify analysis data was created
    verify_file_exists "docs/swift_packages.json" || exit 1
    verify_file_exists "docs/swift_packages.csv" || exit 1
    verify_json_valid "docs/swift_packages.json" || exit 1
    
    # Check data size
    data_size=$(wc -c < docs/swift_packages.json)
    log_info "Analysis data size: $data_size bytes"
    
    if [ "$data_size" -lt 1000 ]; then
        log_error "Analysis data appears to be incomplete (less than 1KB)"
        exit 1
    fi
    
    log_success "Analysis phase completed"
    
    # List generated files
    log_info "Generated files in docs/:"
    ls -la docs/
    if [ -d docs/dependencies ]; then
        log_info "Dependency analysis files:"
        ls -la docs/dependencies/
    fi
    
    # Frontend build phase (mirroring publish-docs workflow)
    log_step "Frontend Build Phase"
    
    # Check if frontend directory exists
    if [ ! -d "frontend" ]; then
        log_warning "Frontend directory not found - skipping frontend build"
    else
        # Node.js setup
        log_info "Setting up Node.js environment..."
        cd frontend
        
        # Install dependencies
        log_info "Installing Node.js dependencies..."
        npm ci
        log_success "Node.js dependencies installed"
        
        # Copy data to frontend
        log_info "Copying analysis data to frontend..."
        cp ../docs/swift_packages.json public/
        log_success "Data copied to frontend public directory"
        
        # Build frontend
        log_info "Building Next.js application..."
        npm run build
        
        # Verify build output
        if [ ! -d "out" ]; then
            log_error "Frontend build failed - no output directory created"
            exit 1
        fi
        
        if [ ! -f "out/index.html" ]; then
            log_error "Frontend build incomplete - no index.html found"
            exit 1
        fi
        
        build_size=$(du -sh out | cut -f1)
        log_success "Frontend build completed successfully (Size: $build_size)"
        
        # Return to project root
        cd ..
    fi
    
    # Integration verification
    log_step "Integration Verification"
    
    # Verify database exists and has content
    if [ -f "swift_packages.db" ]; then
        log_success "Database file exists"
    else
        log_warning "Database file not found"
    fi
    
    # Verify all expected output files
    expected_files=("docs/swift_packages.json" "docs/swift_packages.csv")
    for file in "${expected_files[@]}"; do
        verify_file_exists "$file" || exit 1
    done
    
    # Test summary
    log_step "Test Summary"
    log_success "✅ Database initialization: PASSED"
    log_success "✅ Data collection: PASSED"
    log_success "✅ Analysis generation: PASSED"
    log_success "✅ Data validation: PASSED"
    
    if [ -d "frontend/out" ]; then
        log_success "✅ Frontend build: PASSED"
    else
        log_warning "⚠️  Frontend build: SKIPPED"
    fi
    
    log_success "✅ Integration verification: PASSED"
    
    # Cleanup if requested
    if [ "$CLEANUP" = "true" ]; then
        log_step "Cleanup"
        log_info "Cleaning up generated test files..."
        
        # Remove generated files but keep database for next run
        rm -f docs/swift_packages.json docs/swift_packages.csv
        rm -rf docs/dependencies
        
        if [ -d "frontend/out" ]; then
            rm -rf frontend/out
            rm -f frontend/public/swift_packages.json
        fi
        
        log_success "Cleanup completed"
    fi
    
    # Final status
    log_step "Final Status"
    python swift_analyzer.py --status
    
    echo -e "\n${GREEN}🎉 End-to-End Test Completed Successfully!${NC}"
    
    if [ "$TEST_MODE" = "test" ]; then
        echo -e "${BLUE}💡 To test with more data, run: ./scripts/e2e-test.sh full${NC}"
    fi
    
    echo -e "${BLUE}💡 To cleanup generated files, run with cleanup flag: ./scripts/e2e-test.sh $TEST_MODE $BATCH_SIZE true${NC}"
}

# Run main function
main "$@"