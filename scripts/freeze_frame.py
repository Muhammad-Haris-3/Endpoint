"""The freeze. This is the irreversible step, and it refuses more than it does.

Writing frame/MANIFEST is what turns a query result into a pre-registered cohort.
After it, PREREGISTRATION.md 2.1 can only change by numbered amendment, and any
figure the project publishes cites the hashes recorded here.

So this script's job is mostly to refuse. It will not freeze if:

  * frame/MANIFEST already exists. A freeze happens once. Re-freezing after
    seeing anything is the failure mode the whole document exists to prevent,
    and an --force flag is deliberately not offered.
  * PREREGISTRATION.md still carries its DRAFT marker. The frame and the rules
    freeze together or not at all: a frozen cohort under editable rules is not a
    pre-registration, it is a cohort.
  * frame/studies.tsv disagrees with frame/frame.json about its own size, is not
    sorted by NCT ID, or contains a duplicate. A freeze that blesses a corrupt
    file is worse than no freeze, because it certifies it.
  * The git working tree has uncommitted changes to any file being hashed. The
    manifest records hashes so a stranger can verify them against the commit
    history; hashing a file that exists only on this machine records nothing
    anyone can check.

WHAT IT RECORDS. SHA-256 of the frame, the frame metadata, and the
pre-registration, plus the git commit the freeze was taken at. PREREGISTRATION.md
is hashed because the frame alone is not the pre-registration -- the admission
rules, the adjudication thresholds and the kill condition are what make a later
result checkable, and a manifest that pins the cohort but not the rules pins the
easy half.
"""
import datetime, hashlib, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME = os.path.join(ROOT, 'frame')
MANIFEST = os.path.join(FRAME, 'MANIFEST')
STUDIES = os.path.join(FRAME, 'studies.tsv')
FRAME_JSON = os.path.join(FRAME, 'frame.json')
PREREG = os.path.join(ROOT, 'PREREGISTRATION.md')

DRAFT_MARKERS = ['DRAFT — NOT FROZEN', 'DRAFT - NOT FROZEN', 'not frozen. The blocking']

HASHED = [
    ('frame/studies.tsv', STUDIES),
    ('frame/frame.json', FRAME_JSON),
    ('PREREGISTRATION.md', PREREG),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    try:
        out = subprocess.run(['git'] + list(args), cwd=ROOT,
                             capture_output=True, text=True, timeout=30)
        return (out.stdout or '').strip()
    except Exception:                                           # noqa: BLE001
        return ''


def refuse(msg, *detail):
    print('REFUSING TO FREEZE')
    print('  %s' % msg)
    for d in detail:
        print('  %s' % d)
    return 1


def main():
    print('FREEZING THE FRAME  (M2)')
    print('')

    if os.path.exists(MANIFEST):
        return refuse('frame/MANIFEST already exists. A freeze happens once.',
                      'Changing the frame now requires a numbered amendment',
                      'under PREREGISTRATION.md 11, not a re-run of this script.')

    for path in (STUDIES, FRAME_JSON, PREREG):
        if not os.path.exists(path):
            return refuse('missing %s' % os.path.relpath(path, ROOT),
                          'Run scripts/build_frame.py first.')

    # -- interlock: the rules freeze with the cohort -------------------------
    prereg_text = open(PREREG, encoding='utf-8').read()
    hit = [m for m in DRAFT_MARKERS if m in prereg_text]
    if hit:
        return refuse('PREREGISTRATION.md still carries its DRAFT marker.',
                      'found: %r' % hit[0],
                      '',
                      'The frame and the rules freeze together. Resolve the',
                      'pre-registration to v1.0 FROZEN, commit it, then re-run.')

    # -- integrity of the artefact being blessed ----------------------------
    with open(STUDIES, encoding='utf-8') as fh:
        header = fh.readline().rstrip('\n').split('\t')
        ncts = [line.split('\t', 1)[0] for line in fh if line.strip()]
    if header[0] != 'nct':
        return refuse('frame/studies.tsv header does not start with "nct"')
    if ncts != sorted(ncts):
        return refuse('frame/studies.tsv is not sorted by NCT ID',
                      'A non-deterministic frame file cannot be verified by a stranger.')
    if len(set(ncts)) != len(ncts):
        return refuse('frame/studies.tsv contains duplicate NCT IDs',
                      '%d rows, %d distinct' % (len(ncts), len(set(ncts))))

    meta = json.load(open(FRAME_JSON, encoding='utf-8'))
    declared = meta.get('walk', {}).get('distinct')
    if declared != len(ncts):
        return refuse('frame.json and studies.tsv disagree about the frame size',
                      'frame.json says %s, studies.tsv has %d rows' % (declared, len(ncts)))

    # -- the record must be checkable against a commit ----------------------
    dirty = git('status', '--porcelain', '--', 'frame/studies.tsv', 'frame/frame.json',
                'PREREGISTRATION.md')
    if dirty:
        return refuse('uncommitted changes to files being hashed:',
                      *[('    ' + line) for line in dirty.splitlines()],
                      )

    head = git('rev-parse', 'HEAD')
    if not head:
        return refuse('cannot resolve git HEAD',
                      'The manifest records the commit the freeze was taken at.')

    # -- freeze --------------------------------------------------------------
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    meta['frozen'] = True
    meta['frozen_utc'] = now
    with open(FRAME_JSON, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)
        fh.write('\n')

    digests = [(label, sha256(path), os.path.getsize(path)) for label, path in HASHED]

    lines = [
        '# Endpoint frame manifest',
        '#',
        '# The frame is closed. PREREGISTRATION.md 2.1 defines it and can now only',
        '# change by a numbered amendment under 11. Every figure Endpoint publishes',
        '# cites the hashes below.',
        '#',
        '# Verify:  sha256sum frame/studies.tsv frame/frame.json PREREGISTRATION.md',
        '# against a checkout of the commit that contains THIS file. The digests',
        '# below are the authority; git_commit_at_freeze records where HEAD stood',
        '# when the freeze ran, which is the commit before this manifest existed.',
        '',
        'frozen_utc        %s' % now,
        'git_commit_at_freeze %s' % head,
        'frame_size        %d' % len(ncts),
        'first_nct         %s' % ncts[0],
        'last_nct          %s' % ncts[-1],
        '',
    ]
    for label, digest, size in digests:
        lines.append('%-20s %s  %d bytes' % (label, digest, size))
    lines.append('')

    with open(MANIFEST, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines))

    print('FROZEN')
    print('  frame size     %d' % len(ncts))
    print('  git commit     %s' % head[:12])
    print('  frozen at      %s' % now)
    print('')
    for label, digest, size in digests:
        print('  %-20s %s' % (label, digest))
    print('')
    print('wrote frame/MANIFEST')
    print('')
    print('The frame is closed. Collection may begin.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
