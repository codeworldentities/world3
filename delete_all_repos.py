"""Delete all repos from codeworldentities GitHub account."""

import json
import os
import time
import urllib.request
import urllib.error

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER = "codeworldentities"
API = "https://api.github.com"


def api(method, path, data=None):
    url = f"{API}{path}"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "CodeWorld-Cleanup/1.0",
    }
    body = json.dumps(data).encode() if data else None
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status == 204:
                return {}
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        if e.code == 204:
            return {}
        raise RuntimeError(f"GitHub API {e.code}: {err}")


def list_repos():
    repos = []
    page = 1
    while True:
        data = api("GET", f"/user/repos?per_page=100&page={page}&type=owner")
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.3)
    return repos


def main():
    if not TOKEN:
        print("GITHUB_TOKEN not set!")
        return

    print(f"Fetching repos for {USER}...")
    repos = list_repos()
    print(f"Found {len(repos)} repos to delete\n")

    deleted = 0
    for repo in repos:
        name = repo["name"]
        try:
            api("DELETE", f"/repos/{USER}/{name}")
            deleted += 1
            print(f"  [{deleted}/{len(repos)}] Deleted: {name}")
            time.sleep(0.5)
        except Exception as e:
            print(f"  FAILED: {name} — {e}")
            time.sleep(1)

    print(f"\nDone! Deleted {deleted}/{len(repos)} repos")


if __name__ == "__main__":
    main()
