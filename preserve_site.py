#!/usr/bin/env python3
"""
Lynn C. Jackson Genealogy Preservation Pipeline
================================================
Fully catalogs, scrapes, cleans, and structures the archived genealogy website 
from the Internet Archive Wayback Machine into a clean local SQLite database and media directory.

Setup:
    pip install requests beautifulsoup4

Usage:
    python preserve_site.py [--output-dir ./preservation_output] [--db-name genealogy_preservation.db]
"""

import os
import re
import sys
import sqlite3
import argparse
import urllib.parse
from typing import Dict, List, Tuple, Optional
import requests
from bs4 import BeautifulSoup, Comment

# --- Configuration & Constants ---
ROOT_DOMAIN = "http://www.lynncjackson.com/family/"
CDX_API_URL = "http://web.archive.org/cdx/search/cdx?url=lynncjackson.com/family/*&output=json"
WAYBACK_BASE = "https://web.archive.org/web/"

DEFAULT_OUTPUT_DIR = "./preservation_output"
DEFAULT_DB_NAME = "genealogy_preservation.db"
DEFAULT_IMAGES_DIR = "assets/images"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GenealogyPreservationBot/1.0"


class GenealogyPreservationPipeline:
    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR, db_name: str = DEFAULT_DB_NAME):
        self.output_dir = os.path.abspath(output_dir)
        self.images_dir = os.path.join(self.output_dir, DEFAULT_IMAGES_DIR)
        self.db_path = os.path.join(self.output_dir, db_name)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        os.makedirs(self.images_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Pages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                title TEXT,
                clean_html TEXT,
                text_content TEXT,
                wayback_url TEXT,
                timestamp TEXT
            )
        """)

        # Families and People table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS families_and_people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                surname TEXT,
                individual_name TEXT,
                notes TEXT,
                source_page TEXT,
                FOREIGN KEY(source_page) REFERENCES pages(filename)
            )
        """)

        # Media Assets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT,
                local_path TEXT,
                caption TEXT,
                associated_page TEXT,
                wayback_url TEXT,
                FOREIGN KEY(associated_page) REFERENCES pages(filename)
            )
        """)

        conn.commit()
        conn.close()

    # --- Step 1: CDX URL Discovery ---
    def discover_urls(self) -> Dict[str, Tuple[str, str]]:
        """
        Query CDX API and filter for the most recent capture per unique relative path.
        Returns dict: { relative_path: (timestamp, original_url) }
        """
        print("[1/4] Discovering URLs via Wayback CDX API...")
        try:
            res = self.session.get(CDX_API_URL, timeout=30)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"Error fetching CDX API data: {e}")
            return {}

        if not data or len(data) < 2:
            print("No CDX records found.")
            return {}

        header = data[0]
        try:
            idx_timestamp = header.index("timestamp")
            idx_original = header.index("original")
            idx_status = header.index("statuscode")
        except ValueError:
            idx_timestamp, idx_original, idx_status = 1, 2, 4

        unique_captures: Dict[str, Tuple[str, str]] = {}

        for row in data[1:]:
            status = row[idx_status]
            if status != "200":
                continue

            orig_url = row[idx_original]
            timestamp = row[idx_timestamp]

            parsed = urllib.parse.urlparse(orig_url)
            path = parsed.path
            
            # Ensure path is valid and clean
            if "/family" in path:
                rel_path = path.split("/family", 1)[1].lstrip("/")
            else:
                rel_path = path.lstrip("/")

            if not rel_path:
                rel_path = "main.htm"

            # Skip standalone non-HTML root files if misclassified
            if rel_path.startswith("."):
                continue

            if rel_path not in unique_captures or timestamp > unique_captures[rel_path][0]:
                unique_captures[rel_path] = (timestamp, orig_url)

        print(f"Discovered {len(unique_captures)} unique target paths.")
        return unique_captures

    # --- Step 2: Scrape & Clean Pages ---
    def clean_wayback_html(self, html: str) -> BeautifulSoup:
        """Strip Wayback Machine wrappers, injected scripts, and toolbar elements."""
        soup = BeautifulSoup(html, "html.parser")

        # Selectors commonly added by Wayback Machine
        wm_selectors = [
            "#wm-ipp-base", "#wm-ipp", "#donato", "#wm-share",
            "iframe[src*='archive.org']", "script[src*='archive.org']",
            "link[href*='archive.org']", "div[id^='wm-']"
        ]
        for sel in wm_selectors:
            for el in soup.select(sel):
                el.decompose()

        # Remove HTML comments injected by Wayback
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment) and "WAYBACK" in text):
            comment.extract()

        # Clean links to strip wayback prefix from href/src
        for tag in soup.find_all(["a", "img", "area", "frame", "iframe"]):
            for attr in ["href", "src"]:
                if tag.has_attr(attr):
                    val = tag[attr]
                    if "/web/" in val:
                        parts = val.split("/http", 1)
                        if len(parts) > 1:
                            raw_target = "http" + parts[1]
                            tag[attr] = raw_target
                        else:
                            tag[attr] = re.sub(r"^/web/\d+(im_)?/", "", val)

        return soup

    def scrape_and_clean_page(self, rel_path: str, timestamp: str, orig_url: str) -> Optional[Dict]:
        """Fetch, clean HTML, and extract structured page content."""
        wayback_url = f"{WAYBACK_BASE}{timestamp}/{orig_url}"
        print(f"Scraping page: {rel_path}")

        try:
            resp = self.session.get(wayback_url, timeout=30)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
        except Exception as e:
            print(f"  [Error] Failed to download {wayback_url}: {e}")
            return None

        soup = self.clean_wayback_html(resp.text)

        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else rel_path
        text_content = soup.get_text(separator="\n", strip=True)

        return {
            "filename": rel_path,
            "title": title,
            "clean_html": str(soup),
            "text_content": text_content,
            "wayback_url": wayback_url,
            "timestamp": timestamp,
            "soup": soup
        }

    # --- Step 3: Media Downloader ---
    def download_media(self, soup: BeautifulSoup, page_filename: str, page_timestamp: str):
        """Extract image tags and media references and save locally."""
        img_tags = soup.find_all("img")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for img in img_tags:
            src = img.get("src")
            if not src:
                continue

            caption = img.get("alt", "") or img.get("title", "")
            orig_img_filename = os.path.basename(urllib.parse.urlparse(src).path) or "image.jpg"
            local_filename = f"{page_filename.replace('/', '_')}_{orig_img_filename}"
            local_file_path = os.path.join(self.images_dir, local_filename)
            rel_db_path = os.path.join(DEFAULT_IMAGES_DIR, local_filename)

            if src.startswith("http"):
                wayback_img_url = f"{WAYBACK_BASE}{page_timestamp}im_/{src}"
            else:
                base_orig = urllib.parse.urljoin(ROOT_DOMAIN, src)
                wayback_img_url = f"{WAYBACK_BASE}{page_timestamp}im_/{base_orig}"

            if not os.path.exists(local_file_path):
                try:
                    r = self.session.get(wayback_img_url, timeout=20)
                    if r.status_code == 200:
                        with open(local_file_path, "wb") as f:
                            f.write(r.content)
                        print(f"  [Media] Saved: {local_filename}")
                except Exception as e:
                    print(f"  [Media Error] Could not download {wayback_img_url}: {e}")

            cursor.execute("""
                INSERT INTO media_assets (original_filename, local_path, caption, associated_page, wayback_url)
                VALUES (?, ?, ?, ?, ?)
            """, (orig_img_filename, rel_db_path, caption, page_filename, wayback_img_url))

        conn.commit()
        conn.close()

    # --- Step 4: Structured Data Extraction & Database Persistence ---
    def extract_genealogy_entities(self, soup: BeautifulSoup, page_filename: str):
        """Parse raw genealogical data, family records, and lineages."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        text = soup.get_text()
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for line in lines:
            if any(kw in line.lower() for kw in ["born", "died", "married", "son of", "daughter of", "family", "lineage"]):
                words = line.split()
                surname = words[0] if words else "Unknown"
                cursor.execute("""
                    INSERT INTO families_and_people (surname, individual_name, notes, source_page)
                    VALUES (?, ?, ?, ?)
                """, (surname, line[:100], line, page_filename))

        conn.commit()
        conn.close()

    def save_page_to_db(self, page_data: Dict):
        """Save clean HTML and page records to SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO pages (filename, title, clean_html, text_content, wayback_url, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            page_data["filename"],
            page_data["title"],
            page_data["clean_html"],
            page_data["text_content"],
            page_data["wayback_url"],
            page_data["timestamp"]
        ))

        conn.commit()
        conn.close()

    # --- Execution Pipeline ---
    def run(self):
        """Execute CDX discovery, scraping, cleaning, media downloading, and database build."""
        print("=== Starting Lynn C. Jackson Genealogy Preservation Pipeline ===")
        
        captures = self.discover_urls()
        if not captures:
            captures = {
                "main.htm": ("20180105065600", "http://www.lynncjackson.com/family/main.htm")
            }

        html_pages = {}
        processed_count = 0

        for rel_path, (timestamp, orig_url) in captures.items():
            ext = os.path.splitext(rel_path)[1].lower()
            if ext in [".jpg", ".jpeg", ".gif", ".png", ".bmp", ".pdf", ".css", ".js"]:
                continue
            
            page_data = self.scrape_and_clean_page(rel_path, timestamp, orig_url)
            if page_data:
                self.save_page_to_db(page_data)
                self.download_media(page_data["soup"], rel_path, timestamp)
                self.extract_genealogy_entities(page_data["soup"], rel_path)
                html_pages[rel_path] = page_data
                processed_count += 1

        print(f"\n=== Preservation Complete! ===")
        print(f"Processed {processed_count} pages.")
        print(f"Database saved to: {self.db_path}")
        print(f"Media assets directory: {self.images_dir}")

        # Execute Advanced Pipeline Extension Modules
        print("\n--- Executing Extension Modules ---")
        try:
            import fix_media
            fix_media.repair_media_assets()
        except Exception as e:
            print(f"Error running fix_media: {e}")

        try:
            import cdx_fallback
            cdx_fallback.run_cdx_fallback()
        except Exception as e:
            print(f"Error running cdx_fallback: {e}")

        try:
            import build_relationship_graph
            build_relationship_graph.parse_lineage_graph()
        except Exception as e:
            print(f"Error running build_relationship_graph: {e}")



def main():
    parser = argparse.ArgumentParser(description="Lynn C. Jackson Genealogy Preservation Pipeline")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME, help="SQLite database filename")

    args = parser.parse_args()

    pipeline = GenealogyPreservationPipeline(output_dir=args.output_dir, db_name=args.db_name)
    pipeline.run()


if __name__ == "__main__":
    main()
