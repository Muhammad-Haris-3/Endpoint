"""What the history register supports, and what it does not yet.

Reads data/register/<batch>/records.ndjson.gz and joins it to the frozen frame.

WHAT THIS PRODUCES IS NOT PRIMARY FIGURE 1. PREREGISTRATION.md 5.1 reports a
retrospective change only when the outcome text at version v-1 and version v
differ substantively, and that requires fetching both versions -- M4, not run.
Everything here is the FLAGGED rate: what the registry's own change indicator
says, before anyone reads the text it points at.

On the 400-trial pilot the flagged rate was 30.5% and the adjudicated rate was
19.0%, so 37.7% of the flag was capitalisation, timeframe restatement and
byte-identical records (FEASIBILITY.md 4). There is no reason to assume the same
ratio holds over the full frame, and this script does not apply it. It reports
the flag, labels it as the flag, and sizes the work M4 needs.

Date handling follows PREREGISTRATION.md 4.1 and 4.2 exactly: month precision
resolves to the last day of the month, year precision to 31 December, and a
change is retrospective only if STRICTLY after primary completion.
"""
import argparse, calendar, datetime, gzip, json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDIES = os.path.join(ROOT, 'frame', 'studies.tsv')
REGISTER = os.path.join(ROOT, 'data', 'register')


def parse_date(s):
    """PREREGISTRATION.md 4.1. Month precision -> month end; year -> 31 Dec."""
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


def load_frame():
    frame = {}
    with open(STUDIES, encoding='utf-8') as fh:
        cols = fh.readline().rstrip('\n').split('\t')
        for line in fh:
            if not line.strip():
                continue
            r = dict(zip(cols, line.rstrip('\n').split('\t')))
            frame[r['nct']] = r
    return frame


def pct(a, b):
    return '%.1f%%' % (100.0 * a / b) if b else 'n/a'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', required=True)
    args = ap.parse_args()

    recs_path = os.path.join(REGISTER, args.batch, 'records.ndjson.gz')
    if not os.path.exists(recs_path):
        print('no records at %s' % recs_path)
        return 1

    frame = load_frame()
    print('REGISTER REPORT  %s' % args.batch)
    print('frame: %d trials' % len(frame))
    print('')

    n = 0
    versions = []
    multi_version = 0
    flagged = 0
    datable = 0
    retro = 0
    retro_days = []
    blind_spot = 0            # >1 outcome-touching version (PREREG 5.4)
    no_pc = 0
    m4_fetches = 0
    by_sponsor = {}
    by_status = {}

    with gzip.open(recs_path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            n += 1
            versions.append(r['n'])
            if r['n'] > 1:
                multi_version += 1
            if len(r.get('m') or []) > 1:
                blind_spot += 1

            v = (r.get('luv') or {}).get('primaryOutcomes')
            if not isinstance(v, int) or v < 1:
                continue
            flagged += 1
            m4_fetches += 2

            row = frame.get(r['p'])
            if not row:
                continue
            pc = parse_date(row.get('primary_completion'))
            dates = r.get('d') or []
            cd = parse_date(dates[v]) if v < len(dates) else None
            if pc is None or cd is None:
                no_pc += 1
                continue
            datable += 1
            delta = (cd - pc).days
            if delta > 0:                              # PREREG 4.2: strictly after
                retro += 1
                retro_days.append(delta)
                sc = row.get('sponsor_class') or '(none)'
                by_sponsor[sc] = by_sponsor.get(sc, 0) + 1
                st = row.get('status') or '(none)'
                by_status[st] = by_status.get(st, 0) + 1

    print('COVERAGE')
    print('  records                          %7d' % n)
    print('  trials with >1 submitted version %7d  %s' % (multi_version, pct(multi_version, n)))
    print('  median versions per trial        %7s' % statistics.median(versions))
    print('  max versions                     %7d' % max(versions))
    print('')

    print('FLAGGED PRIMARY-OUTCOME CHANGES   (the registry flag, NOT the finding)')
    print('  primary outcome flagged changed  %7d  %s of frame' % (flagged, pct(flagged, n)))
    print('  ...datable against completion    %7d' % datable)
    print('  ...flagged AFTER completion      %7d  %s of frame' % (retro, pct(retro, n)))
    print('  ...as share of datable flags     %7s' % pct(retro, datable))
    if retro_days:
        print('  median days after completion     %7s' % statistics.median(retro_days))
        print('  max days after completion        %7d' % max(retro_days))
    if no_pc:
        print('  flagged but undatable            %7d  (excluded, not imputed)' % no_pc)
    print('')

    print('  Retrospective FLAGS by lead sponsor class:')
    for k, v in sorted(by_sponsor.items(), key=lambda kv: -kv[1]):
        print('    %-14s %7d  %s of retrospective flags' % (k, v, pct(v, retro)))
    print('')

    print('THE 5.4 BLIND SPOT, now measurable')
    print('  trials with >1 outcome-touching version %7d  %s' % (blind_spot, pct(blind_spot, n)))
    print('  These may carry an earlier change the primary figure cannot see,')
    print('  because lastUpdateVersions reports only the LAST one. This biases')
    print('  the reported rate DOWNWARD and is accepted by PREREGISTRATION.md 5.4.')
    print('')

    print('WORK M4 REQUIRES')
    print('  version fetches (2 per flagged trial)  %7d' % m4_fetches)
    print('  at 2 req/s across 8 shards             %7.1f h' % (m4_fetches / 16.0 / 3600))
    print('')

    print('WHAT THIS IS NOT')
    print('  The numbers above are the registry CHANGE FLAG, not primary figure 1.')
    print('  On the pilot, 37.7% of the flag did not survive reading the outcome')
    print('  text (FEASIBILITY.md 4). That ratio is NOT applied here. The')
    print('  adjudicated rate is unknown until M4 runs.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
