#!/bin/bash
# Run from the project root: bash tools/inat/apply_extra.sh
set -e
cd "$(dirname "$0")/../.."

echo "=== Saving old starter.json for rev tracking ==="
cp starter/starter.json tools/inat/starter.old.json

echo "=== Merging extra photos ==="
python3 -I tools/inat/merge_extra.py build_extra

echo "=== Stamping rev fingerprints ==="
python3 -I tools/inat/starter_revs.py tools/inat/starter.old.json starter/starter.json

echo "=== Done. Check photo counts: ==="
python3 -I -c "
import json
data=json.load(open('starter/starter.json'))
for a in sorted(data['animals'], key=lambda x: x['id'])[30:]:
    print(a['id'][-3:], a['name'].split(': ')[-1], len(a.get('photos',[])))
"
