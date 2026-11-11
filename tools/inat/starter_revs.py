#!/usr/bin/env python3
"""Stamp content fingerprints on starter cards so corrections reach existing users.

Each card gets `rev` (fingerprint of its current content) and `oldRevs` (fingerprints
of earlier versions). The app replaces a person's copy of a built-in card only if
that copy still matches one of the old versions, i.e. they never edited it.
Same formula as starterSig() in index.html.

Usage: starter_revs.py OLD_starter.json NEW_starter.json   (rewrites NEW in place)
"""
import json, sys


def sig(a):
    s = json.dumps([a.get("name") or "", a.get("group") or "", a.get("alts") or [], a.get("traits") or "", a.get("photos") or []],
                   ensure_ascii=False, separators=(",", ":"))
    h = 5381
    for ch in s:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    digits, out = "0123456789abcdefghijklmnopqrstuvwxyz", ""
    while True:
        h, r = divmod(h, 36)
        out = digits[r] + out
        if not h:
            return out


old_path, new_path = sys.argv[1], sys.argv[2]
old = {a["id"]: a for a in json.load(open(old_path, encoding="utf-8"))["animals"]}
data = json.load(open(new_path, encoding="utf-8"))
changed = 0
for a in data["animals"]:
    prev = old.get(a["id"])
    revs = list(a.get("oldRevs") or [])
    if prev:
        revs += list(prev.get("oldRevs") or []) + [prev.get("rev") or sig(prev)]
    a["rev"] = sig(a)
    a["oldRevs"] = sorted({r for r in revs if r != a["rev"]})
    changed += bool(prev and a["rev"] != (prev.get("rev") or sig(prev)))
json.dump(data, open(new_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(data['animals'])} cards, {changed} changed since the old file")
