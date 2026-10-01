"""Pipeline subpackage: clean."""
import sys, os
SUBPKG_DIR = os.path.dirname(os.path.abspath(__file__))
if SUBPKG_DIR not in sys.path:
    sys.path.insert(0, SUBPKG_DIR)
