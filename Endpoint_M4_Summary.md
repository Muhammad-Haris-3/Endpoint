# Endpoint — M4 (Version Crawl & Tier 1 Adjudication) Milestone Summary

Companion to [Endpoint_SRS_v1.0.md](Endpoint_SRS_v1.0.md) (Sections 5.4, 6 —
FR-3, FR-5) and [PREREGISTRATION.md](PREREGISTRATION.md) §5, §6, §7.

**Status: Complete** — 2026-08-31

> **Primary figure 1 is 19.9%, and Section 5 explains why that number cannot be
> read as "19.9% of trials switched their outcomes".** The most important result
> of this milestone is the confound, not the figure.

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
7. **The full crawl: 54,203 of 54,203 pairs, zero missing, zero outside the
   flagged list.** `BATCH COMPLETE: True`. Eight shards at 1h53m each.
8. **The crawl's own failure was recovered and reproduced.** The workflow's final
   push was rejected (main had moved during the two-hour run), stranding the
   register in its artefacts. Recovered from there, and `adjudicate_frame.py`
   was **re-run locally rather than the CI verdicts being copied** — every figure
   matched the CI run exactly. Since the adjudicator is pure and network-free,
   that is a genuine determinism check.
9. **Shard 7's 724 stragglers resumed cleanly**: 724 fetched, zero failures. All
   were `HTTP 0` transport timeouts, not refusals — zero 429s and zero probe
   refusals across every shard, all runs.
10. **An independent cross-check landed to the unit.** The retrospective flag
    count from the version crawl is **42,623**, which is exactly what
    `register_report.py` computed from the *history* register before the version
    crawl existed. Two code paths, two registers, same number.

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
- **THE HEADLINE IS CONFOUNDED, AND THIS IS THE MILESTONE'S REAL RESULT.**
  Primary figure 1 is 19.9%. But the rate among trials that **posted results** is
  **59.0%**, against **4.8%** among trials that posted nothing — a twelvefold
  difference. And **70.9% of flagged changes in reporting trials fall within 31
  days of the results-posting date** (median gap 24 days). ClinicalTrials.gov's
  results-submission process requires restating the outcome measures in a
  structured format, and that restatement is filed as a new version dated after
  primary completion by construction.

  The sponsor breakdown consequently inverts F4's reporting table almost rank for
  rank — NIH reports best (27.7% silent) and "switches" most (56.1%); `OTHER_GOV`
  reports worst (96.2% silent) and "switches" least (7.8%). **That is the
  reporting rate measured twice, not a ranking of research integrity.**

  It does **not** follow that the changes are benign: results posting is exactly
  when genuine outcome switching would happen, because it is when the sponsor
  writes up what they found. The artefact and the offence occur at the same
  moment in the same field, and no date arithmetic separates them. Only reading
  whether the *substance* of the endpoint changed can — which makes M5 load-bearing
  rather than an enhancement. Full working in [FINDINGS.md](FINDINGS.md) F6.

- **A distinction the frozen rules do not draw, surfaced rather than fixed.**
  §5.1 defines `COUNT_CHANGED` as "the number of primary outcomes differs". Some
  trials have **no registered primary outcome** in the earlier version and gain
  one in the later. That satisfies the rule as written, but *"a registration was
  completed"* is not the same act as *"four declared outcomes became one"*. Those
  trials **are** counted in primary figure 1 exactly as §5.1 requires, **and** are
  broken out on their own line so a reader can see how much of the figure rests on
  them. Excluding them now, after seeing which way it moves the headline, is
  precisely what §11 requires an amendment for. **The rehearsal suggested 10.8% of pairs; the census says 0.8%** (408 pairs,
  1.1% of the defensible figure). The rehearsal figure was itself an artefact of
  taking the first 15 trials per shard, which are the oldest — the same
  sorted-slice trap that inflated M3's mean-response estimate. Still reported,
  still not excluded.
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
- [x] Full crawl complete and reconciled — 54,203/54,203, zero missing
- [x] Primary figure 1 reported with its verdict mix and the empty-before breakout
- [x] The confound found, measured and recorded before the figure was published

## 7. Next

**M5 — Gold set and Tier 2.** No longer an enhancement: F6 establishes that the
lexical tier cannot separate a results-format restatement from a genuine switch,
and only reading the substance can. The pairs it needs are now collected.

Two decisions are outstanding and are decisions rather than builds: the **F5**
and **F6** proposed amendments in [FINDINGS.md](FINDINGS.md).

---

## Document Control

| Version | Date | Change |
|---|---|---|
| 0.9 | 30 August 2026 | Built, rehearsed, full crawl launched; result pending |
| 1.0 | 31 August 2026 | Crawl complete (54,203/54,203); primary figure 1 at 19.9%; the results-posting confound found, measured and recorded as F6 |
