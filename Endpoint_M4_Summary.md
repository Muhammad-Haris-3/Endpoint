# Endpoint — M4 (Version Crawl & Tier 1 Adjudication) Milestone Summary

Companion to [Endpoint_SRS_v1.0.md](Endpoint_SRS_v1.0.md) (Sections 5.4, 6 —
FR-3, FR-5) and [PREREGISTRATION.md](PREREGISTRATION.md) §5, §6, §7.

**Status: Built and rehearsed; full crawl running** — started 2026-08-30 19:19Z

> This summary will be completed with the reconciliation and primary figure 1
> once the crawl lands. Everything below is verified; the frame-wide result is
> not yet in and is **not** stated here.

---

## 1. Scope (per SRS Section 12)

> Version crawl + Tier 1. Exit criterion: every flagged change adjudicated
> deterministically.

For each of the 54,203 trials the history register flagged, fetch versions *v−1*
and *v*, store both outcome sets, and classify what actually changed under the
rules frozen in `PREREGISTRATION.md` §5.1. **This is the milestone that produces
primary figure 1.**

## 2. What was built

| Area | Delivered |
|---|---|
| **Frozen rules** | `scripts/verdict.py` — `norm`, `jaccard`, `classify` and the 0.80 threshold, extracted so the pilot and the frame run are produced by the same code rather than two copies that agree until one is edited. `--selftest` re-derives the pilot's committed verdicts from its committed texts. |
| **Collector (FR-3)** | `scripts/collect_versions.py` — sharded, paced, resumable; verifies the frame against `frame/MANIFEST`; stores primary outcomes (measure, timeFrame, description) at both versions plus secondary outcome *measures*. Never classifies anything (Section 5). |
| **Adjudicator (FR-5)** | `scripts/adjudicate_frame.py` — pure, offline, network-free. Classifies every stored pair, joins to the frame for dates and sponsor class, reconciles against the flagged list, and writes verdicts plus a report. |
| **Workflow** | `.github/workflows/collect-versions.yml` — 8-shard matrix → adjudicate → commit, with `verdict.py --selftest` as a gate before adjudication runs. |

## 3. Artefact change

New: `data/register/versions-<date>/shard-NN.versions.ndjson.gz` (~29 MB total,
committed) and `verdicts.ndjson.gz` + `verdicts.txt`. The full documents (~1.8 GB)
are not committed, on the same reasoning as M3.

`scripts/adjudicate.py` (the pilot script) now imports the shared rules; its local
copy was deleted rather than left shadowing the import.

## 4. How it was verified (not just "should work")

1. **The extracted rules reproduce the pilot exactly.** `verdict.py --selftest`
   re-derives verdicts from `data/pilot/adjudication.json`: **97 re-derived, 97
   matched, 0 moved.** 64 are **skipped and counted** rather than silently passed
   — the pilot output kept measures but not timeframes, so timeframe-dependent
   verdicts are not decidable from it. A selftest reporting 100% while quietly
   skipping a category is worse than none.
2. **The selftest runs on CI as a gate** before adjudication, and passed on the
   rehearsal run.
3. **Single source of truth confirmed programmatically**:
   `adjudicate.classify is verdict.classify` → `True`.
4. **Rehearsed end to end on CI** — 8 shards × 15 trials, `commit=false`. All 8
   shards succeeded; 120 pairs adjudicated; reconciliation reported 54,083
   missing against the flagged list and exited 2, which is the incomplete-batch
   guard working. Nothing was committed.
5. **Storage measured before committing to the design**: 568 bytes gzipped per
   pair → ~29 MB for the frame, against ~1.8 GB for the documents. Version
   responses are 41.8 KB mean, larger than the history index because they are
   full study records.
6. **Effective rate 1.96 req/s** with 4 workers, matching M3's corrected figure.

## 5. Decisions & notes worth remembering

- **Fetching and adjudicating are separate programs, deliberately.** The fetch is
  network-bound and rate-limited; the adjudication is pure and deterministic.
  Fusing them would mean any amendment to `PREREGISTRATION.md` §5.1 — which §11
  permits, but permits *by numbered amendment* — costs another 108,406 requests
  against a public API instead of four seconds locally.
- **Secondary outcome measures are stored even though Tier 1 cannot use them.**
  Promotion of a secondary outcome to primary is the classic form of outcome
  switching, and Tier 2 can see it — but only if the data was kept now, while the
  crawl is running anyway.
- **A pair with one half missing is recorded as a failure, not stored
  half-complete**, so nothing downstream can mistake it for a comparison.
- **A distinction the frozen rules do not draw, surfaced rather than fixed.**
  §5.1 defines `COUNT_CHANGED` as "the number of primary outcomes differs". Some
  trials have **no registered primary outcome** in the earlier version and gain
  one in the later. That satisfies the rule as written, but *"a registration was
  completed"* is not the same act as *"four declared outcomes became one"*. Those
  trials **are** counted in primary figure 1 exactly as §5.1 requires, **and** are
  broken out on their own line so a reader can see how much of the figure rests on
  them. Excluding them now, after seeing which way it moves the headline, is
  precisely what §11 requires an amendment for. **In the rehearsal they were 10.8%
  of pairs** — enough to matter.
- **The adjudicator reconciles rather than rescaling.** Adjudicating whatever
  arrived and reporting a rate over it would silently move the denominator to
  whatever the crawl managed to fetch. Missing pairs are named in
  `missing_pairs.txt` and excluded, never half-compared.

## 6. Definition of Done — checked so far

- [x] Rules extracted to one place with a regression test against committed pilot output
- [x] Selftest wired as a CI gate
- [x] Fetch and adjudication separable, so a rule change costs no requests
- [x] Rehearsed on CI with nothing committed
- [x] Storage cost measured, not estimated
- [ ] Full crawl complete and reconciled — **running**
- [ ] Primary figure 1 reported with its verdict mix and the empty-before breakout

## 7. Next

**M5 — Gold set and Tier 2**, which needs M4's pairs to label. Separately, the
**F5 amendment** ([FINDINGS.md](FINDINGS.md)) is a decision, not a build.

---

## Document Control

| Version | Date | Change |
|---|---|---|
| 0.9 | 30 August 2026 | Built, rehearsed, full crawl launched; result pending |
