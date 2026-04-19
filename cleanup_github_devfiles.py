"""Cleanup script — remove all dev{id}_ prefixed files from GitHub repos.

Run: python cleanup_github_devfiles.py
"""

import json
import os
import re
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
DEV_FILE_RE = re.compile(r"^dev\d+_\d+_")

API = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "CodeWorld-Cleanup/1.0",
}


def api(method, path, data=None):
    url = f"{API}{path}"
    body = json.dumps(data).encode() if data else None
    hdrs = dict(HEADERS)
    if body:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        if e.code == 404:
            return None
        raise RuntimeError(f"GitHub API {e.code}: {err}")


def list_repos():
    """Get all repos for the user."""
    repos = []
    page = 1
    while True:
        data = api("GET", f"/users/{USER}/repos?per_page=100&page={page}")
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.3)
    return repos


def get_tree(repo_name, branch="main"):
    """Get full recursive tree of a repo."""
    data = api("GET", f"/repos/{USER}/{repo_name}/git/trees/{branch}?recursive=1")
    if not data or "tree" not in data:
        return []
    return data["tree"]


def delete_file(repo_name, path, sha, branch="main"):
    """Delete a file from a repo."""
    data = {
        "message": f"🧹 cleanup: remove legacy dev-prefixed file {path}",
        "sha": sha,
        "branch": branch,
    }
    api("DELETE", f"/repos/{USER}/{repo_name}/contents/{path}", data)


def cleanup_repo(repo_name):
    """Remove all dev{id}_ files from a single repo."""
    print(f"\n📂 {repo_name}...")
    tree = get_tree(repo_name)
    if not tree:
        print(f"  ⚠ Could not read tree")
        return 0

    dev_files = []
    for item in tree:
        if item["type"] != "blob":
            continue
        basename = item["path"].rsplit("/", 1)[-1]
        if DEV_FILE_RE.match(basename):
            dev_files.append(item)

    if not dev_files:
        print(f"  ✅ Clean — no dev_ files")
        return 0

    print(f"  🗑 Found {len(dev_files)} dev_ files to remove")
    deleted = 0
    for f in dev_files:
        try:
            delete_file(repo_name, f["path"], f["sha"])
            deleted += 1
            print(f"    ✗ {f['path']}")
            time.sleep(0.4)  # Rate limit
        except Exception as e:
            print(f"    ⚠ Failed {f['path']}: {e}")
            time.sleep(1)

    return deleted


def main():
    if not TOKEN:
        print("❌ GITHUB_TOKEN not set in .env!")
        return

    print(f"🔍 Fetching repos for {USER}...")
    repos = list_repos()
    print(f"📁 Found {len(repos)} repos\n")

    total_deleted = 0
    for repo in repos:
        name = repo["name"]
        count = cleanup_repo(name)
        total_deleted += count
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"✅ Done! Deleted {total_deleted} dev_ files across {len(repos)} repos")


if __name__ == "__main__":
    main()
