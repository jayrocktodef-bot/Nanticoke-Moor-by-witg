import urllib.parse
import re
import requests
from bs4 import BeautifulSoup
session = requests.Session()
IGNORE_IMAGES = [
    "ind-footer.gif", "email.fw.png", "email.jpg", "bg.jpg", 
    "background.jpg", "backgr.jpg", "back.jpg", "logo.jpg", "logo.gif", "email1.jpg"
]
url = "https://nativeamericansofdelawarestate.com/Mitsawokett%20Photos/IndexA-C.htm"
r = session.get(url)
soup = BeautifulSoup(r.text, "html.parser")
pages = []
for a in soup.find_all("a")[:30]:
    href = a.get("href")
    if not href: continue
    full = urllib.parse.urljoin(url, href)
    if "Mitsawokett%20Photos/" in full and full.endswith((".htm", ".html")) and "Index" not in full:
        pages.append(full)
print("Found pages:", pages[:3])
for p in pages[:1]:
    r = session.get(p)
    print("Fetched", p, r.status_code)
    soup = BeautifulSoup(r.text, "html.parser")
    for img in soup.find_all("img"):
        print("IMG:", img.get("src"))
