#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Device-side helpers for the v10 lifecycle cycle; prints booleans and counts only, never identifiers.

Compatible with the device's Python 3.5. Subcommands:

  bound-files        validate the private approved-service and ap-target.json files (regular file,
                     owner root, mode 0600, single link, not a symlink, schema)
  service-match      stdin: the connected ConnMan service id; exit 0 when it equals the approved one
  link-match         stdin: `iw dev wlan0 link` output; exit 0 when BSSID, SSID and frequency equal
                     the bound target (iw 4.9's SSID escaping is applied to the target first)
  positive-control FILE ARM_SEQ
                     exit 0 when, after the arm line's kmsg sequence, a `cmd` record with cid=0x81 is
                     followed by an `event` record with eid=0x02 and the same seq
  seal-check FILE    exit 0 when the capture is a complete gwref10 stream: one arm, one seal after it,
                     no record after the seal, the parser's stream integrity and the seal counts
  gateway-check      stdin: the outputs of `ip -4 route show default dev wlan0`, `ip -4 addr show dev wlan0`
                     and `ip -4 route show dev wlan0` separated by lines of `----`; exit 0 and print the
                     gateway when exactly one default gateway exists, wlan0 has exactly one IPv4 address, the
                     gateway lies in that address's prefix, an on-link `scope link` route for the prefix is
                     present, the gateway is RFC 1918 and is not the local address (no `ip route get`:
                     iproute2 4.9 prints this kernel's RTA_UID attribute as `via ??? ???`)
  kmsg-stream SOURCE OUT BOUND
                     copy SOURCE (/dev/kmsg, or a growing file for fixtures) to OUT, flushing every
                     read, stopping at BOUND bytes or on SIGTERM; prints bytes=<n> capped=<0|1>;
                     exit 0 when stopped by the signal, 3 at the bound
"""
import json
import os
import re
import signal
import stat
import sys
import time

ROOT = os.environ.get('GWREF10_BOUND_DIR', '/root/.gemini-wifi-reference')  # the override exists for fixtures
APPROVED = os.path.join(ROOT, 'approved-service')
TARGET = os.path.join(ROOT, 'ap-target.json')
SERVICE = re.compile(r'^wifi_[0-9a-f]{12}_[0-9a-f]+_(managed|adhoc)_(psk|ieee8021x|none|wep)$')
BSSID = re.compile(r'^[0-9a-f]{2}(:[0-9a-f]{2}){5}$')
KMSG = re.compile(r'^(\d+),(\d+),(\d+),[^;]*;(.*)$')


def private_file(path):
    """Raise ValueError (no identifiers in the message) unless the file is a private root file."""
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise ValueError('not a regular file')
    if st.st_uid != 0 or st.st_gid != 0:
        if not os.environ.get('GWREF10_BOUND_DIR'):
            raise ValueError('not owned by root')
    if stat.S_IMODE(st.st_mode) != 0o600:
        raise ValueError('mode is not 0600')
    if st.st_nlink != 1:
        raise ValueError('more than one link')
    if st.st_size > 4096:
        raise ValueError('unexpectedly large')
    with open(path, 'rb') as handle:
        return handle.read()


def load_approved(path=APPROVED):
    text = private_file(path).decode('ascii', 'strict').strip()
    if '\n' in text or not SERVICE.match(text):
        raise ValueError('approved-service is not one ConnMan wifi service id')
    return text


def load_target(path=TARGET):
    data = json.loads(private_file(path).decode('utf-8', 'strict'))
    if not isinstance(data, dict) or set(data) != {'ssid', 'bssid', 'frequency_mhz', 'channel'}:
        raise ValueError('ap-target schema mismatch')
    if not isinstance(data['ssid'], str) or not 1 <= len(data['ssid'].encode('utf-8')) <= 32:
        raise ValueError('ap-target ssid invalid')
    if not isinstance(data['bssid'], str) or not BSSID.match(data['bssid']):
        raise ValueError('ap-target bssid invalid')
    if not isinstance(data['frequency_mhz'], int) or not 2400 <= data['frequency_mhz'] <= 6000:
        raise ValueError('ap-target frequency invalid')
    if not isinstance(data['channel'], int) or not 1 <= data['channel'] <= 200:
        raise ValueError('ap-target channel invalid')
    return data


def iw_escape(ssid):
    """iw 4.9 util.c print_ssid_escaped: a printable ASCII byte other than space and backslash as is;
    an interior space as a space; a leading or trailing space, a backslash and every other byte as \\xNN."""
    data = ssid.encode('utf-8')
    out = []
    for i, byte in enumerate(data):
        if 0x20 < byte < 0x7f and byte != 0x5c:
            out.append(chr(byte))
        elif byte == 0x20 and i != 0 and i != len(data) - 1:
            out.append(' ')
        else:
            out.append('\\x%02x' % byte)
    return ''.join(out)


def link_matches(text, target):
    lines = text.split('\n')
    return (len(lines) > 0 and lines[0] == 'Connected to %s (on wlan0)' % target['bssid'] and
            '\tSSID: %s' % iw_escape(target['ssid']) in lines and
            '\tfreq: %d' % target['frequency_mhz'] in lines)


def positive_control(lines, arm_seq):
    """True when an arm-window CMD 0x81 record is answered by an EVENT 0x02 record with the same seq."""
    pending = set()
    for raw in lines:
        match = KMSG.match(raw.rstrip('\n'))
        if not match:
            continue
        seq = int(match.group(2))
        message = match.group(4)
        if seq <= arm_seq:
            continue
        cmd = re.match(r'^gwref10 cmd: n=\d+ cid=0x81 seq=(\d+) ', message)
        if cmd:
            pending.add(int(cmd.group(1)))
            continue
        event = re.match(r'^gwref10 event: n=\d+ eid=0x02 seq=(\d+) ', message)
        if event and int(event.group(1)) in pending:
            return True
    return False


def gateway_check(text):
    """The owner-LAN gateway from unambiguous on-link routes, or ValueError (no identifiers in the message)."""
    import ipaddress
    parts = text.split('----')
    if len(parts) != 3:
        raise ValueError('expected three route and address blocks')
    default, addr, routes = parts
    gateways = re.findall(r'^default via (\d+\.\d+\.\d+\.\d+)(?: |$)', default, re.M)
    if len(gateways) != 1:
        raise ValueError('expected exactly one default gateway')
    locals_ = re.findall(r'^\s+inet (\d+\.\d+\.\d+\.\d+)/(\d+) ', addr, re.M)
    if len(locals_) != 1:
        raise ValueError('expected exactly one IPv4 address on wlan0')
    gateway = ipaddress.ip_address(gateways[0])
    local = ipaddress.ip_address(locals_[0][0])
    network = ipaddress.ip_network('%s/%s' % locals_[0], strict=False)
    private = any(gateway in ipaddress.ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
    if not private:
        raise ValueError('gateway is not RFC 1918')
    if not 16 <= network.prefixlen <= 30:
        raise ValueError('prefix outside 16..30')
    if gateway not in network or gateway == local:
        raise ValueError('gateway is not another host in the local prefix')
    onlink = re.search(r'^%s(?: .*)? scope link(?: |$)' % re.escape(str(network)), routes, re.M)
    if not onlink:
        raise ValueError('no on-link route for the local prefix')
    return str(gateway)


def load_parser():
    """parse-lifecycle.py next to this file is the single definition of the record schema."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parse-lifecycle.py')
    namespace = {'__name__': 'parse_lifecycle', '__file__': path}
    with open(path, encoding='utf-8') as handle:
        exec(compile(handle.read(), path, 'exec'), namespace)
    return namespace


def seal_check(lines):
    """(ok, summary): exactly one arm, exactly one seal with a later kmsg sequence, no record after the
    seal, and the parser's stream integrity (contiguous kmsg sequence, record numbers, seal counts,
    schema). The summary carries counts and booleans only."""
    lines = list(lines)
    arm_seqs = []
    seal_seqs = []
    records_after_seal = 0
    for raw in lines:
        match = KMSG.match(raw.rstrip('\n'))
        if not match:
            continue
        seq, message = int(match.group(2)), match.group(4)
        if message.startswith('gwref10 arm: '):
            arm_seqs.append(seq)
        elif message.startswith('gwref10 seal: '):
            seal_seqs.append(seq)
        elif message.startswith('gwref10 ') and seal_seqs and seq > seal_seqs[0] and ': n=' in message:
            records_after_seal += 1
    ledger = load_parser()['parse'](lines)
    ordered = len(arm_seqs) == 1 and len(seal_seqs) == 1 and arm_seqs[0] < seal_seqs[0]
    ok = ordered and records_after_seal == 0 and ledger['stream_intact']
    summary = {
        'arm_lines': len(arm_seqs), 'seal_lines': len(seal_seqs), 'arm_before_seal': int(ordered),
        'records_after_seal': records_after_seal, 'stream_intact': int(ledger['stream_intact']),
        'complete': int(ledger['complete']), 'problems': len(ledger['problems']),
        'records': len(ledger['records']), 'suppressed': ledger['suppressed'], 'truncated': ledger['truncated'],
        'length_refusals': ledger['length_refusals'],
        'seal_reason': ledger['seal']['reason'] if ledger['seal'] else 'missing',
    }
    return ok, summary


def kmsg_stream(source, out, bound):
    """Copy the kernel log stream to a file with an exact byte bound and prompt flushing.

    The source is opened non-blocking (/dev/kmsg included), so an idle source never pins the reader in
    read(): EAGAIN and an empty read sleep 20 ms, EPIPE (the kernel's report of dropped messages) is
    counted and reading continues, any other read failure ends the copy with a report. SIGTERM ends it
    normally with the report; the byte bound ends it with exit 3."""
    import errno
    stop = {'signal': False}

    def on_term(signum, frame):
        stop['signal'] = True
    signal.signal(signal.SIGTERM, on_term)
    fd = os.open(source, os.O_RDONLY | os.O_NONBLOCK)
    total = 0
    capped = 0
    drops = 0
    failure = ''
    with open(out, 'wb') as sink:
        while not stop['signal']:
            try:
                chunk = os.read(fd, 8192)
            except BlockingIOError:
                chunk = b''
            except InterruptedError:
                continue
            except OSError as error:
                if error.errno == errno.EPIPE:
                    drops += 1
                    continue
                failure = 'errno%d' % error.errno
                break
            if not chunk:
                time.sleep(0.02)
                continue
            if total + len(chunk) > bound:
                chunk = chunk[:bound - total]
                capped = 1
            sink.write(chunk)
            sink.flush()
            total += len(chunk)
            if capped:
                break
    os.close(fd)
    print('bytes=%d capped=%d drops=%d failure=%s stopped_by=%s' % (
        total, capped, drops, failure or 'none', 'signal' if stop['signal'] else ('bound' if capped else 'error')))
    if failure:
        return 4
    return 3 if capped else 0


def main(argv):
    command = argv[1] if len(argv) > 1 else ''
    try:
        if command == 'bound-files':
            load_approved()
            load_target()
            print('bound_files=1')
            return 0
        if command == 'service-match':
            ok = sys.stdin.read().strip() == load_approved()
            print('service_match=%d' % ok)
            return 0 if ok else 1
        if command == 'link-match':
            ok = link_matches(sys.stdin.read(), load_target())
            print('target_match=%d' % ok)
            return 0 if ok else 1
        if command == 'positive-control' and len(argv) == 4:
            with open(argv[2], encoding='utf-8', errors='replace') as handle:
                ok = positive_control(handle, int(argv[3]))
            print('positive_control=%d' % ok)
            return 0 if ok else 1
        if command == 'seal-check' and len(argv) == 3:
            with open(argv[2], encoding='utf-8', errors='replace') as handle:
                ok, summary = seal_check(handle)
            print(' '.join('%s=%s' % (k, v) for k, v in sorted(summary.items())))
            print('seal_ok=%d' % ok)
            return 0 if ok else 1
        if command == 'gateway-check':
            print(gateway_check(sys.stdin.read()))
            return 0
        if command == 'kmsg-stream' and len(argv) == 5:
            return kmsg_stream(argv[2], argv[3], int(argv[4]))
    except (OSError, ValueError, UnicodeError) as error:
        print('check_error=1 reason=%s' % str(error).replace(' ', '_'))
        return 2
    print('usage error')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
