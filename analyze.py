#!/usr/bin/env python3
"""
Analysis entry point for Swift Package Analyzer.
This script provides a convenient entry point that delegates to the analysis CLI module.
"""

import sys
from swift_package_analyzer.cli.analyze import main

if __name__ == "__main__":
    main()