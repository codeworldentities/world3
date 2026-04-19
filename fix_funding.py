"""Update Ko-fi link and remove PayPal from GitHub repo."""
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

def update_file(path, content, sha, msg):
    api("PUT", f"/repos/{USER}/{REPO}/contents/{path}", {
        "message": msg,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha,
        "branch": "main",
    })

# 1) Fix README.md
readme, sha = get_file("README.md")
readme = readme.replace("https://ko-fi.com/codeworld", "https://ko-fi.com/codeworldentities")
# Remove PayPal badge line
lines = readme.split("\n")
lines = [l for l in lines if "PayPal" not in l and "paypal" not in l]
readme = "\n".join(lines)
update_file("README.md", readme, sha, "☕ Update Ko-fi link, remove PayPal")
print("README.md updated!")

# 2) Fix FUNDING.yml
_, sha2 = get_file(".github/FUNDING.yml")
new_funding = "# These are supported funding model platforms\n\ngithub: [codeworldentities]\nko_fi: codeworldentities\n"
update_file(".github/FUNDING.yml", new_funding, sha2, "💖 Update Ko-fi, remove PayPal from funding")
print("FUNDING.yml updated!")

print("\nDone! https://github.com/codeworldentities/world3")
