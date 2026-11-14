#!/usr/bin/env python3
"""Merge extra photos from build_extra/ into starter/starter.json and CREDITS.md.

For each card in build_extra/cards.json:
- copies its photos into starter/ with numbering that continues from the
  highest existing i-file for that card (i.e., i031-08.jpg, not i031-01.jpg)
- appends those photo paths to the card's photos list in starter.json
- appends new credit entries to CREDITS.md

Usage: python3 -I tools/inat/merge_extra.py [build_extra/]
"""
import json, os, re, shutil, sys

BUILD = sys.argv[1] if len(sys.argv) > 1 else "build_extra"
STARTER_DIR = "starter"
STARTER_JSON = os.path.join(STARTER_DIR, "starter.json")
BUILD_PHOTOS = os.path.join(BUILD, "photos")
BUILD_CARDS = os.path.join(BUILD, "cards.json")
BUILD_META = os.path.join(BUILD, "meta.json")
CREDITS_MD = "CREDITS.md"

starter = json.load(open(STARTER_JSON, encoding="utf-8"))
by_id = {a["id"]: a for a in starter["animals"]}

build_cards = json.load(open(BUILD_CARDS, encoding="utf-8"))
build_meta = json.load(open(BUILD_META, encoding="utf-8")) if os.path.exists(BUILD_META) else {}

# collect photo IDs already referenced in CREDITS.md (rough duplicate guard)
credits_text = open(CREDITS_MD, encoding="utf-8").read() if os.path.exists(CREDITS_MD) else ""
existing_obs_ids = set(re.findall(r"/observations/(\d+)", credits_text))

total_added = 0
credits_additions = []  # (section_name, [line, ...])

for bc in build_cards:
    cid = bc["id"]
    if cid not in by_id:
        print(f"  skip {cid}: not in starter.json")
        continue

    card = by_id[cid]
    card_no = int(cid.split("-a")[1])
    taxon_name = bc["name"].split(": ", 1)[1]

    # find highest existing i-file number for this card
    existing_i = [f for f in os.listdir(STARTER_DIR)
                  if re.match(rf"^i{card_no:03d}-\d{{2}}\.", f)]
    max_num = max((int(re.search(r"-(\d{2})\.", f).group(1)) for f in existing_i), default=0)

    new_meta = build_meta.get(taxon_name, {}).get("photos", [])
    new_files = bc.get("photos", [])

    added = 0
    new_credit_lines = []
    for idx, new_path in enumerate(new_files):
        fname = os.path.basename(new_path)
        src = os.path.join(BUILD_PHOTOS, fname)
        if not os.path.exists(src):
            print(f"  missing {src}, skip")
            continue

        pm = new_meta[idx] if idx < len(new_meta) else {}
        obs_id = str(pm.get("obs_id", ""))
        if obs_id and obs_id in existing_obs_ids:
            print(f"  {fname}: obs {obs_id} already in credits, skip")
            continue

        max_num += 1
        new_fname = f"i{card_no:03d}-{max_num:02d}.jpg"
        dst = os.path.join(STARTER_DIR, new_fname)
        shutil.copy2(src, dst)
        card["photos"].append(f"starter/{new_fname}")
        if obs_id:
            existing_obs_ids.add(obs_id)
        added += 1

        # build credits line
        species = pm.get("species", "?")
        attr = pm.get("attribution", "")
        obs_url = pm.get("obs_url", "") or f"https://www.inaturalist.org/observations/{obs_id}"
        lic = (pm.get("license", "") or "").upper().replace("CC-", "CC ").replace("-", " ")
        new_credit_lines.append(
            f"- `{new_fname}`: *{species}*, {attr}, [{lic}]({obs_url})"
        )
        print(f"  {fname} → {new_fname} ({species} | {pm.get('license','?')} | {pm.get('region','?')})")

    total_added += added
    print(f"{cid} ({bc['name']}): +{added} photos → {len(card['photos'])} total")
    if new_credit_lines:
        credits_additions.append((taxon_name, new_credit_lines))

# save updated starter.json
json.dump(starter, open(STARTER_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# append to CREDITS.md
if credits_additions:
    with open(CREDITS_MD, "a", encoding="utf-8") as f:
        f.write("\n")
        for section, lines in credits_additions:
            f.write(f"\n### {section} (extra)\n\n")
            for line in lines:
                f.write(line + "\n")

print(f"\nDone. Added {total_added} photos total.")
