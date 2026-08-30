# Endpoint — M0 (Feasibility) Milestone Summary

Companion to [Endpoint_SRS_v1.0.md](Endpoint_SRS_v1.0.md) (Section 12) and
[FEASIBILITY.md](FEASIBILITY.md). Records what M0 delivered, how it was verified,
and decisions made along the way.

**Status: Complete** — 2026-08-30

---

## 1. Scope (per SRS Section 12)

> Feasibility. Exit criterion: `FEASIBILITY.md`, backed by committed pilot data.

Establish, by measurement rather than argument, whether the data the project
depends on exists, is reachable, is affordable, and — critically — whether the
field the design proposed to read means what the design assumed it means.

## 2. What was built

| Area | Delivered |
|---|---|
| **HTTP layer** | `scripts/fetch.py` — paced token bucket, exponential backoff honouring `Retry-After`, identifying `User-Agent`. Shells out to `curl` because the archive endpoints refuse Python clients (Section 5). Returns refusals as data rather than raising, so a 403 is recorded rather than thrown away. |
| **Feasibility pilot** | `scripts/pilot.py` — systematic stride of 400 trials across 10,000 scanned from the frame; fetches each trial's version index and measures version depth, primary-outcome change rate, results reporting, date precision and crawl cost. |
| **Adjudication probe** | `scripts/adjudicate.py` — for every flagged change, fetches versions *v−1* and *v* and classifies what actually happened to the outcome text. This is the script that caught the project's central error. |
| **Documentation** | `FEASIBILITY.md` — verdict, the load-bearing fact, the design that was wrong, crawl cost, open risks, what is not claimed. `data/pilot/` — raw output of both scripts, committed as evidence. |

## 3. Artefact change

New: `data/pilot/history_pilot.{txt,json}`, `data/pilot/adjudication.{txt,json}`.
Committed deliberately — a feasibility claim whose measurements are not in the
repository is an assertion.

## 4. How it was verified (not just "should work")

1. **The load-bearing endpoint was found by inspection, not by guessing.** The
   documented API v2 has no history route (`/api/v2/studies/{NCT}/history` → 404).
   Driving a real browser to the study page's history tab and reading its network
   requests revealed `/api/int/studies/{NCT}?history=true`. A first hand-probe of
   `/api/int/studies/{NCT}/history/{v}` returned 403 and was briefly recorded as
   "blocked" — it was not. The probe used `NCT00000102`, a 2005 trial with exactly
   one version, so index 1 was out of range and the endpoint returns 403 rather
   than 404. **A one-trial probe of a variable-length resource is not a probe**,
   and the error was corrected in `FEASIBILITY.md` §1.1.
2. **Client refusal isolated with a control.** On one machine, in one minute, with
   identical headers: the *documented* v2 endpoint returned 200 to `urllib`,
   `requests` and `curl` alike, while both *archive* endpoints returned 403 to the
   Python clients and 200 to curl. The control is what makes it conclusive — the
   refusals are not DNS, not the network, not the project's code.
3. **Header spoofing ruled out.** Browser `User-Agent`, `Accept`, `Referer` from
   the study page, a warmed cookie jar and `Accept-Encoding` were each tried and
   each refused.
4. **722 live requests, zero failures**, across both pilot scripts.
5. **The pilot's central claim was checked against the text, not assumed.** See
   Section 5.

## 5. Decisions & notes worth remembering

- **The pitched measurement was wrong, and cheaply.** Reading
  `history.lastUpdateVersions.primaryOutcomes` and dating it against primary
  completion gives **30.5%** of trials changing their primary outcome after they
  could see the data. Fetching both versions and diffing the text gives **19.0%**.
  **37.7% of the headline was an artefact** — capitalisation passes, timeframe
  restatements, and records that are *byte-identical* across the change the
  registry flagged (one flagged trial in seven). The counter-example that
  triggered the check was found by hand: `NCT02895035`, flagged 386 days after
  completion, differs only in capitalisation. Cost of catching it: 322 requests
  and about eleven minutes.
- **The registry's flag is computed on the field, not on the meaning.** Adjudication
  became a *requirement* rather than a refinement.
- **19.0% is a floor for the method and a ceiling for the claim.** A lexical
  comparator scores `Percent of participants with…` → `Number of Participants
  With…` as substantive, and cannot see that "HbA1c at 12 weeks" and "glycated
  haemoglobin at 3 months" are one endpoint. Stated as such rather than presented
  as the answer.
- **`moduleLabels` is what makes the project affordable.** Each version entry names
  which sections changed, so archived versions need only be fetched where outcomes
  moved — the difference between a ~600,000-request crawl and a ~5,000,000-request
  one.
- **The transport is an external binary, and that is a recorded risk.** Shelling to
  curl is a finding, not a shortcut, and the CI runner's curl links a different TLS
  stack. Left open as the M1 blocker rather than assumed away.
- **The pilot sample is not random** — a systematic stride through the API's own
  ordering. Reported with no confidence intervals because it does not deserve any.

## 6. Definition of Done — checked

- [x] Every number measured against the live API, not quoted
- [x] Raw pilot output committed as evidence
- [x] The design's load-bearing assumption tested, and found wrong
- [x] Crawl cost measured, not estimated (29.1 KB mean, 0.80 s latency, zero refusals at 2 req/s)
- [x] Open risks stated as blocking or carried, not omitted

## 7. Next

**M1 — Runner access probe.** The archive endpoints gate on a client fingerprint;
whether a Linux CI runner is served is unmeasured, and the whole sharded
collection architecture depends on it.

---

## Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 30 August 2026 | M0 complete; feasibility verdict "build it, but not with the headline as pitched" |
