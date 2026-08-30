"""M1. Can a CI runner reach the archive endpoints at all?

This is the single measurement blocking the frame freeze
(FEASIBILITY.md 7.1, PREREGISTRATION.md header).

WHY IT IS NOT OBVIOUS. The archive endpoints gate on a TLS client fingerprint,
not on authorization: on the development machine `urllib` and `requests` are
refused with HTTP 403 in the same second that `curl` is served HTTP 200. That
machine's curl links Schannel, because it is Windows. A GitHub Actions runner
links OpenSSL and presents a different fingerprint, so the result there is not
implied by the result here.

It matters because the whole collection architecture assumes eight sharded CI
runners. If they are refused, the crawl has to move somewhere else and the cost
model in FEASIBILITY.md 5 does not hold.

Halflife made the mirror-image assumption -- that the CI runner would be the
clean environment and the home IP the throttled one -- and measured it exactly
inverted. This probe exists so that this project does not repeat that by
assuming in the other direction.

WHAT IT REPORTS. Per client, on whatever machine it runs:

  * the documented v2 endpoint, which should always work
  * the archive index endpoint
  * the archive version endpoint
  * a short paced burst against the archive index, to see whether a refusal
    appears under sustained use rather than on the first request

Never reports a refusal as a success. Exits non-zero if the archive endpoints
are unreachable by every available client, because that is a blocking result and
a green check would hide it.
"""
import json, os, platform, ssl, subprocess, shutil, sys, time
import urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch                                                    # noqa: E402

V2 = 'https://clinicaltrials.gov/api/v2/studies/NCT02895035'
INDEX = 'https://clinicaltrials.gov/api/int/studies/NCT02895035?history=true'
VERSION = 'https://clinicaltrials.gov/api/int/studies/NCT02895035/history/4'

BURST_N = 20
BURST_RATE = 2.0

UA = 'endpoint-research/0.1 (+https://github.com/Muhammad-Haris-3/Endpoint)'


def try_urllib(url):
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30)
        return r.status, len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception as e:                                      # noqa: BLE001
        return 'ERR:' + type(e).__name__, 0


def try_requests(url):
    try:
        import requests
    except ImportError:
        return 'absent', 0
    try:
        r = requests.get(url, headers={'User-Agent': UA}, timeout=30)
        return r.status_code, len(r.content)
    except Exception as e:                                      # noqa: BLE001
        return 'ERR:' + type(e).__name__, 0


def try_curl(url):
    if not shutil.which('curl'):
        return 'absent', 0
    p = subprocess.run(
        ['curl', '-s', '-o', os.devnull, '-w', '%{http_code} %{size_download}',
         '-H', 'User-Agent: ' + UA, '--max-time', '30', url],
        capture_output=True, text=True, timeout=60)
    parts = (p.stdout or '').split()
    if len(parts) != 2:
        return 'ERR:noparse', 0
    return int(parts[0]), int(parts[1])


CLIENTS = [('urllib', try_urllib), ('requests', try_requests), ('curl', try_curl)]
TARGETS = [('v2 (documented)', V2), ('archive index', INDEX), ('archive version', VERSION)]


def main():
    lines = []

    def log(m):
        print(m, flush=True)
        lines.append(m)

    log('RUNNER ACCESS PROBE  (M1)')
    log('platform   : %s %s' % (platform.system(), platform.release()))
    log('python     : %s' % platform.python_version())
    log('openssl    : %s' % ssl.OPENSSL_VERSION)
    curl_v = 'absent'
    if shutil.which('curl'):
        out = subprocess.run(['curl', '--version'], capture_output=True, text=True)
        curl_v = (out.stdout or '').splitlines()[0] if out.stdout else 'unknown'
    log('curl       : %s' % curl_v)
    log('')

    log('%-18s %-12s %-10s %10s' % ('target', 'client', 'status', 'bytes'))
    log('-' * 54)
    reachable = {}
    for tname, url in TARGETS:
        for cname, fn in CLIENTS:
            status, n = fn(url)
            log('%-18s %-12s %-10s %10s' % (tname, cname, status, n))
            if tname != 'v2 (documented)' and status == 200:
                reachable[cname] = True
        log('-' * 54)
    log('')

    archive_ok = bool(reachable)
    log('ARCHIVE REACHABLE FROM THIS MACHINE: %s' % ('yes, via ' + ', '.join(sorted(reachable))
                                                     if archive_ok else 'NO'))
    log('')

    burst = {'attempted': 0, 'ok': 0, 'refused': 0}
    if archive_ok:
        log('SUSTAINED BURST  %d requests at %.1f req/s against the archive index'
            % (BURST_N, BURST_RATE))
        pacer = fetch.Pacer(BURST_RATE)
        started = time.time()
        for _ in range(BURST_N):
            res = fetch.get(INDEX, pacer=pacer, tries=1)
            burst['attempted'] += 1
            if res.ok:
                burst['ok'] += 1
            else:
                burst['refused'] += 1
        elapsed = time.time() - started
        log('   ok %d / %d, refused %d, %.1fs, %.2f req/s effective'
            % (burst['ok'], burst['attempted'], burst['refused'], elapsed,
               burst['attempted'] / elapsed if elapsed else 0))
        if burst['refused']:
            log('   A REFUSAL APPEARED UNDER SUSTAINED USE. The first-request')
            log('   result is not the whole answer and the shard plan must be re-costed.')
        else:
            log('   No refusal at this rate. The ceiling is UNKNOWN, not high.')
    log('')

    log('VERDICT')
    if archive_ok and not burst['refused']:
        log('   M1 PASSES on this machine. Record the platform line above beside')
        log('   the result: it is a property of the environment, not of the project.')
    elif archive_ok:
        log('   M1 PARTIAL. Reachable, but refused under sustained use.')
    else:
        log('   M1 FAILS. The archive endpoints are unreachable from this machine.')
        log('   PREREGISTRATION.md cannot be frozen and the collection architecture')
        log('   in SRS 5 must change. This is a blocking result, not a flaky test.')

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'data', 'pilot', 'runner_probe.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('\nwrote %s' % out)
    return 0 if archive_ok else 1


if __name__ == '__main__':
    sys.exit(main())
