#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native one-lifetime delivery host: the phase-b C2 session machinery driven for
EXACTLY ONE cycle, with the native identity and the native verdict.

It imports the frozen phase-b passive-host.py and reuses, unchanged, its scan /
C2-join orchestration, the supplicant-log export, the boot-bound quiescence gate,
the per-cycle evidence export and the single reviewed recovery. It changes only:

  * identity -- the kernel release, the evidence/capture roots and the capture
    identity (runtime-nd1/results/candidate.json, a byte copy of the ND1 receipt
    the device actually boots, native-delivery-candidate.json, not the C32 parent);
  * the Wi-Fi helper -- a one-cycle NativeWifiHelper that runs
    laptop-wifi-ssh-native.py so the receipt carries the device post-ACTIVE mode
    marker (mode / after_active / boot);
  * the verdict -- classify-native.py (eligible native delivery AND an
    authenticated post-ACTIVE Wi-Fi challenge bound to the verified sealed boot),
    NOT the two-lifetime C3 conjunction.

The frozen phase-b files and their source pins are not modified; this is a narrow
native variant. No kernel build and no device action live here; root executes it
with the private native join binder and credentials after R34 completes and ND1
is installed under the reviewed boot2 guard.
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
NATIVE_RELEASE = '7.1.3-gemini-a53-wifi-native-delivery-diag'
assert PH.RELEASE == PH_RELEASE, 'frozen phase-b release changed: %r' % PH.RELEASE
RUNTIME_ROOT = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True)
ROOT = RUNTIME_ROOT / 'native-delivery/session-nd1'
CAPTURE = RUNTIME_ROOT / 'native-delivery/capture-nd1'

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
PH.HOST.HERE = HERE / 'runtime-nd1'
if PH.WIFI_SSH_RECEIPT is not None:
    PH.WIFI_SSH_RECEIPT = ROOT / 'wifi-ssh-receipt.json'


class NativeWifiHelper(PH.WifiHelper):
    """One-cycle helper that owns laptop-wifi-ssh-native.py (not the frozen two-cycle
    helper), so the receipt records the device post-ACTIVE mode marker."""

    def start(self):
        if not self.enabled() or self.record['started']:
            return
        import subprocess
        argv = [sys.executable, str(HERE / 'laptop-wifi-ssh-native.py'), str(self.keys),
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
    return ROOT / 'native-session-result.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    if not PH.C2_SCRIPT:
        parser.exit(2, 'native delivery requires the PSK-bound native join script\n')
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
                parser.exit(2, 'native failure session refused: ' + str(error) + '\n')
            combined = {'phase_a_capture': (json.loads(phase_a.read_bytes())
                                            if phase_a.is_file() else None),
                        'scan_attempted': False, 'kernel_release': NATIVE_RELEASE,
                        'native_delivery': {'native_delivery_pass': False,
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
    classify = runpy.run_path(str(HERE / 'classify-native.py'))['classify']
    native = classify(kmsg, receipt, verified_boot)
    combined = {'phase_a_capture': (json.loads(phase_a.read_bytes())
                                    if phase_a.is_file() else None),
                'scan_attempted': ready, 'kernel_release': NATIVE_RELEASE,
                'session_verified': session_verified, 'verified_boot': verified_boot,
                'wifi_ssh_receipt': receipt, 'native_delivery': native}
    with native_result_path().open('x') as stream:
        stream.write(json.dumps(combined, indent=2, sort_keys=True) + '\n')
    verdict = bool(native.get('native_delivery_pass'))
    # A hard parser/setup error (rc == 2) still fails; otherwise the native verdict
    # (which already folds in session health through verified_boot) is authoritative,
    # so the inherited single-scan rc never forces a healthy one-lifetime result to 1.
    return 2 if rc == 2 else (0 if verdict else 1)


if __name__ == '__main__':
    raise SystemExit(main())
