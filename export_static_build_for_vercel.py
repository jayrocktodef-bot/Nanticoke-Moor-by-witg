#!/usr/bin/env python3
"""Root wrapper delegating to pipeline.export.export_static_build_for_vercel."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pipeline.export.export_static_build_for_vercel import export_all

if __name__ == "__main__":
    export_all()
