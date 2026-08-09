import sqlite3
import re
from bs4 import BeautifulSoup

DB_PATH = '/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/preservation_output/genealogy_preservation.db'

def format_html_content(raw_html, filename, title):
    if not raw_html:
        return "<p class='text-amber-200/60 italic'>No preserved text content available for this record.</p>"

    soup = BeautifulSoup(raw_html, 'html.parser')

    # Remove UI artifacts, buttons, footers, return rules
    for tag in soup.find_all(['script', 'style', 'button', 'form']):
        tag.decompose()

    for img in soup.find_all('img'):
        src = img.get('src', '')
        if any(b in src.lower() for b in ['return', 'redrule', 'banner', 'ind-footer', 'email', 'copyright', 'button']):
            img.decompose()

    # Get body text or container
    body = soup.find('body') or soup

    # Extract clean paragraphs and lines
    lines = []
    for elem in body.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'div', 'tr', 'li', 'td']):
        txt = elem.get_text().strip()
        if txt and not any(x in txt.lower() for x in ['main page', 'photo gallery', 'what\'s new?', 'go to photo index', 'kuskarawoak', 'mitsawokett: a 17th']):
            lines.append(txt)

    if not lines:
        raw_text = soup.get_text()
        lines = [l.strip() for l in raw_text.splitlines() if l.strip() and not any(x in l.lower() for x in ['main page', 'photo gallery', 'what\'s new?'])]

    # Build clean formatted HTML document
    formatted_blocks = []

    # Title header
    clean_title = title if title and title != filename else filename.replace('.htm', '').replace('.html', '').replace('_', ' ').replace('-', ' ').title()
    formatted_blocks.append(f"<div class='border-b border-[#332D27] pb-4 mb-6'><h2 class='font-serif text-2xl font-bold text-[#F3EBE3] tracking-tight'>{clean_title}</h2><p class='text-xs font-mono text-[#C68B59] mt-1'>Preserved Primary Document • {filename}</p></div>")

    # Format content based on type (Bible, Will, Census, General)
    is_bible = 'bible' in filename.lower() or 'bible' in clean_title.lower()
    is_probate = 'will' in filename.lower() or 'probate' in filename.lower() or 'indenture' in filename.lower()

    if is_bible and len(lines) > 2:
        formatted_blocks.append("<div class='my-4 p-4 bg-[#181614] border border-[#2D2722] rounded-xl'><h3 class='text-sm font-semibold font-serif text-[#D4A373] uppercase tracking-wider mb-2'>Family Bible Register Entries</h3>")
        formatted_blocks.append("<div class='space-y-2 font-mono text-xs text-[#E5E1DB]'>")
        for line in lines:
            if len(line) < 3: continue
            # Highlight dates and names
            line_formatted = re.sub(r'(\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b|\b\d{4}\b)', r'<span class="text-[#C68B59] font-bold">\1</span>', line)
            formatted_blocks.append(f"<div class='p-2 bg-[#1C1A17] rounded border border-[#26221E] hover:border-[#C68B59]/40 transition-all'>{line_formatted}</div>")
        formatted_blocks.append("</div></div>")
    else:
        formatted_blocks.append("<div class='space-y-4 text-sm text-[#E5E1DB] leading-relaxed font-sans'>")
        for line in lines:
            if len(line) < 3: continue
            # Highlight names and key dates
            line_formatted = re.sub(r'(\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b|\b1[6789]\d{2}\b)', r'<span class="text-[#C68B59] font-bold font-mono">\1</span>', line)
            
            if len(line) < 60 and not line.endswith('.'):
                formatted_blocks.append(f"<h3 class='font-serif font-bold text-[#F3EBE3] text-base mt-4 mb-2 text-[#D4A373]'>{line_formatted}</h3>")
            else:
                formatted_blocks.append(f"<p class='bg-[#181614]/60 p-3 rounded-lg border border-[#26221E]'>{line_formatted}</p>")
        formatted_blocks.append("</div>")

    return "\n".join(formatted_blocks)

def convert_all():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT filename, title, clean_html, text_content FROM pages")
    rows = c.fetchall()
    print(f"Converting {len(rows)} preserved primary document pages into easy-to-read text...")

    updated_count = 0
    for r in rows:
        fn = r['filename']
        title = r['title']
        raw_html = r['clean_html'] or r['text_content']
        
        formatted_html = format_html_content(raw_html, fn, title)
        
        # Plain text version
        soup = BeautifulSoup(formatted_html, 'html.parser')
        plain_text = soup.get_text('\n').strip()

        c.execute("""
            UPDATE pages
            SET clean_html = ?, text_content = ?
            WHERE filename = ?
        """, (formatted_html, plain_text, fn))
        updated_count += 1

    conn.commit()
    conn.close()
    print(f"Successfully converted and formatted {updated_count} primary document pages!")

if __name__ == '__main__':
    convert_all()
