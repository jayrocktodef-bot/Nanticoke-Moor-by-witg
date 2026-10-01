"""Centralized configuration and path anchors for archive pipelines."""
from pathlib import Path
PIPELINE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_DIR.parent
PRESERVATION_DIR = PROJECT_ROOT / "preservation_output"
DB_PATH = PRESERVATION_DIR / "genealogy_preservation.db"
MODELS_DIR = PROJECT_ROOT / "models"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
PUBLIC_API_DIR = FRONTEND_DIR / "public" / "api"
MEDIA_ASSETS_DIR = PRESERVATION_DIR / "assets" / "archive_media"
