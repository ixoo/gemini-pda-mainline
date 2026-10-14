#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""ROOT-only one-lifetime CCMP compatibility host; no native ciphertext claim.

Reuse frozen phase-b scan/join/seal/quiescence/regression/single-recovery mechanics
with fresh receipt-bound roots, release, mode helper and provisional CCMP verdict.
No worker may execute this against a device. Real receipt preparation is required.
"""
import argparse
import importlib.util
import json
import os
import runpy
import sys
from pathlib import Path

# passive-host.py validates GEMINI_PHASE_B_SESSION in {33,34} at import; this only
# satisfies that check -- every identity level (ROOT/CAPTURE/HOST.HERE/RELEASE) is
# re-pointed to the native values below, so the phase-b session id is never used.
os.environ['GEMINI_PHASE_B_SESSION'] = '33'
HERE = Path(__file__).resolve().parent
PHASE_B = HERE.parent / '2026-10-07-mt6797-wifi-phase-b-join'
_spec = importlib.util.spec_from_file_location('wifi_phase_b_host', PHASE_B / 'passive-host.py')
PH = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PH)

PH_RELEASE = '7.1.3-gemini-a53-wifi-phase-b-compile'
NATIVE_RELEASE = '7.1.3-gemini-a53-wifi-ccmp-stable-monitor'
assert PH.RELEASE == PH_RELEASE, 'frozen phase-b release changed: %r' % PH.RELEASE
RUNTIME_ROOT = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True)
ROOT = RUNTIME_ROOT / 'ccmp-stable-monitor/session-ccmp1'
CAPTURE = RUNTIME_ROOT / 'ccmp-stable-monitor/capture-ccmp1'

# Re-point every identity level the phase-b host set at import, to the native
# release and the native (unclaimed) evidence roots; the capture identity dir is
# this experiment's runtime-nd1 (a byte copy of the ND1 receipt the device boots,
# native-delivery-candidate.json, not the C32 build parent).
PH.ROOT = PH.SCAN.ROOT = PH.SCAN.PARENT.ROOT = PH.HOST.ROOT = PH.HOST.DOMAIN.ROOT = \
    PH.HOST.DOMAIN.HOST.ROOT = ROOT
PH.CAPTURE = PH.SCAN.CAPTURE = PH.SCAN.PARENT.CAPTURE = PH.HOST.CAPTURE = CAPTURE
PH.RELEASE = PH.SCAN.RELEASE = PH.HOST.DOMAIN.RELEASE = NATIVE_RELEASE
PH.SCAN.PARENT.WIPHY_PROBE = PH.SCAN.PARENT.WIPHY_PROBE.replace(
    PH_RELEASE.encode(), NATIVE_RELEASE.encode())
PH.HOST.HERE = HERE / 'runtime-ccmp1'
if PH.WIFI_SSH_RECEIPT is not None:
    PH.WIFI_SSH_RECEIPT = ROOT / 'wifi-ssh-receipt.json'


class NativeWifiHelper(PH.WifiHelper):
    """Reuse owned-child mechanics with one reviewed ACTIVE-only CCMP helper."""

    def start(self):
        if not self.enabled() or self.record['started']:
            return
        import subprocess
        argv = [sys.executable, str(HERE / 'laptop-wifi-ssh-ccmp.py'), str(self.keys),
                self.boot, '--cycles', '1', '--poll-seconds', str(self.poll),
                '--receipt', str(self.receipt_path)]
        self.proc = self.spawn(argv, start_new_session=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.pgid = self.proc.pid
        self.record['started'] = True


if PH.WIFI_SSH_RECEIPT is not None and PH.WIFI_SSH_KEYS is not None and PH.WIFI_SSH_BOOT:
    PH.HELPER = NativeWifiHelper(PH.WIFI_SSH_KEYS, PH.WIFI_SSH_BOOT, PH.WIFI_SSH_RECEIPT,
                                 cycles=1)


def native_result_path():
    return ROOT / 'ccmp-session-result.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    if not PH.C2_SCRIPT:
        parser.exit(2, 'CCMP compatibility requires the PSK-bound CCMP join script\n')
    phase_a = CAPTURE / 'phase-a-result.json'
    ready = (phase_a.is_file() and
             json.loads(phase_a.read_bytes()).get('ready_for_scan') is True)
    if args.execute:
        PH.select_prepare(ready)
        if not ready:
            # A failed or unclassified lifetime still gets sealing, the A53
            # regression and the single reviewed recovery; only the scan is withheld.
            try:
                rc = PH.run_without_scan(args.candidate)
            except (OSError, ValueError, KeyError, TypeError) as error:
                parser.exit(2, 'CCMP failure session refused: ' + str(error) + '\n')
            combined = {'phase_a_capture': (json.loads(phase_a.read_bytes())
                                            if phase_a.is_file() else None),
                        'scan_attempted': False, 'kernel_release': NATIVE_RELEASE,
                         'ccmp_compatibility': {'provisional_ccmp_compatibility_pass': False,
                                            'reason': 'no ready lifetime; scan withheld'}}
            with native_result_path().open('x') as stream:
                stream.write(json.dumps(combined, indent=2, sort_keys=True) + '\n')
            return rc or 1
    sys.argv = [sys.argv[0], '--candidate', str(args.candidate)] + (
        ['--execute'] if args.execute else [])
    rc = PH.SCAN.main()
    if not args.execute:
        return rc
    if rc == 1 and ready and PH.phase_b_scan_success(ROOT, PH.C2_SCRIPT):
        rc = 0
    deferred = json.loads((ROOT / 'deferred-start-result.json').read_bytes())
    complete = deferred.get('preservation', {}).get('log_complete') is True
    kmsg = (ROOT / 'kmsg.log').read_bytes() if complete else b''
    session_verified = bool(complete and deferred.get('regression_pass') and
                            deferred.get('recovery_confirmed'))
    # The verified sealed boot is named only when the session is verified; the
    # native verdict binds the receipt and the device marker to exactly this boot.
    verified_boot = deferred.get('mainline_boot') if session_verified else None
    receipt = None
    try:
        receipt = json.loads(PH.WIFI_SSH_RECEIPT.read_bytes()) if PH.WIFI_SSH_RECEIPT else None
    except (OSError, ValueError):
        receipt = None
    classifier = runpy.run_path(str(HERE / 'classify-ccmp.py'))
    protocol = classifier['read_protocol'](ROOT, verified_boot)
    native = classifier['classify'](kmsg, receipt, verified_boot, protocol)
    combined = {'phase_a_capture': (json.loads(phase_a.read_bytes())
                                    if phase_a.is_file() else None),
                'scan_attempted': ready, 'kernel_release': NATIVE_RELEASE,
                'session_verified': session_verified, 'verified_boot': verified_boot,
                 'wifi_ssh_receipt': receipt, 'ccmp_compatibility': native}
    with native_result_path().open('x') as stream:
        stream.write(json.dumps(combined, indent=2, sort_keys=True) + '\n')
    verdict = bool(native.get('provisional_ccmp_compatibility_pass'))
    # A hard parser/setup error (rc == 2) still fails; otherwise the native verdict
    # (which already folds in session health through verified_boot) is authoritative,
    # so the inherited single-scan rc never forces a healthy one-lifetime result to 1.
    return 2 if rc == 2 else (0 if verdict else 1)


if __name__ == '__main__':
    raise SystemExit(main())
