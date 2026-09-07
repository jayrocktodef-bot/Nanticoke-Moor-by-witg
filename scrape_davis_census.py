#!/usr/bin/env python3
"""
scrape_davis_census.py

Focused Ancestry.com Delaware Census Scraper for the Davis Family.
Interacts with the authenticated Chrome session (port 9222) via CDP.
"""

import asyncio
import json
import os
import sys
import time
import re
import urllib.request
import websockets
import sqlite3

CDP_HTTP_URL = "http://localhost:9222"
TREE_ID = "68065145"
OUTPUT_DIR = os.path.abspath("preservation_output/ancestry_documents/delaware_census")
DB_PATH = "preservation_output/genealogy_preservation.db"

CENSUS_COLLECTIONS = {
    "8054": "1850",
    "7667": "1860",
    "7163": "1870",
    "6742": "1880",
    "7602": "1900",
    "7884": "1910",
    "6061": "1920",
    "6224": "1930",
    "2442": "1940",
    "62308": "1950",
}

class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self.msg_id = 0

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=100 * 1024 * 1024)

    async def close(self):
        if self.ws:
            await self.ws.close()

    async def call(self, method, params=None):
        self.msg_id += 1
        cid = self.msg_id
        await self.ws.send(json.dumps({"id": cid, "method": method, "params": params or {}}))
        while True:
            raw = await self.ws.recv()
            resp = json.loads(raw)
            if resp.get("id") == cid:
                return resp

    async def eval_js(self, expression):
        res = await self.call("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        })
        return res.get("result", {}).get("result", {}).get("value")

    async def navigate(self, url, wait_sec=4):
        await self.call("Page.navigate", {"url": url})
        await asyncio.sleep(wait_sec)

def get_open_tabs():
    try:
        with urllib.request.urlopen(f"{CDP_HTTP_URL}/json/list", timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"Error fetching tabs: {e}")
        return []

def open_or_get_working_tab():
    tabs = get_open_tabs()
    # Find existing scraper tab or create new
    for t in tabs:
        if t.get("type") == "page" and "listofallpeople" in t.get("url", ""):
            return t
    # Or create a new tab
    req = urllib.request.Request(f"{CDP_HTTP_URL}/json/new?https://www.ancestry.com", method="PUT")
    return json.loads(urllib.request.urlopen(req).read())

async def extract_davis_people_from_tree():
    """Extracts all Davis family members listed in tree 68065145."""
    tab = open_or_get_working_tab()
    client = CDPClient(tab["webSocketDebuggerUrl"])
    await client.connect()

    url = f"https://www.ancestry.com/family-tree/tree/{TREE_ID}/listofallpeople?name=Davis"
    print(f"Navigating to Davis tree directory: {url}")
    await client.navigate(url, wait_sec=5)

    js = """
    (() => {
        const rows = Array.from(document.querySelectorAll('a[href*="/person/"]')).map(a => {
            const m = a.href.match(/person\\/(\\d+)/);
            // Also look for birth/death text nearby
            const container = a.closest('tr') || a.closest('li') || a.parentElement;
            return {
                name: a.innerText.trim(),
                pid: m ? m[1] : null,
                details: container ? container.innerText.replace(/\\n/g, ' -- ').trim() : ''
            };
        }).filter(p => p.name && p.pid && p.name.toLowerCase().includes('davis'));

        const map = new Map();
        for (const r of rows) {
            if (!map.has(r.pid)) {
                map.set(r.pid, r);
            }
        }
        return Array.from(map.values());
    })()
    """
    people = await client.eval_js(js)
    await client.close()
    return people or []

async def get_person_sources(client, pid):
    """Fetches all source records attached to a person's facts page."""
    url = f"https://www.ancestry.com/family-tree/person/tree/{TREE_ID}/person/{pid}/facts"
    print(f"  Navigating to Facts page for PID {pid}: {url}")
    await client.navigate(url, wait_sec=4)

    js = """
    (() => {
        const results = [];
        // Ancestry modern UI has source buttons and links
        const links = Array.from(document.querySelectorAll('a[href*="/interactive/"], a[href*="/discoveryui-content/"], a[href*="/search/collections/"]'));
        
        for (const a of links) {
            const href = a.href;
            const container = a.closest('li') || a.closest('tr') || a.parentElement;
            const text = (container ? container.innerText : a.innerText).trim();
            results.push({
                text: text,
                href: href
            });
        }
        return results;
    })()
    """
    sources = await client.eval_js(js)
    return sources or []

async def scrape_census_record(client, record_url, person_name, target_dir):
    """Extracts transcript and downloads high-res image from a census record or interactive viewer URL."""
    print(f"    Inspecting Record: {record_url}")
    
    # If it is an /interactive/ URL, convert to /discoveryui-content/view/ or navigate directly
    m_int = re.search(r'/interactive/(\d+)/([^/]+)/(\d+)', record_url)
    m_disc = re.search(r'/discoveryui-content/view/(\d+):(\d+)', record_url)
    
    coll_id = None
    record_id = None
    image_slug = None

    if m_int:
        coll_id = m_int.group(1)
        image_slug = m_int.group(2)
        record_id = m_int.group(3)
    elif m_disc:
        record_id = m_disc.group(1)
        coll_id = m_disc.group(2)

    # 1. First navigate to the discoveryui-content view for full structured transcription
    if record_id and coll_id:
        view_url = f"https://www.ancestry.com/discoveryui-content/view/{record_id}:{coll_id}"
    else:
        view_url = record_url

    await client.navigate(view_url, wait_sec=3)

    # Extract transcription data
    transcription_js = """
    (() => {
        const bodyText = document.body.innerText;
        const title = document.title;
        const heading = document.querySelector('h1')?.innerText?.trim() || '';

        // Extract household table
        const household = [];
        const rows = document.querySelectorAll('table tr');
        for (const r of rows) {
            const cells = Array.from(r.querySelectorAll('th, td')).map(c => c.innerText.trim());
            if (cells.length >= 2) {
                household.push(cells);
            }
        }

        // Extract key-value lines
        const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
        
        // Find citation
        let citation = '';
        const citIdx = lines.findIndex(l => l.toLowerCase().includes('citation'));
        if (citIdx !== -1 && citIdx + 1 < lines.length) {
            citation = lines[citIdx + 1];
        }

        // Image link if available
        const imgLink = document.querySelector('a[href*="/imageviewer/"]')?.href || '';

        return {
            title: title,
            heading: heading,
            bodyText: bodyText,
            household: household,
            citation: citation,
            imageLink: imgLink
        };
    })()
    """
    rec_data = await client.eval_js(transcription_js)
    if not rec_data:
        print("    [Warning] Failed to extract record metadata.")
        return None

    # Parse key census fields from body text
    body = rec_data.get("bodyText", "")
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    fields = {}
    
    target_labels = [
        "Name", "Age", "Birth Date", "Birthplace", "Home in 1850", "Home in 1860", 
        "Home in 1870", "Home in 1880", "Home in 1900", "Home in 1910", "Home in 1920", 
        "Home in 1930", "Home in 1940", "Home in 1950", "Residence", "House Number", 
        "Sheet Number", "Number of Dwelling in Order of Visitation", "Family Number", 
        "Race", "Gender", "Relation to Head of House", "Marital Status", 
        "Father's Name", "Father's Birthplace", "Mother's Name", "Mother's Birthplace",
        "Occupation", "Industry"
    ]

    for i, line in enumerate(lines):
        for lbl in target_labels:
            if line.lower() == lbl.lower() and i + 1 < len(lines):
                val = lines[i + 1]
                if val not in target_labels and len(val) < 150:
                    fields[lbl] = val

    year = CENSUS_COLLECTIONS.get(coll_id, "Census")
    primary_name = fields.get("Name", person_name)
    place = fields.get("Home in " + year, fields.get("Residence", "Delaware"))
    print(f"    ✓ Extracted {year} Census Transcript for {primary_name} ({place})")

    # 2. Download Image Viewer
    img_link = rec_data.get("imageLink")
    if not img_link and image_slug and coll_id:
        img_link = f"https://www.ancestry.com/imageviewer/collections/{coll_id}/images/{image_slug}?pId={record_id}"

    saved_img_path = None
    if img_link:
        print(f"    Navigating to Image Viewer: {img_link}")
        await client.navigate(img_link, wait_sec=4)

        # Set download directory
        await client.call("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": target_dir})

        # Pre-count existing files
        before_files = set(os.listdir(target_dir))

        # Open Tool Menu and click Download
        click_download_js = """
        (() => {
            const toolBtn = Array.from(document.querySelectorAll('button')).find(b => b.getAttribute('title') === 'Tool menu' || b.innerText.includes('Tool menu'));
            if (toolBtn) {
                toolBtn.click();
            }
            setTimeout(() => {
                const dl = Array.from(document.querySelectorAll('.iconDownload, button')).find(el => el.innerText.trim() === 'Download');
                if (dl) dl.click();
            }, 500);
            return true;
        })()
        """
        await client.eval_js(click_download_js)

        # Wait for file download
        for _ in range(12):
            await asyncio.sleep(1)
            after_files = set(os.listdir(target_dir))
            new_files = [f for f in (after_files - before_files) if not f.endswith(".crdownload")]
            if new_files:
                saved_img_path = os.path.join(target_dir, new_files[0])
                print(f"    ✓ Scanned Sheet Downloaded: {new_files[0]} ({os.path.getsize(saved_img_path):,} bytes)")
                break

    # Save structured metadata json
    meta = {
        "person_name": primary_name,
        "census_year": year,
        "collection_id": coll_id,
        "record_id": record_id,
        "fields": fields,
        "household": rec_data.get("household", []),
        "citation": rec_data.get("citation", ""),
        "source_url": view_url,
        "image_file": os.path.basename(saved_img_path) if saved_img_path else None
    }

    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', primary_name)
    meta_filename = f"{year}_{safe_name}_{record_id}.json"
    meta_path = os.path.join(target_dir, meta_filename)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"    ✓ Metadata JSON Saved: {meta_filename}")

    return meta

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 70)
    print("  ANCESTRY.COM DELAWARE CENSUS SCRAPER - DAVIS FAMILY")
    print(f"  Target Output: {OUTPUT_DIR}")
    print("=" * 70 + "\n")

    # 1. Discover Davis ancestors from tree
    print("Phase 1: Discovering Davis Ancestors in tree...")
    davis_people = await extract_davis_people_from_tree()
    print(f"Found {len(davis_people)} Davis individuals in tree.\n")
    for p in davis_people[:25]:
        print(f"  - [{p['pid']}] {p['name']} | {p.get('details', '')[:60]}")

    # Prioritize key Delaware Davis ancestors:
    priority_ids = [
        "112216028092", # Charles Morris Davis (1898-1948)
        "112740815327", # Albert Carmenthis Davis Sr (1938-2011)
        "40345353629",  # Delphine Mae Davis (1939-2002)
        "112216028090", # Bertha May Davis (1893-1982)
        "40345368274",  # Elsie Rebecca Davis (1896-1939)
        "112441598215", # Clarence D Davis (1926-1991)
        "40345372212",  # Alonzo F. Davis (1937-)
    ]

    import datetime
    current_year = datetime.datetime.now().year

    def is_probably_living(person_data):
        name = person_data.get("name", "").lower()
        details = person_data.get("details", "").lower()
        
        if "living" in name or "living" in details:
            return True
            
        # If there's an explicit death indicator
        if "death" in details or "died" in details or "passed away" in details:
            return False
            
        # Extract 4-digit years from details
        years = [int(y) for y in re.findall(r'\b(1[789]\d{2}|20[012]\d)\b', details)]
        if len(years) >= 2:
            return False # Likely has birth and death years
            
        if len(years) == 1:
            birth_year = years[0]
            if current_year - birth_year > 110:
                return False # Over 110 years old, assume deceased
            return True # Has birth but no death, and < 110 years old
            
        return False # Cannot determine, err on side of caution

    # Combine priority with all discovered
    candidate_pids = []
    for pid in priority_ids:
        candidate_pids.append(pid)
    for p in davis_people:
        if p["pid"] not in candidate_pids:
            if is_probably_living(p):
                print(f"  [Privacy] Skipping likely living person: {p['name']}")
                continue
            candidate_pids.append(p["pid"])

    print(f"\nPhase 2: Extracting Census Records for {len(candidate_pids)} Davis ancestors...")
    tab = open_or_get_working_tab()
    client = CDPClient(tab["webSocketDebuggerUrl"])
    await client.connect()

    processed_records_file = os.path.join(OUTPUT_DIR, "processed_urls.txt")
    processed_records = set()
    if os.path.exists(processed_records_file):
        with open(processed_records_file, "r") as f:
            for line in f:
                processed_records.add(line.strip())
                
    total_saved = 0

    for pid in candidate_pids:
        person_info = next((p for p in davis_people if p["pid"] == pid), {"name": f"Davis Ancestor {pid}", "pid": pid})
        print(f"\n=======================================================")
        print(f"Processing: {person_info['name']} (PID: {pid})")
        print(f"=======================================================")

        try:
            sources = await get_person_sources(client, pid)
            census_sources = []
            for s in sources:
                href = s.get("href", "")
                text = s.get("text", "")
                # Check if census
                is_census = any(coll in href for coll in CENSUS_COLLECTIONS.keys()) or "census" in text.lower()
                if is_census and href:
                    census_sources.append(s)

            print(f"  Found {len(census_sources)} attached census records.")

            for s in census_sources:
                href = s["href"]
                if href in processed_records:
                    continue
                processed_records.add(href)

                try:
                    meta = await scrape_census_record(client, href, person_info["name"], OUTPUT_DIR)
                    if meta:
                        total_saved += 1
                        with open(processed_records_file, "a") as f:
                            f.write(href + "\n")
                except Exception as ex:
                    print(f"    [Error scraping record]: {ex}")

                # Gentle pacing between records
                await asyncio.sleep(2.5)

        except Exception as ex:
            print(f"  [Error processing PID {pid}]: {ex}")

    await client.close()
    print(f"\n" + "=" * 70)
    print(f"  DAVIS FAMILY CENSUS INGESTION COMPLETE: {total_saved} records preserved!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
