#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native one-cycle Wi-Fi SSH helper: the frozen phase-b laptop-wifi-ssh.py run,
restricted to one cycle, that ALSO records the device's post-ACTIVE mode marker
(mode / after_active / boot, written by join-native.sh into the ready block only
after the native diagnostic reached ACTIVE) into each cycle of the receipt. The
native verdict (classify-native.py) requires that marker to be present and bound
to the verified boot; it is NOT trusted from receipt booleans alone.

Everything except readiness probing is reused unchanged from the frozen helper:
run(), run_cycle(), exchange_ok(), write_ack(), the credential/known_hosts guard
and the exact USB/Wi-Fi command construction. probe() is re-implemented to mirror
the frozen readiness/closure contract exactly AND to stash the marker for the
cycle it admits; a parity test asserts the decision matches the frozen probe, so
drift is caught. The frozen file is not modified."""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / '2026-10-07-mt6797-wifi-phase-b-join' / 'laptop-wifi-ssh.py'
_spec = importlib.util.spec_from_file_location('wifi_ssh_frozen', FROZEN)
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

MARKERS = {}  # cycle -> {'mode', 'after_active', 'boot'} captured from the admitted ready block


def probe(keys, boot_id, cycle, runner, timeout_s):
    """Mirror the frozen probe's readiness/closure decisions exactly; additionally,
    when a cycle is admitted ('ok'), stash the post-ACTIVE mode marker from the same
    ready block so the native verdict can bind it to this boot and cycle."""
    result = runner(M.usb_command(keys, M.probe_argument(cycle)),
                    stdout=__import__('subprocess').PIPE,
                    stderr=__import__('subprocess').DEVNULL, timeout=timeout_s)
    if result.returncode != 0:
        return ('absent', None)
    fields = M.parse_block(result.stdout.decode('ascii', 'replace'))
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
            not M.re.fullmatch(r'\d{1,7}', identity['sshd_pid'] or '') or
            fields.get('LIVE') != '1' or
            not M.admissible(identity['address'], M.base_command(keys)[1])):
        return ('absent', None)
    # NATIVE ADMISSION GATE: never open the Wi-Fi challenge or write an ack unless the
    # device has written the post-ACTIVE native-delivery marker for THIS boot. A missing
    # or non-native marker, or after_active != 1, is "not ready yet" (keep polling), never
    # an admitted cycle -- so a pre-native / wrong-mode challenge cannot be launched. The
    # marker is also re-verified in the Wi-Fi exchange (exchange_ok) and in classify-native.
    if (fields.get('mode') != 'native-delivery' or fields.get('after_active') != '1' or
            fields.get('boot') != boot_id):
        return ('absent', None)
    identity['marker_mode'] = fields.get('mode')
    identity['marker_after_active'] = fields.get('after_active')
    MARKERS[cycle] = {'mode': fields.get('mode'), 'after_active': fields.get('after_active'),
                      'boot': fields.get('boot')}
    return ('ok', identity)


M.probe = probe


def exchange_ok(keys, boot_id, cycle, identity, runner, timeout_s):
    """Mirror the frozen exchange's boot/cycle/listener/lease binding AND additionally
    require the post-ACTIVE native-delivery marker in the block the device serves over
    Wi-Fi, so the mode-bound proof is validated in the actual exchange, not only in the
    USB probe or a host-held receipt flag."""
    import subprocess
    result = runner(M.wifi_command(keys, identity['address'], cycle),
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout_s)
    if result.returncode != 0:
        return (False, result.returncode)
    text = result.stdout.decode('ascii', 'replace')
    if M.MARKER not in text:
        return (False, 0)
    boot_part, block = text.split(M.MARKER, 1)
    ready = M.parse_block(block)
    served = (M.BOOT_ID.match(boot_part.strip()) is not None and boot_part.strip() == boot_id and
              ready.get('boot') == boot_id and ready.get('cycle') == str(cycle) and
              ready.get('sshd_pid') == identity['sshd_pid'] and
              ready.get('address') == identity['address'] and
              ready.get('mode') == 'native-delivery' and ready.get('after_active') == '1')
    return (served, result.returncode)


M.exchange_ok = exchange_ok
_frozen_run = M.run


def run(keys, boot_id, cycles, poll_seconds, **kwargs):
    """The frozen aggregate run, with each cycle's post-ACTIVE marker merged in.
    A cycle that was never admitted has no stashed marker, so its marker fields are
    recorded as None (the verdict then rejects it)."""
    receipt = _frozen_run(keys, boot_id, cycles, poll_seconds, **kwargs)
    for c in receipt['cycles']:
        mk = MARKERS.get(c['cycle'], {})
        c['marker_mode'] = mk.get('mode')
        # classify-native requires a boolean True here (the device wrote after_active=1
        # only after the native diagnostic reached ACTIVE); a missing/other value is False.
        c['marker_after_active'] = mk.get('after_active') == '1'
        c['marker_boot'] = mk.get('boot')
    return receipt


M.run = run

if __name__ == '__main__':
    os.umask(0o077)
    sys.exit(M.main())
