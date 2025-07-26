#!/usr/bin/env python3
"""
Main entry point for Swift Package Analyzer.
This script provides a convenient entry point that delegates to the CLI module.
"""

import sys
from swift_package_analyzer.cli.main import main

if __name__ == "__main__":
    main()