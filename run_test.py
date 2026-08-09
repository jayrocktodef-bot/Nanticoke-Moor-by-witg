import subprocess
try:
    result = subprocess.run(["python3", "/home/jequan/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/scrape_mitsawokett_photos_v2.py"], capture_output=True, text=True)
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
except Exception as e:
    print("Exception", e)
