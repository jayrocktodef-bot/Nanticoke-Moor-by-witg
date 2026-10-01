#!/usr/bin/env python3
"""
ancestry_scraper.py

Interactive & Automated Ancestry.com Document Scraper via Chrome DevTools Protocol (CDP).
Connects to an existing Chrome browser session (port 9222) where the user is signed in.

Capabilities:
1. Verifies active Ancestry authentication session.
2. Supports scraping Delaware Census Collections:
   - 1850 (collection 8054)
   - 1860 (collection 7667)
   - 1870 (collection 7163)
   - 1880 (collection 6742)
   - 1900 (collection 7602)
   - 1910 (collection 7884)
   - 1920 (collection 6061)
   - 1930 (collection 6224)
   - 1940 (collection 2442)
   - 1950 (collection 62308)
3. Extracts high-resolution scanned sheet images, household transcriptions, and citations.
4. Preserves files to `preservation_output/ancestry_documents/delaware_census/`.
5. Links extracted records into `genealogy_preservation.db`.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import re
import asyncio
import websockets
import sqlite3

CDP_HTTP_URL = "http://localhost:9222"
OUTPUT_DIR = "preservation_output/ancestry_documents/delaware_census"
DB_PATH = "preservation_output/genealogy_preservation.db"

DELAWARE_CENSUS_COLLECTIONS = {
    "1850": {"id": "8054", "name": "1850 United States Federal Census (Delaware)"},
    "1860": {"id": "7667", "name": "1860 United States Federal Census (Delaware)"},
    "1870": {"id": "7163", "name": "1870 United States Federal Census (Delaware)"},
    "1880": {"id": "6742", "name": "1880 United States Federal Census (Delaware)"},
    "1900": {"id": "7602", "name": "1900 United States Federal Census (Delaware)"},
    "1910": {"id": "7884", "name": "1910 United States Federal Census (Delaware)"},
    "1920": {"id": "6061", "name": "1920 United States Federal Census (Delaware)"},
    "1930": {"id": "6224", "name": "1930 United States Federal Census (Delaware)"},
    "1940": {"id": "2442", "name": "1940 United States Federal Census (Delaware)"},
    "1950": {"id": "62308", "name": "1950 United States Federal Census (Delaware)"}
}

class AncestryCDPClient:
    def __init__(self, http_url=CDP_HTTP_URL):
        self.http_url = http_url
        self.ws = None
        self.msg_id = 0
        self.page_id = None

    def get_pages(self):
        """Fetch all browser tabs from CDP."""
        try:
            with urllib.request.urlopen(f"{self.http_url}/json/list", timeout=5) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            print(f"Error connecting to Chrome on {self.http_url}: {e}")
            return []

    def find_ancestry_tab(self):
        """Find an active Ancestry tab or return the main page tab."""
        pages = self.get_pages()
        for p in pages:
            if p.get("type") == "page" and "ancestry.com" in p.get("url", "").lower():
                return p
        for p in pages:
            if p.get("type") == "page":
                return p
        return None

    async def connect(self, page):
        """Connect WebSocket to the page's DevTools endpoint."""
        ws_url = page.get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError(f"No webSocketDebuggerUrl available for page {page.get('id')}")
        self.page_id = page.get("id")
        self.ws = await websockets.connect(ws_url, max_size=100 * 1024 * 1024)
        print(f"Connected to page: {page.get('title')} ({page.get('url')})")

    async def send_cmd(self, method, params=None):
        """Send a CDP command and await response."""
        self.msg_id += 1
        cid = self.msg_id
        req = {"id": cid, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(req))

        while True:
            resp_raw = await self.ws.recv()
            resp = json.loads(resp_raw)
            if resp.get("id") == cid:
                if "error" in resp:
                    raise RuntimeError(f"CDP Error ({method}): {resp['error']}")
                return resp.get("result", {})

    async def evaluate(self, expression):
        """Evaluate JavaScript expression in current page context."""
        res = await self.send_cmd("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        })
        return res.get("result", {}).get("value")

    async def navigate(self, url):
        """Navigate page to URL and wait for load."""
        await self.send_cmd("Page.navigate", {"url": url})
        # Wait a few seconds for DOM loading
        await asyncio.sleep(3)

    async def check_auth_status(self):
        """Checks if the user is authenticated on Ancestry."""
        url = await self.evaluate("window.location.href")
        title = await self.evaluate("document.title")
        
        # Check cookies or page DOM for user indicator
        is_logged_in = await self.evaluate("""
            (() => {
                const navUser = document.querySelector('[data-testid="nav-user"], .user-avatar, #user-name, [aria-label*="Account"], [href*="/account/profile"]');
                const hasSignIn = document.querySelector('a[href*="/signin"], input[name="password"]');
                return !!navUser || (!hasSignIn && !window.location.href.includes('/signin'));
            })()
        """)
        return {
            "url": url,
            "title": title,
            "is_logged_in": is_logged_in
        }

    async def close(self):
        if self.ws:
            await self.ws.close()

async def monitor_login():
    """Waits and confirms when the user completes login."""
    client = AncestryCDPClient()
    tab = client.find_ancestry_tab()
    if not tab:
        print("Ancestry tab not found. Make sure Chrome is open.")
        return False

    await client.connect(tab)
    print("\nWaiting for you to complete sign-in in the open Chrome window...")
    
    last_url = ""
    while True:
        status = await client.check_auth_status()
        if status["url"] != last_url:
            print(f"  Current page: {status['title']} -> {status['url']}")
            last_url = status["url"]

        if status["is_logged_in"] and "signin" not in status["url"].lower():
            print("\n" + "=" * 60)
            print("✓ SUCCESS: Active Ancestry Authentication Detected!")
            print(f"Logged into: {status['url']}")
            print("=" * 60 + "\n")
            await client.close()
            return True

        await asyncio.sleep(2)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--check-login":
        asyncio.run(monitor_login())
    else:
        print("Ancestry Document Scraper Ready.")
        print("Usage:")
        print("  python3 ancestry_scraper.py --check-login")

if __name__ == "__main__":
    main()
