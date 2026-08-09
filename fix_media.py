#!/usr/bin/env python3
"""
Module 1: Media Repair Pipeline (fix_media.py)
==============================================
Scans preserved HTML files and database records for <img> tags, background images,
and media assets. Downloads missing raw images using Wayback im_ URL flag and updates 
local HTML image sources to local assets directory paths.
"""

import os
import re
import sqlite3
import urllib.parse
import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "assets", "images")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")
WAYBACK_BASE = "https://web.archive.org/web/"
ROOT_DOMAIN = "http://www.lynncjackson.com/family/"

os.makedirs(IMAGES_DIR, exist_ok=True)
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 GenealogyMediaFixer/1.0"})

def repair_media_assets():
    print("=== [Module 1] Starting Media Repair & Asset Downloader ===")
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT filename, clean_html, timestamp FROM pages")
    pages = cursor.fetchall()

    repaired_count = 0
    downloaded_assets = 0

    for page_filename, clean_html, timestamp in pages:
        if not clean_html:
            continue

        soup = BeautifulSoup(clean_html, "html.parser")
        modified = False
        img_tags = soup.find_all("img")

        for img in img_tags:
            src = img.get("src")
            if not src:
                continue

            # Extract raw original image URL and filename
            parsed_src = urllib.parse.urlparse(src)
            orig_filename = os.path.basename(parsed_src.path) or "image.jpg"

            # Skip UI icons, navigation buttons, and red rules (only preserve photos of people)
            lower_file = orig_filename.lower()
            if any(ui_img in lower_file for ui_img in ["return.gif", "redrule.gif", "banner.gif", "sorry.gif", "conman.gif", "button"]) or lower_file.endswith(".gif"):
                continue


            
            # Clean filename for local storage
            safe_page = page_filename.replace("/", "_")
            local_filename = f"{safe_page}_{orig_filename}"
            local_file_path = os.path.join(IMAGES_DIR, local_filename)
            rel_src_path = f"/assets/images/{local_filename}"

            # If image missing locally, construct raw wayback im_ URL and download
            if not os.path.exists(local_file_path):
                # Build Wayback im_ flag URL
                if "/web/" in src:
                    # e.g., https://web.archive.org/web/20180105065600/http://lynncjackson.com/family/images/pic.jpg
                    parts = src.split("/http", 1)
                    if len(parts) > 1:
                        target_url = "http" + parts[1]
                        wayback_im_url = f"{WAYBACK_BASE}{timestamp}im_/{target_url}"
                    else:
                        wayback_im_url = src
                else:
                    target_url = urllib.parse.urljoin(ROOT_DOMAIN, src)
                    wayback_im_url = f"{WAYBACK_BASE}{timestamp}im_/{target_url}"

                try:
                    res = session.get(wayback_im_url, timeout=20)
                    if res.status_code == 200 and len(res.content) > 0:
                        with open(local_file_path, "wb") as f:
                            f.write(res.content)
                        downloaded_assets += 1
                        print(f"  [Downloaded] {local_filename}")
                except Exception as e:
                    print(f"  [Error] Failed to fetch {wayback_im_url}: {e}")

            # Update src to point to local assets path
            if img.get("src") != rel_src_path:
                img["src"] = rel_src_path
                modified = True

        if modified:
            updated_html = str(soup)
            cursor.execute("UPDATE pages SET clean_html = ? WHERE filename = ?", (updated_html, page_filename))
            repaired_count += 1

    conn.commit()
    conn.close()
    print(f"=== [Module 1] Completed. Repaired HTML in {repaired_count} pages, downloaded {downloaded_assets} missing assets. ===")

if __name__ == "__main__":
    repair_media_assets()
