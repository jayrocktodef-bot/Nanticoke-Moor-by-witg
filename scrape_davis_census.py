#!/usr/bin/env python3
"""
scrape_davis_census.py

Automated Ancestry.com Historical Document Scraper for Delmarva Genealogies.
Connects to an authenticated Chrome browser session (port 9222) via CDP.

Capabilities:
1. Reuses active authenticated Ancestry browser tabs on port 9222.
2. Discovers tree members across all paginated tree directories.
3. Automatically extracts Federal Censuses (1850-1950), Delaware Marriage records,
   Draft registration cards, Vital records, and SSDI.
4. Downloads original high-resolution microfilm/scanned sheet images.
5. Saves structured metadata JSON files and mirror-syncs to frontend public assets.
6. Automatically integrates newly saved records into SQLite and frontend transcriptions.
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
import shutil
import glob

CDP_HTTP_URL = "http://localhost:9222"
TREE_ID = "68065145"
OUTPUT_DIR = os.path.abspath("preservation_output/ancestry_documents/delaware_census")
FRONTEND_DIR = os.path.abspath("frontend/public/ancestry_documents/delaware_census")
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

SUPPORTED_COLLECTIONS = {
    # Censuses
    "8054": ("1850", "1850 United States Federal Census"),
    "7667": ("1860", "1860 United States Federal Census"),
    "7163": ("1870", "1870 United States Federal Census"),
    "6742": ("1880", "1880 United States Federal Census"),
    "7602": ("1900", "1900 United States Federal Census"),
    "7884": ("1910", "1910 United States Federal Census"),
    "6061": ("1920", "1920 United States Federal Census"),
    "6224": ("1930", "1930 United States Federal Census"),
    "2442": ("1940", "1940 United States Federal Census"),
    "62308": ("1950", "1950 United States Federal Census"),
    # Delaware Vitals & Church/Probate
    "61368": ("Marriage", "Delaware, U.S., Marriage Records, 1750-1954"),
    "61843": ("Marriage", "Delaware, U.S., Marriage Records"),
    "62209": ("Vital", "Delaware, U.S., Birth and Death Records"),
    "9044": ("Probate", "Delaware Wills and Probate Records"),
    # Military
    "2238": ("WWII", "U.S., World War II Draft Registration Cards"),
    "6482": ("WWI", "U.S., World War I Draft Registration Cards"),
    # Social Security & Directory
    "60901": ("SSDI", "U.S., Social Security Applications and Claims Index"),
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
            try:
                await self.ws.close()
            except Exception:
                pass

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
    # 1. Prefer existing Ancestry tab
    for t in tabs:
        if t.get("type") == "page" and "ancestry.com" in t.get("url", ""):
            return t
    # 2. Prefer any open page tab
    for t in tabs:
        if t.get("type") == "page":
            return t
    # 3. Create a new tab
    req = urllib.request.Request(f"{CDP_HTTP_URL}/json/new?https://www.ancestry.com", method="PUT")
    return json.loads(urllib.request.urlopen(req).read())

def extract_coll_and_rec(url):
    m_int = re.search(r'/interactive/(\d+)/([^/]+)/(\d+)', url)
    m_disc = re.search(r'/discoveryui-content/view/(\d+):(\d+)', url)
    m_search = re.search(r'/collections/(\d+)/records/(\d+)', url)
    if m_int:
        return m_int.group(1), m_int.group(3)
    if m_disc:
        return m_disc.group(2), m_disc.group(1)
    if m_search:
        return m_search.group(1), m_search.group(2)
    return None, None

def get_processed_keys(output_dir):
    processed_keys = set()
    processed_urls_file = os.path.join(output_dir, "processed_urls.txt")
    if os.path.exists(processed_urls_file):
        with open(processed_urls_file, "r", encoding="utf-8") as f:
            for line in f:
                u = line.strip()
                cid, rid = extract_coll_and_rec(u)
                if cid and rid:
                    processed_keys.add(f"{cid}:{rid}")
                if u:
                    processed_keys.add(u)

    # Also inspect all existing JSON files in directory
    for jf in glob.glob(os.path.join(output_dir, "*.json")):
        try:
            with open(jf, "r", encoding="utf-8") as fp:
                d = json.load(fp)
                cid = str(d.get("collection_id", ""))
                rid = str(d.get("record_id", ""))
                if cid and rid:
                    processed_keys.add(f"{cid}:{rid}")
                s_url = d.get("source_url", "")
                if s_url:
                    processed_keys.add(s_url)
        except Exception:
            pass

    return processed_keys

async def extract_people_from_tree(surname="Davis"):
    """Extracts all family members with given surname listed in tree 68065145 across all pages."""
    tab = open_or_get_working_tab()
    client = CDPClient(tab["webSocketDebuggerUrl"])
    await client.connect()

    people_map = {}
    page_num = 1
    while True:
        url = f"https://www.ancestry.com/family-tree/tree/{TREE_ID}/listofallpeople?name={surname}&rows=100#page={page_num}"
        print(f"Navigating to {surname} tree directory page {page_num}: {url}")
        await client.navigate(url, wait_sec=4)

        js = r"""
        (() => {
            const rows = [];
            const anchors = document.querySelectorAll('a');
            for (const a of anchors) {
                const href = a.getAttribute('href') || '';
                const match = href.match(/\/person\/(\d+)$/);
                if (match) {
                    const tr = a.closest('tr');
                    rows.push({
                        pid: match[1],
                        name: a.innerText.trim(),
                        details: tr ? tr.innerText.replace(/\s+/g, ' ').trim() : ''
                    });
                }
            }
            return rows;
        })()
        """
        page_rows = await client.eval_js(js) or []
        new_count = 0
        for r in page_rows:
            if r.get("pid") and r["pid"] not in people_map:
                people_map[r["pid"]] = r
                new_count += 1
        print(f"  Page {page_num}: retrieved {len(page_rows)} entries ({new_count} new, total: {len(people_map)})")
        if new_count == 0 or len(page_rows) < 100:
            break
        page_num += 1
        if page_num > 50:
            break

    await client.close()
    return list(people_map.values())

async def get_person_sources(client, pid):
    """Fetches all source records attached to a person's facts page."""
    url = f"https://www.ancestry.com/family-tree/person/tree/{TREE_ID}/person/{pid}/facts"
    print(f"  Navigating to Facts page for PID {pid}: {url}")
    await client.navigate(url, wait_sec=3.5)

    js = r"""
    (() => {
        const results = [];
        const links = Array.from(document.querySelectorAll('a[href*="/interactive/"], a[href*="/discoveryui-content/"], a[href*="/search/collections/"]'));
        for (const a of links) {
            const container = a.closest('li') || a.closest('tr') || a.parentElement;
            results.push({
                text: (container ? container.innerText : a.innerText).replace(/\s+/g, ' ').trim(),
                href: a.href
            });
        }
        return results;
    })()
    """
    sources = await client.eval_js(js)
    return sources or []

async def scrape_census_record(client, record_url, person_name, target_dir):
    """Extracts transcript and downloads high-res image from a record or interactive viewer URL."""
    print(f"    Inspecting Record: {record_url}")
    
    m_int = re.search(r'/interactive/(\d+)/([^/]+)/(\d+)', record_url)
    m_disc = re.search(r'/discoveryui-content/view/(\d+):(\d+)', record_url)
    m_search = re.search(r'/collections/(\d+)/records/(\d+)', record_url)
    
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
    elif m_search:
        coll_id = m_search.group(1)
        record_id = m_search.group(2)

    # 1. First navigate to the discoveryui-content view for full structured transcription
    if record_id and coll_id:
        view_url = f"https://www.ancestry.com/discoveryui-content/view/{record_id}:{coll_id}"
    else:
        view_url = record_url

    await client.navigate(view_url, wait_sec=3)

    # Extract transcription data
    transcription_js = r"""
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
        const lines = bodyText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        
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

    # Parse key census & vital fields from body text
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
        "Occupation", "Industry", "Spouse", "Child", "Marriage Date", "Marriage Place",
        "Death Date", "Death Place", "Burial Place", "Draft Board", "Employer",
        "Complexion", "Eye Color", "Hair Color", "Weight", "Height"
    ]

    for i, line in enumerate(lines):
        for lbl in target_labels:
            if line.lower() == lbl.lower() and i + 1 < len(lines):
                val = lines[i + 1]
                if val not in target_labels and len(val) < 150:
                    fields[lbl] = val

    coll_info = SUPPORTED_COLLECTIONS.get(coll_id, (CENSUS_COLLECTIONS.get(coll_id, "Record"), "Historical Record"))
    tag_name = coll_info[0]
    coll_title = coll_info[1]
    primary_name = fields.get("Name", person_name)
    place = fields.get("Home in " + tag_name, fields.get("Residence", fields.get("Marriage Place", fields.get("Death Place", "Delaware"))))
    print(f"    ✓ Extracted {tag_name} Transcript for {primary_name} ({place})")

    # 2. Download Image Viewer if scan is available
    img_link = rec_data.get("imageLink")
    if not img_link and image_slug and coll_id:
        img_link = f"https://www.ancestry.com/imageviewer/collections/{coll_id}/images/{image_slug}?pId={record_id}"

    saved_img_path = None
    if img_link:
        print(f"    Navigating to Image Viewer: {img_link}")
        await client.navigate(img_link, wait_sec=4)

        # Set download directory in Chrome
        try:
            await client.call("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": target_dir, "eventsEnabled": True})
        except Exception:
            pass
        try:
            await client.call("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": target_dir})
        except Exception:
            pass

        before_files = set(os.listdir(target_dir))
        home_downloads = os.path.expanduser("~/Downloads")
        before_home = set(os.listdir(home_downloads)) if os.path.exists(home_downloads) else set()

        # Click Tool Menu and Download button
        click_download_js = r"""
        (() => {
            const toolBtn = Array.from(document.querySelectorAll('button')).find(b => 
                (b.getAttribute('title') || '').includes('Tool menu') || 
                (b.innerText || '').includes('Tool menu')
            );
            if (toolBtn) {
                toolBtn.click();
            }
            setTimeout(() => {
                const dl = Array.from(document.querySelectorAll('.iconDownload, button')).find(el => 
                    (el.innerText || '').trim() === 'Download' || (el.className || '').includes('iconDownload')
                );
                if (dl) dl.click();
            }, 600);
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
                
            # Check fallback in ~/Downloads
            if os.path.exists(home_downloads):
                after_home = set(os.listdir(home_downloads))
                new_home = [f for f in (after_home - before_home) if not f.endswith(".crdownload") and (f.endswith(".jpg") or f.endswith(".jpeg"))]
                if new_home:
                    src = os.path.join(home_downloads, new_home[0])
                    dst = os.path.join(target_dir, new_home[0])
                    shutil.move(src, dst)
                    saved_img_path = dst
                    print(f"    ✓ Scanned Sheet Relocated from Downloads: {new_home[0]} ({os.path.getsize(saved_img_path):,} bytes)")
                    break

    # Save structured metadata json
    meta = {
        "person_name": primary_name,
        "census_year": tag_name,
        "collection_title": coll_title,
        "collection_id": coll_id,
        "record_id": record_id,
        "fields": fields,
        "household": rec_data.get("household", []),
        "citation": rec_data.get("citation", ""),
        "source_url": view_url,
        "image_file": os.path.basename(saved_img_path) if saved_img_path else None
    }

    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', primary_name)
    meta_filename = f"{tag_name}_{safe_name}_{record_id}.json"
    meta_path = os.path.join(target_dir, meta_filename)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"    ✓ Metadata JSON Saved: {meta_filename}")

    # Mirror copy to frontend public directory
    os.makedirs(FRONTEND_DIR, exist_ok=True)
    if saved_img_path and os.path.exists(saved_img_path):
        shutil.copy2(saved_img_path, os.path.join(FRONTEND_DIR, os.path.basename(saved_img_path)))
    if os.path.exists(meta_path):
        shutil.copy2(meta_path, os.path.join(FRONTEND_DIR, meta_filename))

    return meta

async def run_scraper(target_surnames=None, max_new_records=50):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FRONTEND_DIR, exist_ok=True)

    if target_surnames is None:
        target_surnames = ["Davis"]

    print("=" * 70)
    print("  ANCESTRY.COM DELMARVA DOCUMENT PRESERVATION SCRAPER")
    print(f"  Target Surnames: {', '.join(target_surnames)}")
    print(f"  Output Directory: {OUTPUT_DIR}")
    print(f"  Frontend Mirror: {FRONTEND_DIR}")
    print("=" * 70 + "\n")

    processed_keys = get_processed_keys(OUTPUT_DIR)
    print(f"Loaded {len(processed_keys)} previously processed record keys.")

    tab = open_or_get_working_tab()
    client = CDPClient(tab["webSocketDebuggerUrl"])
    await client.connect()

    import datetime
    current_year = datetime.datetime.now().year

    def is_probably_living(details, name):
        details_l = details.lower()
        name_l = name.lower()
        if "living" in name_l or "living" in details_l:
            return True
        if "death" in details_l or "died" in details_l or "passed away" in details_l:
            return False
        years = [int(y) for y in re.findall(r'\b(1[789]\d{2}|20[012]\d)\b', details_l)]
        if len(years) >= 2:
            return False
        if len(years) == 1:
            if current_year - years[0] > 105:
                return False
            return True
        return False

    total_saved = 0
    processed_urls_file = os.path.join(OUTPUT_DIR, "processed_urls.txt")

    for surname in target_surnames:
        print(f"\n--- Gathering Ancestors for Surname: {surname} ---")
        try:
            people = await extract_people_from_tree(surname)
        except Exception as e:
            print(f"Error fetching people for {surname}: {e}")
            continue

        print(f"Found {len(people)} individuals for {surname}.")

        for person in people:
            if total_saved >= max_new_records:
                print(f"Reached session goal of {max_new_records} records.")
                break

            pid = person["pid"]
            name = person["name"]
            details = person.get("details", "")

            if is_probably_living(details, name):
                continue

            print(f"\nProcessing: {name} (PID: {pid})")
            try:
                sources = await get_person_sources(client, pid)
                matching_sources = []
                for s in sources:
                    href = s.get("href", "")
                    text = s.get("text", "")
                    cid, rid = extract_coll_and_rec(href)
                    key = f"{cid}:{rid}" if (cid and rid) else href

                    if key in processed_keys or href in processed_keys:
                        continue

                    is_match = (cid in SUPPORTED_COLLECTIONS) or \
                               any(k in text.lower() for k in ["census", "marriage", "draft", "birth", "death", "social security"])
                    if is_match and href:
                        matching_sources.append((s, key))

                print(f"  Found {len(matching_sources)} new records attached to {name}.")

                for s, key in matching_sources:
                    if total_saved >= max_new_records:
                        break

                    href = s["href"]
                    try:
                        meta = await scrape_census_record(client, href, name, OUTPUT_DIR)
                        if meta:
                            total_saved += 1
                            processed_keys.add(key)
                            processed_keys.add(href)
                            with open(processed_urls_file, "a", encoding="utf-8") as f:
                                f.write(href + "\n")
                    except Exception as ex:
                        print(f"    [Error scraping record]: {ex}")

                    await asyncio.sleep(2.5)

            except Exception as ex:
                print(f"  [Error processing PID {pid}]: {ex}")

    await client.close()

    print("\n" + "=" * 70)
    print(f"  SCRAPING COMPLETE: {total_saved} new records preserved and synced!")
    print("=" * 70)

    # Automatically run integration
    try:
        print("\nTriggering database & frontend integration...")
        import subprocess
        subprocess.run(["python3", "integrate_census_documents.py"], check=True)
    except Exception as e:
        print(f"Error during integration step: {e}")

if __name__ == "__main__":
    surnames = ["Davis"]
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        surnames = [s.strip() for s in sys.argv[1].split(",")]
    asyncio.run(run_scraper(target_surnames=surnames, max_new_records=30))
