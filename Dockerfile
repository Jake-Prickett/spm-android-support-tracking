# Multi-stage build for Swift Package Analyzer
FROM python:3.11-slim as builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set up Python environment
WORKDIR /app
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Set up application
WORKDIR /app
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/exports /app/logs

# Make sure scripts are executable
RUN chmod +x /app/scripts/*.sh 2>/dev/null || true

# Add local Python packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Default command - setup database and run analysis
CMD ["python", "swift_analyzer.py", "--setup"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/app/swift_packages.db').close()" || exit 1