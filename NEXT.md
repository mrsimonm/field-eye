# Field Eye: where we left off

Live app: https://mrsimonm.github.io/field-eye/  (repo: github.com/mrsimonm/field-eye, GitHub Pages from `main`)

## Latest (2026-11-14) — read this first
- 62 cards, 585 photos, all photos checked by eye (first 30: tester photos + `mNNN-*` iNat additions; rest: `kNNN-*`).
- App features: phone/laptop layout switch, Progress tab (mastery: right on 3 photos on 2 days; streaks; practice time; 30-day charts; hardest cards; mix-ups), Test mode (exam, results + retry missed), progress syncs/merges across devices when signed in, Google sign-in falls back to full-page sign-in when blocked.
- Bump `V` in `sw.js` on every release (now field-eye-v10).
- Firebase Storage (photo upload when signed in) still blocked: Google Cloud shows NO active billing account ("Firebase Payment" closed/suspended). User must fix billing, then: Firebase console → Storage → Get started → Create; then deploy `storage.rules`.
- Ideas not done yet: Class view (testers share progress), daily reminder, "report a wrong photo" button.

## State
- Single-file app: `index.html`. Built-in cards: `starter/starter.json` + photos in `starter/`.
- Starter cards are added to every user by id ("top-up": `topUpLocal` / `adoptLocal`), so new cards reach existing users automatically; deleted ones never return.
- **All 62 required cards done** (2026-11-12). Notes on the 30 tester cards were fact-checked and rewritten (Notostraca, Decapoda, Turbellaria, Oligochaeta, Xiphosura were wrong).
- Corrections reach existing users: each card in starter.json has `rev`/`oldRevs` (run `tools/inat/starter_revs.py OLD NEW` after editing cards); the app updates built-in cards the person never edited.
- Photos always shown in full (`contain` + blurred fill); random zoom/tilt is now off by default for everyone.
- Previously: 43 of 62 (list = Zoja's "0) Zoology_Taxonomic levels_2026.pdf" in the shared Drive folder "zoology"). Heterobranchia deliberately NOT a card (parent of two existing cards).
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

## Adding a tester's cards for everyone
1. Tester: My animals → Share a set → Export file, and sends you the file.
2. `python3 -I tools/import_set.py path/to/field-eye-xxx.json` (dry run: lists new cards and new photos).
3. Same with `--apply` (add `--notes` to also take her notes for existing cards). Then commit + push `starter/`.
New animals become built-in cards; existing ones only get her new photos (duplicates skipped). Users get them automatically.

## Photos (2026-11-13)
The 32 iNaturalist cards were re-done by hand: 18 high-res candidates per card (`tools/inat/inat_candidates.py`), the best 7-8 picked by eye (animal large and sharp), files `starter/kNNN-MM.jpg`, 1280 px. Old `iNNN-*.jpg` files are kept only for people who edited those cards.

## Open items
- Add a "Photo credits" link in the app pointing to `CREDITS.md` (CC-BY needs attribution).
- Signed-in photo upload is OFF: Firebase Storage can't be created because the Google billing account "Firebase Payment" looks disabled (storage returns 402). Fix the card/billing in Google Cloud Billing, then create the bucket in the Firebase console for `field-eye-mrsimonm` and run `firebase deploy --only storage` (rules are in `storage.rules`).
- The older photos (first 30 cards) came from the testers' own sources: licence unknown while the repo is public.
- Untracked leftovers that can be deleted: `field-eye.html`, `field-eye-site/`.
