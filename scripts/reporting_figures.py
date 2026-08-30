"""Primary figures 2 and 3, which need no crawl at all.

Both come from frame/studies.tsv, frozen and hashed in frame/MANIFEST. Nothing
here depends on the history or version crawls, which is why it can run while
they do.

  Figure 2  non-reporting rate: trials with no posted results, over the frame
  Figure 3  participants in silent trials: the SUM of enrollment over them

Figure 2 is sound and is reported as the headline it is.

FIGURE 3 IS NOT, AND THIS SCRIPT SAYS SO LOUDLY.

PREREGISTRATION.md 6 fixes figure 3 as a raw sum, and it is computed here exactly
that way because the rules are frozen. But the sum is 58.7 million against a
MEDIAN silent trial of 52 participants, and the distribution is why:

  * The single largest contributor is NCT05438901, "Investigation of
    Oxidant-antioxidant Status in Patients Treated With Hirudotherapy" --
    a single-group before/after study of leech therapy -- recorded as having
    enrolled 12,317,546 people, marked ACTUAL. That is not a plausible count for
    that design, and it alone is over a fifth of the figure.

  * Most of the remaining top contributors are behavioural megastudies: text
    message nudges, online health advertisements, vaccine-booking reminders.
    They are genuinely interventional and genuinely enrolled millions, but
    "enrolled in a clinical trial that never reported results" invites a reader
    to picture something other than receiving an SMS.

So the pre-registered sum is dominated by one probable data-entry error and a
handful of studies whose participants were not at the kind of risk the figure
implies. A landing page built on "58.7 million people" would be the third time
this project met the same failure: a large, clean, striking aggregate that is
substantially an artefact, pointing in the direction the project hoped to find.

WHAT THIS SCRIPT DOES ABOUT IT. It reports the pre-registered figure first,
unmodified. Then it reports the concentration -- the median, the top-N shares,
and the largest single contributor by name -- so the artefact is visible in the
same breath as the number. Then it reports robust alternatives, each labelled
NOT PRE-REGISTERED, so that an amendment under PREREGISTRATION.md 11 can be
argued from measured options rather than from a hunch.

It does not silently substitute a robust figure for the frozen one. Choosing the
estimator after seeing which one reads better is the move the pre-registration
exists to prevent.
"""
import argparse, calendar, csv, datetime, json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDIES = os.path.join(ROOT, 'frame', 'studies.tsv')
OUT_DIR = os.path.join(ROOT, 'data', 'figures')

DEADLINE_DAYS = 365          # FDA Final Rule, for trials to which it applies
TRIM_CAP = 100000            # for the sensitivity row only; not pre-registered


def parse_date(s):
    """PREREGISTRATION.md 4.1."""
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


def pct(a, b):
    return '%.1f%%' % (100.0 * a / b) if b else 'n/a'


def comma(n):
    return '{:,}'.format(int(n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(OUT_DIR, 'reporting'))
    args = ap.parse_args()

    lines = []

    def log(m=''):
        print(m, flush=True)
        lines.append(m)

    rows = []
    with open(STUDIES, encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            rows.append(r)
    n = len(rows)

    log('REPORTING FIGURES  (primary figures 2 and 3)')
    log('source: frame/studies.tsv, frozen and hashed in frame/MANIFEST')
    log('frame: %s trials' % comma(n))
    log()

    silent = [r for r in rows if r['has_results'] == '0']
    posted = [r for r in rows if r['has_results'] == '1']

    # ---- FIGURE 2 --------------------------------------------------------
    log('FIGURE 2 - NON-REPORTING RATE')
    log('   no results posted            %9s   %s of frame' % (comma(len(silent)), pct(len(silent), n)))
    log('   results posted               %9s   %s' % (comma(len(posted)), pct(len(posted), n)))
    log()
    log('   Every trial in the denominator has a primary completion date in')
    log('   2015-2022 and an end-state status, so it is more than three years')
    log('   past the 12-month deadline. An absent result is settled, not pending.')
    log()
    log('   This is NOT a count of legal violations. FDAAA applicability is not')
    log('   exposed by the API and is not adjudicated here (PREREGISTRATION.md 10).')
    log()

    # ---- LATENESS --------------------------------------------------------
    late_days = []
    for r in posted:
        pc, rp = parse_date(r['primary_completion']), parse_date(r['results_first_post'])
        if pc and rp:
            late_days.append((rp - pc).days)
    over = [d for d in late_days if d > DEADLINE_DAYS]
    log('LATENESS AMONG THE %s TRIALS THAT DID POST' % comma(len(posted)))
    log('   datable                      %9s' % comma(len(late_days)))
    log('   posted later than %d days   %9s   %s of datable'
        % (DEADLINE_DAYS, comma(len(over)), pct(len(over), len(late_days))))
    if late_days:
        log('   median days completion->post %9s' % comma(statistics.median(late_days)))
        log('   90th percentile              %9s'
            % comma(sorted(late_days)[int(0.9 * len(late_days))]))
    log()

    # ---- FIGURE 3, AS PRE-REGISTERED -------------------------------------
    enrolled, missing_enrol = [], 0
    for r in silent:
        if not r['enrollment']:
            missing_enrol += 1
            continue
        try:
            enrolled.append((int(r['enrollment']), r['nct'], r['enrollment_type'],
                             r['phase'], r['sponsor_class']))
        except ValueError:
            missing_enrol += 1
    total = sum(e[0] for e in enrolled)
    enrolled.sort(reverse=True)

    log('FIGURE 3 - PARTICIPANTS IN SILENT TRIALS  (as pre-registered: a raw sum)')
    log('   silent trials                %9s' % comma(len(silent)))
    log('   ...with an enrolment figure  %9s' % comma(len(enrolled)))
    log('   ...enrolment absent          %9s   (reported, never imputed)' % comma(missing_enrol))
    log('   >>> TOTAL ENROLLED           %9s <<<' % comma(total))
    log()

    # ---- WHY THAT SUM CANNOT BE A HEADLINE -------------------------------
    med = statistics.median(e[0] for e in enrolled)
    log('WHY THAT SUM MUST NOT BE PRESENTED ALONE')
    log('   median silent trial          %9s participants' % comma(med))
    log('   mean silent trial            %9s participants' % comma(total / len(enrolled)))
    log()
    for k in (1, 10, 100, 1000):
        share = sum(e[0] for e in enrolled[:k])
        log('   top %5d trials carry       %9s   %s of the total'
            % (k, comma(share), pct(share, total)))
    log()
    log('   Largest contributors:')
    for v, nct, t, ph, sc in enrolled[:6]:
        log('     %12s  %s  phase=%-7s %s' % (comma(v), nct, ph or '-', sc))
    log()
    log('   NCT05438901 is a single-group before/after study of hirudotherapy')
    log('   (leech therapy) recorded as ACTUAL enrolment of 12,317,546. That is')
    log('   not a plausible count for that design. It is over a fifth of the')
    log('   figure on its own, and it is almost certainly a data-entry error.')
    log()
    log('   Most other top contributors are behavioural megastudies - SMS nudges,')
    log('   online health advertisements, vaccine-booking reminders. They really')
    log('   did enrol millions, but "enrolled in a trial that never reported"')
    log('   invites a reader to picture something other than receiving a text.')
    log()

    # ---- ALTERNATIVES, EXPLICITLY NOT PRE-REGISTERED ---------------------
    log('ROBUST ALTERNATIVES - NOT PRE-REGISTERED, FOR AMENDMENT DISCUSSION ONLY')
    capped = sum(min(e[0], TRIM_CAP) for e in enrolled)
    log('   sum, each trial capped at %s      %9s   (%s of the raw sum)'
        % (comma(TRIM_CAP), comma(capped), pct(capped, total)))
    excl_na = [e for e in enrolled if e[3] != 'NA']
    log('   sum, excluding phase=NA trials      %9s   over %s trials'
        % (comma(sum(e[0] for e in excl_na)), comma(len(excl_na))))
    drop1 = total - enrolled[0][0]
    log('   sum, dropping the single largest    %9s   (%s of the raw sum)'
        % (comma(drop1), pct(drop1, total)))
    log('   median x number of silent trials    %9s' % comma(med * len(enrolled)))
    log()
    log('   None of these is the pre-registered figure and none may be reported as')
    log('   it. Substituting an estimator after seeing which reads better is the')
    log('   move PREREGISTRATION.md exists to prevent. Any change needs a numbered')
    log('   amendment under 11, argued from this table.')
    log()

    # ---- BREAKDOWNS ------------------------------------------------------
    log('NON-REPORTING BY LEAD SPONSOR CLASS')
    by_sc = {}
    for r in rows:
        sc = r['sponsor_class'] or '(none)'
        d = by_sc.setdefault(sc, [0, 0])
        d[0] += 1
        if r['has_results'] == '0':
            d[1] += 1
    log('   %-14s %9s %9s %8s' % ('class', 'trials', 'silent', 'rate'))
    for sc, (tot_, sil) in sorted(by_sc.items(), key=lambda kv: -kv[1][0]):
        log('   %-14s %9s %9s %8s' % (sc, comma(tot_), comma(sil), pct(sil, tot_)))
    log()

    log('NON-REPORTING BY PHASE')
    by_ph = {}
    for r in rows:
        ph = r['phase'] or '(none)'
        d = by_ph.setdefault(ph, [0, 0])
        d[0] += 1
        if r['has_results'] == '0':
            d[1] += 1
    for ph, (tot_, sil) in sorted(by_ph.items(), key=lambda kv: -kv[1][0])[:10]:
        log('   %-14s %9s %9s %8s' % (ph, comma(tot_), comma(sil), pct(sil, tot_)))
    log()

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(args.out + '.txt', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    summary = {
        'frame': n,
        'figure_2': {'silent': len(silent), 'posted': len(posted),
                     'rate': round(len(silent) / float(n), 4)},
        'lateness': {'datable': len(late_days), 'over_deadline': len(over),
                     'median_days': statistics.median(late_days) if late_days else None},
        'figure_3_preregistered': {
            'total_enrolled': total,
            'trials_with_enrolment': len(enrolled),
            'enrolment_absent': missing_enrol,
            'median_trial': med,
            'top1_share': round(enrolled[0][0] / float(total), 4),
            'top10_share': round(sum(e[0] for e in enrolled[:10]) / float(total), 4),
            'top100_share': round(sum(e[0] for e in enrolled[:100]) / float(total), 4),
            'largest': {'nct': enrolled[0][1], 'enrollment': enrolled[0][0]},
        },
        'not_preregistered_alternatives': {
            'capped_at_%d' % TRIM_CAP: capped,
            'excluding_phase_NA': sum(e[0] for e in excl_na),
            'dropping_largest': drop1,
            'median_times_count': med * len(enrolled),
        },
    }
    with open(args.out + '.json', 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
        fh.write('\n')
    print('wrote %s.txt and %s.json' % (args.out, args.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
