# Endpoint — M7 (Web Tier) Milestone Summary

Companion to [Endpoint_SRS_v1.0.md](Endpoint_SRS_v1.0.md) (Section 7 — UI-1 to
UI-8) and [FINDINGS.md](FINDINGS.md) F5.

**Status: Partial — every section built; outcome sections render as pending** — 2026-08-31

---

## 1. Scope (per SRS Section 12)

> Web. Exit criterion: UI-1 … UI-8.

## 2. What was built

| Area | Delivered |
|---|---|
| **Page** | `web/index.html` — hero, reporting, attrition funnel, outcome switching, participants, explorer, methods. |
| **Styling** | `web/styles.css` — light and dark palettes defined as tokens on bare `:root`, redefined under `prefers-color-scheme` and `[data-theme]`, so the page is correct in all three theme states. One accent colour, reserved for the finding. |
| **Behaviour** | `web/app.js` — loads the five static artefacts, renders four hand-rolled SVG charts (no chart library), and drives the explorer. |
| **Local preview** | `.claude/launch.json` — a static server for verification. |

**UI coverage:** UI-1 hero ✅ (retargeted — Section 5), UI-2 version diff ⬜
(needs M4), UI-3 funnel ✅, UI-4 lifecycle ◐ (per-trial dates in the explorer;
swimlane pending), UI-5 sponsor table ✅, UI-6 URL-addressable ◐ (anchors; filter
state pending), UI-7 source links ✅, UI-8 methods panel ✅.

## 3. Artefact change

None. The web tier reads `data/serve/` and writes nothing.

## 4. How it was verified (not just "should work")

1. **Rendered in a real browser** against a local static server, then inspected via
   the DOM rather than by eye: 4 stat tiles, 7 sponsor rows, 4 phase rows, 85
   explorer rows loaded from a shard, lateness chart 36 SVG children, funnel 12,
   concentration 17, provenance 14 fields.
2. **Chart geometry checked, not assumed** — all three SVGs resolved to a real
   `viewBox` (983 px wide) and non-zero height, so a chart that silently collapsed
   to zero height would have been caught.
3. **Console checked for errors: none.**
4. **The pending path was verified as pending**: `#switching-body` renders the
   "Not yet measured" notice with the registry flag beside it, rather than a zero
   or an empty chart.
5. **An early blank screenshot was chased down rather than dismissed** — it was a
   narrow preview pane and a scroll-position artefact, confirmed by querying
   element counts and bounding boxes directly. Worth recording: *a screenshot is
   not a test.*

## 5. Decisions & notes worth remembering

- **The SRS said UI-1 should be the participant count. It cannot be.**
  `FINDINGS.md` F5 measured that figure as dominated by one implausible record and
  a handful of behavioural megastudies, ranging 4.8M–58.7M by estimator. So the
  hero is **72.2% non-reporting** — a robust census — and the participant count
  gets its own section built around *why it is not the headline*: the median trial
  beside the sum, a concentration chart, and the leech-therapy record named and
  linked. **The methodological finding became a feature of the site rather than a
  footnote in a docs file.** This is a deliberate deviation from SRS §7 and is
  recorded here rather than made quietly.
- **No framework, no build step, no external requests.** That follows from NFR-1
  and §5.6, not from laziness: a published figure has to be traceable to a file,
  and a file is easier to trace than a query. It also means the site has no
  toolchain that can break between now and whenever anyone next touches it.
- **Charts are hand-rolled SVG.** Four small charts did not justify a charting
  dependency, and inline SVG keeps the page self-contained.
- **The site never renders a number it does not have.** Every section reads its own
  `available` flag. The registry *flag* rate is shown in the outcome-switching
  section but labelled, twice, as not the finding — with the pilot's 37.7%
  non-survival rate stated next to it.
- **Every row links to ClinicalTrials.gov** (UI-7), and the methods panel publishes
  the pipeline's own failure counts (FR-11) — so a gap in the record is visible to a
  reader of the site, not just to a reader of the repository.
- **The explorer loads one shard at a time.** Searching a full NCT ID fetches
  exactly the shard containing it; there is no index to query and no server to run.

## 6. Definition of Done — checked

- [x] Renders from the static artefacts with no build step
- [x] Verified in a real browser by DOM inspection, not by screenshot alone
- [x] Theme-aware in all three states; responsive; no horizontal body scroll
- [x] Pending sections render as pending, never as zero
- [x] Every figure carries its denominator; every row links to its source
- [ ] UI-2 version diff viewer — **blocked on M4**
- [ ] Deploy workflow to GitHub Pages — not built

## 7. Next

Re-run `materialise.py` after M4 and the outcome sections populate with no code
change. Then UI-2 (the version diff viewer, the signature interaction) and a
Pages deploy workflow.

---

## Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 31 August 2026 | Web tier built and browser-verified; UI-1 retargeted away from the contaminated participant figure |
