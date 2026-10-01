"""Lynn C. Jackson & Mitsawokett Delmarva Afro-Indigenous Family Archive Pipeline."""
import sys, os
PIPELINE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PIPELINE_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, PIPELINE_ROOT)
