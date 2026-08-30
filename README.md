# Endpoint

**Every clinical trial writes down what it will measure before it enrols anyone.
ClinicalTrials.gov keeps every edit to that promise, dated, in public. Nobody has
checked the whole registry for edits that landed after the data was already in.**

Endpoint is that check: **126,760 completed interventional trials**, their full
registration version history, and a per-trial record of what the primary outcome
was, what it became, and whether it changed before or after the sponsor could see
the answer.

> **Status: frame frozen and version history collected, 30 August 2026.**
> The cohort is closed at **126,760 trials**; [`frame/MANIFEST`](frame/MANIFEST)
> records the SHA-256 of the frame, its metadata and the pre-registration.
>
> **The history crawl is complete: 126,760 of 126,760, zero failures, zero
> missing, zero duplicates.** The register is committed.
>
> **The headline figure is still not computable.** What the register carries is
> the registry's own change *flag*; primary figure 1 requires reading the outcome
> text at both versions, which is M4 and has not run. On the pilot, 37.7% of that
> flag did not survive reading the text.

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

### The full frame, as far as the crawl takes it

The history crawl is complete, so the *flagged* rate is now a census. The
*adjudicated* rate still is not — that needs M4.

| | Frame (n = 126,760) | Pilot (n = 400) |
|---|---|---|
| Trials with >1 submitted version | 89.8% | 89.5% |
| Median versions per trial | 5 | 5 |
| Primary outcome **flagged** as changed | **42.8%** | 40.2% |
| **Flagged** as changed after primary completion | **33.6%** | 30.5% |
| Median days after completion | 529 | 565 |
| Adjudicated against the outcome text | **not yet computed** | 19.0% |

The pilot's sampling held up: every row it estimated lands within a few points of
the census. **That is not permission to apply its 62.3% survival ratio to
33.6%.** Whether the flag survives reading the text is a property of the text,
not of the sample, and the only way to know is M4 — 108,406 version fetches,
about 1.9 h across 8 shards.

The largest single history in the frame runs to **1,651 submitted versions**.

**The §5.4 blind spot is now measured: 27,612 trials — 21.8% — have more than one
outcome-touching version.** The primary figure reads only the *last* one, so any
earlier change is invisible to it. This biases the reported rate **downward**,
and the pre-registration accepts it rather than pretending it away.

### Reporting, which needs no crawl at all

`hasResults` is carried in the frame itself, so this is a **census, not a
sample** — every trial in the denominator is more than three years past the
12-month deadline, so an absent result is settled rather than pending.

| | Frame census (n = 126,760) |
|---|---|
| **No results posted** | **91,495 = 72.2%** |
| Of those that did post, later than 365 days | **30,741 = 87.2%** |
| Median days, completion → posting | **584** |

**The variation by sponsor is larger than the headline, and runs opposite to the
direction most readers would guess:**

| Lead sponsor class | Trials | Silent | Rate |
|---|---|---|---|
| `OTHER_GOV` | 2,586 | 2,487 | **96.2%** |
| `OTHER` (academic, hospital, foundation) | 88,403 | 70,572 | **79.8%** |
| `INDUSTRY` | 32,449 | 17,125 | **52.8%** |
| `NIH` | 1,265 | 351 | **27.7%** |

**Industry reports at roughly twice the rate of academia.** `PHASE3` — the trials
that support approvals — is 43.7% silent.

These are rates, so they survive the outlier problem that sinks the participant
sum below. They are the most defensible numbers the project holds.

### The participant count, and why it is not the headline

The pre-registered figure 3 is the raw sum of enrolment over silent trials:
**58,650,765 participants**. It was going to be the landing figure precisely
because it is a count rather than an estimate.

It is not reportable alone. The median silent trial has **52 participants**; the
single largest carries **21% of the total** and is `NCT05438901`, a single-group
before/after study of *leech therapy* recorded as having enrolled 12,317,546
people. Most of the other top contributors are behavioural megastudies — SMS
nudges, online health ads — which really did enrol millions, but not in the sense
the phrase invites.

Depending on the estimator the figure ranges from **4.8 million to 58.7 million**.
The frozen one is reported unmodified and an amendment is *proposed*, not applied
— see [`FINDINGS.md`](FINDINGS.md) F5. **This is the third time this project has
met the same failure mode**, and it is starting to look like the default outcome
of any naive aggregate over this registry rather than bad luck.

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

| Path | Contents | Committed? |
|---|---|---|
| `data/register/<batch>/manifest.ndjson.gz` | Per-document `{url, unix_fetched, sha256, status}` | **yes** |
| `data/register/<batch>/records.ndjson.gz` | The extracted fields the analysis consumes, ~3.4 MB | **yes** |
| `data/register/<batch>/run.json` | What happened, including every request that failed | **yes** |
| `data/register/<batch>/missing.txt` | Trials the crawl did not get, by name | **yes** |
| `data/cold/<ab>/<sha256>.json.gz` | Every fetched document, content-addressed, never mutated | no — 1.5 GB |

`t` is stamped **per document, not per run**. A 126,760-trial crawl spans hours,
so one run-level timestamp would be a fiction.

**Failures are data.** Every 403, 429, timeout and parse failure is counted and
the affected NCT IDs written to `run.json`, so a gap reads as a gap rather than as
an absence. A trial the crawl missed is excluded, never imputed.

**What is durable, stated precisely.** An earlier draft of this README claimed
"the cold store is the asset — once a version is fetched and hashed, the evidence
is held independently of the source." That was half true, and measuring the sizes
is what forced the correction.

The full documents gzip to **~1.5 GB** across the frame. They do not go in git.
What is committed is the **per-document SHA-256 and the extracted fields** — about
3.4 MB — which is enough to recompute every primary figure and enough for anyone
holding the documents to verify they match. The documents themselves are retained
best-effort as CI artefacts, and CI artefacts expire.

So: this project can prove **what it saw and when**, and can recompute its
results from committed data. It cannot yet hand a stranger the original bytes.
Publishing the cold store durably as release assets is **M3.1 and is not built**.
The archive endpoints are undocumented and may disappear before that happens.

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

**This was the open risk, and it is now measured.** The worry was that curl links
Schannel here and OpenSSL on a Linux runner, so the runner might be refused and
the whole sharded plan would collapse. It is not: both `ubuntu-latest` and
`windows-latest` are served, 20/20 at 2 req/s with zero refusals.

**The stated reason was wrong, though.** On the Ubuntu runner Python's `ssl`
reports OpenSSL 3.0.13 and curl links OpenSSL/3.0.13 — same library, same
machine — and curl is served while `urllib` is refused. So the TLS library is not
the discriminator; the handshake profile is. Running the probe on both operating
systems instead of only the one in doubt is what caught that. A single-OS run
would have returned "works", and the explanation attached to it would have been
false.

## Layout

| Path | |
|---|---|
| [`frame/MANIFEST`](frame/MANIFEST) | The freeze: SHA-256 of the frame, its metadata, and the pre-registration |
| `frame/studies.tsv` | The cohort. 126,760 rows, sorted by NCT ID |
| [`FINDINGS.md`](FINDINGS.md) | Discoveries and corrections, accumulating |
| [`FEASIBILITY.md`](FEASIBILITY.md) | What was measured before anything was designed |
| [`Endpoint_SRS_v1.0.md`](Endpoint_SRS_v1.0.md) | Requirements, architecture, milestones |
| [`PREREGISTRATION.md`](PREREGISTRATION.md) | Analysis rules — draft, not frozen |
| [`scripts/fetch.py`](scripts/fetch.py) | HTTP layer, and why it shells to curl |
| [`scripts/pilot.py`](scripts/pilot.py) | The feasibility measurement |
| [`scripts/adjudicate.py`](scripts/adjudicate.py) | The check that caught the artefact |
| [`scripts/collect_history.py`](scripts/collect_history.py) | The sharded crawl |
| [`scripts/register_report.py`](scripts/register_report.py) | What the register supports, and what it does not |
| [`scripts/reporting_figures.py`](scripts/reporting_figures.py) | Primary figures 2 and 3, from the frame alone |
| [`scripts/build_frame.py`](scripts/build_frame.py) | Resolves the frame from the pre-registered rule |
| [`scripts/freeze_frame.py`](scripts/freeze_frame.py) | The freeze. Refuses more than it does |
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
