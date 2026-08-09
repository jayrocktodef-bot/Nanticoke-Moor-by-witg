#!/usr/bin/env python3
"""
Local Viewer Server for Preserved Lynn C. Jackson Genealogy Site
================================================================
Serves preserved HTML pages, images, and provides an interactive SQLite browser.

Usage:
    python serve_viewer.py [--port 8000]
"""

import os
import sqlite3
import argparse
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "preservation_output")
DB_PATH = os.path.join(OUTPUT_DIR, "genealogy_preservation.db")

class ViewerHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path.startswith("/assets/"):
            return os.path.join(OUTPUT_DIR, path.lstrip("/"))
        return super().translate_path(path)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.lstrip("/")

        # Root index page
        if not path or path == "index.html":
            self.serve_dashboard()
            return
        
        # SQLite API for search
        if path == "api/search":
            query_components = urllib.parse.parse_qs(parsed.query)
            q = query_components.get("q", [""])[0]
            self.serve_search_api(q)
            return

        # Check if requested page exists in SQLite `pages` table
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT clean_html, title FROM pages WHERE filename = ?", (path,))
            row = cursor.fetchone()
            conn.close()

            if row:
                clean_html, title = row
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(clean_html.encode("utf-8"))
                return

        # Fallback to standard static file handling
        super().do_GET()

    def serve_dashboard(self):
        if not os.path.exists(DB_PATH):
            self.send_error(500, f"Database file not found at {DB_PATH}")
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM pages")
        total_pages = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM media_assets")
        total_media = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM families_and_people")
        total_people = c.fetchone()[0]

        c.execute("SELECT filename, title FROM pages ORDER BY filename LIMIT 50")
        pages_list = c.fetchall()
        conn.close()

        page_links_html = "".join([f'<li><a href="/{filename}" target="viewer">{filename} - {title}</a></li>' for filename, title in pages_list])

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Lynn C. Jackson Genealogy Preservation Viewer</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #0f172a; color: #f8fafc; display: flex; height: 100vh; }}
        #sidebar {{ width: 340px; background: #1e293b; border-right: 1px solid #334155; display: flex; flex-direction: column; }}
        #header {{ padding: 20px; border-bottom: 1px solid #334155; }}
        h1 {{ font-size: 1.1rem; margin: 0 0 10px 0; color: #38bdf8; }}
        .stats {{ display: flex; gap: 10px; font-size: 0.8rem; color: #94a3b8; }}
        .stat-box {{ background: #0f172a; padding: 6px 10px; border-radius: 6px; flex: 1; text-align: center; }}
        .stat-num {{ display: block; font-weight: bold; color: #f8fafc; font-size: 1rem; }}
        #search {{ padding: 15px; border-bottom: 1px solid #334155; }}
        input {{ width: 100%; padding: 8px 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; }}
        #list {{ flex: 1; overflow-y: auto; padding: 10px 20px; }}
        ul {{ list-style: none; padding: 0; margin: 0; }}
        li {{ margin-bottom: 8px; }}
        a {{ color: #cbd5e1; text-decoration: none; font-size: 0.9rem; }}
        a:hover {{ color: #38bdf8; text-decoration: underline; }}
        #content {{ flex: 1; background: #fff; border: none; }}
    </style>
</head>
<body>
    <div id="sidebar">
        <div id="header">
            <h1>Genealogy Archive Viewer</h1>
            <div class="stats">
                <div class="stat-box"><span class="stat-num">{total_pages}</span> Pages</div>
                <div class="stat-box"><span class="stat-num">{total_media}</span> Media</div>
                <div class="stat-box"><span class="stat-num">{total_people}</span> Records</div>
            </div>
        </div>
        <div id="list">
            <h3 style="font-size: 0.85rem; text-transform: uppercase; color: #64748b; margin-top: 10px;">Preserved Pages</h3>
            <ul>
                {page_links_html}
            </ul>
        </div>
    </div>
    <iframe id="content" name="viewer" src="/main.htm"></iframe>
</body>
</html>
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    server_address = ("", args.port)
    httpd = HTTPServer(server_address, ViewerHandler)
    print(f"Serving genealogy viewer on http://localhost:{args.port} ...")
    httpd.serve_forever()

if __name__ == "__main__":
    main()
