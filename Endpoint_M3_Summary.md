# Endpoint — M3 (History Crawl) Milestone Summary

Companion to [Endpoint_SRS_v1.0.md](Endpoint_SRS_v1.0.md) (Sections 5.2, 6 —
FR-2, FR-4, FR-11) and [PREREGISTRATION.md](PREREGISTRATION.md) §8.

**Status: Complete** — 2026-08-30

---

## 1. Scope (per SRS Section 12)

> History crawl. Exit criterion: version index for the full frame in the register.

One request per trial against `/api/int/studies/{NCT}?history=true`, for all
126,760 trials in the frozen frame. Sharded, paced, resumable, recording every
failure.

## 2. What was built

| Area | Delivered |
|---|---|
| **Collector (FR-2, FR-4)** | `scripts/collect_history.py` — verifies `frame/studies.tsv` against `frame/MANIFEST` before fetching anything, shards by index modulo N, probes its own sustainable rate before committing to it, and writes content-addressed documents plus a manifest and an extraction. Resumable within a batch: already-fetched trials are read from the shard manifest and skipped. |
| **Merge (FR-11)** | `scripts/merge_shards.py` — reconciles the union of shards against the frozen frame and refuses to merge on duplicate NCTs or records outside the frame. Missing trials are written by name to `missing.txt`. |
| **Workflow** | `.github/workflows/collect-history.yml` — 8-shard matrix → artifacts → merge → commit. `workflow_dispatch` only, with `shards`, `rate`, `workers`, `limit`, `cold_store`, `batch` and `commit` inputs. |
| **Report** | `scripts/register_report.py` — what the register supports, and explicitly what it does not. |

## 3. Artefact change

New and committed: `data/register/history-2026-08-30/` — `records.ndjson.gz`
(8.9 MB), `manifest.ndjson.gz` (6.0 MB), `run.json`, and the eight per-shard
files the merge is a claim about.

Manifest lines are `{p, u, t, h, s}`; `t` is stamped **per document, not per
run**, because a 126,760-trial crawl spans hours and one run-level timestamp
would be a fiction.

## 4. How it was verified (not just "should work")

1. **126,760 of 126,760 collected. Zero failures** — no 403s, no 429s, no
   timeouts, no unparseable documents. Zero missing, zero duplicates, zero
   records outside the frame.
2. **The merge reconciles against the frozen frame**, not against whatever
   arrived; `BATCH COMPLETE: True`. The workflow's incomplete-batch guard would
   have failed the run otherwise, so the green conclusion is meaningful.
3. **Cold-store round-trip verified by hash** during smoke testing: a stored
   `.json.gz` decompresses to bytes whose SHA-256 matches the digest recorded in
   the manifest.
4. **Rehearsed end to end on CI before the real run** — 8 shards × 20 trials,
   `commit=false`. Confirmed the matrix, artifact upload/download, merge and the
   incomplete-batch guard, with **zero duplicates across shards**, proving the
   partition is correct. Nothing was committed.
5. **Estimates held.** Predicted 133 min per shard against **132 measured**;
   predicted 24.6 KB mean response against **28.3 measured**. 3.675 GB fetched.
6. **The pilot's sampling validated against the census**: 89.5% multi-version
   estimated vs **89.8%** actual; 40.2% flagged vs **42.8%**.

## 5. Decisions & notes worth remembering

- **The pacer was serial, and the crawl is latency-bound.** A 2 req/s target
  delivered 1.11 req/s because each request takes ~0.8 s and the token bucket was
  releasing into a single thread. Adding a worker pool *under the same global
  pacer* — workers exist to make the cap reachable, not to exceed it — took it to
  **1.99 req/s**, halving per-shard time to ~2.2 h against the 6-hour ceiling.
- **A `--limit` smoke test on an NCT-sorted frame measures the oldest trials.**
  The first run reported a 61.7 KB mean response; the frame is sorted by NCT ID,
  so the first 30 rows are the oldest trials, which have the longest histories.
  Sampling *across* the frame instead gave 24.6 KB. **A convenience slice of a
  sorted list is not a sample of it**, and the cost model would have been inflated
  2.5× by trusting it.
- **A durability claim was walked back rather than left flattering.** The README,
  `.gitignore` and SRS all said the cold store was either the durable asset or
  reproducible from the manifest. Measured, it is **~1.5 GB gzipped and neither**:
  the manifest lets a holder *verify* bytes, nothing *regenerates* them, and the
  archive endpoints may disappear. What is committed is the hashes plus the
  extracted fields (~3.4 MB), enough to recompute every primary figure. Publishing
  the documents durably became **M3.1, explicitly not built**.
- **The collector refuses to run against a drifted frame.** A collector reading a
  frame file that no longer matches the manifest is crawling a different cohort
  than the pre-registered one and would have no way to know.
- **Every version whose `moduleLabels` mention `Outcome Measures` is recorded**,
  not just the last. That is what makes the §5.4 blind spot measurable later
  without re-crawling — and it turned out to be **27,612 trials, 21.8%**.
- **Not scheduled.** The frame is frozen and closed, so this is a one-shot
  collection; a cron would re-fetch a fixed cohort forever.

## 6. Definition of Done — checked

- [x] Full frame collected with zero gaps, reconciled against `frame/MANIFEST`
- [x] Rehearsed on CI before the real run
- [x] Failures recorded as data (there were none, and `run.json` says so with counts)
- [x] Register committed; cold store correctly excluded with the reasoning corrected
- [x] `register_report.py` refuses to present the registry flag as the finding

## 7. Next

**M4 — Version crawl and Tier 1 adjudication.** 54,203 flagged trials × 2 versions
= 108,406 fetches. This is what makes primary figure 1 computable.

---

## Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 30 August 2026 | Full crawl complete, 126,760/126,760, zero failures; concurrency and mean-size corrections recorded; cold-store durability claim corrected |
