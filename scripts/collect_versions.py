"""M4, part one. Fetch the two versions that bracket each flagged change.

For every trial whose history register flagged a primary-outcome change at
version v, this fetches version v-1 and version v and stores the outcome sets
from each. That pair IS the evidence for the project's central claim: this trial
promised to measure X, and on this date it began promising to measure Y.

WHY FETCHING AND ADJUDICATING ARE SEPARATE PROGRAMS. The fetch is network-bound,
slow and rate-limited; the adjudication is pure, fast and deterministic. Fusing
them would mean that any change to the rules in verdict.py -- which
PREREGISTRATION.md 5.1 permits only by numbered amendment, but permits -- costs
another 108,406 requests against a public API. Storing the outcome text once and
re-classifying it locally is the difference between a rule change costing two
hours of someone else's infrastructure and costing four seconds of ours.

So this program never classifies anything. It fetches, extracts, and stores.
adjudicate_frame.py reads what it stored.

WHAT IS STORED. Per flagged trial, the primary outcomes at both versions with
their measure, timeFrame and description, plus the secondary outcome MEASURES at
both versions. The secondaries are carried because promotion of a secondary
outcome to primary is the classic form of outcome switching, and Tier 1 cannot
see it -- but Tier 2 can, and only if the data was kept. Descriptions are carried
because a change can hide there while the measure text stays put.

The full documents go to the cold store when it is enabled, but the extraction is
what gets committed, on the same reasoning as M3: the documents are ~1.5 GB and
the evidence is a few tens of megabytes.

Resumable, sharded and paced exactly as collect_history.py. Refuses to run
against a frame that no longer matches frame/MANIFEST.
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

VERSION = 'https://clinicaltrials.gov/api/int/studies/%s/history/%d'

PROBE_N = 20
PROBE_CEILING = 0.05


def gzip_bytes(raw):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=9, mtime=0) as fh:
        fh.write(raw)
    return buf.getvalue()


def read_manifest_hash(label):
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


def flagged_from_history(batch):
    """[(nct, change_version)] for every trial the history register flagged.

    The filter is PREREGISTRATION.md 3 and 5: lastUpdateVersions.primaryOutcomes
    present and >= 1. Version 0 is the original registration, so a change AT
    version 0 is not a change.
    """
    path = os.path.join(REGISTER, batch, 'records.ndjson.gz')
    if not os.path.exists(path):
        return None
    out = []
    with gzip.open(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            v = (r.get('luv') or {}).get('primaryOutcomes')
            if isinstance(v, int) and v >= 1:
                out.append((r['p'], v))
    out.sort()
    return out


def outcomes_of(doc):
    """Primary outcomes (full) and secondary outcome measures, for one version."""
    study = doc.get('study', doc)
    om = (study.get('protocolSection') or {}).get('outcomesModule') or {}
    primary = [{'m': o.get('measure') or '',
                't': o.get('timeFrame') or '',
                'd': o.get('description') or ''}
               for o in (om.get('primaryOutcomes') or [])]
    secondary = [o.get('measure') or '' for o in (om.get('secondaryOutcomes') or [])]
    return primary, secondary


def rate_probe(pacer, pairs, log):
    sample = pairs[:PROBE_N]
    ok = refused = 0
    started = time.time()
    for nct, v in sample:
        res = fetch.get(VERSION % (nct, v), pacer=pacer, tries=1)
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
    ap.add_argument('--history-batch', default='history-2026-08-30',
                    help='the M3 register batch naming the flagged trials')
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--shards', type=int, default=1)
    ap.add_argument('--rate', type=float, default=2.0)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--batch', default=None)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--no-cold', action='store_true')
    args = ap.parse_args()

    lines = []

    def log(m):
        print(m, flush=True)
        lines.append(m)

    started = datetime.datetime.now(datetime.timezone.utc)
    batch = args.batch or 'versions-%s' % started.strftime('%Y-%m-%d')

    log('VERSION CRAWL  (M4)   shard %d of %d' % (args.shard, args.shards))
    log('batch: %s   from history batch: %s' % (batch, args.history_batch))

    if not os.path.exists(MANIFEST):
        log('')
        log('REFUSING TO COLLECT: frame/MANIFEST does not exist.')
        return 1
    expected, actual = read_manifest_hash('frame/studies.tsv'), sha256_file(STUDIES)
    if expected != actual:
        log('')
        log('REFUSING TO COLLECT: frame/studies.tsv does not match frame/MANIFEST.')
        log('  manifest %s' % expected)
        log('  actual   %s' % actual)
        return 1
    log('frame verified against MANIFEST: %s' % actual[:16])

    pairs = flagged_from_history(args.history_batch)
    if pairs is None:
        log('')
        log('REFUSING TO COLLECT: no history register at data/register/%s.'
            % args.history_batch)
        log('M4 reads the flagged list from M3. Run the history crawl first.')
        return 1
    log('flagged trials in history register: %d' % len(pairs))

    shard = [p for i, p in enumerate(pairs) if i % args.shards == args.shard]
    if args.limit:
        shard = shard[:args.limit]
    log('this shard: %d trials, %d version fetches' % (len(shard), 2 * len(shard)))

    bdir = os.path.join(REGISTER, batch)
    os.makedirs(bdir, exist_ok=True)
    man_path = os.path.join(bdir, 'shard-%02d.manifest.ndjson.gz' % args.shard)
    ver_path = os.path.join(bdir, 'shard-%02d.versions.ndjson.gz' % args.shard)
    run_path = os.path.join(bdir, 'shard-%02d.run.json' % args.shard)

    done = set()
    if os.path.exists(ver_path):
        with gzip.open(ver_path, 'rt', encoding='utf-8') as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)['p'])
                except Exception:                               # noqa: BLE001
                    continue
        log('resuming: %d trials already stored' % len(done))
    todo = [(n, v) for n, v in shard if n not in done]
    log('to fetch: %d trials (%d requests)' % (len(todo), 2 * len(todo)))
    log('')

    if not todo:
        log('nothing to do')
        return 0

    pacer = fetch.Pacer(args.rate)
    log('rate probe at %.2f req/s' % args.rate)
    probe = rate_probe(pacer, todo, log)
    if probe['refusal_share'] > PROBE_CEILING:
        log('  refusal share %.0f%% exceeds the %.0f%% ceiling. ABORTING.'
            % (100 * probe['refusal_share'], 100 * PROBE_CEILING))
        json.dump({'batch': batch, 'shard': args.shard,
                   'aborted': 'probe refusal share', 'probe': probe},
                  open(run_path, 'w'), indent=1)
        return 1
    log('')

    man_out = gzip.open(man_path, 'at', encoding='utf-8')
    ver_out = gzip.open(ver_path, 'at', encoding='utf-8')
    stats = {'ok': 0, 'partial': 0, 'failed': 0, 'requests': 0, 'bytes': 0}
    failures = {}
    lock = threading.Lock()
    progress = {'n': 0}
    t0 = time.time()

    def fetch_one(nct, v):
        obj, res = fetch.get_json(VERSION % (nct, v), pacer=pacer)
        digest = hashlib.sha256(res.body).hexdigest() if (obj is not None and res.ok) else None
        if digest and not args.no_cold:
            sub = os.path.join(COLD, digest[:2])
            os.makedirs(sub, exist_ok=True)
            dest = os.path.join(sub, digest + '.json.gz')
            if not os.path.exists(dest):
                tmp = dest + '.%d.tmp' % threading.get_ident()
                with open(tmp, 'wb') as fh:
                    fh.write(gzip_bytes(res.body))
                os.replace(tmp, dest)
        return obj, res, digest

    def handle(item):
        nct, v = item
        before_doc, rb, hb = fetch_one(nct, v - 1)
        after_doc, ra, ha = fetch_one(nct, v)
        now = int(time.time())

        with lock:
            progress['n'] += 1
            i = progress['n']
            stats['requests'] += 2
            stats['bytes'] += rb.bytes + ra.bytes
            for (vv, rr, hh) in ((v - 1, rb, hb), (v, ra, ha)):
                man_out.write(json.dumps(
                    {'p': nct, 'v': vv, 'u': VERSION % (nct, vv), 't': now,
                     'h': hh, 's': rr.status,
                     **({'e': (rr.error or '')[:80]} if not hh else {})},
                    separators=(',', ':')) + '\n')

            if before_doc is None or after_doc is None:
                # A pair with one half missing cannot be adjudicated. It is
                # recorded as a failure rather than stored half-complete, so
                # nothing downstream can mistake it for a comparison.
                stats['failed'] += 1
                failures[nct] = 'v%d:%s v%d:%s' % (
                    v - 1, rb.error or rb.status, v, ra.error or ra.status)
            else:
                bp, bs = outcomes_of(before_doc)
                ap_, as_ = outcomes_of(after_doc)
                stats['ok'] += 1
                ver_out.write(json.dumps(
                    {'p': nct, 'v': v, 't': now,
                     'hb': hb, 'ha': ha,
                     'before': bp, 'after': ap_,
                     'before_sec': bs, 'after_sec': as_},
                    separators=(',', ':')) + '\n')

            if i % 500 == 0:
                rate = (2.0 * i) / (time.time() - t0)
                left = (2.0 * (len(todo) - i)) / rate / 3600 if rate else 0
                log('  %6d/%d trials  ok=%d fail=%d  %.2f req/s  ~%.1fh left'
                    % (i, len(todo), stats['ok'], stats['failed'], rate, left))
                man_out.flush()
                ver_out.flush()

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(handle, todo))
    finally:
        man_out.close()
        ver_out.close()

    elapsed = time.time() - t0
    run = {
        'batch': batch,
        'history_batch': args.history_batch,
        'shard': args.shard,
        'shards': args.shards,
        'started_utc': started.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'elapsed_seconds': round(elapsed, 1),
        'target_rate': args.rate,
        'workers': args.workers,
        'effective_rate': round(stats['requests'] / elapsed, 3) if elapsed else 0.0,
        'probe': probe,
        'frame_sha256': actual,
        'shard_trials': len(shard),
        'attempted': len(todo),
        'stats': stats,
        'failure_count': len(failures),
        'failures': failures,
        'complete': not failures,
        'cold_store_written': not args.no_cold,
    }
    with open(run_path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(run, fh, indent=1, sort_keys=True)

    log('')
    log('SHARD %d DONE' % args.shard)
    log('  pairs stored     %6d' % stats['ok'])
    log('  pairs failed     %6d' % stats['failed'])
    log('  requests         %6d' % stats['requests'])
    log('  elapsed          %6.2f h' % (elapsed / 3600))
    log('  effective rate   %6.2f req/s' % (stats['requests'] / elapsed if elapsed else 0))
    log('  mean response    %6.1f KB'
        % (stats['bytes'] / stats['requests'] / 1024 if stats['requests'] else 0))
    log('  complete         %s' % run['complete'])
    if failures:
        log('  NOTE: %d pairs could not be completed. Named in %s and'
            % (len(failures), os.path.basename(run_path)))
        log('        EXCLUDED from adjudication, never half-compared.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
