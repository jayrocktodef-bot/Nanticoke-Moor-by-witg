#!/usr/bin/env python3
"""Root wrapper delegating to pipeline.enrich.auto_link_primary_documents_and_citations."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pipeline.enrich.auto_link_primary_documents_and_citations import main

if __name__ == "__main__":
    main()
