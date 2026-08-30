# Endpoint — feasibility check

**Checked 30 August 2026, before any collection has begun and before
`PREREGISTRATION.md` exists. Every number below was measured against the live
API, not quoted.** Raw pilot output in [`data/pilot/`](data/pilot/), the three
scripts that produced it in [`scripts/`](scripts/).

Nothing in this document is a result. It is a check on whether a result is
obtainable, and the pilot data described here is explicitly **not** part of any
figure the project later publishes.

---

## Verdict

**Build it — but the headline number the design was pitched on is inflated by
about a third, and this check is what caught it.**

The load-bearing data exists and is richer than expected (§1). The phenomenon is
real and large (§4). But the registry's own change flag fires on cosmetic edits,
and taking it at face value would have produced **30.5%** where reading the
actual text supports **19.0%** — a large, clean, publishable-looking number,
inflated in exactly the direction the project hopes to find. The adjudication
stage that fixes it is now a requirement rather than a refinement (§4.3).

---

## 1. The load-bearing fact

Everything depends on one property of ClinicalTrials.gov, so it was checked
first.

| Endpoint | Result |
|---|---|
| `/api/v2/studies` | **200** — documented, keyless, cursor-paginated, 600,762 studies |
| `/api/int/studies/{NCT}?history=true` | **200** — the full version index |
| `/api/int/studies/{NCT}/history/{v}` | **200** — one archived version, in full |
| `/api/v2/studies/{NCT}/history` | 404 — no documented history route exists |

**ClinicalTrials.gov keeps every submitted version of every registration, dated,
and serves them publicly.** The version index returns, per trial:

- `changes[]` — one entry per submitted version, each with `version`, `date`,
  `status`, and `moduleLabels[]` naming which sections changed
- `lastUpdateVersions` — a map whose `primaryOutcomes` key is the version index
  at which the primary outcome was **last** modified
- `outcomesUpdateCount`

`moduleLabels` is what makes the project affordable. It identifies which versions
touched outcomes, so full archived versions are fetched only where they matter —
the difference between a ~600,000-request crawl and a ~5,000,000-request one.

This is the entire justification for the project. The record of what a trial
promised to measure, and when that promise changed, is public, complete, and as
far as this check can establish, unexamined at registry scale.

### 1.1 The internal endpoints refuse most HTTP clients

Measured on one machine, in one minute, with identical headers. The documented
v2 endpoint is included as a control ([`data/pilot/runner_probe.txt`](data/pilot/runner_probe.txt)):

| Endpoint | `urllib` | `requests` | `curl` |
|---|---|---|---|
| `/api/v2/studies/{NCT}` (documented) | **200** | **200** | **200** |
| `/api/int/studies/{NCT}?history=true` | **403** | **403** | **200** |
| `/api/int/studies/{NCT}/history/{v}` | **403** | **403** | **200** |

**The control is what makes this conclusive.** Every client reaches the
documented endpoint from the same process, so the refusals are not DNS, not the
network, not a blocked address, and not the project's code. Only the archive
endpoints discriminate, and only against the Python clients.

A browser `User-Agent`, an `Accept` header, a `Referer` from the study page, a
warmed cookie jar and `Accept-Encoding` were each tried and each refused. What
separates curl from the two Python clients is the TLS handshake, so the gate is
a **client fingerprint, not an authorization check** — there is nothing to
authenticate to, and any browser visiting the page receives the same bytes.

**It is not the TLS library, and the first draft of this section said it was.**
See §7.1: on a Linux CI runner, Python's `ssl` reports OpenSSL 3.0.13 and curl
links OpenSSL/3.0.13 — the same library, the same version, the same machine —
and curl is served while `urllib` is refused. The discriminator is the handshake
profile the client presents, not the library underneath it.

The collector therefore shells out to curl ([`scripts/fetch.py`](scripts/fetch.py)).
That is a finding, not a shortcut, and it carries a risk this check cannot close
— see §7.1.

*Method note: the first probe of `/history/{v}` returned 403 and was briefly
recorded as "blocked". It was not. The probe used `NCT00000102`, a 2005 trial
with exactly one version, so index 1 was out of range. The endpoint returns 403
rather than 404 for an out-of-range version. A one-trial probe of a
variable-length resource is not a probe.*

---

## 2. The frame

| Filter | Count |
|---|---|
| All studies | 600,762 |
| Interventional, primary completion 2015–2022, `COMPLETED\|TERMINATED` | **126,760** |

The window closes in 2022 so that every trial in it is more than three years
past the 12-month results deadline. An absent result is then **settled, not
pending** — which is the difference between measuring non-reporting and
measuring slowness.

---

## 3. The version history exists and is deep

Sample of **400 trials**, drawn as every 25th record across 10,000 scanned from
the frame. Zero fetch failures.

| | Measured |
|---|---|
| Trials with more than one submitted version | **358 / 400 = 89.5%** |
| Median versions per trial | **5** |
| Maximum versions seen | **297** |
| Primary outcome changed after registration | **161 / 400 = 40.2%** |
| Primary completion date given to month precision only | 99 / 400 = 24.8% |

**This 400-trial sample is not random.** It is a systematic stride through the
API's own ordering, which is opaque. The numbers carry no confidence intervals
because they do not deserve any. They establish that the phenomenon is large
enough to be worth measuring properly, and nothing else.

---

## 4. The design that was wrong

The pitch proposed reading `lastUpdateVersions.primaryOutcomes`, comparing its
date against primary completion, and reporting the share of trials whose primary
outcome changed after the sponsor could see the data.

Done that way, on this sample:

> **122 of 400 trials — 30.5% — changed their primary outcome after primary
> completion.**

That number is wrong, and it is wrong in the direction that flatters the
project.

### 4.1 The counter-example, found by hand

`NCT02895035` is flagged as a retrospective change 386 days after completion.
Fetching the two versions and reading them:

| | Primary outcome |
|---|---|
| **v4** | `the mean area under the curve change from baseline in pupil diameter over time to the end of cataract surgery`<br>timeFrame: `N/A (during cataract surgery)` |
| **v5** | `Mean Area Under the Curve Change From Baseline in Pupil Diameter Over Time to the End of Cataract Surgery`<br>timeFrame: `During cataract surgery, with maximum end time of 20 minutes` |

That is a capitalisation pass and a timeframe restatement, applied when results
were attached. It is not outcome switching. **The registry's change flag is
computed on the field, not on the meaning**, and cannot tell the two apart.

### 4.2 How big the artefact is

Every flagged change in the sample was adjudicated by fetching version *v−1* and
version *v* and comparing the primary outcome sets
([`scripts/adjudicate.py`](scripts/adjudicate.py)). 161 flagged trials, 322
version fetches, zero failures.

| Verdict | All flagged (n=161) | Retrospective only (n=122) |
|---|---|---|
| `COUNT_CHANGED` — outcomes added or removed | 29 — 18.0% | **25 — 20.5%** |
| `SUBSTANTIVE` — measure text materially differs | 62 — 38.5% | **51 — 41.8%** |
| `REWORDED` — same measure, Jaccard ≥ 0.80 | 6 — 3.7% | 3 — 2.5% |
| `TIMEFRAME_ONLY` — measure identical, timeframe differs | 25 — 15.5% | 18 — 14.8% |
| `COSMETIC` — identical after normalisation | 9 — 5.6% | 8 — 6.6% |
| `IDENTICAL` — byte-identical | 30 — 18.6% | 17 — 13.9% |
| **Defensible** (`COUNT_CHANGED` + `SUBSTANTIVE`) | **91 — 56.5%** | **76 — 62.3%** |

### The comparison that decides it

| | Rate |
|---|---|
| Naive, taking the registry's flag at face value | **30.5%** of trials |
| Adjudicated against the actual outcome text | **19.0%** of trials |
| Share of the naive signal that survives | **62.3%** |

**37.7% of the pitched headline was an artefact of how the registry records
edits.** It would not have failed loudly. It would have produced a striking,
round, defensible-sounding number and a beautiful chart.

`IDENTICAL` at 13.9% is its own finding: for one flagged trial in seven, the
primary outcome set is **byte-identical** across the change the registry
flagged. The flag fires on fields this comparison does not read — descriptions,
or the results-attached outcome module. Any project consuming
`lastUpdateVersions` as ground truth inherits that error silently.

### 4.3 What survives, and what it looks like

The phenomenon is real. **19.0% of sampled trials made a defensible change to
their primary outcome after primary completion.** The clearest cases:

| Trial | Days after completion | Change |
|---|---|---|
| `NCT02100631` | +2,228 | `Seroconversion by vibriocidal antibody (4-fold rise over baseline titer)` → `Seroconversion Rate at Day 11` (Jaccard 0.06) |
| `NCT00478361` | +1,906 | **4 primary outcomes → 1.** `Overall response rate`, `Time to progression`, and two others → `Objective Response Rate` |
| `NCT01360606` | +2,267 | **1 → 2 primary outcomes**; dose-limiting toxicities added |
| `NCT02547441` | +1,852 | **3 → 2 primary outcomes** |

### 4.4 The adjudicated number is itself still an upper bound

Two of the surviving examples do not look like switching on a careful read:

- `NCT02473276`: `Percent of participants with postdural puncture headache` →
  `Number of Participants With...` — a units restatement, scored `SUBSTANTIVE`
  at Jaccard 0.75.
- `NCT02462187`: `Clearance of Baseline External Genital and Perianal Warts` →
  `Complete Clearance ... at or Before Week 12` — added specificity, not a
  different endpoint.

A lexical comparator cannot resolve these, and it fails in the other direction
too: it cannot see that *"HbA1c at 12 weeks"* and *"glycated haemoglobin at 3
months"* are one endpoint, nor that a promoted secondary outcome is a switch.

**So 19.0% is a floor for the method and a ceiling for the claim, and the true
rate is not yet known.** That is the argument for the semantic tier specified in
`Endpoint_SRS_v1.0.md` §5.4 — and the argument for refusing to ship it without a
hand-labelled gold set and a published error rate. An LLM in the loop without a
measured error rate is an opinion generator.

---

## 5. Collection cost

Measured over 400 history fetches plus 322 version fetches, paced at 2 req/s.

| | Measured |
|---|---|
| Mean history response | **29.1 KB** |
| Mean latency | **0.80 s** |
| Refusals (any 4xx/5xx) | **0 / 722** |

| Crawl | Requests | Raw | 1 runner @ 2 req/s | 8 shards |
|---|---|---|---|---|
| Version index, full frame | 126,760 | 3.5 GB | 17.6 h | **4.4 h** |
| Archived versions for flagged trials (~40%) | ~101,000 | ~2.8 GB | 14.0 h | **3.5 h** |

**Cost: zero.** One documented API, two undocumented ones, all keyless; GitHub
Actions unlimited on public repositories. Neither crawl fits a 6-hour CI ceiling
on one runner, and both fit comfortably across eight shards — the same sharding
Halflife measured and deployed.

**Zero refusals at 2 req/s means the ceiling is unknown, not that it is high.**
The probe never provoked a limit, so no sustainable maximum has been established.
Any shard plan must measure its own rate before it runs, not inherit this one.

---

## 6. Reporting, as a second measurement

The same 400 trials, all more than three years past the 12-month deadline:

| | Measured |
|---|---|
| Results posted | **106 / 400 = 26.5%** |
| **No results posted** | **294 / 400 = 73.5%** |
| Of those posted, later than 365 days | **90 / 106 = 84.9%** |
| Median days, completion → posting | **583.5** |
| Enrolled participants in the 294 trials with no posted results | **76,384** |

That last row is the site's emotional payload and it is a **count**, not an
estimate — it cannot be an artefact of a modelling choice. It is also **not
extrapolated here.** 76,384 participants across 294 trials in a non-random
sample of 400 does not license a frame-wide figure, and the real number is only
knowable after the full crawl. Multiplying it out would be exactly the move this
document exists to prevent.

---

## 7. Open before pre-registration

### 7.1 Resolved — M1, measured on CI 30 August 2026

The question was whether a Linux CI runner reaches the archive endpoints at all.
This machine's curl links Schannel; a GitHub Actions runner links OpenSSL, and
the draft of this section predicted it might therefore be refused — which would
have invalidated the entire sharded collection plan.

Run on both runners
([`runner_probe_ci_ubuntu.txt`](data/pilot/runner_probe_ci_ubuntu.txt),
[`runner_probe_ci_windows.txt`](data/pilot/runner_probe_ci_windows.txt)):

| Runner | curl build | archive index | archive version | 20-request burst @ 2 req/s |
|---|---|---|---|---|
| `ubuntu-latest` | 8.5.0, **OpenSSL/3.0.13** | **200** | **200** | 20/20, 0 refused, 2.08 req/s |
| `windows-latest` | 8.16.0, Schannel | **200** | **200** | 20/20, 0 refused, 2.07 req/s |

**M1 passes. The collection architecture holds and the freeze is unblocked.**

**The prediction was wrong, in an instructive way.** On the Ubuntu runner
Python's `ssl` module reports **OpenSSL 3.0.13** and curl links
**OpenSSL/3.0.13** — same library, same version, same machine — and curl is
served 200 while `urllib` is refused 403. The TLS *library* is therefore not the
discriminator. What differs is the handshake profile each client presents:
cipher and extension ordering, ALPN, HTTP/2 negotiation. §1.1 is corrected
accordingly.

This is why the probe ran on both operating systems rather than only the one in
doubt. A single-OS run would have returned "ubuntu works", the plan would have
proceeded, and the stated reason for it working would have been false — which
survives undetected until the fingerprint rule changes and nobody knows which
property mattered.

*Caveat: `requests` is not installed on either runner, so the CI rows report it
`absent`. The three-client comparison in §1.1 rests on the local measurement.*

### 7.2 Carried

- **The internal endpoints are undocumented and unversioned.** They may change
  shape or disappear without notice. Mitigation: the cold store is the asset —
  once a version is archived it is held independently of the source.
- **`lastUpdateVersions` reports only the LAST primary-outcome change.** A trial
  changed retrospectively and then again prospectively is missed entirely. This
  under-reports. Fixing it means scanning all of `changes[]` for
  `Outcome Measures` labels and fetching every such version, which is specified
  but not costed.
- **24.8% of completion dates are month-precision.** Resolved to month end,
  which under-reports retrospective changes by up to 30 days.

### 7.3 To fix in pre-registration, before the crawl

1. **The kill condition** — the defensible-change rate below which the finding
   is *"outcome switching is rare and the registry is broadly honest."* Stated
   before the full crawl, not after seeing it.
2. **Whether `TIMEFRAME_ONLY` counts.** It is 14.8% of retrospective flags and
   sometimes genuinely substantive. Decided in advance, not at analysis time.
3. **The gold-set protocol** for the semantic tier, and its labeller.

---

## 8. What is not claimed

- **A retrospective change is not fraud.** Registries are edited for many
  legitimate reasons, including at a regulator's instruction. Endpoint reports
  what changed and when, never why, and never intent.
- **Non-reporting is not a legal violation.** FDAAA applicability is not exposed
  by the API and this project does not adjudicate it. "No results posted" is the
  claim; "in breach" is not.
- **19.0% is a method floor and a claim ceiling**, for the reasons in §4.4.
- **The pilot sample is not random** and nothing here is a population estimate.
- ClinicalTrials.gov only. EU CTR, ISRCTN and the WHO ICTRP would each need
  their own access check, and none was run.

---

## Reusable

The check that mattered was not whether the data existed — it plainly did, and
richly. It was **whether the field the design proposed to read meant what the
design assumed it meant.** `lastUpdateVersions.primaryOutcomes` looks like a
ground-truth flag for outcome switching. It is a change indicator on a text
field, and 37.7% of what it flags retrospectively is capitalisation, punctuation
and byte-identical records.

Fetching two versions and diffing them cost 322 requests and about eleven
minutes. Not doing it would have cost the project its central claim, discovered
by a reader rather than by its author.

**Read the field before you build on it.** That table should be the first thing
built, every time.
