#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The native Wi-Fi SSH helper must (a) decide the SHARED readiness/closure rules
(boot/cycle/dmesg/fault/terminal/live/address) exactly as the frozen phase-b probe,
and (b) be STRICTER for native admission: it returns 'ok' / connects only when the
device wrote the post-ACTIVE native-delivery marker (mode=native-delivery,
after_active=1, matching boot) -- a missing or wrong marker is 'absent' (keep polling),
never an admitted cycle. The marker is re-verified in the Wi-Fi exchange and merged
into the receipt. Frozen parity applies to the shared rules only, not native admission."""
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE_DIR = HERE.parent
FROZEN = PROBE_DIR.parent / '2026-10-07-mt6797-wifi-phase-b-join' / 'laptop-wifi-ssh.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


F = load(FROZEN, 'frozen_ref')
N = load(PROBE_DIR / 'laptop-wifi-ssh-native.py', 'native_ref')
TARGET = 'root@10.0.0.1'
F.base_command = lambda keys: (['ssh'], TARGET)
N.M.base_command = lambda keys: (['ssh'], TARGET)
BOOT = 'c3c13385-7138-493e-b7df-6fe5673c6739'


def out(boot='BOOT', dmesg='ok', fatal='0', term='0', rboot=None, cycle='1',
        pid='1234', addr='10.0.0.55', mode='native-delivery', after='1', live='1'):
    rboot = BOOT if rboot is None else rboot
    boot = BOOT if boot == 'BOOT' else boot
    lines = ['BOOT=%s' % boot, 'FATAL=%s' % fatal, 'TERM=%s' % term, 'DMESG=%s' % dmesg,
             'READY_BEGIN', 'boot=%s' % rboot, 'cycle=%s' % cycle, 'sshd_pid=%s' % pid,
             'address=%s' % addr, 'mode=%s' % mode, 'after_active=%s' % after,
             'READY_END', 'LIVE=%s' % live]
    return ('\n'.join(lines) + '\n').encode()


def runner_for(stdout, rc=0):
    return lambda argv, **kw: subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr=b'')


# A) Shared rules: frozen and native agree (all non-ok); the native marker gate is
#    downstream of these, so it never changes the shared decision.
SHARED = {
    'boot-mismatch': dict(boot='deadbeef-0000-0000-0000-000000000000'),
    'dmesg-fail': dict(dmesg='fail'),
    'fault': dict(fatal='1'),
    'window-closed': dict(term='1'),
    'not-live': dict(live='0'),
    'bad-address': dict(addr='10.0.0.1'),
    'multicast-addr': dict(addr='224.0.0.1'),
    'wrong-ready-boot': dict(rboot='deadbeef-0000-0000-0000-000000000000'),
}
for name, kw in SHARED.items():
    N.MARKERS.clear()
    stdout = out(**kw)
    fr = F.probe(Path('/x'), BOOT, 1, runner_for(stdout), 15)
    nr = N.probe(Path('/x'), BOOT, 1, runner_for(stdout), 15)
    assert fr == nr and fr[0] != 'ok', '%s: frozen %r native %r' % (name, fr, nr)
    assert 1 not in N.MARKERS, name

# B) Shared pass + native marker present: both 'ok'; native stashes the marker.
N.MARKERS.clear()
stdout = out()
assert F.probe(Path('/x'), BOOT, 1, runner_for(stdout), 15)[0] == 'ok'
nr = N.probe(Path('/x'), BOOT, 1, runner_for(stdout), 15)
assert nr[0] == 'ok' and nr[1].get('marker_mode') == 'native-delivery', nr
assert N.MARKERS.get(1) == {'mode': 'native-delivery', 'after_active': '1', 'boot': BOOT}

# C) Native STRICTER: shared pass but marker missing/wrong -> frozen 'ok', native 'absent'
#    (no connection), nothing stashed.
for name, kw in {'no-marker': dict(mode='', after=''), 'wrong-mode': dict(mode='phase-b'),
                 'not-after-active': dict(after='0')}.items():
    N.MARKERS.clear()
    stdout = out(**kw)
    assert F.probe(Path('/x'), BOOT, 1, runner_for(stdout), 15)[0] == 'ok', name
    nr = N.probe(Path('/x'), BOOT, 1, runner_for(stdout), 15)
    assert nr == ('absent', None) and 1 not in N.MARKERS, '%s: native %r' % (name, nr)

# D) The Wi-Fi exchange re-verifies the marker: served block with the marker passes;
#    without it, the native exchange refuses even though the frozen one would accept.
MK = N.M.MARKER
identity = {'sshd_pid': '1234', 'address': '10.0.0.55'}


def served(mode='native-delivery', after='1'):
    block = 'boot=%s\ncycle=1\nsshd_pid=1234\naddress=10.0.0.55\nmode=%s\nafter_active=%s\n' % (BOOT, mode, after)
    return ('%s\n%s\n%s' % (BOOT, MK, block)).encode()


assert N.exchange_ok(Path('/x'), BOOT, 1, identity, runner_for(served()), 15) == (True, 0)
assert N.exchange_ok(Path('/x'), BOOT, 1, identity, runner_for(served(mode='phase-b')), 15)[0] is False
assert N.exchange_ok(Path('/x'), BOOT, 1, identity, runner_for(served(after='0')), 15)[0] is False
# the frozen exchange would accept the no-marker served block; the native one does not
assert F.exchange_ok(Path('/x'), BOOT, 1, identity, runner_for(served(mode='', after='')), 15)[0] is True
assert N.exchange_ok(Path('/x'), BOOT, 1, identity, runner_for(served(mode='', after='')), 15)[0] is False

# E) run() merges the marker (boolean after_active); an unseen cycle gets None/False.
N.MARKERS.clear()
N.MARKERS[1] = {'mode': 'native-delivery', 'after_active': '1', 'boot': BOOT}
N._frozen_run = lambda *a, **k: {'boot_id': BOOT, 'cycles_expected': 1, 'all_pass': True,
                                 'cycles': [{'cycle': 1, 'boot_match': True, 'ack_written': True}]}
c = N.run(Path('/x'), BOOT, 1, 90)['cycles'][0]
assert c['marker_mode'] == 'native-delivery' and c['marker_after_active'] is True and c['marker_boot'] == BOOT, c
N.MARKERS.clear()
c = N.run(Path('/x'), BOOT, 1, 90)['cycles'][0]
assert c['marker_mode'] is None and c['marker_after_active'] is False and c['marker_boot'] is None, c

print('wifi-ssh-native: PASS (shared-rule parity with frozen on %d cases; native marker '
      'GATE refuses missing/wrong marker before connecting; Wi-Fi exchange re-verifies the '
      'marker; receipt merge boolean)' % len(SHARED))
