#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Laptop side of the two-lifetime data checks: one bounded attributable SSH exchange over Wi-Fi per cycle, then a fail-closed host acknowledgment written back over USB.

The custodian runs this on the laptop while the two-lifetime device session runs. For each
cycle it issues ONE bounded USB read that returns, in a single authenticated call, the live
boot id, whether a named join fault has been recorded, how many healthy stage-3 terminals
have occurred, and the cycle's private "ready" block (this boot, this cycle ordinal, the
fresh Dropbear listener pid and the station's leased address) that the device writes only
with the listener confirmed up inside the open data window. The host returns the address
only when the boot matches, no fault is recorded, this cycle's terminal has not yet occurred
(the window is open), the ready block names this boot and this cycle with a listener pid,
and the address is an admissible unicast lease. A recorded fault or a reached terminal is a
closed cycle and stops the run; it is never retried.

It then opens exactly one SSH session to that address over Wi-Fi and runs one read-only
command that prints the boot id and the device's own per-cycle ready block, and accepts the
exchange only when the boot matches AND the block the device serves over Wi-Fi names this
cycle (the marker is the device's, not an echo of the ordinal the host supplied). Because
the kernel only delivers and transmits station data during the data phase, a successful
Wi-Fi exchange is itself attributable to this cycle's data window.

Only then does it write this cycle's acknowledgment back over USB with a guarded,
fail-closed remote command that re-verifies the live boot, the absence of a fault, that this
cycle's stage-3 terminal has not yet occurred, and that the acknowledgment leaf does not
already exist, before writing the one exact line the device consumes:
"host_ack boot=<boot> cycle=<N> ssh_exit=0". A late (post-terminal) or post-fault
acknowledgment is refused by that same guard, so it cannot start the next cycle; the device
drives the next cycle only on its own rendezvous and this ack. The chosen cutoff is exact:
the data exchange must occur in this cycle's data window (the kernel gates it there); the USB
control notification may land during the healthy cleanup tail but only when guarded that no
terminal or fault has intervened, and it fails closed otherwise. This is a control
notification, not a claim that station data moves outside the data phase.

Both hops use the baseline's exact direct SSH options (no configuration file, no agent, no
proxy, no multiplexing, Ed25519 only, key only, strict host-key checking against the
retained known_hosts, which pins the fixed USB endpoint's host key); the Wi-Fi hop names
that endpoint as its HostKeyAlias so the same retained host key is required. The receipt
carries statuses, byte counts and seconds only; the address is never printed, logged or
kept. The readiness/ack polling uses a short 0.2 s interval within the same finite per-cycle
budget; one Wi-Fi attempt per cycle; no retry; the first failed or closed cycle stops. The
custodian joins and stops this helper before evidence sealing and recovery, so nothing can
write an acknowledgment after the return to Gemian.
"""
import argparse
import json
import os
import pathlib
import re
import runpy
import shlex
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
BASELINE = runpy.run_path(str(HERE.parents[0] / '2026-09-05-owner-away-experiment-preparation/baseline/scripts/collect-baseline.py'),
                          run_name='a53_baseline')
BASE_DIR = '/tmp/mt6797-wifi-phase-b-1'
READY_TEMPLATE = BASE_DIR + '/c{}/ready'
ACK_TEMPLATE = BASE_DIR + '/c{}/host-ack'
BOOT_ID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
ADDRESS = re.compile(r'^(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$')
FATAL_RE = "one-shot WLAN join (stopped:|rearm refused:|rearm wrap:)"
TERMINAL_RE = "one-shot WLAN join cleanup: stage=3 "
MARKER = '---ready---'
# The Wi-Fi command: the device prints its boot id and serves this cycle's own ready block.
COMMAND = ('cat /proc/sys/kernel/random/boot_id; printf %s\\\\n ' + shlex.quote(MARKER) +
           '; cat {ready}')


def base_command(keys):
    """The baseline's exact SSH options and admin identity, without its target and shell."""
    command = BASELINE['ssh_command'](keys)
    assert command[-1] == '/bin/busybox sh -s' and command[-2].startswith('root@')
    return command[:-2], command[-2]


def usb_command(keys, argument):
    base, target = base_command(keys)
    return base + [target, argument]


def wifi_command(keys, address, cycle):
    base, target = base_command(keys)
    alias = target.split('@', 1)[1]
    return base + ['-o', 'HostKeyAlias=' + alias, 'root@' + address,
                   COMMAND.format(ready=shlex.quote(READY_TEMPLATE.format(cycle)))]


def ack_line(boot_id, cycle):
    """The exact single line the device matches with grep -qxF; no address, only identity."""
    return 'host_ack boot=%s cycle=%d ssh_exit=0' % (boot_id, cycle)


def probe_argument(cycle):
    """One bounded USB read. A single dmesg snapshot is captured with explicit failure
    handling (DMESG=ok|fail) and reused for the fault flag and the stage-3 count, so a failed
    read fails safe instead of silently reading as "no fault". It also emits the live boot,
    the cycle's ready block, and LIVE from a kill -0 on the ready block's listener pid.
    """
    ready = shlex.quote(READY_TEMPLATE.format(cycle))
    return ("printf BOOT=; cat /proc/sys/kernel/random/boot_id; "
            "if d=$(dmesg 2>/dev/null); then "
            "if printf '%s' \"$d\" | grep -Eq " + shlex.quote(FATAL_RE) + "; then printf 'FATAL=1\\n'; else printf 'FATAL=0\\n'; fi; "
            "printf 'TERM=%s\\n' \"$(printf '%s' \"$d\" | grep -Ec " + shlex.quote(TERMINAL_RE) + ")\"; "
            "printf 'DMESG=ok\\n'; "
            "else printf 'FATAL=0\\nTERM=0\\nDMESG=fail\\n'; fi; "
            "printf 'READY_BEGIN\\n'; cat " + ready + " 2>/dev/null; printf 'READY_END\\n'; "
            "printf LIVE=; pid=$(sed -n 's/^sshd_pid=//p' " + ready + " 2>/dev/null); "
            "if [ -n \"$pid\" ] && kill -0 \"$pid\" 2>/dev/null; then printf '1\\n'; else printf '0\\n'; fi")


def ack_argument(boot_id, cycle):
    """A guarded, fail-closed remote write: a single dmesg snapshot (fail closed if it cannot
    be read), the live boot, no fault, the window still open (this cycle's stage-3 not
    reached), and NO existing leaf and NO symlink (a dangling symlink must not redirect the
    write); then the one exact line written under noclobber.
    """
    ack = shlex.quote(ACK_TEMPLATE.format(cycle))
    return ("d=$(dmesg 2>/dev/null) || exit 14; "
            "test \"$(cat /proc/sys/kernel/random/boot_id)\" = " + shlex.quote(boot_id) + " || exit 10; "
            "printf '%s' \"$d\" | grep -Eq " + shlex.quote(FATAL_RE) + " && exit 11; "
            "[ \"$(printf '%s' \"$d\" | grep -Ec " + shlex.quote(TERMINAL_RE) + ")\" -lt " + str(cycle) + " ] || exit 12; "
            "[ ! -e " + ack + " ] && [ ! -L " + ack + " ] || exit 13; "
            "set -C; printf '%s\\n' " + shlex.quote(ack_line(boot_id, cycle)) + " > " + ack)


def admissible(address, usb_target):
    """A leased station address the Wi-Fi hop may use: a well-formed unicast address that is
    not the fixed USB endpoint (an accidental USB lease must not reach the USB listener and pass),
    not loopback, multicast, unspecified or broadcast."""
    if not ADDRESS.match(address) or address == usb_target.split('@', 1)[1]:
        return False
    first = int(address.split('.')[0])
    return not (first == 0 or first == 127 or first >= 224 or address == '255.255.255.255')


def parse_block(text):
    """key=value lines into a dict (first occurrence wins)."""
    fields = {}
    for line in text.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            fields.setdefault(key.strip(), value.strip())
    return fields


def probe(keys, boot_id, cycle, runner, timeout_s):
    """One bounded USB probe. Returns:
      ('ok', identity)  - boot matches, no fault, window open, a live listener and an
                          admissible address; identity = {boot, cycle, sshd_pid, address};
      ('closed', reason)- a stop condition: the live boot differs from the session boot, a
                          named fault was recorded, or this cycle's stage-3 terminal reached;
      ('absent', None)  - not yet ready, or the dmesg snapshot was unreliable (fail safe:
                          never proceed to an exchange without a reliable fault snapshot).
    """
    result = runner(usb_command(keys, probe_argument(cycle)),
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout_s)
    if result.returncode != 0:
        return ('absent', None)
    fields = parse_block(result.stdout.decode('ascii', 'replace'))
    if fields.get('BOOT') != boot_id:
        return ('closed', 'the live boot differs from the session boot')
    if fields.get('DMESG') != 'ok':
        return ('absent', None)
    if fields.get('FATAL') != '0':
        return ('closed', 'a named join fault was recorded')
    try:
        term = int(fields.get('TERM', ''))
    except ValueError:
        return ('absent', None)
    if term >= cycle:
        return ('closed', "this cycle's data window has closed (stage-3 terminal reached)")
    identity = {'boot': fields.get('boot'), 'cycle': fields.get('cycle'),
                'sshd_pid': fields.get('sshd_pid'), 'address': fields.get('address', '')}
    if (identity['boot'] != boot_id or identity['cycle'] != str(cycle) or
            not re.fullmatch(r'\d{1,7}', identity['sshd_pid'] or '') or
            fields.get('LIVE') != '1' or
            not admissible(identity['address'], base_command(keys)[1])):
        return ('absent', None)
    return ('ok', identity)


def exchange_ok(keys, boot_id, cycle, identity, runner, timeout_s):
    """One Wi-Fi exchange to the leased address; True only when the device prints the session
    boot AND serves, over Wi-Fi, the SAME ready block the USB probe saw - this boot, this
    cycle, the same listener pid and the same address - so the exchange is bound to the exact
    station/listener/lease, not merely to a returned boot UUID."""
    result = runner(wifi_command(keys, identity['address'], cycle), stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, timeout=timeout_s)
    if result.returncode != 0:
        return (False, result.returncode)
    text = result.stdout.decode('ascii', 'replace')
    if MARKER not in text:
        return (False, 0)
    boot_part, block = text.split(MARKER, 1)
    ready = parse_block(block)
    served = (BOOT_ID.match(boot_part.strip()) is not None and boot_part.strip() == boot_id and
              ready.get('boot') == boot_id and ready.get('cycle') == str(cycle) and
              ready.get('sshd_pid') == identity['sshd_pid'] and ready.get('address') == identity['address'])
    return (served, result.returncode)


def write_ack(keys, boot_id, cycle, runner, timeout_s):
    """Write this cycle's ack with the fail-closed remote guard; True only on a guarded write (exit 0)."""
    result = runner(usb_command(keys, ack_argument(boot_id, cycle)),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout_s)
    return result.returncode == 0


def run_cycle(keys, boot_id, cycle, poll_seconds, runner=subprocess.run, monotonic=time.monotonic, sleep=time.sleep):
    """Poll, exchange and (guarded) acknowledge one cycle; a self-contained receipt. A closed cycle stops."""
    deadline = monotonic() + poll_seconds
    started = monotonic()
    receipt = {'cycle': cycle, 'ready_seen': False, 'ready_wait_s': None, 'ssh_attempted': False,
               'ssh_exit': None, 'boot_match': False, 'ack_written': False, 'closed': False,
               'elapsed_s': None, 'reason': None}
    identity = None
    while True:
        remaining = deadline - monotonic()
        if remaining <= 1:
            receipt['reason'] = 'no readiness within the poll budget'
            receipt['elapsed_s'] = round(monotonic() - started, 1)
            return receipt
        try:
            status, value = probe(keys, boot_id, cycle, runner, min(15.0, remaining))
        except subprocess.TimeoutExpired:
            status, value = 'absent', None
        if status == 'closed':
            receipt['closed'] = True
            receipt['reason'] = value
            receipt['elapsed_s'] = round(monotonic() - started, 1)
            return receipt
        if status == 'ok':
            identity = value
            break
        sleep(0.2)
    receipt['ready_seen'] = True
    receipt['ready_wait_s'] = round(monotonic() - started, 1)
    remaining = deadline - monotonic()
    if remaining <= 2:
        receipt['reason'] = 'no budget left for the exchange'
        receipt['elapsed_s'] = round(monotonic() - started, 1)
        return receipt
    receipt['ssh_attempted'] = True
    try:
        served, rc = exchange_ok(keys, boot_id, cycle, identity, runner, min(25.0, remaining))
    except subprocess.TimeoutExpired:
        receipt['reason'] = 'exchange timed out'
        receipt['elapsed_s'] = round(monotonic() - started, 1)
        return receipt
    receipt['ssh_exit'] = rc
    receipt['boot_match'] = served
    if not served:
        receipt['reason'] = 'exchange failed' if rc else 'boot or cycle marker differs'
        receipt['elapsed_s'] = round(monotonic() - started, 1)
        return receipt
    remaining = deadline - monotonic()
    if remaining <= 1:
        receipt['reason'] = 'no budget left to acknowledge'
        receipt['elapsed_s'] = round(monotonic() - started, 1)
        return receipt
    try:
        receipt['ack_written'] = write_ack(keys, boot_id, cycle, runner, min(15.0, remaining))
    except subprocess.TimeoutExpired:
        receipt['ack_written'] = False
    if not receipt['ack_written']:
        receipt['reason'] = 'acknowledgment refused by the device guard (late, faulted or existing leaf)'
    receipt['elapsed_s'] = round(monotonic() - started, 1)
    return receipt


def run(keys, boot_id, cycles, poll_seconds, runner=subprocess.run, monotonic=time.monotonic, sleep=time.sleep):
    """Run the cycles in order; the first cycle that does not validate and acknowledge, or is closed, stops the run."""
    results = []
    for cycle in range(1, cycles + 1):
        receipt = run_cycle(keys, boot_id, cycle, poll_seconds, runner=runner, monotonic=monotonic, sleep=sleep)
        results.append(receipt)
        if receipt['closed'] or not (receipt['boot_match'] and receipt['ack_written']):
            break
    all_pass = len(results) == cycles and all(r['boot_match'] and r['ack_written'] and not r['closed'] for r in results)
    return {'boot_id': boot_id, 'cycles_expected': cycles, 'cycles': results, 'all_pass': all_pass}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('keys', type=pathlib.Path,
                        help='the retained credential directory holding admin and known_hosts (private, never copied)')
    parser.add_argument('boot_id', help='the verified boot ID the device session was launched with')
    parser.add_argument('--cycles', type=int, default=2, help='the number of explicit lifetimes to acknowledge (1 or 2)')
    parser.add_argument('--poll-seconds', type=int, default=90, help='per-cycle monotonic budget, 10 to 120')
    parser.add_argument('--receipt', type=pathlib.Path, default=None,
                        help='write the aggregate receipt as JSON to this new mode-0600 file for the host session')
    args = parser.parse_args()
    if not BOOT_ID.match(args.boot_id):
        parser.error('boot id is not a UUID')
    if not 1 <= args.cycles <= 2:
        parser.error('cycles must be 1 or 2')
    if not 10 <= args.poll_seconds <= 120:
        parser.error('poll budget must be between 10 and 120 seconds')
    keys = args.keys.resolve(strict=True)
    if not (keys / 'admin').is_file() or not (keys / 'known_hosts').is_file():
        parser.error('keys directory lacks admin or known_hosts')
    receipt = run(keys, args.boot_id, args.cycles, args.poll_seconds)
    if args.receipt is not None:
        fd = os.open(str(args.receipt), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    summary = {'boot_id': receipt['boot_id'], 'cycles_expected': receipt['cycles_expected'],
               'cycles_run': len(receipt['cycles']), 'all_pass': receipt['all_pass']}
    print(' '.join('%s=%s' % (k, v) for k, v in sorted(summary.items())))
    return 0 if receipt['all_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
