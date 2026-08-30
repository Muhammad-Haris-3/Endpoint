# Endpoint — M6 (Warehouse & Materialisation) Milestone Summary

Companion to [Endpoint_SRS_v1.0.md](Endpoint_SRS_v1.0.md) (Sections 5.6, 6 —
FR-8, FR-9, FR-10, FR-11) and [FINDINGS.md](FINDINGS.md) F4, F5.

**Status: Partial — complete for every figure that does not depend on M4** — 2026-08-31

---

## 1. Scope (per SRS Section 12)

> Warehouse + materialisation. Exit criterion: static serving artefacts
> regenerable end to end.

Built out of order, and deliberately: primary figures 2 and 3 come from the
frozen frame alone, so this milestone ran **in parallel with the M4 crawl**
rather than waiting behind it.

## 2. What was built

| Area | Delivered |
|---|---|
| **Reporting analysis (FR-8)** | `scripts/reporting_figures.py` — primary figures 2 and 3 plus lateness and breakdowns, from `frame/studies.tsv` alone. Reports the pre-registered figure first and unmodified, then the concentration that makes it unreportable, then robust alternatives each labelled **not pre-registered**. |
| **Materialiser (FR-9, FR-10, FR-11)** | `scripts/materialise.py` — writes `summary.json`, `funnel.json`, `breakdowns.json`, `distributions.json`, `trials/<prefix>.json` (79 shards) and `manifest.json` to `data/serve/`. Refuses to run against a frame that does not match `frame/MANIFEST`. |
| **Findings** | `FINDINGS.md` — F1–F5, newest first, matching the Groundtruth convention. |

## 3. Artefact change

New and committed: `data/figures/reporting.{txt,json}`.

New and **not** committed: `data/serve/` (39 MB). It is a pure function of the
frame, the named register batches and the pipeline commit — all three recorded in
`manifest.json` — so it is regenerated at deploy rather than committed and allowed
to drift from its inputs.

## 4. How it was verified (not just "should work")

1. **Figure 2 is a census, and cross-checks.** 91,495 of 126,760 (72.2%) with no
   posted results. The M0 pilot estimated 73.5% from 400 trials — close, which is
   reassurance about the pilot's *sampling* and nothing else.
2. **The registry flag rate materialised by `materialise.py` (33.6%, 42,623
   retrospective flags) matches `register_report.py` exactly**, computed by a
   different code path from the same register. An independent agreement, not a
   shared bug.
3. **Serving artefacts verified in a real browser** against a local server: 4 stat
   tiles, 7 sponsor rows, 4 phase rows, 85 explorer rows from a shard, lateness
   histogram at 36 SVG children, funnel at 12, concentration at 17, provenance at
   14 fields.
4. **The pending path was verified as pending**, not merely absent: `summary.json`
   carries `figure_1_outcome_switching.available: false` with `status: "pending"`,
   and the page renders "Not yet measured".
5. **Shard sizes checked**: 79 buckets, largest 1.3 MB, so a drill-through is one
   small fetch rather than a query.

## 5. Decisions & notes worth remembering

- **Figure 3's pre-registered sum is not reportable alone, and that is now a
  measured claim.** The raw sum is **58,650,765 participants**; the **median silent
  trial has 52**. The single largest contributor carries **21.0% of the total** —
  `NCT05438901`, *"Oxidant-antioxidant Status in Patients Treated With
  Hirudotherapy"*, a single-group before/after study of leech therapy recorded as
  `ACTUAL` enrolment of 12,317,546. Most other top contributors are behavioural
  megastudies (SMS nudges, online health ads) which genuinely enrolled millions,
  but not in the sense the phrase invites. **Depending on estimator the figure
  ranges from 4.8M to 58.7M.** The frozen one is computed and reported unmodified;
  an amendment is *proposed* in `FINDINGS.md` F5 and stays proposed. See F5 for the
  full table.
- **This is the third time the project has met the same failure mode** — after the
  control arm that never was (M0) and the change flag that overstated by 37.7%
  (M0). It is starting to look like the default outcome of any naive aggregate over
  this registry rather than bad luck.
- **The most defensible numbers the project holds are rates, not sums.**
  Non-reporting by sponsor class is a census and immune to the outlier problem:
  `OTHER_GOV` **96.2%**, academic **79.8%**, `INDUSTRY` **52.8%**, `NIH` **27.7%**.
  **Industry reports at roughly twice the rate of academia**, which inverts the
  direction most readers would guess. `PHASE3` — the trials that support approvals
  — is **43.7%** silent.
- **Every artefact section carries its own `available` flag.** A frontend that read
  a missing file as `0` would publish *"0% of trials switched outcomes"* as a
  finding — a false result manufactured by an absent file. The artefacts make that
  impossible to do by accident, and `summary.json` carries the instruction
  *"Do NOT render 0"* in the data itself.
- **Figure 3's warning lives inside the artefact**, not only in the documentation,
  so a frontend that reads nothing but JSON still cannot render the sum without its
  median and concentration.
- **`data/serve/` stays gitignored** for the same reason the cold store does: it is
  derived, and a committed derivative can drift from its inputs without anything
  noticing.

## 6. Definition of Done — checked

- [x] Primary figures 2 and 3 computed from the frozen frame, with provenance
- [x] Every serving artefact regenerable by one documented command
- [x] Outcome sections degrade to `available: false` rather than to zero
- [x] Failure counts published in `manifest.json` (FR-11), not just kept in the repo
- [x] Per-trial drill-through sharded and verified in a browser (FR-10)
- [ ] Outcome-switching sections populated — **blocked on M4**

## 7. Next

Re-run `materialise.py` once M4 lands; the pending sections fill in with no code
change. Then **M5** (gold set) and the **F5 amendment decision**.

---

## Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 31 August 2026 | Figures 2 and 3 computed; serving artefacts built pending-aware; F5 recorded as a proposed amendment |
