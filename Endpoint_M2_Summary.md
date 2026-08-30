# Endpoint — M2 (Frame Freeze) Milestone Summary

Companion to [Endpoint_SRS_v1.0.md](Endpoint_SRS_v1.0.md) (Section 5.1) and
[PREREGISTRATION.md](PREREGISTRATION.md) (Section 2, authoritative).

**Status: Complete** — 2026-08-30

---

## 1. Scope (per SRS Section 12)

> Frame freeze. Exit criterion: `frame/MANIFEST` committed; pre-registration frozen.

Resolve the rule fixed in `PREREGISTRATION.md` §2.1 to a concrete, hashed cohort,
and seal the analysis rules alongside it. **This is the irreversible milestone:**
after it, §2.1 can only change by a numbered amendment under §11.

## 2. What was built

| Area | Delivered |
|---|---|
| **Frame builder** | `scripts/build_frame.py` — walks the pre-registered query with cursor pagination, deduplicates by NCT ID, and writes `frame/studies.tsv` (sorted, byte-exact) plus `frame/frame.json` (the rule, the counts, and how the walk went). Records duplicates and the gap against the API's own `totalCount` rather than assuming both are zero. |
| **Freeze** | `scripts/freeze_frame.py` — computes SHA-256 of the frame, its metadata and the pre-registration, and writes `frame/MANIFEST` with the git commit the freeze was taken at. **Mostly it refuses** (Section 5). |
| **Sealed rules** | `PREREGISTRATION.md` → v1.0 FROZEN, with new §2.4 (the frame as resolved) and §2.5 (a disclosure — see Section 5). |

## 3. Artefact change

New and committed: `frame/studies.tsv` (8.2 MB, 126,760 rows + header),
`frame/frame.json`, `frame/MANIFEST`.

Frame columns: `nct, status, primary_completion, pc_type, has_results,
results_first_post, phase, enrollment, enrollment_type, sponsor_class`. The
frozen *status* is stored deliberately — `PREREGISTRATION.md` §2.1 requires that
trials whose status changes later stay in the frame with their frozen status
recorded, because a frame that tracks the world is a frame the world can reshape
after the question has been asked.

## 4. How it was verified (not just "should work")

1. **The walk reconciles exactly.** 127 pages of 1,000; **126,760 distinct NCT
   IDs**, matching the API's own `totalCount` of 126,760, with **zero duplicate
   rows** and zero records outside the frame.
2. **Duplicates were counted, not assumed absent.** A cursor walk over a live
   database can return a record twice or skip one whose sort key moves mid-walk;
   Halflife's equivalent build caught two such duplicates. Here there were none,
   and the frame size is recorded as a fact about the fetch rather than a round
   number the fetch is presumed to have delivered.
3. **The freeze interlock was tested before it was satisfied.** `freeze_frame.py`
   was run while `PREREGISTRATION.md` still carried its DRAFT marker and correctly
   refused, naming the marker it found.
4. **All three hashes reproduce independently.** `sha256sum` on the committed files
   matches `frame/MANIFEST` byte for byte:
   - `frame/studies.tsv` → `33a0128f48affe66cfc692d5a6999eaf28e44db121c08e428640c2c1053bd030`
   - `frame/frame.json` → `ff9b588d3cb1495df2ecd85c4c50ba40dc18dcb041fa08920044b9954fad91a6`
   - `PREREGISTRATION.md` → `54074c3ad5f4f72c88f08c52cceba9c4365c4917105bd99824652e0e5ad31b35`
5. **A second freeze is refused**, verified by running it again: *"frame/MANIFEST
   already exists. A freeze happens once."*
6. Frozen at `2026-08-30T12:45:01Z`, at commit `8f4fa68`.

**Composition as resolved:** 113,059 `COMPLETED` (89.2%) / 13,701 `TERMINATED`
(10.8%); lead sponsor `OTHER` 88,403 (69.7%), `INDUSTRY` 32,449 (25.6%);
month-precision primary completion 33,189 (26.2%).

## 5. Decisions & notes worth remembering

- **One primary figure was observable at freeze, and the document says so.**
  `hasResults` is carried in the frame itself, so **primary figure 2 was
  computable the moment the walk finished: 91,495 of 126,760 — 72.2% — have no
  results posted.** That is stated in `PREREGISTRATION.md` §2.5 *at freeze*,
  rather than presented later as a pre-registered prediction that was
  subsequently confirmed. Its *rule* — denominator, window, end-state filter —
  was fixed before the build, which is what pre-registration is for. But no
  reader should be left with the impression the number was unknown when the
  document was sealed. It was not. Figures 1 and 3 are not observable at freeze;
  the kill condition in §7 is written against figure 1.
- **The pre-registration is hashed alongside the frame.** A manifest that pins the
  cohort but not the rules pins the easy half: the admission rules, the 0.80
  Jaccard threshold, the `TIMEFRAME_ONLY` exclusion and the 5% kill condition are
  what make a later result checkable.
- **`freeze_frame.py` refuses more than it does.** No freeze if the manifest
  already exists (and no `--force` flag is offered), if the pre-registration is
  still a draft, if the frame file is unsorted or contains a duplicate, or if any
  hashed file has uncommitted changes — a hash of a file that exists only on one
  machine records nothing a stranger can check.
- **`git_commit_at_freeze` is informational, and the manifest says so.** The freeze
  mutates `frame.json` (setting `frozen: true`) before hashing, so the recorded
  commit is the one *before* the manifest existed. The digests are the authority
  and the verification instruction points at them.
- **A 2022 window end is a design choice, not an accident.** Every trial in the
  frame is more than three years past the 12-month deadline, which is the
  difference between measuring non-reporting and measuring slowness.

## 6. Definition of Done — checked

- [x] `frame/MANIFEST` committed with three reproducible SHA-256 digests
- [x] `PREREGISTRATION.md` sealed at v1.0 FROZEN with no prior amendments
- [x] Walk reconciles to the API's own count with zero duplicates
- [x] Refusal paths tested, not just the success path
- [x] The one figure visible at freeze disclosed in the sealed document itself

## 7. Next

**M3 — History crawl.** Fetch the version index for all 126,760 trials. The first
step that writes to the cold store.

---

## Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 30 August 2026 | Frame resolved to 126,760 and frozen; pre-registration sealed; §2.5 disclosure added |
