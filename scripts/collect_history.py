"""M3. The version-index crawl. This is the thing that makes the record exist.

One request per trial against

    /api/int/studies/{NCT}?history=true

for all 126,760 trials in the frozen frame. Sharded across runners, paced,
resumable, and it records every failure.

WHAT IS COMMITTED AND WHAT IS NOT, AND WHY IT IS NOT WHAT THE FIRST DRAFT SAID.

Measured: one history document is 29.1 KB raw and gzips to about 42% of that, so
the full cold store is ~1.5 GB compressed. That does not go in git, and no amount
of wanting it to changes that.

So the record splits in two:

  data/cold/<ab>/<sha256>.json.gz     the documents. NOT committed. A cache.
  data/register/<batch>/*.manifest    url, fetch time, sha256, status. Committed.
  data/register/<batch>/*.records     the extracted fields. Committed. ~3.4 MB.

The manifest is what makes the cache checkable. Anyone holding the documents can
verify them against the committed hashes; anyone who does not can still read what
was fetched, when, and what came back. The extraction carries every field the
analysis in PREREGISTRATION.md 5 actually consumes, so the primary figures are
computable from committed data alone.

THE CLAIM THIS CORRECTS. An earlier README said "the cold store is the asset --
once a version is fetched and hashed, the evidence is held independently of the
source." Half true. The HASHES and the EXTRACTION are held independently and are
committed. The documents are retained best-effort, as CI artefacts, which expire.
Publishing them durably as release assets is M3.1 and is not done. Until it is,
the honest statement is that this project can prove WHAT it saw and WHEN, and can
recompute its figures, but cannot by itself hand a stranger the original bytes.

WHY IT VERIFIES THE FRAME BEFORE IT STARTS. The frame is frozen and hashed
(frame/MANIFEST). A collector that reads a frame file which no longer matches the
manifest is collecting a different cohort than the one pre-registered, and would
have no way to know. So the hash is checked first and a mismatch is fatal.

Failures are data. Every 403, 429, timeout and parse failure is counted and the
affected NCT IDs written to the shard's run.json, so a gap in the register reads
as a gap rather than as an absence. A trial the crawl misses is excluded, never
imputed.

Resumable: safe to kill and re-run. Already-fetched trials are read from the
shard manifest and skipped, so a run that dies at hour two does not repeat hour
one.
"""
import argparse, datetime, gzip, hashlib, io, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch                                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME_DIR = os.path.join(ROOT, 'frame')
MANIFEST = os.path.join(FRAME_DIR, 'MANIFEST')
STUDIES = os.path.join(FRAME_DIR, 'studies.tsv')
COLD = os.path.join(ROOT, 'data', 'cold')
REGISTER = os.path.join(ROOT, 'data', 'register')

HISTORY = 'https://clinicaltrials.gov/api/int/studies/%s?history=true'

PROBE_N = 20            # requests used to check the rate before committing to it
PROBE_CEILING = 0.05    # refusal share above which the shard slows down
OUTCOME_LABEL = 'Outcome Measures'


def gzip_bytes(raw):
    """Deterministic gzip. mtime=0 so the same input always yields the same file.

    .gitattributes exists because a hash a verifier cannot reproduce is not
    evidence. A gzip header carrying the wall clock would break that for every
    committed .gz in the register.
    """
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=9, mtime=0) as fh:
        fh.write(raw)
    return buf.getvalue()


def read_manifest_hash(label):
    """The SHA-256 frame/MANIFEST recorded for `label` at freeze."""
    if not os.path.exists(MANIFEST):
        return None
    for line in open(MANIFEST, encoding='utf-8'):
        parts = line.split()
        if len(parts) >= 2 and parts[0] == label:
            return parts[1]
    return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_frame():
    with open(STUDIES, encoding='utf-8') as fh:
        fh.readline()                                   # header
        return [line.split('\t', 1)[0] for line in fh if line.strip()]


def extract(nct, digest, fetched_at, doc):
    """The fields PREREGISTRATION.md 5 consumes, and nothing else.

    `m` is every version index whose moduleLabels mention Outcome Measures, not
    just the last one. PREREGISTRATION.md 5.4 accepts that the primary figure
    reads only lastUpdateVersions and therefore misses a trial changed
    retrospectively and then again prospectively. Recording every
    outcome-touching version here means the size of that blind spot is
    measurable later without re-crawling.
    """
    hist = doc.get('history') or {}
    changes = hist.get('changes') or []
    luv = hist.get('lastUpdateVersions') or {}
    return {
        'p': nct,
        't': fetched_at,
        'h': digest,
        'n': len(changes),
        'd': [c.get('date') for c in changes],
        'm': [c.get('version') for c in changes
              if OUTCOME_LABEL in (c.get('moduleLabels') or [])],
        'luv': {k: luv[k] for k in ('primaryOutcomes', 'secondaryOutcomes', 'outcomes')
                if k in luv},
        'ouc': hist.get('outcomesUpdateCount'),
    }


def rate_probe(pacer, ncts, log):
    """PREREGISTRATION.md 8: each shard measures its own rate before the crawl.

    Zero refusals over 722 pilot requests means the ceiling is unknown, not high.
    A shard that inherits someone else's number and then runs for two hours is
    guessing, so it checks, and it records what it found.
    """
    sample = ncts[:PROBE_N]
    ok = refused = 0
    started = time.time()
    for nct in sample:
        res = fetch.get(HISTORY % nct, pacer=pacer, tries=1)
        if res.ok:
            ok += 1
        else:
            refused += 1
    elapsed = time.time() - started
    share = refused / float(len(sample)) if sample else 0.0
    log('  probe: %d ok, %d refused (%.0f%%), %.2f req/s effective'
        % (ok, refused, 100 * share, len(sample) / elapsed if elapsed else 0))
    return {'attempted': len(sample), 'ok': ok, 'refused': refused,
            'refusal_share': round(share, 4),
            'effective_rate': round(len(sample) / elapsed, 3) if elapsed else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--shards', type=int, default=1)
    ap.add_argument('--rate', type=float, default=2.0, help='requests/second, this shard')
    ap.add_argument('--workers', type=int, default=4,
                    help='concurrent requests; the Pacer still caps the rate, '
                         'workers only make that cap reachable under latency')
    ap.add_argument('--batch', default=None, help='register batch name')
    ap.add_argument('--limit', type=int, default=0, help='0 = the whole shard; >0 for smoke tests')
    ap.add_argument('--no-cold', action='store_true',
                    help='skip writing documents to the cold store (manifest and records only)')
    args = ap.parse_args()

    lines = []

    def log(m):
        print(m, flush=True)
        lines.append(m)

    started = datetime.datetime.now(datetime.timezone.utc)
    batch = args.batch or 'history-%s' % started.strftime('%Y-%m-%d')

    log('HISTORY CRAWL  (M3)   shard %d of %d' % (args.shard, args.shards))
    log('batch: %s' % batch)

    # -- refuse to run against an unfrozen or altered frame ------------------
    if not os.path.exists(MANIFEST):
        log('')
        log('REFUSING TO COLLECT: frame/MANIFEST does not exist.')
        log('The frame is not frozen. Run scripts/freeze_frame.py first, or the')
        log('first snapshot precedes the freeze and the cohort stops being a rule')
        log('fixed in advance.')
        return 1

    expected = read_manifest_hash('frame/studies.tsv')
    actual = sha256_file(STUDIES)
    if expected != actual:
        log('')
        log('REFUSING TO COLLECT: frame/studies.tsv does not match frame/MANIFEST.')
        log('  manifest %s' % expected)
        log('  actual   %s' % actual)
        log('This collector would be crawling a different cohort than the one')
        log('pre-registered, and nothing downstream would detect it.')
        return 1
    log('frame verified against MANIFEST: %s' % actual[:16])

    all_ncts = load_frame()
    shard = [n for i, n in enumerate(all_ncts) if i % args.shards == args.shard]
    if args.limit:
        shard = shard[:args.limit]
    log('frame %d trials, this shard %d' % (len(all_ncts), len(shard)))

    # -- resume ---------------------------------------------------------------
    bdir = os.path.join(REGISTER, batch)
    os.makedirs(bdir, exist_ok=True)
    man_path = os.path.join(bdir, 'shard-%02d.manifest.ndjson.gz' % args.shard)
    rec_path = os.path.join(bdir, 'shard-%02d.records.ndjson.gz' % args.shard)
    run_path = os.path.join(bdir, 'shard-%02d.run.json' % args.shard)

    done = set()
    if os.path.exists(man_path):
        with gzip.open(man_path, 'rt', encoding='utf-8') as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)['p'])
                except Exception:                               # noqa: BLE001
                    continue
        log('resuming: %d trials already in this shard manifest' % len(done))
    todo = [n for n in shard if n not in done]
    log('to fetch: %d' % len(todo))
    log('')

    if not todo:
        log('nothing to do')
        return 0

    pacer = fetch.Pacer(args.rate)
    log('rate probe at %.2f req/s' % args.rate)
    probe = rate_probe(pacer, todo, log)
    if probe['refusal_share'] > PROBE_CEILING:
        log('  refusal share %.0f%% exceeds the %.0f%% ceiling.'
            % (100 * probe['refusal_share'], 100 * PROBE_CEILING))
        log('  ABORTING. Re-run with a lower --rate. A shard that pushes through')
        log('  refusals produces a register full of gaps it caused itself.')
        json.dump({'batch': batch, 'shard': args.shard, 'aborted': 'probe refusal share',
                   'probe': probe}, open(run_path, 'w'), indent=1)
        return 1
    log('')

    # -- crawl ----------------------------------------------------------------
    man_out = gzip.open(man_path, 'at', encoding='utf-8')
    rec_out = gzip.open(rec_path, 'at', encoding='utf-8')
    stats = {'ok': 0, 'http_403': 0, 'http_404': 0, 'http_429': 0,
             'other_error': 0, 'unparseable': 0, 'bytes': 0}
    failures = {}
    t0 = time.time()

    # One lock for both append-only streams and the counters. The Pacer already
    # governs the request rate globally, so workers exist to keep that rate
    # achievable under ~0.8 s latency, not to go faster than it: serially, a
    # 2 req/s target delivers 1.1 req/s and the crawl is latency-bound.
    lock = threading.Lock()
    progress = {'n': 0}

    def handle(nct):
        obj, res = fetch.get_json(HISTORY % nct, pacer=pacer)
        now = int(time.time())
        digest = hashlib.sha256(res.body).hexdigest() if (obj is not None and res.ok) else None

        # Cold-store write happens outside the lock: it is content-addressed, so
        # two workers producing the same digest write identical bytes.
        if digest and not args.no_cold:
            sub = os.path.join(COLD, digest[:2])
            os.makedirs(sub, exist_ok=True)
            dest = os.path.join(sub, digest + '.json.gz')
            if not os.path.exists(dest):
                tmp = dest + '.%d.tmp' % threading.get_ident()
                with open(tmp, 'wb') as fh:
                    fh.write(gzip_bytes(res.body))
                os.replace(tmp, dest)                   # atomic; last writer wins, same bytes

        with lock:
            progress['n'] += 1
            i = progress['n']
            if obj is None or 'history' not in obj:
                if res.status == 403:
                    stats['http_403'] += 1
                elif res.status == 404:
                    stats['http_404'] += 1
                elif res.status == 429:
                    stats['http_429'] += 1
                elif res.ok:
                    stats['unparseable'] += 1
                else:
                    stats['other_error'] += 1
                failures[nct] = res.error or 'no history key'
                man_out.write(json.dumps(
                    {'p': nct, 'u': HISTORY % nct, 't': now, 'h': None,
                     's': res.status, 'e': (res.error or '')[:80]},
                    separators=(',', ':')) + '\n')
            else:
                stats['ok'] += 1
                stats['bytes'] += res.bytes
                man_out.write(json.dumps(
                    {'p': nct, 'u': HISTORY % nct, 't': now, 'h': digest, 's': 200},
                    separators=(',', ':')) + '\n')
                rec_out.write(json.dumps(extract(nct, digest, now, obj),
                                         separators=(',', ':')) + '\n')
            if i % 500 == 0:
                rate = i / (time.time() - t0)
                left = (len(todo) - i) / rate / 3600 if rate else 0
                log('  %6d/%d  ok=%d fail=%d  %.2f req/s  ~%.1fh left'
                    % (i, len(todo), stats['ok'], len(failures), rate, left))
                man_out.flush()
                rec_out.flush()

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(handle, todo))
    finally:
        man_out.close()
        rec_out.close()

    elapsed = time.time() - t0
    complete = not failures

    run = {
        'batch': batch,
        'shard': args.shard,
        'shards': args.shards,
        'started_utc': started.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'elapsed_seconds': round(elapsed, 1),
        'target_rate': args.rate,
        'workers': args.workers,
        'effective_rate': round(len(todo) / elapsed, 3) if elapsed else 0.0,
        'probe': probe,
        'frame_sha256': actual,
        'shard_size': len(shard),
        'attempted': len(todo),
        'stats': stats,
        'failure_count': len(failures),
        'failures': failures,
        'complete': complete,
        'cold_store_written': not args.no_cold,
    }
    with open(run_path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(run, fh, indent=1, sort_keys=True)

    log('')
    log('SHARD %d DONE' % args.shard)
    log('  ok               %6d' % stats['ok'])
    log('  failed           %6d' % len(failures))
    for k in ('http_403', 'http_404', 'http_429', 'other_error', 'unparseable'):
        if stats[k]:
            log('    %-14s %6d' % (k, stats[k]))
    log('  elapsed          %6.2f h' % (elapsed / 3600))
    log('  effective rate   %6.2f req/s' % (len(todo) / elapsed if elapsed else 0))
    log('  mean response    %6.1f KB' % (stats['bytes'] / stats['ok'] / 1024 if stats['ok'] else 0))
    log('  complete         %s' % complete)
    if not complete:
        log('  NOTE: this shard is INCOMPLETE. The missing trials are named in')
        log('        %s and are excluded, never imputed.' % os.path.basename(run_path))
    log('')
    log('wrote %s' % os.path.relpath(man_path, ROOT))
    log('      %s' % os.path.relpath(rec_path, ROOT))
    log('      %s' % os.path.relpath(run_path, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
