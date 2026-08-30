# Endpoint — pre-registration v1.0 (DRAFT — NOT FROZEN)

> ## ⚠ DRAFT — not frozen. One measurement blocks the freeze.
>
> **§7.1 of [`FEASIBILITY.md`](FEASIBILITY.md) is open.** The archive endpoints
> gate on a TLS client fingerprint. Whether a Linux CI runner reaches them at all
> is unmeasured, and if it does not, the collection architecture in §8 is not
> buildable as written.
>
> **No crawl has run. `frame/MANIFEST` does not exist. The frame is not frozen.**

**Drafted 30 August 2026, after the pilot in [`FEASIBILITY.md`](FEASIBILITY.md)
and before any collection.** That pilot had been seen when this was written, and
is explicitly **not** part of any result reported under this document. Its
sample is discarded, not reused: the full crawl re-fetches every trial in it.

Everything below is fixed at freeze. Changes require a numbered amendment under
§11 stating what changed, why, and what had already been seen, kept in git
history beside the original.

---

## 0. Why this document exists

The pilot already demonstrated how this project fails. Taking the registry's
change flag at face value gives **30.5%**; reading the underlying text gives
**19.0%** ([`FEASIBILITY.md`](FEASIBILITY.md) §4). Both are defensible-sounding.
Both would chart beautifully. The difference between them is a decision about
what counts as a change — and a decision like that, made after seeing which
answer it produces, is not a method.

So the rules are fixed here, before the crawl, and every figure Endpoint
publishes cites the commit hash of this file as it stood when that figure's
crawl **began**.

---

## 1. The question

> **Among completed interventional trials, what share made a substantive change
> to their registered primary outcome after primary completion — and what share
> reported no results at all?**

The null this is built to report is that substantive retrospective change is
rare, that the registry is broadly honest, and that post-completion edits are
administrative. That is a publishable finding, pre-committed as such.

---

## 2. The frame

### 2.1 The rule, fixed now

Every study returned by ClinicalTrials.gov API v2 matching, on the build date:

```
AREA[StudyType]INTERVENTIONAL
AND AREA[PrimaryCompletionDate]RANGE[2015-01-01,2022-12-31]
filter.overallStatus = COMPLETED|TERMINATED
```

**Measured size on 30 August 2026: 126,760 studies.**

The window ends at 2022 so that every trial in it is more than three years past
the 12-month results deadline. An absent result is then *settled, not pending* —
the difference between measuring non-reporting and measuring slowness.

The frame is written to `frame/frame.json` with a SHA-256 recorded in
`frame/MANIFEST` alongside the freeze timestamp and the resolved size. It is
**closed at freeze and does not grow.** Trials whose status changes afterwards
stay in the frame with their frozen status recorded, because a frame that tracks
the world is a frame that can be reshaped by the world after the question is
asked.

### 2.2 Why this frame and not a larger one

The obvious alternative is all 600,762 registered studies. It is rejected on
interpretability, not cost: observational studies have no comparable
pre-commitment, and trials still recruiting have not reached the point at which
a retrospective change is definable. The measurement requires a completion date
that has passed.

### 2.3 Known dependency

Membership rests on the API's own `PrimaryCompletionDate` indexing. A trial whose
completion date is absent or malformed is not returned and is missed. Nothing in
this design would detect that, and the count of such records is not established.

---

## 3. Admission to the primary set

A trial in the frame enters the primary analysis if **all** hold:

1. Its version history was fetched successfully.
2. `statusModule.primaryCompletionDateStruct.date` is present and parseable.
3. `history.lastUpdateVersions.primaryOutcomes` is present and ≥ 1, **or** it is
   absent (which is an observation of "never changed", not a missing value).

A trial failing (1) is **excluded and counted**, never imputed. The count of
exclusions is published beside every figure that depends on the frame.

---

## 4. Definitions, fixed

| Term | Definition |
|---|---|
| **Primary completion** | `statusModule.primaryCompletionDateStruct.date` |
| **Change version** | `history.lastUpdateVersions.primaryOutcomes` |
| **Change date** | `history.changes[change_version].date` |
| **Retrospective** | `change_date > primary_completion`, **strictly** |
| **Silent trial** | End-state status, `hasResults` false, no resolved publication |

### 4.1 Date precision

A month-precision date (`2019-03`) resolves to the **last day of that month**. A
year-precision date resolves to 31 December.

This is the conservative direction: it makes a change *less* likely to be called
retrospective, never more. **24.8% of pilot completion dates were month
precision**, so the convention is load-bearing and is fixed here rather than
chosen at analysis time.

### 4.2 Same-day changes

A change dated the same day as primary completion is **prospective**. Fixed now
because the alternative is defensible and would raise the headline.

---

## 5. Adjudication, fixed

For every trial with a change version ≥ 1, versions *v−1* and *v* are fetched and
their primary outcome sets compared.

### 5.1 Tier 1, lexical — the reported figure

Normalisation: HTML-unescape twice (the API double-escapes), lowercase, replace
all non-alphanumeric runs with a single space, collapse whitespace.

| Verdict | Rule |
|---|---|
| `COUNT_CHANGED` | Number of primary outcomes differs |
| `SUBSTANTIVE` | Normalised measure sets differ, min pairwise token Jaccard **< 0.80** |
| `REWORDED` | Normalised measure sets differ, min Jaccard **≥ 0.80** |
| `TIMEFRAME_ONLY` | Normalised measures equal, normalised timeframes differ |
| `COSMETIC` | Equal after normalisation |
| `IDENTICAL` | Byte-identical |

**The primary figure counts `COUNT_CHANGED` and `SUBSTANTIVE` only.**

The 0.80 Jaccard threshold is fixed now. It was set from the pilot and it is
arbitrary; sensitivity at 0.70 and 0.90 will be published alongside the primary
figure **whatever it shows**.

### 5.2 `TIMEFRAME_ONLY` does not count

It is 14.8% of retrospective flags in the pilot and is sometimes genuinely
substantive — a changed measurement window can change a result. It is excluded
from the primary figure because including a category this ambiguous would make
the headline unfalsifiable, and it is reported separately in full.

This is the decision most likely to be argued with. It is made here, in advance,
in the direction that lowers the number.

### 5.3 Tier 2, semantic — not in the primary figure

Any embedding or LLM adjudication is **reported separately and never substituted
into the primary figure**, and does not ship at all without:

- a hand-labelled gold set of **≥ 300 version pairs**, labelled before Tier 2 is
  run over the frame;
- published precision and recall for Tier 1 and Tier 2 against that gold set;
- every judgement cached keyed by `(sha256(a), sha256(b), prompt_hash, model_id)`
  and committed, so a re-run produces a *diff against recorded judgements* rather
  than a silently different result.

### 5.4 Known under-reporting, accepted

`lastUpdateVersions` reports only the **last** primary-outcome change. A trial
changed retrospectively and then again prospectively is missed. This biases the
primary figure **downward** and is accepted rather than fixed, because the full
`changes[]` scan that would fix it is uncosted. The count of trials with more
than one outcome-touching version is published so the size of the blind spot is
visible.

---

## 6. The primary figures

Three, fixed now, each published with its denominator and exclusion count:

1. **Retrospective change rate.** Trials with a `COUNT_CHANGED` or
   `SUBSTANTIVE` verdict dated after primary completion, over trials admitted
   under §3.
2. **Non-reporting rate.** Trials with `hasResults` false, over trials admitted.
3. **Participants in silent trials.** Sum of `enrollmentInfo.count` over trials
   with no posted results. A **count**, reported with the number of trials whose
   enrolment field is absent.

No figure is published without the verdict mix from §5.1 shown beside it.

---

## 7. The kill condition

Fixed before the crawl:

> **If the defensible retrospective change rate over the full frame is below
> 5%, the finding is reported as "substantive retrospective outcome change is
> uncommon; the registry's own change flag overstates it by roughly a factor of
> two, and that overstatement is the result."**

That is a publishable outcome and the site ships with it. The pilot's 19.0% does
not license an expectation — it is a non-random sample of 400 against a frame of
126,760, and the full crawl may land anywhere.

---

## 8. Collection

Sharded across CI runners, paced at **≤ 2 req/s per egress IP**, exponential
backoff honouring `Retry-After`, identifying `User-Agent`.

Two passes:

1. Version index for all 126,760 trials — 3.5 GB, 4.4 h across 8 shards.
2. Versions *v−1* and *v* for every trial with a change version ≥ 1 — ~101,000
   requests, ~2.8 GB, 3.5 h across 8 shards.

Every document is written content-addressed to the cold store and never mutated.
Every failure is recorded in `run.json` with its NCT ID and status.

**Zero refusals were observed at 2 req/s over 722 pilot requests. That means the
ceiling is unknown, not high.** Each shard measures its own sustainable rate
before the crawl and records it.

---

## 9. Integrity of the record

The register is **gzipped files in git, not a database.** Cost is the smaller
reason. The larger one is that this project's claim is that a specific trial's
promise changed on a specific date, and a public commit history is *evidence*
where a database grant is only an assurance. A `REVOKE UPDATE` only its owner can
inspect is a promise; a public commit history is checkable by a stranger.

The repository is byte-exact on every platform (`.gitattributes`), because a hash
a verifier cannot reproduce is not evidence.

---

## 10. What is not claimed

- **A retrospective change is not fraud**, and no figure, chart, label or headline
  may imply intent. The site reports what changed and when.
- **Non-reporting is not a legal violation.** FDAAA applicability is not exposed
  by the API and is not adjudicated here.
- **Tier 1 is a floor for the method and a ceiling for the claim**
  ([`FEASIBILITY.md`](FEASIBILITY.md) §4.4).
- **No sponsor is named in a headline.** Sponsor rollups are reachable by
  drill-through, where the underlying per-trial evidence is one click away.

---

## 11. Amendments

None. The document is not yet frozen.

| # | Date | Change | What had been seen |
|---|---|---|---|
| — | — | — | — |
