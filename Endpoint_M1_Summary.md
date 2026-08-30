# Endpoint — M1 (Runner Access Probe) Milestone Summary

Companion to [Endpoint_SRS_v1.0.md](Endpoint_SRS_v1.0.md) (Sections 9.3, 11.1)
and [FEASIBILITY.md](FEASIBILITY.md) §7.1.

**Status: Complete** — 2026-08-30

---

## 1. Scope (per SRS Section 12)

> Runner access probe. Exit criterion: §11.1 answered on Linux CI, recorded.

The only item blocking the frame freeze. `FEASIBILITY.md` §1.1 established that
the archive endpoints refuse some HTTP clients. The development machine's `curl`
links Schannel; a GitHub Actions runner links OpenSSL. **If the runner is
refused, the entire sharded collection architecture in SRS §5 is not buildable
and NFR-2 is unachievable as written.**

## 2. What was built

| Area | Delivered |
|---|---|
| **Probe** | `scripts/runner_probe.py` — tests three HTTP clients (`urllib`, `requests`, `curl`) against three endpoints (the documented v2 record as a control, the archive index, one archived version), then runs a 20-request paced burst to see whether a refusal appears under sustained use rather than only on the first request. Records platform, Python version, OpenSSL version and curl build alongside the result, because the answer is a property of the environment rather than of the project. |
| **Workflow** | `.github/workflows/runner-probe.yml` — matrix over `ubuntu-latest` **and** `windows-latest`, `fail-fast: false`, uploads its result on `always()`. Deliberately not scheduled: this is a one-shot measurement whose result is committed and cited, and a cron would turn a recorded fact into a flapping badge. |
| **Evidence** | `data/pilot/runner_probe_local.txt`, `runner_probe_ci_ubuntu.txt`, `runner_probe_ci_windows.txt` |

## 3. Artefact change

None to the frame or register. Three probe outputs committed to `data/pilot/`.

## 4. How it was verified (not just "should work")

1. **Run on both operating systems, not only the one in doubt.** This is the
   decision the milestone turned on — see Section 5.
2. **`ubuntu-latest`** (curl 8.5.0, **OpenSSL/3.0.13**): archive index **200**,
   archived version **200**, burst **20/20 with zero refusals** at 2.08 req/s
   effective.
3. **`windows-latest`** (curl 8.16.0, Schannel): archive index **200**, archived
   version **200**, burst **20/20 with zero refusals** at 2.07 req/s effective.
4. **The documented v2 endpoint was included as a control on every run**, so a
   refusal could be distinguished from a network or DNS failure. It returned 200
   everywhere.
5. Probe exits non-zero when the archive endpoints are unreachable by every
   available client, so a blocking result cannot hide behind a green check.

**Verdict: M1 passes. The collection architecture holds and the freeze is
unblocked.**

## 5. Decisions & notes worth remembering

- **The prediction was wrong, and that is the more valuable result.**
  `FEASIBILITY.md` argued the Linux runner might be refused *because its curl
  links OpenSSL where the dev machine's links Schannel*. On the Ubuntu runner,
  Python's `ssl` module reports **OpenSSL 3.0.13** and curl links
  **OpenSSL/3.0.13** — same library, same version, same machine — and curl is
  served 200 while `urllib` is refused 403. **The TLS library is not the
  discriminator.** What differs is the handshake profile each client presents:
  cipher and extension ordering, ALPN, HTTP/2 negotiation.
- **Only visible because the matrix ran both operating systems.** A single-OS run
  would have returned "ubuntu works", the plan would have proceeded, and the
  stated reason for it working would have been false — an error that survives
  undetected until the fingerprint rule changes and nobody knows which property
  mattered. Probing the case you are *not* worried about is what turns a passing
  result into an explained one.
- **Halflife made the mirror-image mistake** — assumed the CI runner was the clean
  environment and the home IP the throttled one, and measured it exactly
  inverted. This project does not get to make that class of assumption twice.
- **Zero refusals at 2 req/s means the ceiling is unknown, not high.** The probe
  never provoked a limit, so no sustainable maximum has been established. Each
  shard measures its own rate before its crawl rather than inheriting this one.
- **`requests` is absent on both runners**, so the CI rows report it as such. The
  three-client comparison rests on the local measurement, and the CI output says
  so rather than implying a two-client result was a three-client one.

## 6. Definition of Done — checked

- [x] Answered on real Linux CI, not assumed from the local result
- [x] Answered on Windows CI as a control, which is what caught the false explanation
- [x] Result committed to `data/pilot/` and cited by `FEASIBILITY.md` §7.1
- [x] `FEASIBILITY.md` §1.1, SRS §9.3 and §11.1, README and the pre-registration header all corrected
- [x] Probe fails loudly rather than passing quietly when the archive is unreachable

## 7. Next

**M2 — Frame freeze.** Resolve the pre-registered rule to a concrete cohort,
hash it, and seal the pre-registration. Irreversible by design.

---

## Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 30 August 2026 | M1 passes on both runners; the OpenSSL-vs-Schannel explanation refuted and corrected across five documents |
