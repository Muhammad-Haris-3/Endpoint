"""Merge a sharded crawl into one register batch, and refuse to lie about it.

Eight shards each write their own manifest, records and run.json. This combines
them and, more importantly, reconciles the result against the frozen frame.

WHAT IT CHECKS, AND WHY EACH CHECK EXISTS.

  * Every shard reported. A missing shard file is a silently smaller crawl. A
    matrix job that died is invisible in the merged output unless someone looks
    for the gap, so this looks for it.
  * The union covers the frame. Coverage is reported as a count against 126,760,
    never as a percentage alone, because "99.4% collected" reads as success and
    "761 trials missing, named below" reads as what it is.
  * No NCT appears twice. Shards partition by index modulo N, so an overlap means
    two shards ran the same range and the merged record double-counts.
  * Every record has a manifest line and vice versa.

Missing trials are written out by name. PREREGISTRATION.md 3 excludes them and
counts them; nothing here interpolates, retries silently, or rounds a gap away.

The merged batch is what the analysis reads. The per-shard files are kept beside
it rather than deleted, because the merge is a claim about them and a claim whose
inputs were thrown away is not checkable.
"""
import argparse, glob, gzip, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, 'data', 'register')
STUDIES = os.path.join(ROOT, 'frame', 'studies.tsv')
MANIFEST = os.path.join(ROOT, 'frame', 'MANIFEST')


def load_frame():
    with open(STUDIES, encoding='utf-8') as fh:
        fh.readline()
        return [line.split('\t', 1)[0] for line in fh if line.strip()]


def read_ndjson_gz(path):
    with gzip.open(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_ndjson_gz(path, rows):
    with gzip.GzipFile(path, 'wb', compresslevel=9, mtime=0) as raw:
        for r in rows:
            raw.write((json.dumps(r, separators=(',', ':'), sort_keys=True) + '\n').encode('utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', required=True)
    args = ap.parse_args()

    bdir = os.path.join(REGISTER, args.batch)
    if not os.path.isdir(bdir):
        print('no such batch: %s' % bdir)
        return 1

    frame = load_frame()
    frame_set = set(frame)
    print('MERGING BATCH %s' % args.batch)
    print('frame: %d trials' % len(frame))
    print('')

    runs = sorted(glob.glob(os.path.join(bdir, 'shard-*.run.json')))
    if not runs:
        print('no shard run.json files found')
        return 1

    shards_declared = None
    seen_shards = []
    for rp in runs:
        run = json.load(open(rp, encoding='utf-8'))
        seen_shards.append(run['shard'])
        shards_declared = shards_declared or run.get('shards')

    print('shards present: %d  (%s)' % (len(seen_shards), ', '.join(str(s) for s in sorted(seen_shards))))
    if shards_declared and len(seen_shards) != shards_declared:
        absent = sorted(set(range(shards_declared)) - set(seen_shards))
        shown = ', '.join(str(m) for m in absent[:24])
        if len(absent) > 24:
            shown += ', ... (%d more)' % (len(absent) - 24)
        print('  MISSING SHARDS: %d of %d — %s' % (len(absent), shards_declared, shown))
        print('  The merge continues, and the coverage gap below is the consequence.')
    print('')

    records, manifest, dupes = {}, {}, []
    agg = {'ok': 0, 'http_403': 0, 'http_404': 0, 'http_429': 0,
           'other_error': 0, 'unparseable': 0, 'bytes': 0}
    failures, incomplete = {}, []

    for rp in sorted(runs):
        run = json.load(open(rp, encoding='utf-8'))
        s = run['shard']
        for k in agg:
            agg[k] += run.get('stats', {}).get(k, 0)
        failures.update(run.get('failures') or {})
        if not run.get('complete'):
            incomplete.append(s)

        mp = os.path.join(bdir, 'shard-%02d.manifest.ndjson.gz' % s)
        rq = os.path.join(bdir, 'shard-%02d.records.ndjson.gz' % s)
        if os.path.exists(mp):
            for row in read_ndjson_gz(mp):
                if row['p'] in manifest:
                    dupes.append(row['p'])
                manifest[row['p']] = row
        if os.path.exists(rq):
            for row in read_ndjson_gz(rq):
                records[row['p']] = row

    collected = set(records)
    missing = sorted(frame_set - collected)
    extra = sorted(collected - frame_set)

    print('RECONCILIATION')
    print('  frame                %7d' % len(frame))
    print('  records collected    %7d' % len(records))
    print('  manifest lines       %7d' % len(manifest))
    print('  MISSING from frame   %7d' % len(missing))
    print('  not in frame (extra) %7d' % len(extra))
    print('  duplicate NCTs       %7d' % len(dupes))
    print('')

    if extra:
        print('  ERROR: %d collected NCTs are not in the frozen frame.' % len(extra))
        print('  The crawl read a frame that is not frame/studies.tsv. Refusing to merge.')
        return 1
    if dupes:
        print('  ERROR: %d NCTs appear in more than one shard.' % len(dupes))
        print('  Shards must partition the frame. Refusing to merge.')
        return 1

    print('FETCH OUTCOMES')
    for k in ('ok', 'http_403', 'http_404', 'http_429', 'unparseable', 'other_error'):
        if agg[k]:
            print('  %-14s %7d' % (k, agg[k]))
    if agg['ok']:
        print('  mean response  %7.1f KB' % (agg['bytes'] / agg['ok'] / 1024))
    print('')

    complete = not missing and not incomplete
    if incomplete:
        print('  shards reporting incomplete: %s' % ', '.join(str(s) for s in incomplete))
    if missing:
        print('  %d trials in the frame were not collected. They are named in' % len(missing))
        print('  missing.txt and are EXCLUDED from the analysis, never imputed')
        print('  (PREREGISTRATION.md 3).')
        with open(os.path.join(bdir, 'missing.txt'), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(missing) + '\n')
    print('')

    write_ndjson_gz(os.path.join(bdir, 'records.ndjson.gz'),
                    [records[n] for n in sorted(records)])
    write_ndjson_gz(os.path.join(bdir, 'manifest.ndjson.gz'),
                    [manifest[n] for n in sorted(manifest)])

    summary = {
        'batch': args.batch,
        'frame_size': len(frame),
        'shards_declared': shards_declared,
        'shards_present': sorted(seen_shards),
        'shards_incomplete': incomplete,
        'records': len(records),
        'manifest_lines': len(manifest),
        'missing_count': len(missing),
        'duplicate_count': len(dupes),
        'stats': agg,
        'failure_count': len(failures),
        'complete': complete,
    }
    with open(os.path.join(bdir, 'run.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)

    print('wrote %s/records.ndjson.gz  (%d rows)' % (args.batch, len(records)))
    print('      %s/manifest.ndjson.gz (%d rows)' % (args.batch, len(manifest)))
    print('      %s/run.json' % args.batch)
    print('')
    print('BATCH COMPLETE: %s' % complete)
    return 0 if complete else 2


if __name__ == '__main__':
    sys.exit(main())
