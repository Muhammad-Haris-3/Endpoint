"""Feasibility pilot. Does the forensic signal this project depends on exist?

The design rests on one claim: that ClinicalTrials.gov publishes enough history
to tell whether a trial's PRIMARY OUTCOME was changed AFTER the point at which
the sponsor could see the data. If it does not, there is no project, and this
script is the cheapest way to find that out.

The signal, confirmed by hand before this was written:

    /api/int/studies/{NCT}?history=true

returns `history.changes` (one entry per submitted version, each dated and
labelled with the modules that changed) and `history.lastUpdateVersions`, a map
whose `primaryOutcomes` key is the version index at which the primary outcome
was last modified. One request per trial therefore yields the change date
without fetching every version, which is the difference between a ~600,000
request crawl and a ~5,000,000 request one.

WHAT THIS SCRIPT IS NOT. Nothing it prints is a result. It is a check on whether
a result is obtainable. The sample is a systematic stride through the API's own
ordering, which is not a random sample of anything, and the numbers below carry
no confidence intervals because they do not deserve any.

Two definitional choices, both made to under-report rather than over-report:

  * A month-precision date ("2019-03") is read as the LAST day of that month.
    A change is only called retrospective if it lands after the latest date the
    completion could have meant.
  * A change is only called retrospective if it is strictly after primary
    completion. Same-day changes are counted as prospective.

Both push the headline number down. If the phenomenon still shows up, it is not
an artefact of date handling.
"""
import argparse, calendar, datetime, json, os, sys, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch                                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'pilot')

SEARCH = 'https://clinicaltrials.gov/api/v2/studies'
HISTORY = 'https://clinicaltrials.gov/api/int/studies/%s?history=true'

FIELDS = ','.join([
    'protocolSection.identificationModule.nctId',
    'protocolSection.statusModule',
    'protocolSection.designModule',
    'protocolSection.sponsorCollaboratorsModule',
    'hasResults',
])

# Interventional, primary completion 2015-2022, reached an end state. The window
# closes in 2022 so that even the latest trial in it is more than three years
# past the 12-month results deadline: an absent result is settled, not pending.
FILTER = ('AREA[StudyType]INTERVENTIONAL AND '
          'AREA[PrimaryCompletionDate]RANGE[2015-01-01,2022-12-31]')
STATUS = 'COMPLETED|TERMINATED'

REPORTING_DEADLINE_DAYS = 365


def q(s):
    return urllib.parse.quote(s, safe='')


def parse_date(s):
    """'2019-03-14' or '2019-03' -> date. Month precision resolves to month end.

    Resolving to the end of the month is the conservative direction: it makes a
    later change less likely to be called retrospective, never more.
    """
    if not s:
        return None
    parts = s.split('-')
    try:
        if len(parts) == 3:
            return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
        if len(parts) == 2:
            y, m = int(parts[0]), int(parts[1])
            return datetime.date(y, m, calendar.monthrange(y, m)[1])
        if len(parts) == 1:
            return datetime.date(int(parts[0]), 12, 31)
    except ValueError:
        return None
    return None


def sample(n, stride, pacer, log):
    """Systematic stride through the API's ordering. Not a random sample.

    Every `stride`-th record is kept, so the draw spans ~n*stride records of the
    frame rather than the first n. The API's ordering is opaque and its pages are
    cursor-linked, so a true random draw would require enumerating the frame
    first; that is a collection decision, not a pilot one.
    """
    kept, seen, token = [], 0, None
    while len(kept) < n:
        url = ('%s?pageSize=1000&fields=%s&filter.advanced=%s&filter.overallStatus=%s'
               % (SEARCH, q(FIELDS), q(FILTER), q(STATUS)))
        if token:
            url += '&pageToken=' + q(token)
        page, res = fetch.get_json(url, pacer=pacer)
        if page is None:
            log('  page fetch failed: %s' % res.error)
            break
        studies = page.get('studies', [])
        if not studies:
            break
        for st in studies:
            if seen % stride == 0 and len(kept) < n:
                kept.append(st)
            seen += 1
        token = page.get('nextPageToken')
        log('  scanned %d, kept %d' % (seen, len(kept)))
        if not token:
            break
    return kept, seen


def row_for(study, hist):
    """One trial reduced to the fields the feasibility question needs."""
    ps = study.get('protocolSection', {})
    ident = ps.get('identificationModule', {})
    status = ps.get('statusModule', {})
    design = ps.get('designModule', {})
    spons = ps.get('sponsorCollaboratorsModule', {})

    pc_raw = (status.get('primaryCompletionDateStruct') or {}).get('date')
    pc = parse_date(pc_raw)
    results_raw = (status.get('resultsFirstPostDateStruct') or {}).get('date')
    results = parse_date(results_raw)

    changes = hist.get('changes') or []
    by_version = {c.get('version'): c for c in changes}
    luv = hist.get('lastUpdateVersions') or {}
    po_version = luv.get('primaryOutcomes')

    po_change_date, days_after_pc = None, None
    if isinstance(po_version, int) and po_version in by_version:
        po_change_date = parse_date(by_version[po_version].get('date'))
        if po_change_date and pc:
            days_after_pc = (po_change_date - pc).days

    # How many submitted versions touched the outcome section at all. This is a
    # cross-check on lastUpdateVersions, which reports only the LAST such change.
    outcome_versions = [c.get('version') for c in changes
                        if 'Outcome Measures' in (c.get('moduleLabels') or [])]

    days_to_results = (results - pc).days if (results and pc) else None
    return {
        'nct': ident.get('nctId'),
        'status': status.get('overallStatus'),
        'phase': ','.join(design.get('phases') or []) or None,
        'enrollment': (design.get('enrollmentInfo') or {}).get('count'),
        'sponsor_class': (spons.get('leadSponsor') or {}).get('class'),
        'pc_date': pc_raw,
        'pc_precision': len((pc_raw or '').split('-')),
        'versions': len(changes),
        'outcomes_update_count': hist.get('outcomesUpdateCount'),
        'po_last_change_version': po_version,
        'po_last_change_date': po_change_date.isoformat() if po_change_date else None,
        'po_days_after_pc': days_after_pc,
        'outcome_touching_versions': len(outcome_versions),
        'has_results': bool(study.get('hasResults')),
        'results_post_date': results_raw,
        'days_pc_to_results': days_to_results,
    }


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def pct(a, b):
    return '%.1f%%' % (100.0 * a / b) if b else 'n/a'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=400, help='trials to sample')
    ap.add_argument('--stride', type=int, default=25, help='keep every Nth record')
    ap.add_argument('--rate', type=float, default=2.0, help='requests/second')
    ap.add_argument('--out', default=os.path.join(OUT, 'history_pilot'))
    args = ap.parse_args()

    lines = []

    def log(msg):
        print(msg, flush=True)
        lines.append(msg)

    os.makedirs(OUT, exist_ok=True)
    pacer = fetch.Pacer(args.rate)

    log('ENDPOINT FEASIBILITY PILOT')
    log('sampled %s' % datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%MZ'))
    log('frame filter: %s / %s' % (FILTER, STATUS))
    log('')

    # -- frame size ---------------------------------------------------------
    count_url = ('%s?countTotal=true&pageSize=1&filter.advanced=%s&filter.overallStatus=%s'
                 % (SEARCH, q(FILTER), q(STATUS)))
    head, _ = fetch.get_json(count_url, pacer=pacer)
    frame_total = head.get('totalCount') if head else None
    log('frame size (API totalCount): %s' % (('{:,}'.format(frame_total)) if frame_total else 'unknown'))
    log('')

    log('drawing sample (every %dth record, target %d)' % (args.stride, args.n))
    studies, scanned = sample(args.n, args.stride, pacer, log)
    log('sample: %d trials drawn from %d scanned' % (len(studies), scanned))
    log('')

    # -- history crawl ------------------------------------------------------
    log('fetching version history, one request per trial')
    rows, failures, total_bytes, total_seconds = [], {}, 0, 0.0
    for i, st in enumerate(studies, 1):
        nct = st['protocolSection']['identificationModule']['nctId']
        obj, res = fetch.get_json(HISTORY % nct, pacer=pacer)
        total_bytes += res.bytes
        total_seconds += res.seconds
        if obj is None or 'history' not in obj:
            failures[nct] = res.error or 'no history key'
            continue
        rows.append(row_for(st, obj['history']))
        if i % 50 == 0:
            log('  %d/%d  (%d ok, %d failed)' % (i, len(studies), len(rows), len(failures)))

    log('  history fetched: %d ok, %d failed' % (len(rows), len(failures)))
    for nct, err in list(failures.items())[:10]:
        log('    %s %s' % (nct, err))
    log('')

    n = len(rows)
    if not n:
        log('NO ROWS. The load-bearing endpoint did not deliver. Stop here.')
        write(args.out, lines, rows)
        return 1

    # -- 1. does the history exist at all -----------------------------------
    multi = [r for r in rows if r['versions'] > 1]
    log('1. VERSION HISTORY')
    log('   trials with >1 submitted version   %5d / %d   %s' % (len(multi), n, pct(len(multi), n)))
    log('   median versions per trial          %5s' % median([r['versions'] for r in rows]))
    log('   max versions seen                  %5d' % max(r['versions'] for r in rows))
    log('')

    # -- 2. the forensic signal ---------------------------------------------
    changed = [r for r in rows if r['po_last_change_version'] not in (None, 0)]
    dated = [r for r in changed if r['po_days_after_pc'] is not None]
    retro = [r for r in dated if r['po_days_after_pc'] > 0]
    log('2. PRIMARY OUTCOME CHANGES  (the signal the project depends on)')
    log('   primary outcome changed after registration  %5d / %d   %s'
        % (len(changed), n, pct(len(changed), n)))
    log('   ...of those, datable against completion      %5d' % len(dated))
    log('   ...changed AFTER primary completion          %5d / %d   %s'
        % (len(retro), len(dated), pct(len(retro), len(dated))))
    log('   retrospective changes as share of all trials %s' % pct(len(retro), n))
    if retro:
        log('   median days after completion                %5s' % median([r['po_days_after_pc'] for r in retro]))
        log('   max days after completion                   %5d' % max(r['po_days_after_pc'] for r in retro))
    log('')

    # -- 3. reporting ------------------------------------------------------
    with_results = [r for r in rows if r['has_results']]
    timed = [r for r in with_results if r['days_pc_to_results'] is not None]
    late = [r for r in timed if r['days_pc_to_results'] > REPORTING_DEADLINE_DAYS]
    silent = [r for r in rows if not r['has_results']]
    silent_n = sum(r['enrollment'] or 0 for r in silent)
    log('3. RESULTS REPORTING')
    log('   results posted                     %5d / %d   %s' % (len(with_results), n, pct(len(with_results), n)))
    log('   NO results posted                  %5d / %d   %s' % (len(silent), n, pct(len(silent), n)))
    log('   of those posted, later than %dd    %5d / %d   %s'
        % (REPORTING_DEADLINE_DAYS, len(late), len(timed), pct(len(late), len(timed))))
    if timed:
        log('   median days completion->posting    %5s' % median([r['days_pc_to_results'] for r in timed]))
    log('   enrolled participants in trials with no posted results: %s' % '{:,}'.format(silent_n))
    log('')

    # -- 4. crawl cost ------------------------------------------------------
    reqs = len(rows) + len(failures)
    mean_kb = (total_bytes / reqs / 1024.0) if reqs else 0
    log('4. CRAWL COST  (history endpoint, measured)')
    log('   requests issued                    %5d' % reqs)
    log('   mean response                      %5.1f KB' % mean_kb)
    log('   mean latency                       %5.2f s' % (total_seconds / reqs if reqs else 0))
    log('   refusals (any 4xx/5xx)             %5d' % len(failures))
    if frame_total:
        log('   projected for frame of %s:' % '{:,}'.format(frame_total))
        log('     raw download                     %6.1f GB' % (frame_total * mean_kb / 1024 / 1024))
        log('     wall clock at 2 req/s            %6.1f h' % (frame_total / 2.0 / 3600))
        log('     wall clock at 8 req/s (8 shards) %6.1f h' % (frame_total / 8.0 / 3600))
    log('')

    # -- 5. date precision, the caveat on section 2 -------------------------
    monthly = [r for r in rows if r['pc_precision'] == 2]
    log('5. DATE PRECISION')
    log('   primary completion given to month only  %5d / %d   %s   (read as month end)'
        % (len(monthly), n, pct(len(monthly), n)))
    log('')

    log('WORKED EXAMPLES  (largest retrospective gaps in the sample)')
    for r in sorted(retro, key=lambda r: -r['po_days_after_pc'])[:8]:
        log('   %s  completed %-10s  outcome changed %-10s  +%4dd  results=%s'
            % (r['nct'], r['pc_date'], r['po_last_change_date'], r['po_days_after_pc'],
               'yes' if r['has_results'] else 'NO'))

    write(args.out, lines, rows)
    return 0


def write(base, lines, rows):
    with open(base + '.txt', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    with open(base + '.json', 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(rows, fh, indent=1, sort_keys=True)
    print('\nwrote %s.txt and %s.json' % (base, base))


if __name__ == '__main__':
    sys.exit(main())
