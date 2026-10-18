#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Unadmitted 0202 SSH A/B operation; no standalone runtime entry point.

The eventual session adapter supplies the fresh ready identity, USB command
builder, original Wi-Fi exchange and a verified laptop LAN address. No retry,
cache modification, packet capture, privilege or new device control interface.
"""
import ipaddress
import shlex
import subprocess
import time


def numeric_unicast(value):
    address = ipaddress.IPv4Address(value)
    if int(str(address).split('.')[0]) == 0 or address.is_loopback or address.is_multicast or \
            int(address) >= 0xe0000000 or str(address) != value:
        raise ValueError('numeric unicast IPv4 address required')
    return value


def prime_command(boot, identity, laptop, fatal_re, terminal_re, ready_path):
    """Guard one device-originated ping against the boot/listener/window.

    Caller already validated the ready block. Recheck its exact identity and
    ACTIVE/nonterminal state immediately before the admitted radio operation.
    """
    q = shlex.quote
    numeric_unicast(laptop)
    numeric_unicast(identity['address'])
    if identity['boot'] != boot or identity['cycle'] != '1' or \
            not str(identity['sshd_pid']).isdigit():
        raise ValueError('one fresh boot-bound lifetime required')
    lines = {**identity, 'mode': 'ccmp-stable-monitor', 'after_active': '1'}
    checks = ''.join('grep -qxF ' + q(k + '=' + str(lines[k])) + ' ' + q(ready_path) +
                     ' || exit 13; ' for k in
                     ('boot', 'cycle', 'sshd_pid', 'address', 'mode', 'after_active'))
    return ('test "$(cat /proc/sys/kernel/random/boot_id)" = ' + q(boot) +
            ' || exit 10; d=$(dmesg 2>/dev/null) || exit 14; '
            'printf "%s" "$d" | grep -Eq ' + q(fatal_re) + ' && exit 11; '
            '[ "$(printf "%s" "$d" | grep -Ec ' + q(terminal_re) +
            ')" -eq 0 ] || exit 12; '
            'if printf "%s" "$d" | grep -q "one-shot WLAN join data phase end:"; '
            'then exit 12; fi; '
            'printf "%s" "$d" | grep -q "one-shot WLAN native-diag: state=2 " || exit 15; ' +
            checks + 'kill -0 ' + q(str(identity['sshd_pid'])) + ' || exit 16; '
            '/bin/busybox timeout 3 /bin/busybox ping -I wlan0 -c 1 -W 2 ' + q(laptop))


def exchange(*, prime, laptop, device, command, usb_command, wifi_exchange,
             retain, budget_s, runner=subprocess.run, clock=time.monotonic):
    """One controlled intervention inside the existing exchange's time budget.

    retain(label, bytes, scalars) feeds the existing private evidence seal and
    single per-run scalars file. Query errors mean unknown. Prime failure does
    not trigger a retry or suppress the SSH observation; a guarded refusal
    blocks SSH because the live window/identity is no longer established.
    """
    if type(prime) is not bool or not 0 < budget_s <= 25:
        raise ValueError('explicit arm and original finite exchange budget required')
    numeric_unicast(laptop)
    numeric_unicast(device)
    if laptop == device:
        raise ValueError('laptop and device addresses must differ')
    deadline = clock() + budget_s

    def acquire(label, argv, maximum):
        remaining = deadline - clock()
        record = {'started_s': clock(), 'exit': None, 'timeout': False, 'error': None,
                  'attempted': remaining > 0}
        data = b''
        if remaining <= 0:
            record['error'] = 'budget-exhausted'
        else:
            try:
                result = runner(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=min(maximum, remaining))
                data, record['exit'] = result.stdout, result.returncode
            except subprocess.TimeoutExpired as exc:
                data, record['timeout'] = exc.output or b'', True
            except OSError as exc:
                record['error'] = type(exc).__name__
        record['ended_s'] = clock()
        retain(label, data, record)
        return record

    acquire('route-before', ['/sbin/route', '-n', 'get', device], 0.5)
    acquire('arp-before-prime', ['/usr/sbin/arp', '-n', device], 0.5)
    intervention = {'enabled': prime, 'attempted': False}
    if prime:
        intervention = {**intervention, 'attempted': True,
                        **acquire('device-ping', usb_command(command), 4)}
    retain('prime-arm', b'', intervention)
    acquire('arp-before-ssh', ['/usr/sbin/arp', '-n', device], 0.5)
    try:
        if prime and (intervention['timeout'] or intervention['error'] or
                      intervention['exit'] not in (0, 1, 124)):
            return {'attempted': False, 'reason': 'prime guard/transport refused'}
        remaining = deadline - clock()
        if remaining <= 0:
            return {'attempted': False, 'reason': 'exchange budget exhausted'}
        return wifi_exchange(remaining)
    finally:
        acquire('arp-after-ssh', ['/usr/sbin/arp', '-n', device], 0.5)
