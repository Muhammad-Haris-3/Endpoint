# Endpoint

**Every clinical trial writes down what it will measure before it enrols anyone.
ClinicalTrials.gov keeps every edit to that promise, dated, in public. Nobody has
checked the whole registry for edits that landed after the data was already in.**

Endpoint is that check: **126,760 completed interventional trials**, their full
registration version history, and a per-trial record of what the primary outcome
was, what it became, and whether it changed before or after the sponsor could see
the answer.

> **Status: feasibility complete, collection not started.**
> Nothing has been crawled. The pilot in [`data/pilot/`](data/pilot/) is a
> feasibility check and is explicitly not a result. One measurement blocks the
> frame freeze — whether a Linux CI runner can reach the archive endpoints at all
> ([`FEASIBILITY.md`](FEASIBILITY.md) §7.1).

---

## The question

A trial that picks its outcome *after* seeing the data can find something in
almost any dataset. That is why the primary outcome is declared in advance, and
why the declaration is the entire basis of the evidence.

> **Which trials changed the outcome they promised to measure after they could
> already see the answer — and what happened to the trials that promised, and
> then reported nothing at all?**

The null this is built to be able to report is that outcome switching is rare,
that the registry is broadly honest, and that the edits it records after
completion are administrative tidying. That outcome is pre-committed as a
publishable finding, not a failure.

## The design that was killed first

The pitch was to read the registry's own change flag —
`history.lastUpdateVersions.primaryOutcomes` — date it against primary
completion, and report the share of trials that edited their promise after the
fact. On a 400-trial sample that gives **30.5%**.

It is wrong, and it is wrong in the direction that flatters the project.

`NCT02895035` is flagged as a change 386 days after completion. The two versions:

| | Primary outcome |
|---|---|
| **v4** | `the mean area under the curve change from baseline in pupil diameter over time to the end of cataract surgery` |
| **v5** | `Mean Area Under the Curve Change From Baseline in Pupil Diameter Over Time to the End of Cataract Surgery` |

A capitalisation pass, applied when results were attached. **The registry's flag
is computed on the field, not on the meaning.**

Fetching both versions for all 161 flagged trials and diffing the actual text:

| | Rate |
|---|---|
| Naive, taking the flag at face value | **30.5%** of trials |
| Adjudicated against the outcome text | **19.0%** of trials |
| Share of the naive signal that survives | **62.3%** |

**37.7% of the headline was an artefact.** For one flagged trial in seven the
primary outcome set is *byte-identical* across the change the registry flagged.

The naive version does not fail loudly. It returns a striking, round,
defensible-sounding number and a beautiful chart. The full measurement is in
[`FEASIBILITY.md`](FEASIBILITY.md) §4.

## What survives

**19.0% of sampled trials made a defensible change to their primary outcome
after primary completion.** The clearest cases are not subtle:

| Trial | After completion | Change |
|---|---|---|
| `NCT02100631` | +2,228 days | `Seroconversion by vibriocidal antibody (4-fold rise over baseline titer)` → `Seroconversion Rate at Day 11` |
| `NCT00478361` | +1,906 days | **4 primary outcomes → 1** |
| `NCT01360606` | +2,267 days | **1 → 2 primary outcomes** |

And separately, on the same 400 trials, all more than three years past the
12-month results deadline:

| | Measured |
|---|---|
| No results posted | **294 / 400 = 73.5%** |
| Of those posted, later than 365 days | **90 / 106 = 84.9%** |
| Enrolled participants in trials with no posted results | **76,384** |

That last figure is a count, not an estimate. It is **not** extrapolated to the
frame here, and doing so from a non-random sample of 400 would be exactly the
move this project exists to avoid.

## Why 19.0% is still an upper bound

A lexical comparator scores `Percent of participants with...` → `Number of
Participants With...` as substantive. It also cannot see that *"HbA1c at 12
weeks"* and *"glycated haemoglobin at 3 months"* are one endpoint.

So the number is a **floor for the method and a ceiling for the claim**, and the
true rate is not yet known. The semantic tier that would resolve it does not ship
without a hand-labelled gold set and a published precision and recall
([`Endpoint_SRS_v1.0.md`](Endpoint_SRS_v1.0.md) §5.4). An LLM in the loop without
a measured error rate is an opinion generator.

## What is being recorded

| Path | Contents |
|---|---|
| `data/cold/<ab>/<sha256>.json.gz` | Every fetched document, content-addressed, never mutated |
| `data/register/<batch>/manifest.ndjson.gz` | `{"u": url, "t": unix_fetched, "h": sha256, "s": status}` |
| `data/register/<batch>/run.json` | What happened, including every request that failed |

`t` is stamped **per document, not per run**. A 126,760-trial crawl spans hours,
so one run-level timestamp would be a fiction.

**Failures are data.** Every 403, 429, timeout and parse failure is counted and
the affected NCT IDs written to `run.json`, so a gap reads as a gap rather than as
an absence. A trial the crawl missed is excluded, never imputed.

**The cold store is the asset.** The archive endpoints are undocumented and
unversioned and may disappear without notice. Once a version is fetched and
hashed, the evidence is held independently of the source, and the register proves
when it was taken.

## The awkward part

The archive endpoints refuse most HTTP clients. Measured on one machine, in one
minute, with identical headers, with the documented endpoint as a control:

| Endpoint | `urllib` | `requests` | `curl` |
|---|---|---|---|
| `/api/v2/studies/{NCT}` (documented) | **200** | **200** | **200** |
| `/api/int/studies/{NCT}?history=true` | **403** | **403** | **200** |
| `/api/int/studies/{NCT}/history/{v}` | **403** | **403** | **200** |

Every client reaches the documented endpoint from the same process, so the
refusals are not the network and not the code — only the archive endpoints
discriminate.

Header spoofing does not move it; the gate is a TLS client fingerprint, not an
authorization check. There is nothing to authenticate to and nothing being
circumvented — a browser visiting the page receives the same bytes. So
[`scripts/fetch.py`](scripts/fetch.py) shells out to curl, paced at 2 req/s with
backoff and an identifying `User-Agent`.

**This is the open risk.** That curl links Schannel on Windows and OpenSSL on a
Linux runner, and the runner may be refused. Halflife assumed the CI runner was
the clean environment and found the assumption exactly inverted. Until that is
measured, the frame is not frozen.

## Layout

| Path | |
|---|---|
| [`FEASIBILITY.md`](FEASIBILITY.md) | What was measured before anything was designed |
| [`Endpoint_SRS_v1.0.md`](Endpoint_SRS_v1.0.md) | Requirements, architecture, milestones |
| [`PREREGISTRATION.md`](PREREGISTRATION.md) | Analysis rules — draft, not frozen |
| [`scripts/fetch.py`](scripts/fetch.py) | HTTP layer, and why it shells to curl |
| [`scripts/pilot.py`](scripts/pilot.py) | The feasibility measurement |
| [`scripts/adjudicate.py`](scripts/adjudicate.py) | The check that caught the artefact |
| [`data/pilot/`](data/pilot/) | Raw output of both, committed as evidence |

## Reproducing the pilot

```bash
python scripts/pilot.py --n 400 --stride 25 --rate 2.0
```

```bash
python scripts/adjudicate.py --rate 2.0
```

Roughly eleven minutes and 722 requests, all against public endpoints.

## What is not claimed

- **A retrospective change is not fraud.** Registrations are edited for many
  legitimate reasons, including at a regulator's instruction. Endpoint reports
  what changed and when, never why, and never intent.
- **Non-reporting is not a legal violation.** FDAAA applicability is not exposed
  by the API and this project does not adjudicate it.
- **The pilot sample is not random.** It is a systematic stride through the API's
  own ordering, and carries no confidence intervals because it does not deserve
  any.
- ClinicalTrials.gov only. EU CTR, ISRCTN and the WHO ICTRP have not been checked.
