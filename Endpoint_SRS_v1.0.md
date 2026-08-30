# Endpoint — Software Requirements Specification v1.0

**Status:** 30 August 2026. M0–M3 complete. The frame is frozen at 126,760 trials
and the full version-history crawl has landed with zero failures. M4 (version
fetches plus Tier 1 adjudication) is the next step and is what makes primary
figure 1 computable. §5.2.1 corrects a durability claim this document made before
the sizes were measured.
**Author:** Muhammad Haris Khokhar
**Companion documents:** [`FEASIBILITY.md`](FEASIBILITY.md) (what was measured
before any of this was designed), [`PREREGISTRATION.md`](PREREGISTRATION.md)
(authoritative for every analysis rule). `DECISION_MEMO.md` — the finding, for a
reader who will not open anything else — is M8 and does not exist yet, because
there is no finding yet.

Where this document and `PREREGISTRATION.md` disagree about the analysis, the
pre-registration wins. It is committed first and can only be amended by a
numbered amendment; this document can be revised freely.

---

## 1. Introduction

### 1.1 Purpose

Every interventional clinical trial declares, before it enrols anyone, the
single measurement by which it will be judged. That declaration is the entire
basis of the evidence: a trial that picks its outcome after seeing the data can
find something in almost any dataset.

ClinicalTrials.gov keeps every submitted version of every registration, dated.
Endpoint reads that history and answers, for the whole registry rather than for
a hand-checked handful:

> **Which trials changed the outcome they promised to measure after they could
> already see the answer — and what happened to the trials that promised and
> then reported nothing at all?**

The deliverable is not a rate. It is **a per-trial, source-linked record of what
changed and when**, of which the rate is a summary. Every number on the site
resolves to two archived registry versions a reader can open.

### 1.2 Scope

| In scope | Out of scope |
|---|---|
| Interventional studies registered on ClinicalTrials.gov | Observational studies, expanded access |
| Primary outcome changes, dated against primary completion | Secondary outcome churn (recorded, not reported on) |
| Results-reporting presence and lateness | Adjudicating FDAAA legal applicability (§12) |
| Trial-to-publication linkage where a PMID resolves | Systematic review of what the papers concluded |
| A static, precomputed, published site | A live-query analytics service |
| Zero-cost infrastructure | Anything requiring payment |

### 1.3 Definitions

| Term | Meaning |
|---|---|
| **NCT ID** | ClinicalTrials.gov's trial identifier, e.g. `NCT02895035` |
| **Version** | One submitted revision of a registration. Index 0 is the original |
| **Primary completion** | The date the last participant was measured for the primary outcome |
| **Retrospective change** | A primary-outcome edit dated strictly after primary completion |
| **Defensible change** | A retrospective change that survives adjudication (§5.4) as `COUNT_CHANGED` or `SUBSTANTIVE` |
| **Silent trial** | Reached an end state, no results posted, no linked publication |
| **The register** | The committed, hashed record of what Endpoint fetched and when |
| **Cold store** | Content-addressed raw documents, never mutated |

### 1.4 The one sentence

> Trials write down what they will measure before they start, the registry keeps
> every edit with a date, and nobody has ever checked the whole registry for
> edits that landed after the data was already in.

---

## 2. Problem statement

Three failures degrade the published evidence base, and all three are computable
from public data:

1. **Outcome switching.** The trial reports a different primary outcome from the
   one it registered. Detected at scale only in small hand-checked samples —
   most famously the COMPare project, which read 67 trials by hand.
2. **Non-reporting.** The trial completes and no result is ever posted. For
   applicable trials the FDA Final Rule sets a 12-month deadline; compliance is
   known to be poor and is tracked by the EBM DataLab's FDAAA TrialsTracker.
3. **Late reporting.** Results appear, years after the deadline, when nobody is
   looking.

**What has not been done, and what Endpoint does:** use the registry's own
version history to date each primary-outcome change against the trial's primary
completion date, at registry scale, and separate the changes that are real from
the ones that are an artefact of how the registry records edits.

That last clause is the whole engineering problem. See §5.4 and
[`FEASIBILITY.md`](FEASIBILITY.md) §4 — the naive version of this measurement
produces a large, clean, and substantially artefactual number.

### 2.1 Prior art, stated plainly

| Project | What it measures | What it leaves open |
|---|---|---|
| FDAAA TrialsTracker (EBM DataLab) | Results-reporting compliance | Does not read outcome text or version history |
| COMPare (2015–2016) | Outcome switching, 67 trials, by hand | Not scalable; superseded by no automated equivalent |
| AACT (CTTI) | Full relational mirror of current records | Carries no version history |

Endpoint is not a reimplementation of any of these. It uses the one public
artefact none of them consume: the per-record version archive.

---

## 3. The measurement

For each trial in the frame:

| Quantity | Source |
|---|---|
| `primary_completion` | `statusModule.primaryCompletionDateStruct` |
| `po_change_version` | `history.lastUpdateVersions.primaryOutcomes` |
| `po_change_date` | `history.changes[po_change_version].date` |
| `days_after_completion` | `po_change_date − primary_completion` |
| `verdict` | Adjudication of the outcome text across the two versions (§5.4) |
| `results_posted`, `days_late` | `statusModule.resultsFirstPostDateStruct` |
| `publication` | `referencesModule` PMIDs, then Europe PMC linkage (§4.2) |

A trial is reported as a **defensible retrospective change** only when
`days_after_completion > 0` **and** the verdict is `COUNT_CHANGED` or
`SUBSTANTIVE`. Every other flagged trial is retained in the register and shown
in the explorer under its own verdict, never silently discarded.

### 3.1 Two conventions, both chosen to under-report

- A month-precision completion date (`2019-03`, **24.8%** of the pilot sample)
  resolves to the **last** day of that month.
- A change is retrospective only if **strictly** after completion; same-day is
  prospective.

Both push the headline down. If the phenomenon survives them, it is not an
artefact of date handling.

---

## 4. Data sources

### 4.1 Primary — required

| Source | Access | Role |
|---|---|---|
| ClinicalTrials.gov API v2 `/studies` | Public, documented, keyless | Frame, current record, dates |
| ClinicalTrials.gov `/api/int/studies/{NCT}?history=true` | Public, **undocumented** | Version index: dates, changed modules, `lastUpdateVersions` |
| ClinicalTrials.gov `/api/int/studies/{NCT}/history/{v}` | Public, **undocumented** | One archived version, in full |

The two internal endpoints are the project. They are undocumented, unversioned,
and refuse some HTTP clients (§9.3). Their risk is carried explicitly in §11.2.

### 4.2 Secondary — enrichment, not load-bearing

| Source | Role |
|---|---|
| AACT (CTTI) Postgres dumps | Bulk cross-check of the frame; sponsor and MeSH rollups |
| PubMed / Europe PMC | Publication linkage where a PMID resolves |
| OpenAlex, Crossref | Funder and institution resolution |
| ROR | Sponsor organisation canonicalisation |
| NIH RePORTER | Public-funding rollup |

Nothing in §4.2 may enter a headline figure. If Europe PMC is unavailable the
site loses a column, not a claim.

---

## 5. Architecture

```
  ingest          register            warehouse           serve            web
  ------          --------            ---------           -----            ---
  frame build  →  cold store      →   normalise       →   materialise  →   static
  history      →  (content-       →   adjudicate      →   Parquet /    →   Next.js
  versions     →   addressed,     →   link            →   JSON on      →   (no live
                   hashed,            aggregate           object           queries)
                   immutable)                             storage
```

Each stage writes only forward. No stage mutates the stage before it, and the
warehouse is a pure function of the cold store plus a pinned pipeline commit —
so any published figure can be regenerated from the register alone.

### 5.1 Frame

Interventional studies with a primary completion date in a fixed window and an
end-state status. **Frozen at 126,760 trials** for 2015–2022 /
`COMPLETED|TERMINATED`. The window ends in 2022 so that every trial in it is more
than three years past the 12-month deadline: an absent result is settled, not
pending.

Resolved 30 August 2026 across 127 pages, matching the API's `totalCount`
exactly with zero duplicate rows (`PREREGISTRATION.md` §2.4). Written to
`frame/studies.tsv` (sorted by NCT ID) and `frame/frame.json`, with SHA-256 of
both plus the pre-registration recorded in `frame/MANIFEST`.

**The frame is closed and does not grow.** Changing it now requires a numbered
amendment under `PREREGISTRATION.md` §11.

### 5.2 Cold store

Every fetched document is written content-addressed by SHA-256 and never
mutated. Layout:

```
data/cold/<sha256[0:2]>/<sha256>.json.gz    documents.  NOT committed (~1.5 GB)
data/register/<batch>/manifest.ndjson.gz    one line per fetch.   committed
data/register/<batch>/records.ndjson.gz     extracted fields.     committed
data/register/<batch>/run.json              what happened.        committed
data/register/<batch>/missing.txt           what was not got.     committed
```

`manifest.ndjson.gz` lines are `{"p": nct, "u": url, "t": unix_fetched, "h": sha256, "s": status}`.
`t` is stamped **per document, not per run** — a 126,760-trial crawl spans hours
and one run-level timestamp would be a fiction.

#### 5.2.1 What is durable, corrected

The cold store gzips to **~1.5 GB** across the frame (measured: 24.6 KB mean
response on a spread sample, 42% gzip ratio). It cannot be committed, and it is
**not** regenerable from the manifest — an earlier draft of this document and of
`.gitignore` both claimed it was, and both were wrong. The manifest lets a holder
*verify* bytes; nothing *regenerates* them, and the archive endpoints are
undocumented and may disappear.

What is committed is the manifest and the extraction — about **3.4 MB** — which
carries every field §5.4 and §6 consume. **The primary figures are therefore
computable from committed data alone.** The documents are retained best-effort as
CI artefacts, which expire.

Publishing the cold store durably as GitHub release assets is **M3.1**, and until
it is done the honest claim is that Endpoint can prove what it saw and when, and
can recompute its figures, but cannot itself hand a stranger the original bytes.

**Failures are data.** Every 403, 429, timeout and parse failure is counted and
the affected NCT IDs written to `run.json`, so a gap reads as a gap rather than
as an absence. A trial the crawl missed is **excluded, never imputed**.

### 5.3 Normalisation

Each archived version parses into a typed record: primary outcomes
`(measure, timeFrame, description)`, secondary outcomes, enrolment, status,
sponsor, phase. Parse failures are recorded per document, never swallowed.

### 5.4 Adjudication — the load-bearing stage

**Tier 1, lexical (implemented, `scripts/adjudicate.py`).** Compare the primary
outcome set at version *v−1* against version *v*:

| Verdict | Rule |
|---|---|
| `COUNT_CHANGED` | The number of primary outcomes differs. Unambiguous |
| `SUBSTANTIVE` | Measure text differs, min token Jaccard < 0.80 |
| `REWORDED` | Measure text differs, Jaccard ≥ 0.80 |
| `TIMEFRAME_ONLY` | Measures normalise equal, timeframes differ |
| `COSMETIC` | Identical after normalising case, HTML entities, punctuation |
| `IDENTICAL` | Byte-identical |

Only `COUNT_CHANGED` and `SUBSTANTIVE` are reported as outcome switching.

**Tier 2, semantic (specified, not built).** Tier 1 cannot see that *"HbA1c at
12 weeks"* and *"glycated haemoglobin at 3 months"* are one endpoint, nor that a
promoted secondary outcome is a switch. Tier 2 adds embedding retrieval and, for
the ambiguous band only, an LLM adjudication.

Every Tier 2 judgement is cached keyed by
`(sha256(text_a), sha256(text_b), prompt_hash, model_id)` and stored in the
register. The pipeline stays deterministic and re-runnable, and re-running it
next year with a different model produces a *diff against the recorded
judgements* rather than a silently different result.

**Tier 2 does not ship without a gold set.** A hand-labelled sample of ≥300
version pairs, labelled before Tier 2 is run, with precision and recall against
Tier 1 and Tier 2 both published on the site. An LLM in the loop without a
measured error rate is an opinion generator, and its output would not be
admissible in any figure.

### 5.5 Linkage

NCT ID in the abstract resolves a minority of trials. The remainder needs
blocking on `(sponsor, condition, intervention, enrolment, date window)`,
embedding retrieval, and reranking. **Linkage precision is measured on a
labelled sample and propagated into every count that depends on it**, or the
count is not published.

### 5.6 Serving

The frontend issues **no live queries**. A nightly job materialises Parquet and
JSON to object storage; the web tier reads static files. This is a cost
decision and a correctness one: a static artefact is versionable and a query
result is not.

---

## 6. Functional requirements

| ID | Requirement |
|---|---|
| FR-1 | Build the frame from API v2 and freeze it with a SHA-256 manifest before any history is fetched |
| FR-2 | Fetch the version index for every trial in the frame, resumably, recording every failure |
| FR-3 | Fetch archived versions *v−1* and *v* for every trial with a flagged primary-outcome change |
| FR-4 | Write every fetched document to the cold store content-addressed, never mutating |
| FR-5 | Adjudicate each flagged change to a Tier 1 verdict, deterministically |
| FR-6 | Date each change against primary completion under the §3.1 conventions |
| FR-7 | Classify results reporting: posted / not posted, days from completion, against the 365-day deadline |
| FR-8 | Aggregate by sponsor, sponsor class, phase, therapeutic area, funder, year |
| FR-9 | Materialise all serving artefacts as static files, regenerable from the register |
| FR-10 | Expose every aggregate as a drill-through to the per-trial record and both archived versions |
| FR-11 | Publish the pipeline's own failure counts on the site, not only in the repository |

---

## 7. Frontend requirements

| ID | Requirement |
|---|---|
| UI-1 | **The reveal.** Landing sequence resolving to the count of participants enrolled in trials that reported nothing. A count, not an estimate |
| UI-2 | **The version diff.** Side-by-side primary outcome text, *v−1* vs *v*, word-level diff, pinned to a timeline marking primary completion. The signature interaction |
| UI-3 | **The attrition funnel.** Registered → completed → reported → published → outcome-consistent, across the whole frame |
| UI-4 | **Trial lifecycle swimlane**, with the overdue interval rendered explicitly |
| UI-5 | **Sponsor table**, sortable, virtualised, drill-through |
| UI-6 | Every figure is URL-addressable and shareable |
| UI-7 | Every number links to its primary source on ClinicalTrials.gov |
| UI-8 | A methods panel reachable from every figure, stating denominator, exclusions, and verdict mix |

**UI-7 and UI-8 are not polish.** They are what make a striking number checkable
rather than merely striking, and they are requirements at the same level as the
crawl.

---

## 8. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | Zero marginal cost. Free APIs, free CI, static hosting |
| NFR-2 | The full history crawl completes inside a 6-hour CI ceiling, sharded |
| NFR-3 | Request pacing ≤ 2 req/s per egress IP, exponential backoff honouring `Retry-After` |
| NFR-4 | A `User-Agent` identifying the project and linking to the repository |
| NFR-5 | Every published figure regenerable from the register by a documented command |
| NFR-6 | Byte-exact repository on every platform (`.gitattributes`) |
| NFR-7 | The crawl is resumable and idempotent within a batch |

### 8.1 Measured cost

From `FEASIBILITY.md` §5, over 400 trials with zero refusals:

| | Measured |
|---|---|
| Mean history response | 29.1 KB |
| Mean latency | 0.80 s |
| Refusals at 2 req/s | 0 / 400 |
| Projected raw download, 126,760 trials | 3.5 GB |
| Projected wall clock, 1 runner at 2 req/s | 17.6 h |
| Projected wall clock, 8 shards | 4.4 h |

Version fetches (FR-3) add ~2 requests per flagged trial, roughly 40% of the
frame — approximately 101,000 further requests, sharded the same way.

---

## 9. Interface notes

### 9.1 The version index

`GET /api/int/studies/{NCT}?history=true` → `history.changes[]` with `version`,
`date`, `status`, `moduleLabels[]`; `history.lastUpdateVersions` mapping
`primaryOutcomes` to a version index; `history.outcomesUpdateCount`.

`moduleLabels` is what makes the crawl affordable: it identifies which versions
touched outcomes, so archived versions are fetched only where they matter.

### 9.2 One archived version

`GET /api/int/studies/{NCT}/history/{v}` → `{studyVersion, study}`, the full
record as submitted at index `v`.

### 9.3 Client fingerprinting

Measured 30 August 2026, same machine, same second, same headers:

| Client | Result |
|---|---|
| `urllib.request` | **HTTP 403** |
| `requests` | **HTTP 403** |
| `curl` 8.14.1 | **HTTP 200** |

Browser User-Agent, `Accept`, `Referer`, a warmed cookie jar and
`Accept-Encoding` were each tried and each refused. The gate is a TLS client
fingerprint, not an authorization check — there is nothing to authenticate to,
and a browser visiting the page receives the same bytes.

**Consequence:** the transport is an external binary (`scripts/fetch.py` shells
to curl). Measured on CI 30 August 2026, both `ubuntu-latest` (curl/OpenSSL) and
`windows-latest` (curl/Schannel) reach both archive endpoints, 20/20 at 2 req/s
with zero refusals. **The transport holds on the deployment target.**

The library is not the discriminator. On the Ubuntu runner Python's `ssl` reports
OpenSSL 3.0.13 and curl links OpenSSL/3.0.13 — same library, same machine — and
curl is served while `urllib` is refused. What differs is the handshake profile:
cipher and extension ordering, ALPN, HTTP/2 negotiation. The dependency is
therefore on curl's specific profile continuing to be accepted, which is a
weaker guarantee than "any OpenSSL client works" and is carried in §11.2.

### 9.4 Escaping

Version documents double-escape: a slash arrives as `&#x2F;`. Normalisation
unescapes twice, deliberately.

---

## 10. What is not claimed

- **A retrospective change is not fraud.** Registries are edited for many
  legitimate reasons, including at a regulator's instruction. Endpoint reports
  *what changed and when*, never *why*, and never intent.
- **Non-reporting is not a legal violation.** FDAAA applicability is not a field
  in the API and Endpoint does not adjudicate it. The site says "no results
  posted", never "in breach".
- **Tier 1 is a floor.** It under-detects semantically equivalent rewrites in
  both directions. Its error rate is published, not assumed.
- **The pilot is not a result.** `FEASIBILITY.md`'s numbers come from a
  systematic stride through the API's own ordering — not a random sample — and
  carry no confidence intervals because they do not deserve any.
- **Downloads of a registry record are not attention.** Nothing here measures
  whether anyone read the trial.

---

## 11. Open before baselining

### 11.1 Blocking

**None. The one blocking item is closed.**

1. ~~Does a Linux CI runner reach the internal endpoint?~~ **Answered 30 August
   2026, M1.** Both runners reach both archive endpoints at 2 req/s with zero
   refusals (`FEASIBILITY.md` §7.1). NFR-2 is achievable as written.

   The probe ran on both operating systems rather than only the one in doubt,
   which is what revealed that the OpenSSL-vs-Schannel explanation was wrong
   (§9.3). A single-OS run would have returned a passing result attached to a
   false reason.

### 11.2 Carried risks

2. **The internal endpoints are undocumented and may disappear.** Mitigation:
   the cold store is the asset. Once a version is archived it is held
   independently of the source, and the register proves when it was fetched.
3. **Rate limits are unmeasured above 2 req/s.** The pilot never provoked a
   refusal, which means the ceiling is unknown, not that it is high.
4. **`lastUpdateVersions` reports only the LAST primary-outcome change.** A
   trial changed retrospectively and then again prospectively is missed. This
   under-reports, and the full `changes[]` scan that would fix it is specified
   but not costed.

### 11.3 To be fixed in pre-registration

5. The kill condition — the defensible-change rate below which the finding is
   *"outcome switching is rare and the registry is broadly honest"* — stated
   before the full crawl runs.
6. Whether `TIMEFRAME_ONLY` counts as switching. It sometimes is. Decide before
   seeing the rate, not after.
7. The Tier 2 gold-set protocol and who labels it.

---

## 12. Milestones

| ID | Deliverable | Exit criterion |
|---|---|---|
| **M0** | Feasibility | ✅ Done. `FEASIBILITY.md`, backed by committed pilot data |
| **M1** | Runner access probe | ✅ Done. Both runners served; result committed to `data/pilot/` |
| **M2** | Frame freeze | ✅ Done. 126,760 trials; `frame/MANIFEST` committed; pre-registration v1.0 FROZEN |
| **M3** | History crawl | ✅ Done 30 Aug 2026. 126,760/126,760, zero failures, zero missing, zero duplicates |
| **M3.1** | Durable cold store | Documents published as release assets. Not built |
| **M4** | Version crawl + Tier 1 | Every flagged change adjudicated deterministically |
| **M5** | Gold set + Tier 2 | ◐ Apparatus complete: 419 pairs drawn and hashed, codebook and blind labelling tool built. **0 labelled — blocked on a human labeller** (`GOLDSET_PROTOCOL.md` §0) |
| **M6** | Warehouse + materialisation | ◐ Partial. `materialise.py` writes every artefact; outcome sections materialise as `available:false` until M4 lands |
| **M7** | Web | UI-1 … UI-8 |
| **M8** | Decision memo | `DECISION_MEMO.md`, two pages, no statistics required |

M3 cannot start before M2, and M2 cannot start before M1.
