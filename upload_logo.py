"""Upload WORLD3.png logo to GitHub repo and update README to use it."""
import json, os, base64, urllib.request
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER = "codeworldentities"
REPO = "world3"

def api(method, path, data=None):
    url = f"https://api.github.com{path}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json", "User-Agent": "CodeWorld/3.0"}
    body = json.dumps(data).encode() if data else None
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def get_file(path):
    r = api("GET", f"/repos/{USER}/{REPO}/contents/{path}")
    content = base64.b64decode(r["content"]).decode()
    return content, r["sha"]

def update_file(path, content_b64, sha, msg):
    data = {"message": msg, "content": content_b64, "branch": "main"}
    if sha:
        data["sha"] = sha
    api("PUT", f"/repos/{USER}/{REPO}/contents/{path}", data)

# 1) Upload logo image
logo_path = r"C:\Users\shvel\Downloads\WORLD3.png"
with open(logo_path, "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode()

# Check if already exists
sha_logo = None
try:
    r = api("GET", f"/repos/{USER}/{REPO}/contents/assets/WORLD3.png")
    sha_logo = r["sha"]
except:
    pass

update_file("assets/WORLD3.png", logo_b64, sha_logo, "🎨 Add project logo")
print("Logo uploaded!")

# 2) Update README to show logo at top
readme, sha_readme = get_file("README.md")

# Replace the badge-based header with the logo
old_header = '<img src="https://img.shields.io/badge/Code_World-v3.0_Beta-00d4ff?style=for-the-badge'
logo_img = '<img src="assets/WORLD3.png" alt="Code World v3" width="200" />\n\n<img src="https://img.shields.io/badge/Code_World-v3.0_Beta-00d4ff?style=for-the-badge'

readme = readme.replace(old_header, logo_img)

update_file("README.md", base64.b64encode(readme.encode()).decode(), sha_readme, "🎨 Add logo to README")
print("README updated with logo!")

print("\nDone! https://github.com/codeworldentities/world3")
