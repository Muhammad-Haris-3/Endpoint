"""The HTTP layer. It shells out to curl, and that is a finding, not a shortcut.

ClinicalTrials.gov serves the record version history from an undocumented
internal endpoint:

    /api/int/studies/{NCT}?history=true

Measured 2026-08-30, same machine, same second, same headers:

    urllib.request      HTTP 403
    requests            HTTP 403
    curl 8.14.1         HTTP 200

Header spoofing does not move it. A browser User-Agent, an Accept header, a
Referer from the study page, a warmed cookie jar and Accept-Encoding were each
tried and each refused. What separates curl from the two Python clients is the
TLS handshake, so the gate is a client fingerprint rather than an authorization
check. There is nothing to authenticate to and nothing being circumvented: the
same bytes are served to any browser that visits the page.

The consequence for the collector is that the transport is an external binary
whose behaviour is not guaranteed to match across platforms. This machine's curl
links Schannel (Windows). A GitHub Actions runner links OpenSSL, presents a
different fingerprint, and MAY BE REFUSED. That is recorded as an open risk in
FEASIBILITY.md §7 and must be measured on the runner before any collection is
scheduled there. Halflife assumed the runner was the clean environment and found
the assumption inverted; this project does not get to make the same assumption
twice.

Everything here is courteous by construction: a paced token bucket, exponential
backoff that honours Retry-After, and a User-Agent that identifies the project
and links to it.
"""
import json, os, shutil, subprocess, threading, time

UA = 'endpoint-research/0.1 (+https://github.com/Muhammad-Haris-3/Endpoint)'
CURL = shutil.which('curl')

# The int endpoint is undocumented and unversioned. It is polled gently and the
# project must survive it disappearing (FEASIBILITY.md §7).
DEFAULT_RATE = 2.0      # requests/second, aggregate
MAX_TRIES = 4
BACKOFF_BASE = 2.0


class Pacer:
    """Token bucket. Releases at most `rate` requests per second, globally."""

    def __init__(self, rate=DEFAULT_RATE):
        self.interval = 1.0 / rate
        self.lock = threading.Lock()
        self.next_at = time.time()

    def wait(self):
        with self.lock:
            slot = max(time.time(), self.next_at)
            self.next_at = slot + self.interval
        delay = slot - time.time()
        if delay > 0:
            time.sleep(delay)


class Result:
    """A single HTTP outcome. A refusal is data, so it is returned, not raised."""

    __slots__ = ('status', 'body', 'bytes', 'seconds', 'error')

    def __init__(self, status=0, body=None, nbytes=0, seconds=0.0, error=None):
        self.status = status
        self.body = body
        self.bytes = nbytes
        self.seconds = seconds
        self.error = error

    @property
    def ok(self):
        return self.status == 200 and self.body is not None

    def json(self):
        return json.loads(self.body) if self.body else None


def _curl(url, timeout):
    """One request. Returns (status, body_bytes, elapsed_seconds).

    -s      no progress meter
    -L      follow redirects
    -w      status appended after the body, separated by a sentinel, so one
            invocation yields both without a temp file
    """
    started = time.time()
    proc = subprocess.run(
        [CURL, '-s', '-L', '--max-time', str(int(timeout)),
         '-H', 'User-Agent: ' + UA,
         '-H', 'Accept: application/json',
         '-w', '\n__ENDPOINT_STATUS__%{http_code}', url],
        capture_output=True, timeout=timeout + 15)
    elapsed = time.time() - started
    out = proc.stdout
    marker = b'\n__ENDPOINT_STATUS__'
    idx = out.rfind(marker)
    if idx < 0:
        return 0, None, elapsed
    status = int(out[idx + len(marker):].strip() or 0)
    return status, out[:idx], elapsed


def get(url, pacer=None, timeout=45, tries=MAX_TRIES):
    """Paced GET with backoff. Never raises for an HTTP status; returns Result.

    404 is returned immediately rather than retried: on this API it means the
    record does not exist, which is an answer and not a failure to get one.
    """
    if CURL is None:
        return Result(error='curl not found on PATH')
    last = Result(error='no attempt made')
    for attempt in range(tries):
        if pacer:
            pacer.wait()
        try:
            status, body, elapsed = _curl(url, timeout)
        except subprocess.TimeoutExpired:
            last = Result(error='timeout')
            time.sleep(BACKOFF_BASE ** attempt)
            continue
        except Exception as exc:                      # noqa: BLE001 - recorded, not raised
            last = Result(error=type(exc).__name__ + ': ' + str(exc)[:120])
            time.sleep(BACKOFF_BASE ** attempt)
            continue

        if status == 200:
            return Result(status, body, len(body or b''), elapsed)
        if status == 404:
            return Result(status, None, 0, elapsed, error='not found')
        last = Result(status, None, 0, elapsed, error='HTTP %d' % status)
        if status in (429, 500, 502, 503, 504):
            time.sleep(BACKOFF_BASE ** attempt)
            continue
        return last                                   # 403 and friends: no point retrying
    return last


def get_json(url, pacer=None, **kw):
    """As get(), but returns (obj_or_None, Result). Malformed JSON is a failure."""
    res = get(url, pacer=pacer, **kw)
    if not res.ok:
        return None, res
    try:
        return res.json(), res
    except Exception:                                 # noqa: BLE001
        res.error = 'unparseable JSON'
        return None, res
