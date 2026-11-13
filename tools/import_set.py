#!/usr/bin/env python3
"""Merge a set file from a tester (made in the app with My animals -> Share a set ->
Export file) into the built-in starter set, so every user gets it.

- A new animal (name not in the starter set) becomes a new built-in card.
- An animal already in the starter set gets only the tester's NEW photos; photos the
  set already has are recognised by their content and skipped.
- Notes/alternative names of existing cards are only REPORTED, unless --notes is given.
- Photos are converted to JPEG, max 1600 px. Crops/rotations from the tester are kept.
- Afterwards card versions are stamped (starter_revs.py), so people who already have a
  card get the new photos too (unless they edited that card themselves).

Usage:  python3 -I tools/import_set.py SETFILE.json            (dry run: shows what would change)
        python3 -I tools/import_set.py SETFILE.json --apply    (writes starter/)
        add --notes to also take the tester's notes for existing cards
"""
import base64, hashlib, json, os, re, shutil, subprocess, sys, tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("FIELD_EYE_ROOT") or os.path.dirname(TOOLS)
STARTER = os.path.join(ROOT, "starter", "starter.json")

args = sys.argv[1:]
apply, take_notes = "--apply" in args, "--notes" in args
files = [a for a in args if not a.startswith("--")]
if not files:
    sys.exit(__doc__)
d = json.load(open(files[0], encoding="utf-8"))
if d.get("app") != "field-eye" or not isinstance(d.get("animals"), list):
    sys.exit("That file isn't a Field Eye set (make it with Export file in the app).")

st = json.load(open(STARTER, encoding="utf-8"))
norm = lambda s: re.sub(r"\s+", " ", str(s or "").strip().lower())
bare = lambda s: norm(re.sub(r"^[^:]+:\s*", "", str(s or "")))   # "order: Decapoda" -> "decapoda"


def find(name):
    n, b = norm(name), bare(name)
    for a in st["animals"]:
        if n == norm(a["name"]) or b == bare(a["name"]) or b in {norm(x) for x in a.get("alts", [])}:
            return a
    return None


sha = lambda b: hashlib.sha1(b).hexdigest()
known = {}
for a in st["animals"]:
    for p in a["photos"]:
        fp = os.path.join(ROOT, p)
        if os.path.exists(fp):
            known[sha(open(fp, "rb").read())] = p
        m = re.search(r"/t\d+-([0-9a-f]{8})\.jpg$", p)     # imported earlier: name holds the original's fingerprint
        if m:
            known[m.group(1)] = p
next_no = max(int(re.search(r"(\d+)$", a["id"]).group(1)) for a in st["animals"]) + 1


def decode(data):
    m = re.match(r"data:([^;,]+);base64,(.*)$", data or "", re.S)
    return base64.b64decode(m.group(2)) if m else None


def save_photo(raw, base):
    rel = f"starter/{base}.jpg"
    with tempfile.NamedTemporaryFile(delete=False) as t:
        t.write(raw); tmp = t.name
    try:
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "84", "-Z", "1600", tmp, "--out", os.path.join(ROOT, rel)],
                       capture_output=True, check=True)
    finally:
        os.remove(tmp)
    return rel


ok_edit = lambda e: isinstance(e, dict) and e.get("rot") in (0, 90, 180, 270) and all(isinstance(e.get(k), (int, float)) and 0 <= e[k] <= 1 for k in "xywh") and e["w"] > 0 and e["h"] > 0
report, new_cards, changes = [], 0, 0
old_copy = tempfile.NamedTemporaryFile(delete=False, suffix=".json").name
shutil.copy(STARTER, old_copy)

for raw in d["animals"]:
    name = str(raw.get("name") or "").strip()
    if not name:
        continue
    photos = []
    for ph in raw.get("photos") or []:
        b = decode((ph or {}).get("data"))
        if b and sha(b) not in known and sha(b)[:8] not in known:
            photos.append((b, ph.get("edit") if ok_edit(ph.get("edit")) else None))
            known[sha(b)] = known[sha(b)[:8]] = "(new)"
    card = find(name)
    if card:
        line = f"EXISTING  {card['name']}: +{len(photos)} new photo(s)"
        t_notes = str(raw.get("traits") or "").strip()
        if t_notes and norm(t_notes) != norm(card.get("traits")):
            line += "  | tester's notes differ" + (" -> TAKEN" if take_notes else " (not changed; use --notes to take them)")
        report.append(line)
        if apply and (photos or (take_notes and t_notes)):
            card_no = int(re.search(r"(\d+)$", card["id"]).group(1))
            for b, e in photos:
                rel = save_photo(b, f"t{card_no:03d}-{sha(b)[:8]}")
                card["photos"].append(rel)
                if e:
                    card.setdefault("photoEdits", []).append({"pid": rel, **{k: e[k] for k in ("rot", "x", "y", "w", "h")}})
            if take_notes and t_notes:
                card["traits"] = t_notes
                card["alts"] = list(dict.fromkeys(card.get("alts", []) + [str(x).strip() for x in raw.get("alts") or [] if str(x).strip()]))
            changes += 1
    else:
        if not photos:
            report.append(f"SKIPPED   {name}: new animal but no photos")
            continue
        cid = f"starter-a{next_no:03d}"
        prefix = "" if ":" in name else "  (no rank like 'order:' in the name)"
        report.append(f"NEW CARD  {name} -> {cid}, {len(photos)} photo(s), group '{raw.get('group') or ''}'{prefix}")
        if apply:
            rels, edits = [], []
            for b, e in photos:
                rel = save_photo(b, f"t{next_no:03d}-{sha(b)[:8]}")
                rels.append(rel)
                if e:
                    edits.append({"pid": rel, **{k: e[k] for k in ("rot", "x", "y", "w", "h")}})
            plain = re.sub(r"^[^:]+:\s*", "", name)
            alts = list(dict.fromkeys([plain, plain.lower()] + [str(x).strip() for x in raw.get("alts") or [] if str(x).strip()]))
            st["animals"].append({"id": cid, "name": name, "group": str(raw.get("group") or "").strip(), "alts": alts,
                                  "traits": str(raw.get("traits") or "").strip(), "photos": rels, "photoEdits": edits, "created": next_no})
            new_cards += 1
        next_no += 1

print("\n".join(report) or "Nothing in the file.")
if not apply:
    print("\nDry run. Nothing changed. Run again with --apply to add this to the app.")
else:
    json.dump(st, open(STARTER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "inat", "starter_revs.py"), old_copy, STARTER], check=True)
    print(f"\nApplied: {new_cards} new card(s), {changes} existing card(s) updated. Now commit and push starter/.")
os.remove(old_copy)
