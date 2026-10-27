"""Export the published dashboard as a static, read-only GitHub Pages site."""
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = "https://koleso-tire-storage-regions.stonyrose8.chatgpt.site"
OUT = Path("docs")

def fetch(path):
    req = Request(SOURCE + path, headers={"User-Agent": "Koleso42-dashboard-sync/1.0", "Cache-Control": "no-cache"})
    with urlopen(req, timeout=90) as response:
        return response.read()

def prepare(html, raw_snapshot, head):
    snapshot = json.loads(raw_snapshot)
    if not isinstance(snapshot.get("queries"), dict) or not snapshot["queries"].get("tariffs", {}).get("rows"):
        raise ValueError("Source has no tariff rows; retain previous publication")
    marker = re.search(r'<meta name="data-app-snapshot-sha256" content="([^"]+)">', html)
    if not marker or marker[1] != head.get("snapshotSha256"):
        raise ValueError("Source changed during export; retry later")
    if 'const localSource = ' not in html:
        raise ValueError("Unsupported dashboard bootstrap")
    html = re.sub(r'<meta name="data-app-snapshot-storage"[^>]*>', '', html)
    html = re.sub(r'<meta name="data-app-sites-project"[^>]*>', '', html)
    html = html.replace('<html lang="en">', '<html lang="ru">')
    html = html.replace('<head>', '<head><meta name="data-app-local-snapshot" content="./snapshot.json">', 1)
    html = html.replace('fetch(new URL(localSource, document.baseURI), {credentials: "same-origin"})',
                        'fetch(new URL(localSource, document.baseURI), {credentials: "same-origin", cache: "no-store"})')
    # Static copies have no authenticated editing backend.
    view = '<script>const u=new URL(location.href);u.searchParams.set("view","1");if(!u.searchParams.has("tab"))u.searchParams.set("tab","compare");history.replaceState(null,"",u);</script>'
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + view, 1)
    return html, snapshot

def main():
    html = fetch("/").decode("utf-8")
    raw = fetch("/api/snapshot")
    head = json.loads(fetch("/api/snapshot/head"))
    html, snapshot = prepare(html, raw, head)
    OUT.mkdir(exist_ok=True)
    (OUT / "snapshot.json").write_bytes(raw)
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    manifest = {"source": SOURCE, "sourceSnapshotSha256": head["snapshotSha256"],
                "dataRefresh": snapshot.get("refresh"), "snapshotFileSha256": hashlib.sha256(raw).hexdigest()}
    (OUT / "source.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Exported", len(snapshot["queries"]["tariffs"]["rows"]), "tariff rows;",
          snapshot.get("refresh", {}).get("date", "source date unknown"))

if __name__ == "__main__":
    main()
