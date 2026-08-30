"""M6. Turn the register into static files the web tier can read.

SRS 5.6: the frontend issues no live queries. This writes every artefact it will
read, as plain JSON, to data/serve/.

WHY data/serve/ IS NOT COMMITTED. Everything here is a pure function of the
frozen frame plus a register batch plus this script. Committing it would be
committing a cache, and a cache that can drift from its inputs without anything
noticing. It is regenerated at deploy time instead, and manifest.json records
the frame hash, the register batch and the git commit it was built from -- so a
published figure can always be traced back to the exact inputs that produced it.

WHY IT DEGRADES INSTEAD OF FAILING. The outcome-switching figures depend on M4.
This runs before M4 finishes and writes those fields as `null` with an explicit
`"pending"` status rather than omitting them or, worse, defaulting them to zero.
A frontend that reads 0 and renders "0% of trials switched outcomes" would be
publishing a false finding produced by a missing file. Every artefact therefore
carries `available: true|false` per section, and the web tier is expected to
render "not yet measured" rather than a number.

WHAT IT REFUSES. It will not materialise against a frame that does not match
frame/MANIFEST, for the same reason the collectors will not collect against one:
the figures would describe a different cohort than the one pre-registered.
"""
import argparse, calendar, csv, datetime, glob, gzip, hashlib, json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME_DIR = os.path.join(ROOT, 'frame')
MANIFEST = os.path.join(FRAME_DIR, 'MANIFEST')
STUDIES = os.path.join(FRAME_DIR, 'studies.tsv')
REGISTER = os.path.join(ROOT, 'data', 'register')
SERVE = os.path.join(ROOT, 'data', 'serve')

DEADLINE_DAYS = 365
SCHEMA = 1


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_manifest_hash(label):
    if not os.path.exists(MANIFEST):
        return None
    for line in open(MANIFEST, encoding='utf-8'):
        p = line.split()
        if len(p) >= 2 and p[0] == label:
            return p[1]
    return None


def parse_date(s):
    if not s:
        return None
    p = s.split('-')
    try:
        if len(p) == 3:
            return datetime.date(int(p[0]), int(p[1]), int(p[2]))
        if len(p) == 2:
            y, m = int(p[0]), int(p[1])
            return datetime.date(y, m, calendar.monthrange(y, m)[1])
        if len(p) == 1:
            return datetime.date(int(p[0]), 12, 31)
    except ValueError:
        return None
    return None


def git(*args):
    import subprocess
    try:
        return subprocess.run(['git'] + list(args), cwd=ROOT, capture_output=True,
                              text=True, timeout=30).stdout.strip()
    except Exception:                                           # noqa: BLE001
        return ''


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(obj, fh, separators=(',', ':'), sort_keys=True)
    return os.path.getsize(path)


def load_frame():
    with open(STUDIES, encoding='utf-8') as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def load_history(batch):
    """nct -> {versions, outcome_touching, change_version, change_date}."""
    path = os.path.join(REGISTER, batch, 'records.ndjson.gz')
    if not os.path.exists(path):
        return None
    out = {}
    with gzip.open(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            v = (r.get('luv') or {}).get('primaryOutcomes')
            d = r.get('d') or []
            out[r['p']] = {
                'n': r.get('n'),
                'ot': len(r.get('m') or []),
                'cv': v if isinstance(v, int) else None,
                'cd': d[v] if (isinstance(v, int) and 0 <= v < len(d)) else None,
            }
    return out


def load_verdicts(batch):
    """nct -> verdict record, or None when M4 has not produced any yet."""
    if not batch:
        return None
    path = os.path.join(REGISTER, batch, 'verdicts.ndjson.gz')
    if not os.path.exists(path):
        return None
    out = {}
    with gzip.open(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                out[r['p']] = r
    return out


def counter(rows, key):
    d = {}
    for r in rows:
        d[key(r) or '(none)'] = d.get(key(r) or '(none)', 0) + 1
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--history-batch', default='history-2026-08-30')
    ap.add_argument('--versions-batch', default=None,
                    help='M4 batch; omit or point at a missing batch to '
                         'materialise with outcome sections marked pending')
    ap.add_argument('--out', default=SERVE)
    args = ap.parse_args()

    # -- refuse against a drifted frame -------------------------------------
    expected, actual = read_manifest_hash('frame/studies.tsv'), sha256_file(STUDIES)
    if expected != actual:
        print('REFUSING TO MATERIALISE: frame/studies.tsv does not match frame/MANIFEST.')
        print('  manifest %s' % expected)
        print('  actual   %s' % actual)
        return 1
    print('frame verified: %s' % actual[:16])

    rows = load_frame()
    n = len(rows)
    history = load_history(args.history_batch)
    verdicts = load_verdicts(args.versions_batch)
    outcomes_available = verdicts is not None
    print('frame %d, history %s, verdicts %s'
          % (n, 'loaded' if history else 'MISSING',
             '%d loaded' % len(verdicts) if outcomes_available else 'PENDING (M4)'))

    silent = [r for r in rows if r['has_results'] == '0']
    posted = [r for r in rows if r['has_results'] == '1']

    lateness = []
    for r in posted:
        pc, rp = parse_date(r['primary_completion']), parse_date(r['results_first_post'])
        if pc and rp:
            lateness.append((rp - pc).days)
    over = [d for d in lateness if d > DEADLINE_DAYS]

    enrol = []
    missing_enrol = 0
    for r in silent:
        try:
            enrol.append(int(r['enrollment']))
        except (ValueError, KeyError, TypeError):
            missing_enrol += 1
    enrol.sort(reverse=True)
    total_enrol = sum(enrol)

    built = {
        'schema': SCHEMA,
        'built_utc': datetime.datetime.now(datetime.timezone.utc)
                              .strftime('%Y-%m-%dT%H:%M:%SZ'),
        'frame_sha256': actual,
        'frame_size': n,
        'history_batch': args.history_batch,
        'versions_batch': args.versions_batch,
        'pipeline_commit': git('rev-parse', 'HEAD'),
        'prereg_sha256': read_manifest_hash('PREREGISTRATION.md'),
    }

    artefacts = {}

    # ---- summary.json ----------------------------------------------------
    flagged = retro_flagged = 0
    if history:
        for r in rows:
            h = history.get(r['nct'])
            if not h or not isinstance(h['cv'], int) or h['cv'] < 1:
                continue
            flagged += 1
            pc, cd = parse_date(r['primary_completion']), parse_date(h['cd'])
            if pc and cd and (cd - pc).days > 0:
                retro_flagged += 1

    summary = {
        'provenance': built,
        'figure_2_non_reporting': {
            'available': True,
            'silent': len(silent), 'posted': len(posted), 'frame': n,
            'rate': round(len(silent) / float(n), 4),
            'note': 'Census. Not a count of legal violations; FDAAA '
                    'applicability is not adjudicated (PREREGISTRATION.md 10).',
        },
        'lateness': {
            'available': True,
            'datable': len(lateness), 'over_deadline': len(over),
            'over_deadline_rate': round(len(over) / float(len(lateness)), 4) if lateness else None,
            'median_days': statistics.median(lateness) if lateness else None,
            'deadline_days': DEADLINE_DAYS,
        },
        'figure_3_participants': {
            'available': True,
            'preregistered_sum': total_enrol,
            'trials_with_enrolment': len(enrol),
            'enrolment_absent': missing_enrol,
            'median_trial': statistics.median(enrol) if enrol else None,
            'top1_share': round(enrol[0] / float(total_enrol), 4) if enrol else None,
            'top10_share': round(sum(enrol[:10]) / float(total_enrol), 4) if enrol else None,
            'top100_share': round(sum(enrol[:100]) / float(total_enrol), 4) if enrol else None,
            'warning': 'The pre-registered sum is dominated by a small number of '
                       'records, one of which is implausible. It must never be '
                       'rendered without its median and concentration. See '
                       'FINDINGS.md F5.',
        },
        'figure_1_outcome_switching': ({
            'available': True,
            'adjudicated': len(verdicts),
            'defensible_retrospective': sum(
                1 for v in verdicts.values()
                if v.get('retrospective') and v.get('label') in ('COUNT_CHANGED', 'SUBSTANTIVE')),
            'rate': round(sum(
                1 for v in verdicts.values()
                if v.get('retrospective') and v.get('label') in ('COUNT_CHANGED', 'SUBSTANTIVE')
            ) / float(n), 4),
        } if outcomes_available else {
            'available': False,
            'status': 'pending',
            'blocked_on': 'M4 version crawl and adjudication',
            'note': 'Render this as "not yet measured". Do NOT render 0. The '
                    'registry FLAG rate below is not this figure: on the pilot '
                    '37.7% of the flag did not survive reading the outcome text.',
            'flagged_only': {
                'available': bool(history),
                'flagged': flagged,
                'retrospective_flagged': retro_flagged,
                'rate': round(retro_flagged / float(n), 4) if history else None,
            },
        }),
    }
    artefacts['summary.json'] = write(os.path.join(args.out, 'summary.json'), summary)

    # ---- funnel.json -----------------------------------------------------
    on_time = len(lateness) - len(over)
    funnel = {
        'provenance': built,
        'stages': [
            {'key': 'registered', 'label': 'In frame (interventional, completed 2015-2022)',
             'count': n, 'available': True},
            {'key': 'reported', 'label': 'Posted results at all',
             'count': len(posted), 'available': True},
            {'key': 'on_time', 'label': 'Posted within 365 days of completion',
             'count': on_time, 'available': True},
            {'key': 'outcome_consistent',
             'label': 'Primary outcome not substantively changed after completion',
             'count': (n - summary['figure_1_outcome_switching']['defensible_retrospective'])
                      if outcomes_available else None,
             'available': outcomes_available,
             'blocked_on': None if outcomes_available else 'M4'},
        ],
    }
    artefacts['funnel.json'] = write(os.path.join(args.out, 'funnel.json'), funnel)

    # ---- breakdowns.json -------------------------------------------------
    def rollup(key):
        out = {}
        for r in rows:
            k = (r[key] or '(none)')
            d = out.setdefault(k, {'trials': 0, 'silent': 0})
            d['trials'] += 1
            if r['has_results'] == '0':
                d['silent'] += 1
        for k, d in out.items():
            d['silent_rate'] = round(d['silent'] / float(d['trials']), 4)
        return out

    years = {}
    for r in rows:
        y = (r['primary_completion'] or '')[:4] or '(none)'
        d = years.setdefault(y, {'trials': 0, 'silent': 0})
        d['trials'] += 1
        if r['has_results'] == '0':
            d['silent'] += 1
    for d in years.values():
        d['silent_rate'] = round(d['silent'] / float(d['trials']), 4)

    breakdowns = {
        'provenance': built,
        'by_sponsor_class': rollup('sponsor_class'),
        'by_phase': rollup('phase'),
        'by_status': rollup('status'),
        'by_completion_year': years,
        'outcome_switching_breakdowns_available': outcomes_available,
    }
    artefacts['breakdowns.json'] = write(os.path.join(args.out, 'breakdowns.json'), breakdowns)

    # ---- distributions.json ----------------------------------------------
    def histogram(vals, edges):
        h = [0] * (len(edges) + 1)
        for v in vals:
            placed = False
            for i, e in enumerate(edges):
                if v <= e:
                    h[i] += 1
                    placed = True
                    break
            if not placed:
                h[-1] += 1
        return h

    late_edges = [0, 90, 182, 365, 547, 730, 1095, 1460, 1825, 2555]
    distributions = {
        'provenance': built,
        'lateness_days': {
            'available': True,
            'edges': late_edges,
            'counts': histogram(lateness, late_edges),
            'note': 'Days from primary completion to results first posted. '
                    'Negative buckets are results posted before the recorded '
                    'completion date.',
        },
        'enrolment_concentration': {
            'available': True,
            'total': total_enrol,
            'median': statistics.median(enrol) if enrol else None,
            'top_n_shares': {str(k): round(sum(enrol[:k]) / float(total_enrol), 4)
                             for k in (1, 10, 100, 1000)},
            'note': 'Why the pre-registered sum cannot be rendered alone. '
                    'See FINDINGS.md F5.',
        },
        'versions_per_trial': ({
            'available': True,
            'median': statistics.median([h['n'] for h in history.values() if h['n']]),
            'max': max(h['n'] for h in history.values() if h['n']),
        } if history else {'available': False, 'blocked_on': 'M3'}),
    }
    artefacts['distributions.json'] = write(
        os.path.join(args.out, 'distributions.json'), distributions)

    # ---- trials/<prefix>.json  (drill-through, FR-10) ---------------------
    buckets = {}
    for r in rows:
        nct = r['nct']
        h = history.get(nct) if history else None
        v = verdicts.get(nct) if verdicts else None
        rec = {
            'nct': nct,
            'status': r['status'],
            'phase': r['phase'] or None,
            'sponsor_class': r['sponsor_class'] or None,
            'pc': r['primary_completion'] or None,
            'results': r['results_first_post'] or None,
            'enrol': int(r['enrollment']) if r['enrollment'].isdigit() else None,
            'versions': h['n'] if h else None,
            'outcome_touching': h['ot'] if h else None,
            'change_version': h['cv'] if h else None,
            'change_date': h['cd'] if h else None,
            'verdict': v['label'] if v else None,
            'retrospective': v['retrospective'] if v else None,
            'days_after_pc': v['days_after_pc'] if v else None,
            'source': 'https://clinicaltrials.gov/study/%s' % nct,
        }
        buckets.setdefault(nct[3:6], []).append(rec)

    trial_bytes = 0
    for prefix, recs in buckets.items():
        recs.sort(key=lambda x: x['nct'])
        trial_bytes += write(os.path.join(args.out, 'trials', prefix + '.json'),
                             {'prefix': prefix, 'count': len(recs), 'trials': recs})
    artefacts['trials/*.json'] = trial_bytes
    write(os.path.join(args.out, 'trials', 'index.json'),
          {'provenance': built, 'scheme': 'nct[3:6]',
           'buckets': {k: len(v) for k, v in sorted(buckets.items())}})

    # ---- manifest.json (FR-9, FR-11) -------------------------------------
    def run_json(batch):
        p = os.path.join(REGISTER, batch, 'run.json') if batch else None
        if p and os.path.exists(p):
            return json.load(open(p, encoding='utf-8'))
        return None

    hist_run = run_json(args.history_batch)
    manifest = {
        'provenance': built,
        'artefacts': {k: {'bytes': v} for k, v in sorted(artefacts.items())},
        'pipeline_health': {
            'history_crawl': ({
                'complete': hist_run.get('complete'),
                'records': hist_run.get('records'),
                'missing': hist_run.get('missing_count'),
                'failures': hist_run.get('failure_count'),
                'stats': hist_run.get('stats'),
            } if hist_run else {'available': False}),
            'version_crawl': ({'available': True, 'adjudicated': len(verdicts)}
                              if outcomes_available
                              else {'available': False, 'status': 'pending'}),
        },
        'note': 'Every artefact here is a pure function of the frame, the named '
                'register batches and pipeline_commit. Nothing is hand-edited. '
                'Failure counts are published (FR-11) rather than kept in the '
                'repository, so a gap is visible to a reader of the site.',
    }
    write(os.path.join(args.out, 'manifest.json'), manifest)

    total_bytes = sum(os.path.getsize(p) for p in glob.glob(os.path.join(args.out, '**', '*.json'),
                                                            recursive=True))
    print('')
    print('MATERIALISED to %s' % os.path.relpath(args.out, ROOT))
    for k, v in sorted(artefacts.items()):
        print('  %-24s %8.1f KB' % (k, v / 1024.0))
    print('  %-24s %8.1f MB total' % ('', total_bytes / 1024.0 / 1024.0))
    print('')
    print('  figure 1 (outcome switching): %s'
          % ('AVAILABLE' if outcomes_available else 'PENDING - rendered as "not yet measured"'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
