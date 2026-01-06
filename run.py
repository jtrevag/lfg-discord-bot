#!/usr/bin/env python3
"""
Simple entry point to run the LFG Discord bot.

Usage:
    python run.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from lfg_bot.main import main

if __name__ == '__main__':
    sys.exit(main())
