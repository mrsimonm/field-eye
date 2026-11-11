#!/usr/bin/env python3
"""Build Field Eye starter cards from iNaturalist.

For each card spec it:
  1. resolves the taxon on iNaturalist and checks its lineage contains the expected parent,
  2. picks research-grade, open-licensed photos spread across different families
     (Europe first, adults first, CC0/CC-BY first, one photo per observer),
  3. downloads them, checks they are real images of a usable size,
  4. writes cards.json (app card format), meta.json (credits) and review.html (preview).

Usage: inat_build.py SPECS.json OUT_DIR [Name1,Name2,...]
"""
import html, json, os, re, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request

API = "https://api.inaturalist.org/v1"
UA = "field-eye-study-app"
BY = ("cc0", "cc-by")
BYNC = ("cc0", "cc-by", "cc-by-nc")
# (region, adults only, licences): tried in order until enough photos are found
STAGES = [("eu", True, BY), ("world", True, BY), ("eu", True, BYNC), ("world", True, BYNC), ("world", False, BYNC)]
MIN_SIDE = 700

spec_path, out_dir = sys.argv[1], sys.argv[2]
only = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
specs = json.load(open(spec_path, encoding="utf-8"))
if only:
    specs = [s for s in specs if s["name"] in only]
photo_dir = os.path.join(out_dir, "photos")
os.makedirs(photo_dir, exist_ok=True)

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
                time.sleep(6 * (attempt + 1))
                continue
            raise
        except Exception:
            time.sleep(4 * (attempt + 1))
    raise RuntimeError("iNaturalist request failed: " + url)


def lineage(t):
    return [(a["rank"], a["name"]) for a in t.get("ancestors", [])] + [(t["rank"], t["name"])]


def resolve(spec):
    res = api("taxa", q=spec["name"], per_page=30, is_active="true")["results"]
    exact = [t for t in res if t["name"].lower() == spec["name"].lower()]
    good = []
    for t in exact:
        full = api(f"taxa/{t['id']}")["results"][0]
        if any(n == spec["expect"] for _, n in lineage(full)):
            good.append(full)
    if not good:
        raise SystemExit(f"STOP {spec['name']}: no iNaturalist taxon with that exact name under {spec['expect']}")
    good.sort(key=lambda t: -t.get("observations_count", 0))
    return good[0]


def find_europe():
    try:
        for p in api("places/autocomplete", q="Europe", per_page=10)["results"]:
            if p["name"] == "Europe":
                return p["id"]
    except Exception:
        pass
    return None


def pools(tid):
    """Child groups to spread photos across: families (or genera), most observed first."""
    for rank in ("family", "genus"):
        res = api("taxa", taxon_id=tid, rank=rank, per_page=200, is_active="true")["results"]
        res = [t for t in res if t.get("observations_count", 0) > 0]
        if res:
            res.sort(key=lambda t: -t["observations_count"])
            return [(t["id"], t["name"]) for t in res[:24]]
    return [(tid, None)]


_cache = {}


def top_obs(pool_id, place, adult, lic):
    key = (pool_id, place, adult, lic)
    if key not in _cache:
        p = dict(taxon_id=pool_id, quality_grade="research", photos="true", photo_license=",".join(lic),
                 captive="false", order_by="votes", order="desc", per_page=12,
                 identifications="most_agree", locale="en")
        if place:
            p["place_id"] = place
        if adult:
            p.update(term_id=1, term_value_id=2)   # life stage = adult
        _cache[key] = api("observations", **p)["results"]
    return _cache[key]


def pick_photo(obs, lic):
    for ph in obs.get("photos", []):
        if (ph.get("license_code") or "").lower() in lic:
            d = ph.get("original_dimensions") or {}
            if d.get("width") and d["width"] < MIN_SIDE:
                continue
            return ph
    return None


def collect(pool_list, europe, want):
    chosen, used_obs, used_users = [], set(), set()
    for si, (reg, adult, lic) in enumerate(STAGES):
        if reg == "eu" and not europe:
            continue
        place = europe if reg == "eu" else None
        while len(chosen) < want:
            added = 0
            for pid, pname in pool_list:
                if len(chosen) >= want:
                    break
                for obs in top_obs(pid, place, adult, lic):
                    uid = obs["user"]["id"]
                    if obs["id"] in used_obs or uid in used_users:
                        continue
                    ph = pick_photo(obs, lic)
                    if not ph:
                        continue
                    chosen.append(dict(obs=obs, photo=ph, family=pname, stage=si))
                    used_obs.add(obs["id"])
                    used_users.add(uid)
                    added += 1
                    break
            if not added:
                break
        if len(chosen) >= want:
            break
    return chosen


def download(ph, dest_base):
    url = re.sub(r"/(square|small|medium|large|original)\.(\w+)$", r"/large.\2", ph["url"])
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
        data = r.read()
    if data[:3] == b"\xff\xd8\xff":
        ext = "jpg"
    elif data[:4] == b"\x89PNG":
        ext = "png"
    else:
        raise ValueError("not an image")
    if len(data) < 15000:
        raise ValueError("too small")
    path = f"{dest_base}.{ext}"
    open(path, "wb").write(data)
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path], capture_output=True, text=True).stdout
    w = int(re.search(r"pixelWidth: (\d+)", out).group(1))
    h = int(re.search(r"pixelHeight: (\d+)", out).group(1))
    if max(w, h) < MIN_SIDE:
        os.remove(path)
        raise ValueError(f"only {w}x{h}")
    return path, w, h


cards_path, meta_path = os.path.join(out_dir, "cards.json"), os.path.join(out_dir, "meta.json")
cards = {c["name"]: c for c in (json.load(open(cards_path, encoding="utf-8")) if os.path.exists(cards_path) else [])}
meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
europe = find_europe()
print("Europe place id:", europe)

for spec in specs:
    print("=" * 70)
    t = resolve(spec)
    print(f"{spec['name']}: iNaturalist taxon {t['id']} ({t['rank']}, {t.get('observations_count')} obs)")
    print("  lineage:", " > ".join(n for _, n in lineage(t)))
    pl = pools(t["id"])
    print(f"  spreading across {len(pl)} groups: {', '.join(str(n) for _, n in pl[:10])}{' ...' if len(pl) > 10 else ''}")
    for f in os.listdir(photo_dir):                       # rebuilding a card replaces its old photos
        if f.startswith(f"i{spec['card_no']:03d}-"):
            os.remove(os.path.join(photo_dir, f))
    cands = collect(pl, europe, spec["n"] + 4)
    files, pm = [], []
    for c in cands:
        if len(files) >= spec["n"]:
            break
        base = os.path.join(photo_dir, f"i{spec['card_no']:03d}-{len(files) + 1:02d}")
        try:
            path, w, h = download(c["photo"], base)
        except Exception as e:
            print("  skip photo:", e)
            continue
        o = c["obs"]
        files.append(os.path.basename(path))
        pm.append(dict(file=os.path.basename(path), inat_photo_id=c["photo"]["id"], obs_id=o["id"], obs_url=o.get("uri"),
                       species=(o.get("taxon") or {}).get("name"), common=(o.get("taxon") or {}).get("preferred_common_name"),
                       family=c["family"], user=o["user"]["login"], license=c["photo"].get("license_code"),
                       attribution=c["photo"].get("attribution"), observed_on=o.get("observed_on"),
                       place=o.get("place_guess"), width=w, height=h,
                       region=("Europe" if STAGES[c["stage"]][0] == "eu" else "world"),
                       adult_filter=STAGES[c["stage"]][1]))
    lic = {}
    for m in pm:
        lic[m["license"]] = lic.get(m["license"], 0) + 1
    print(f"  photos: {len(files)}/{spec['n']} | licences {lic} | Europe: {sum(m['region'] == 'Europe' for m in pm)} | families: {len({m['family'] for m in pm})}")
    for m in pm:
        print(f"   - {m['file']}: {m['species']} ({m['common']}) | {m['family']} | {m['license']} | {m['user']} | {m['width']}x{m['height']}")
    if len(files) < spec["n"]:
        print(f"  !! only {len(files)} usable photos found for {spec['name']}")
    cards[spec["name"]] = {
        "id": f"starter-a{spec['card_no']:03d}", "name": f"{spec['rank']}: {spec['name']}", "group": spec["group"],
        "alts": [spec["name"], spec["name"].lower()], "traits": spec["notes"],
        "photos": ["starter/" + f for f in files], "photoEdits": [], "created": spec["card_no"],
    }
    meta[spec["name"]] = dict(taxon_id=t["id"], rank=t["rank"], lineage=[n for _, n in lineage(t)], photos=pm)

order = sorted(cards.values(), key=lambda c: c["created"])
json.dump(order, open(cards_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# Preview page for checking every photo against its card
rows = []
for c in order:
    key = c["name"].split(": ", 1)[1]
    m = meta.get(key, {})
    figs = "".join(
        f'<figure><img src="photos/{html.escape(p["file"])}" loading="lazy"><figcaption><b>{html.escape(str(p["species"]))}</b>'
        f'{" (" + html.escape(p["common"]) + ")" if p.get("common") else ""}<br>{html.escape(str(p["family"]))} &middot; {html.escape(str(p["license"]))} &middot; {html.escape(p["region"])}</figcaption></figure>'
        for p in m.get("photos", []))
    rows.append(f'<section><h2>{html.escape(c["name"])} <small>{html.escape(c["group"])} &middot; {len(c["photos"])} photos</small></h2>'
                f'<pre>{html.escape(c["traits"])}</pre><div class="g">{figs}</div></section>')
open(os.path.join(out_dir, "review.html"), "w", encoding="utf-8").write(
    '<!doctype html><meta charset="utf-8"><title>Field Eye new cards review</title>'
    '<style>body{font:15px system-ui;margin:0;padding:16px;background:#14181a;color:#e8ece9}h2{margin:28px 0 6px;font-size:22px}'
    'h2 small{font-weight:400;font-size:14px;color:#9aa8a0}pre{white-space:pre-wrap;font:14px/1.5 system-ui;background:#1d2326;padding:10px 12px;border-radius:8px;margin:0 0 12px}'
    '.g{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}figure{margin:0;background:#1d2326;border-radius:8px;overflow:hidden}'
    'img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;background:#000}figcaption{font-size:12px;line-height:1.35;padding:6px 8px;color:#b9c4bd}</style>'
    + "".join(rows))
print("=" * 70)
print("wrote", cards_path, meta_path, "and review.html")
