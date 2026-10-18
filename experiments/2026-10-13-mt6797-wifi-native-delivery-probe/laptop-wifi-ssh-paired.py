#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One unchanged-C10 lifetime: original A, conditional predeclared ping/B.

No kernel/leaf change, shortened timeout, cache flush, capture or silent retry.
A's receipt remains authoritative for the original verdict even if B succeeds.
"""
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D = load('paired_d2', HERE / 'laptop-wifi-ssh-neighbor.py')
P = load('paired_prime', HERE / 'ssh-prime.py')
C = D.O.C


def paired_run(keys, boot, cycles, poll_seconds, root, runner=subprocess.run,
               clock=time.monotonic):
    if cycles != 1:
        raise ValueError('one lifetime; no rekey/reuse/reconnect')
    root.mkdir(mode=0o700)
    events = []
    deadline = None

    def arm(label):
        def bounded(argv, **kwargs):
            if label == 'arm-b' and any(arg.startswith('HostKeyAlias=') for arg in argv):
                remaining = deadline - clock()
                events.append({'label': 'B-client-budget', 'seconds': max(0, remaining),
                               'attempted': remaining > 0})
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv, 0)
                kwargs['timeout'] = min(kwargs['timeout'], remaining)
            return runner(argv, **kwargs)

        observed = D.O.observing_runner(root / label,
                    runner=D.neighbor_runner(root / label, bounded, lambda: int(clock() * 1e9)))

        def invoke(argv, **kwargs):
            nonlocal deadline
            if any(arg.startswith('HostKeyAlias=') for arg in argv) and deadline is None:
                deadline = clock() + 25  # both arms share the original exchange ceiling
            return observed(argv, **kwargs)
        return invoke

    a = C.run(keys, boot, 1, poll_seconds, runner=arm('arm-a'))
    a['paired'] = {'arm_a': dict(a), 'arm_b': None, 'prime_exit': None,
                   'b_not_reached': None, 'events': events}
    pair = a['paired']
    if a['all_pass']:
        pair['b_not_reached'] = 'A succeeded; missing-neighbor hypothesis not reproduced'
        return a
    cycle = a['cycles'][0]
    if not cycle['ssh_attempted'] or cycle['closed'] or cycle['ssh_exit'] == 0:
        pair['b_not_reached'] = 'A was not an ordinary failed SSH attempt'
        return a

    def acquire(label, argv, limit):
        remaining = deadline - clock() if deadline is not None else 0
        entry = {'label': label, 'started_ns': int(clock() * 1e9),
                 'exit': None, 'timeout': False, 'error': None}
        data = b''
        if remaining <= 0:
            entry['error'] = 'original exchange budget exhausted'
        else:
            try:
                result = runner(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=min(limit, remaining))
                data, entry['exit'] = result.stdout, result.returncode
            except subprocess.TimeoutExpired as exc:
                data, entry['timeout'] = exc.output or b'', True
            except OSError as exc:
                entry['error'] = type(exc).__name__
        entry.update(ended_ns=int(clock() * 1e9), bytes=len(data))
        with (root / (label + '.bin')).open('xb') as stream:
            stream.write(data)
        events.append(entry)
        return data, entry

    def live():
        remaining = deadline - clock() if deadline is not None else 0
        if remaining <= 0:
            return None
        try:
            status, identity = C.probe(keys, boot, 1, runner, min(0.5, remaining))
        except (subprocess.TimeoutExpired, OSError):
            return None
        return identity if status == 'ok' else None

    identity = live()
    if identity is None:
        pair['b_not_reached'] = 'window/boot/listener not freshly live after A'
        return a
    # Reuse A's numeric-route observation; never guess a LAN interface/address.
    try:
        queries = json.loads((root / 'arm-a/local-queries.json').read_text())['queries']
        if queries[0]['exit'] != 0:
            raise ValueError('route read failed')
        route = (root / 'arm-a/route-before.bin').read_text()
        matches = re.findall(r'^\s*interface:\s*([a-zA-Z0-9]+)\s*$', route, re.M)
        if len(matches) != 1:
            raise ValueError('one routed interface required')
        interface = matches[0]
        address, info = acquire('laptop-address', ['/usr/sbin/ipconfig', 'getifaddr', interface], 0.5)
        if info['exit'] != 0:
            raise ValueError('local interface address unavailable')
        laptop = P.numeric_unicast(address.decode('ascii').strip())
        mask, info = acquire('laptop-mask', ['/usr/sbin/ipconfig', 'getoption', interface, 'subnet_mask'], 0.5)
        if info['exit'] != 0:
            raise ValueError('local DHCP mask unavailable')
        subnet = ipaddress.IPv4Network(laptop + '/' + mask.decode('ascii').strip(), strict=False)
        device = ipaddress.IPv4Address(identity['address'])
        local = ipaddress.IPv4Address(laptop)
        if local in (subnet.network_address, subnet.broadcast_address, device) or device not in subnet:
            raise ValueError('addresses are not distinct peers on the routed subnet')
        lease, info = acquire('laptop-lease', ['/usr/sbin/ipconfig', 'getpacket', interface], 0.5)
        leased = re.findall(rb'^\s*yiaddr\s*=\s*([0-9.]+)\s*$', lease, re.M)
        if info['exit'] != 0 or leased != [laptop.encode('ascii')]:
            raise ValueError('current DHCP lease/address not established')
    except (OSError, ValueError, KeyError, IndexError, UnicodeError):
        pair['b_not_reached'] = 'numeric laptop LAN lease not established'
        return a
    command = P.prime_command(boot, identity, laptop, C.M.FATAL_RE,
                              C.M.TERMINAL_RE, C.M.READY_TEMPLATE.format(1))
    _, prime = acquire('device-ping', C.M.usb_command(keys, command), 4)
    pair['prime_exit'] = prime['exit']
    acquire('arp-after-prime', ['/usr/sbin/arp', '-n', identity['address']], 0.5)
    if prime['timeout'] or prime['error'] or prime['exit'] not in (0, 1, 124):
        pair['b_not_reached'] = 'prime guard/transport refused; no second attempt'
        return a
    if live() != identity:
        pair['b_not_reached'] = 'window or exact ready identity changed after prime'
        return a
    remaining = deadline - clock()
    if remaining <= 0:
        pair['b_not_reached'] = 'original exchange budget exhausted'
        return a
    # B is separately retained, never substituted for A's failed original verdict.
    pair['arm_b'] = C.run(keys, boot, 1, remaining, runner=arm('arm-b'))
    return a


def main():
    os.umask(0o077)
    if sys.platform != 'darwin' or sys.argv.count('--receipt') != 1:
        raise ValueError('custodian laptop and one owned receipt required')
    receipt = Path(sys.argv[sys.argv.index('--receipt') + 1])
    expected = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / \
        'ccmp-stable-monitor/session-ccmp10/wifi-ssh-receipt.json'
    if receipt != expected or receipt.parent.is_symlink():
        raise ValueError('receipt is outside the admitted fresh C10 session')
    C.M.run = lambda keys, boot, cycles, poll_seconds: paired_run(
        keys, boot, cycles, poll_seconds, receipt.parent / 'ssh-client-observation')
    return C.M.main()


if __name__ == '__main__':
    sys.exit(main())
