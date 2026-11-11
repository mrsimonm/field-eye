# Field Eye: where we left off

Live app: https://mrsimonm.github.io/field-eye/  (repo: github.com/mrsimonm/field-eye, GitHub Pages from `main`)

## State
- Single-file app: `index.html`. Built-in cards: `starter/starter.json` + photos in `starter/`.
- Starter cards are added to every user by id ("top-up": `topUpLocal` / `adoptLocal`), so new cards reach existing users automatically; deleted ones never return.
- **43 of 62 required cards done** (list = Zoja's "0) Zoology_Taxonomic levels_2026.pdf" in the shared Drive folder "zoology"). Heterobranchia deliberately NOT a card (parent of two existing cards).
- Sign-in (Google + email), sync, install, liquid-glass design: done, on Firebase project `field-eye-mrsimonm`.

## Cards still to build (19), card_no = id number
43 Caelifera, 44 Dermaptera, 45 Anoplura, 46 Aphidoidea, 47 Coccoidea, 48 Auchenorrhyncha, 49 Heteroptera (notes: Seminar 6),
50 Neuroptera, 51 Megaloptera, 52 Raphidioptera, 53 Adephaga, 54 Polyphaga, 55 Mecoptera, 56 Nematocera, 57 Brachycera, 58 Siphonaptera, 59 Trichoptera, 61 Symphyta, 62 Apocrita (notes: Seminar 7).
Ranks: Caelifera/Anoplura*/Auchenorrhyncha/Heteroptera/Adephaga/Polyphaga/Nematocera/Brachycera/Symphyta/Apocrita = suborder (*Anoplura is a superfamily on iNaturalist); Aphidoidea/Coccoidea = superfamily; the rest = order. Group for all: `subphylum: Hexapoda`.

## Notes source (use ONLY the slides, nothing invented)
Drive, shared by Zoja. `download_file_content` fails (>10 MB); use `read_file_content`:
- Seminar 6 Pterygota1: file id `11gtAwu93YYdi8477nOql7urdeIqzHbZr`
- Seminar 7 Pterygota2: file id `1wLoFvbP4lkk_-o8SQGLNn6zfW52xMSgq`
Style = the existing cards: line 1 parent-group features, then the taxon's own features, short and lowercase (see `tools/inat/cards.batch1.json`).

## How to build cards
1. Write `tools/inat/cards.batch2.json` (same fields as batch1: card_no, name, rank, group, expect, n, notes).
2. `python3 -I tools/inat/inat_build.py tools/inat/cards.batch2.json <build dir>` (needs network; ~30 s per card; photos = iNaturalist research-grade, CC0/CC-BY first, Europe + adults first, one per observer, spread across families; it stops with "STOP" if a taxon can't be matched, and prints "!!" if a card has too few photos).
3. Merge: copy `<build>/photos/*` to `starter/`, append `<build>/cards.json` entries (skip ids already present) to `starter/starter.json`, regenerate `CREDITS.md` from `<build>/meta.json`, commit, push, wait for the live count.
Expect thin photo supply for Anoplura (lice) and Siphonaptera (fleas).

## Open items
- Add a "Photo credits" link in the app pointing to `CREDITS.md` (CC-BY needs attribution).
- Signed-in photo upload is OFF: Firebase Storage can't be created because the Google billing account "Firebase Payment" looks disabled (storage returns 402). Fix the card/billing in Google Cloud Billing, then create the bucket in the Firebase console for `field-eye-mrsimonm` and run `firebase deploy --only storage` (rules are in `storage.rules`).
- The older photos (first 30 cards) came from the testers' own sources: licence unknown while the repo is public.
- Untracked leftovers that can be deleted: `field-eye.html`, `field-eye-site/`.
