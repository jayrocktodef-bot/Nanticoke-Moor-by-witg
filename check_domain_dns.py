import subprocess
import time
import sys

subdomain = "FamilyArchive.writteninthegenome.blog"

print(f"Checking DNS resolution for {subdomain}...")

cmd = ["dig", "CNAME", subdomain, "+short"]
res = subprocess.run(cmd, capture_output=True, text=True)
output = res.stdout.strip()

if "vercel" in output.lower():
    print(f"✅ SUCCESS! {subdomain} resolves to {output}")
else:
    print(f"⏳ CNAME record not detected yet. (Current dig output: '{output}')")
