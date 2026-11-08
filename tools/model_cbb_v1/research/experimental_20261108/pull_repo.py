#!/usr/bin/env python3
"""Pull durable CBB artifacts from the public repo read-only. Skips files already local."""
import json, os, sys, time, gzip, urllib.request

RAW = "https://raw.githubusercontent.com/Garrettwalker1/ediths-picks/main/tools/model_cbb_v1/data"
API = "https://api.github.com/repos/Garrettwalker1/ediths-picks/contents/tools/model_cbb_v1/data"
UA = {"User-Agent": "Mozilla/5.0 (model research)", "Accept": "application/vnd.github+json"}

def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    for a in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read() if binary else json.load(r)
        except Exception as e:
            if a == 2: print(f"FAIL {url}: {e}", file=sys.stderr); return None
            time.sleep(1.5)

def pull_summaries(outdir, limit=400):
    os.makedirs(outdir, exist_ok=True)
    listing = get(f"{API}/summaries")
    if not listing: return 0
    n = 0
    for item in listing:
        name = item["name"]  # <event_id>.json.gz
        out = os.path.join(outdir, name.replace(".json.gz", ".json"))
        if os.path.exists(out): continue
        if n >= limit: break
        blob = get(f"{RAW}/summaries/{name}", binary=True)
        if blob is None: continue
        try:
            data = gzip.decompress(blob)
        except OSError:
            data = blob  # stored uncompressed
        with open(out, "wb") as f: f.write(data)
        n += 1; time.sleep(0.1)
    return n

if __name__ == "__main__":
    if sys.argv[1] == "summaries":
        print("pulled:", pull_summaries(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 400))
