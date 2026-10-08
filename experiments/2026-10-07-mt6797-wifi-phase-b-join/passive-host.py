#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""After the Phase B trigger: one passive scan, sealed logs, reviewed recovery."""

import argparse
import importlib.util
import json
import os
import runpy
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / 'wifi-phase-b/session-5'
CAPTURE = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / 'wifi-phase-b/capture-5'
RELEASE = '7.1.3-gemini-a53-wifi-phase-b-compile'
SOURCE = HERE.parent / '2026-10-02-mt6797-scan-tuning-sample/passive-host.py'
SPEC = importlib.util.spec_from_file_location('scan_tuning_host', SOURCE)
SCAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCAN)
# Re-point every level the scan-tuning host already re-points.
SCAN.ROOT = ROOT
SCAN.CAPTURE = CAPTURE
SCAN.RELEASE = RELEASE
SCAN.SCAN_SOURCE = Path(os.environ['GEMINI_JOIN_SCRIPT']).resolve(strict=True)
SCAN.PARENT.HERE = HERE
SCAN.PARENT.ROOT = ROOT
SCAN.PARENT.CAPTURE = CAPTURE
SCAN.PARENT.WIPHY_PROBE = SCAN.PARENT.WIPHY_PROBE.replace(
    b'7.1.3-gemini-a53-wifi-scan-tuning-sample', RELEASE.encode())
HOST = SCAN.HOST
# The inherited WMT host main reads HERE/results/candidate.json for the capture
# identity check. Runtime 6 must compare against the candidate-5 receipt, so
# bind only that module's HERE to runtime-6/, whose results/candidate.json is a
# byte copy of results/candidate-5.json once that receipt is committed;
# results/candidate.json stays runtime 1, runtime-2/ runtimes 2 and 3,
# runtime-4/ runtime 4 and runtime-5/ runtime 5.
HOST.HERE = HERE / 'runtime-6'
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


SETUP_MARKER = b'one-shot WMT setup complete: clear=351232 verified, CONN held off'
# The Phase B kernel names this CONSYS; the inherited host counts the old WLAN name.
PREPOWER_MARKER = b'one-shot CONSYS after WMT: prepower admission passed'


def phase_b_scan_success(root):
    """Phase B success from the session's own records, with the renamed marker.

    Mirrors the inherited host's exit condition and replaces only its obsolete
    'one-shot WLAN after WMT' count; the scan must also be demonstrated.
    """
    try:
        deferred = json.loads((root / 'deferred-start-result.json').read_bytes())
        scan = json.loads((root / 'passive-scan-result.json').read_bytes())
        records = deferred['deferred_start_records']
        lines = ((root / 'kmsg.log').read_bytes().splitlines()
                 if deferred.get('preservation', {}).get('log_complete') else [])
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return bool(deferred.get('regression_pass') and
                deferred.get('preservation', {}).get('provider_probe', {}).get('registered') and
                deferred.get('recovery_confirmed') and lines and
                records.get('record_counts', {}).get(SETUP_MARKER.decode()) == 1 and
                sum(PREPOWER_MARKER in line for line in lines) == 1 and
                scan.get('passive_scan_demonstrated') is True)


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
                parser.exit(2, 'Phase B failure session refused: ' + str(error) + '\n')
            combined = {'phase_a_capture': (json.loads(phase_a.read_bytes())
                                            if phase_a.is_file() else None),
                        'scan_attempted': False, 'scan': None, 'kernel_release': RELEASE}
            combined['join'] = {'bounded_join_pass': False}
            with (ROOT / 'phase-b-session-result.json').open('x') as stream:
                stream.write(json.dumps(combined, indent=2, sort_keys=True) + '\n')
            return rc or 1
    sys.argv = [sys.argv[0], '--candidate', str(args.candidate)] + (
        ['--execute'] if args.execute else [])
    rc = SCAN.main()
    if not args.execute:
        return rc
    if rc == 1 and ready and phase_b_scan_success(ROOT):
        rc = 0
    result_path = ROOT / 'passive-scan-result.json'
    combined = {'phase_a_capture': (json.loads(phase_a.read_bytes())
                                    if phase_a.is_file() else None),
                'scan_attempted': ready,
                'scan': json.loads(result_path.read_bytes()) if result_path.is_file() else None,
                'kernel_release': RELEASE}
    join = runpy.run_path(str(HERE / 'classify-join.py'))['classify']
    deferred = json.loads((ROOT / 'deferred-start-result.json').read_bytes())
    complete = deferred.get('preservation', {}).get('log_complete') is True
    combined['join'] = join((ROOT / 'kmsg.log').read_bytes()) if complete else {'bounded_join_pass': False}
    combined['join']['session_verified'] = bool(complete and deferred.get('regression_pass') and deferred.get('recovery_confirmed'))
    with (ROOT / 'phase-b-session-result.json').open('x') as stream:
        stream.write(json.dumps(combined, indent=2, sort_keys=True) + '\n')
    return rc or (0 if combined['join'].get('bounded_join_pass') and combined['join']['session_verified'] else 1)


if __name__ == '__main__':
    raise SystemExit(main())
