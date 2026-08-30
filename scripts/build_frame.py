"""M2. Resolve the frame defined in PREREGISTRATION.md 2.1.

The rule, fixed before this ran:

    AREA[StudyType]INTERVENTIONAL
    AND AREA[PrimaryCompletionDate]RANGE[2015-01-01,2022-12-31]
    filter.overallStatus = COMPLETED|TERMINATED

Everything the API returns for that query, on the build date, is the frame. It is
closed at freeze and does not grow.

WHY THE FROZEN STATUS IS STORED. PREREGISTRATION.md 2.1 says trials whose status
changes after the freeze stay in the frame with their frozen status recorded. A
frame that tracks the world is a frame the world can reshape after the question
has been asked, so the observed state at build time is written down and the crawl
records the state it finds separately. Where they disagree, both are visible.

WHY DUPLICATES ARE COUNTED RATHER THAN ASSUMED ABSENT. This is a cursor-paginated
walk of roughly 127 pages over a live database. A record whose sort key moves
during the walk can be returned twice or skipped entirely. Halflife hit exactly
this and caught two packages returned on two pages. So this counts distinct NCT
IDs, reports how many duplicates it saw, and reports the gap between the API's
own totalCount and what the walk actually collected. A frame whose size is a
round number the fetch is ASSUMED to have delivered is not a frame; the size is a
fact about the fetch and is recorded as one.

Output, both deterministic and byte-exact:

    frame/studies.tsv   one row per trial, sorted by NCT ID, with a header
    frame/frame.json    the rule, the counts, and how the walk went

Neither is the freeze. `freeze_frame.py` hashes these and writes frame/MANIFEST,
and that is the irreversible step.
"""
import argparse, datetime, json, os, sys, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch                                                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME = os.path.join(ROOT, 'frame')

SEARCH = 'https://clinicaltrials.gov/api/v2/studies'

# Fixed by PREREGISTRATION.md 2.1. Changing either string changes the frame and
# requires a numbered amendment, not an edit.
FILTER = ('AREA[StudyType]INTERVENTIONAL AND '
          'AREA[PrimaryCompletionDate]RANGE[2015-01-01,2022-12-31]')
STATUS = 'COMPLETED|TERMINATED'

FIELDS = ','.join([
    'protocolSection.identificationModule.nctId',
    'protocolSection.statusModule.overallStatus',
    'protocolSection.statusModule.primaryCompletionDateStruct',
    'protocolSection.statusModule.resultsFirstPostDateStruct',
    'protocolSection.designModule.phases',
    'protocolSection.designModule.enrollmentInfo',
    'protocolSection.sponsorCollaboratorsModule.leadSponsor',
    'hasResults',
])

COLUMNS = ['nct', 'status', 'primary_completion', 'pc_type', 'has_results',
           'results_first_post', 'phase', 'enrollment', 'enrollment_type',
           'sponsor_class']

PAGE_SIZE = 1000


def q(s):
    return urllib.parse.quote(s, safe='')


def row_of(study):
    ps = study.get('protocolSection', {})
    status = ps.get('statusModule', {})
    design = ps.get('designModule', {})
    spons = ps.get('sponsorCollaboratorsModule', {})
    pcd = status.get('primaryCompletionDateStruct') or {}
    rfp = status.get('resultsFirstPostDateStruct') or {}
    enrol = design.get('enrollmentInfo') or {}
    return {
        'nct': (ps.get('identificationModule') or {}).get('nctId') or '',
        'status': status.get('overallStatus') or '',
        'primary_completion': pcd.get('date') or '',
        'pc_type': pcd.get('type') or '',
        'has_results': '1' if study.get('hasResults') else '0',
        'results_first_post': rfp.get('date') or '',
        'phase': '|'.join(design.get('phases') or []),
        'enrollment': '' if enrol.get('count') is None else str(enrol.get('count')),
        'enrollment_type': enrol.get('type') or '',
        'sponsor_class': (spons.get('leadSponsor') or {}).get('class') or '',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rate', type=float, default=2.0)
    ap.add_argument('--resume-token', default=None,
                    help='nextPageToken to resume a walk that died mid-way')
    args = ap.parse_args()

    os.makedirs(FRAME, exist_ok=True)
    pacer = fetch.Pacer(args.rate)
    started = datetime.datetime.now(datetime.timezone.utc)

    print('BUILDING THE FRAME  (M2)')
    print('rule   : %s' % FILTER)
    print('status : %s' % STATUS)
    print('')

    count_url = ('%s?countTotal=true&pageSize=1&filter.advanced=%s&filter.overallStatus=%s'
                 % (SEARCH, q(FILTER), q(STATUS)))
    head, res = fetch.get_json(count_url, pacer=pacer)
    if head is None:
        print('FAILED to read totalCount: %s' % res.error)
        return 1
    declared = head.get('totalCount')
    print('API totalCount at start: %s' % '{:,}'.format(declared))
    print('')

    studies, dupes, pages, token = {}, [], 0, args.resume_token
    while True:
        url = ('%s?pageSize=%d&fields=%s&filter.advanced=%s&filter.overallStatus=%s'
               % (SEARCH, PAGE_SIZE, q(FIELDS), q(FILTER), q(STATUS)))
        if token:
            url += '&pageToken=' + q(token)
        page, res = fetch.get_json(url, pacer=pacer)
        if page is None:
            print('')
            print('WALK FAILED on page %d: %s' % (pages + 1, res.error))
            print('resume with:  --resume-token %s' % (token or '<start>'))
            return 1
        batch = page.get('studies') or []
        if not batch:
            break
        pages += 1
        for st in batch:
            row = row_of(st)
            nct = row['nct']
            if not nct:
                continue
            if nct in studies:
                dupes.append(nct)
                continue
            studies[nct] = row
        token = page.get('nextPageToken')
        print('  page %3d  collected %6d  distinct %6d' % (pages, pages * PAGE_SIZE, len(studies)))
        if not token:
            break

    n = len(studies)
    print('')
    print('WALK COMPLETE')
    print('  pages fetched          %6d' % pages)
    print('  distinct NCT IDs       %6d' % n)
    print('  duplicate rows seen    %6d' % len(dupes))
    if dupes:
        print('    %s' % ', '.join(sorted(set(dupes))[:8]))
    print('  API totalCount         %6d' % declared)
    print('  difference             %6d' % (n - declared))
    if n != declared:
        print('  NOTE: the walk and the API disagree. That is recorded, not reconciled.')
        print('        The frame is what the walk collected.')
    print('')

    # -- write, deterministically -------------------------------------------
    tsv = os.path.join(FRAME, 'studies.tsv')
    with open(tsv, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\t'.join(COLUMNS) + '\n')
        for nct in sorted(studies):
            r = studies[nct]
            fh.write('\t'.join(r[c] for c in COLUMNS) + '\n')

    with_results = sum(1 for r in studies.values() if r['has_results'] == '1')
    month_prec = sum(1 for r in studies.values() if len(r['primary_completion'].split('-')) == 2)
    by_status, by_sponsor = {}, {}
    for r in studies.values():
        by_status[r['status']] = by_status.get(r['status'], 0) + 1
        by_sponsor[r['sponsor_class']] = by_sponsor.get(r['sponsor_class'], 0) + 1

    meta = {
        'built_utc': started.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'rule': {'filter_advanced': FILTER, 'overall_status': STATUS,
                 'page_size': PAGE_SIZE, 'fields': FIELDS},
        'walk': {'pages': pages, 'distinct': n, 'duplicate_rows': len(dupes),
                 'duplicates': sorted(set(dupes)), 'api_total_count': declared,
                 'difference': n - declared},
        'composition': {
            'by_status': dict(sorted(by_status.items())),
            'by_sponsor_class': dict(sorted(by_sponsor.items())),
            'with_results_posted': with_results,
            'without_results_posted': n - with_results,
            'month_precision_completion': month_prec,
        },
        'files': {'studies': 'studies.tsv', 'columns': COLUMNS},
        'frozen': False,
    }
    with open(os.path.join(FRAME, 'frame.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)
        fh.write('\n')

    print('COMPOSITION')
    for k, v in sorted(by_status.items()):
        print('  %-24s %6d  %5.1f%%' % (k, v, 100.0 * v / n))
    print('')
    for k, v in sorted(by_sponsor.items(), key=lambda kv: -kv[1]):
        print('  %-24s %6d  %5.1f%%' % (k or '(none)', v, 100.0 * v / n))
    print('')
    print('  results posted           %6d  %5.1f%%' % (with_results, 100.0 * with_results / n))
    print('  no results posted        %6d  %5.1f%%' % (n - with_results, 100.0 * (n - with_results) / n))
    print('  month-precision PCD      %6d  %5.1f%%' % (month_prec, 100.0 * month_prec / n))
    print('')
    print('wrote frame/studies.tsv (%d rows) and frame/frame.json' % n)
    print('')
    print('THE FRAME IS NOT FROZEN. Run scripts/freeze_frame.py to freeze it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
