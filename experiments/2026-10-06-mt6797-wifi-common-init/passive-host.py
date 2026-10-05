#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""After the Phase A trigger: one passive scan, sealed logs, reviewed recovery."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/wifi-phase-a/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/wifi-phase-a/capture-1'
RELEASE = '7.1.3-gemini-a53-wifi-phase-a'
SOURCE = HERE.parent / '2026-10-02-mt6797-scan-tuning-sample/passive-host.py'
SPEC = importlib.util.spec_from_file_location('scan_tuning_host', SOURCE)
SCAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCAN)
# Re-point every level the scan-tuning host already re-points.
SCAN.ROOT = ROOT
SCAN.CAPTURE = CAPTURE
SCAN.RELEASE = RELEASE
SCAN.SCAN_SOURCE = HERE / 'phase-a-scan.sh'
SCAN.PARENT.HERE = HERE
SCAN.PARENT.ROOT = ROOT
SCAN.PARENT.CAPTURE = CAPTURE
SCAN.PARENT.WIPHY_PROBE = SCAN.PARENT.WIPHY_PROBE.replace(
    b'7.1.3-gemini-a53-wifi-scan-tuning-sample', RELEASE.encode())
HOST = SCAN.HOST
HOST.HERE = HERE
HOST.ROOT = ROOT
HOST.CAPTURE = CAPTURE
HOST.DOMAIN.HERE = HERE
HOST.DOMAIN.ROOT = ROOT
HOST.DOMAIN.RELEASE = RELEASE
HOST.DOMAIN.HOST.HERE = HERE
HOST.DOMAIN.HOST.ROOT = ROOT
HOST.DOMAIN.HOST.REPO = PRIVATE_REPO
HOST.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())


def select_prepare(ready):
    """Scan only after a ready lifetime; otherwise the same session without it.

    SCAN.PREPARE is the wiphy-probe prepare the scan-tuning host wrapped. It
    keeps observation, log sealing, the A53 regression and reviewed recovery,
    and injects no scan. Its wiphy probe records an absent wiphy without
    failing the session.
    """
    HOST.DOMAIN.prepare = SCAN.prepare if ready else SCAN.PREPARE
    return HOST.DOMAIN.prepare


def run_without_scan(candidate):
    """Session, sealing, A53 regression and recovery with no capture prerequisite.

    The inherited host main refuses unless the capture accepted WMT and sent the
    start request, which an early failure may not have. Call the scan-free
    prepare and its execute directly, as that main does after its checks.
    """
    prepared = SCAN.PREPARE(candidate)
    prepared['finish'].REPO = PRIVATE_REPO
    result = prepared['execute'](prepared)
    result['scan_attempted'] = False
    (ROOT / 'failure-session-result.json').write_bytes(HOST.DOMAIN.HOST.encoded(result))
    prepared['finish'].sync_directory(ROOT)
    print(json.dumps(result, sort_keys=True))
    return 0 if (result.get('regression_pass') and result.get('recovery_confirmed')) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    phase_a = CAPTURE / 'phase-a-result.json'
    ready = (phase_a.is_file() and
             json.loads(phase_a.read_bytes()).get('ready_for_scan') is True)
    if args.execute:
        select_prepare(ready)
        if not ready:
            # A failed or unclassified lifetime still gets sealing, the A53
            # regression and reviewed recovery; only the scan is withheld.
            try:
                rc = run_without_scan(args.candidate)
            except (OSError, ValueError, KeyError, TypeError) as error:
                parser.exit(2, 'Phase A failure session refused: ' + str(error) + '\n')
            combined = {'phase_a_capture': (json.loads(phase_a.read_bytes())
                                            if phase_a.is_file() else None),
                        'scan_attempted': False, 'scan': None, 'kernel_release': RELEASE}
            with (ROOT / 'phase-a-session-result.json').open('x') as stream:
                stream.write(json.dumps(combined, indent=2, sort_keys=True) + '\n')
            return rc
    sys.argv = [sys.argv[0], '--candidate', str(args.candidate)] + (
        ['--execute'] if args.execute else [])
    rc = SCAN.main()
    if not args.execute:
        return rc
    result_path = ROOT / 'passive-scan-result.json'
    combined = {'phase_a_capture': (json.loads(phase_a.read_bytes())
                                    if phase_a.is_file() else None),
                'scan_attempted': ready,
                'scan': json.loads(result_path.read_bytes()) if result_path.is_file() else None,
                'kernel_release': RELEASE}
    with (ROOT / 'phase-a-session-result.json').open('x') as stream:
        stream.write(json.dumps(combined, indent=2, sort_keys=True) + '\n')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
