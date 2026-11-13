#!/usr/bin/env python3
"""Fetch MANY high-resolution photo candidates per card for a by-eye review.

inat_build.py picks photos automatically; this script instead downloads ~18
candidates per card (open licence, research grade, Europe + adults first, one
per observer, spread across families), only photos at least MIN_SHORT px on
the short side, resized to max 1600 px. A person (or Claude) then looks at
sheet.html and picks the best ones with pick_photos.py.

Usage: inat_candidates.py OUT_DIR SPECS.json [SPECS2.json ...]
"""
import html, json, os, re, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request

API = "https://api.inaturalist.org/v1"
UA = "field-eye-study-app"
BY = ("cc0", "cc-by")
BYNC = ("cc0", "cc-by", "cc-by-nc")
STAGES = [("eu", True, BY), ("world", True, BY), ("eu", True, BYNC), ("world", True, BYNC)]
MIN_SHORT = 1000
WANT = 18

out_dir = sys.argv[1]
specs = [s for p in sys.argv[2:] for s in json.load(open(p, encoding="utf-8"))]
os.makedirs(out_dir, exist_ok=True)
_last = [0.0]


def api(path, **params):
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
    url = f"{API}/{path}?{q}"
    for attempt in range(6):
        gap = 1.1 - (time.time() - _last[0])
        if gap > 0:
            time.sleep(gap)
        _last[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=45) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(6 * (attempt + 1)); continue
            raise
        except Exception:
            time.sleep(4 * (attempt + 1))
    raise RuntimeError("iNaturalist request failed: " + url)


def resolve(spec):
    res = api("taxa", q=spec["name"], per_page=30, is_active="true")["results"]
    good = []
    for t in (t for t in res if t["name"].lower() == spec["name"].lower()):
        full = api(f"taxa/{t['id']}")["results"][0]
        if spec["expect"] in [a["name"] for a in full.get("ancestors", [])] + [full["name"]]:
            good.append(full)
    if not good:
        raise SystemExit(f"STOP {spec['name']}: not found under {spec['expect']}")
    return max(good, key=lambda t: t.get("observations_count", 0))


def pools(tid):
    for rank in ("family", "genus"):
        res = [t for t in api("taxa", taxon_id=tid, rank=rank, per_page=200, is_active="true")["results"] if t.get("observations_count", 0) > 0]
        if res:
            res.sort(key=lambda t: -t["observations_count"])
            return [(t["id"], t["name"]) for t in res[:20]]
    return [(tid, None)]


def find_europe():
    for p in api("places/autocomplete", q="Europe", per_page=10)["results"]:
        if p["name"] == "Europe":
            return p["id"]
    return None


_cache = {}


def top_obs(pool_id, place, adult, lic):
    key = (pool_id, place, adult, lic)
    if key not in _cache:
        p = dict(taxon_id=pool_id, quality_grade="research", photos="true", photo_license=",".join(lic), captive="false",
                 order_by="votes", order="desc", per_page=30, locale="en")
        if place:
            p["place_id"] = place
        if adult:
            p.update(term_id=1, term_value_id=2)
        _cache[key] = api("observations", **p)["results"]
    return _cache[key]


def pick_photo(obs, lic):
    for ph in obs.get("photos", []):
        d = ph.get("original_dimensions") or {}
        if (ph.get("license_code") or "").lower() in lic and min(d.get("width") or 0, d.get("height") or 0) >= MIN_SHORT:
            return ph
    return None


def collect(pl, europe):
    chosen, used_obs, used_users = [], set(), set()
    for reg, adult, lic in STAGES:
        place = europe if reg == "eu" else None
        if reg == "eu" and not europe:
            continue
        while len(chosen) < WANT:
            added = 0
            for pid, pname in pl:
                if len(chosen) >= WANT:
                    break
                for obs in top_obs(pid, place, adult, lic):
                    if obs["id"] in used_obs or obs["user"]["id"] in used_users:
                        continue
                    ph = pick_photo(obs, lic)
                    if not ph:
                        continue
                    chosen.append((obs, ph, pname)); used_obs.add(obs["id"]); used_users.add(obs["user"]["id"]); added += 1
                    break
            if not added:
                break
        if len(chosen) >= WANT:
            break
    return chosen


def download(ph, path):
    url = re.sub(r"/(square|small|medium|large|original)\.(\w+)$", r"/original.\2", ph["url"])
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
        data = r.read()
    if data[:3] != b"\xff\xd8\xff" and data[:4] != b"\x89PNG":
        raise ValueError("not an image")
    tmp = path + ".src"
    open(tmp, "wb").write(data)
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "84", "-Z", "1600", tmp, "--out", path], capture_output=True, check=True)
    os.remove(tmp)
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path], capture_output=True, text=True).stdout
    return int(re.search(r"pixelWidth: (\d+)", out).group(1)), int(re.search(r"pixelHeight: (\d+)", out).group(1))


meta_path = os.path.join(out_dir, "cands.json")
meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
europe = find_europe()
for spec in specs:
    if spec["name"] in meta:
        continue
    t = resolve(spec)
    cdir = os.path.join(out_dir, f"{spec['card_no']:03d}")
    os.makedirs(cdir, exist_ok=True)
    rows = []
    for obs, ph, fam in collect(pools(t["id"]), europe):
        f = f"{len(rows) + 1:02d}.jpg"
        try:
            w, h = download(ph, os.path.join(cdir, f))
        except Exception as e:
            print("  skip:", e); continue
        rows.append(dict(file=f, photo_id=ph["id"], obs_url=obs.get("uri"), species=(obs.get("taxon") or {}).get("name"),
                         family=fam, license=ph.get("license_code"), attribution=ph.get("attribution"), w=w, h=h))
    meta[spec["name"]] = dict(card_no=spec["card_no"], cands=rows)
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)
    print(f"{spec['name']}: {len(rows)} candidates", flush=True)

# Contact sheet: one section per card, numbered tiles
secs = []
for name, m in sorted(meta.items(), key=lambda kv: kv[1]["card_no"]):
    tiles = "".join(f'<figure><img src="{m["card_no"]:03d}/{c["file"]}"><figcaption><b>{i + 1}</b> {html.escape(str(c["species"]))}</figcaption></figure>'
                    for i, c in enumerate(m["cands"]))
    secs.append(f'<section id="c{m["card_no"]:03d}"><h2>{m["card_no"]:03d} {html.escape(name)}</h2><div class="g">{tiles}</div></section>')
open(os.path.join(out_dir, "sheet.html"), "w").write(
    '<!doctype html><meta charset="utf-8"><style>body{margin:0;padding:8px;background:#111;color:#eee;font:13px system-ui}'
    'h2{margin:4px 0;font-size:16px}section{height:100vh;box-sizing:border-box}.g{display:grid;grid-template-columns:repeat(6,1fr);gap:4px}'
    'figure{margin:0;background:#000}img{width:100%;aspect-ratio:4/3;object-fit:contain;display:block}'
    'figcaption{padding:1px 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}figcaption b{color:#fd0;font-size:15px}</style>' + "".join(secs))
print("sheet written")
