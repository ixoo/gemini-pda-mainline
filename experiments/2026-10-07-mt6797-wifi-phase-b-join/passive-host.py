#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""After the Phase B trigger: one passive scan, sealed logs, reviewed recovery."""

import argparse
import importlib.util
import json
import os
import re
import runpy
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / 'wifi-phase-b/session-31'
CAPTURE = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / 'wifi-phase-b/capture-31'
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
# Runtime 21: the revised join script plus its private prefix is about 22.6 KB;
# the same finite cap as bind-target.py and prepare-runtime.py.
SCAN.SOURCE_LIMIT = 32768
SCAN.PARENT.HERE = HERE
SCAN.PARENT.ROOT = ROOT
SCAN.PARENT.CAPTURE = CAPTURE
SCAN.PARENT.WIPHY_PROBE = SCAN.PARENT.WIPHY_PROBE.replace(
    b'7.1.3-gemini-a53-wifi-scan-tuning-sample', RELEASE.encode())
HOST = SCAN.HOST
# The inherited WMT host main reads HERE/results/candidate.json for the capture
# identity check. Runtime 31 must compare against the candidate-30 receipt, so
# bind only that module's HERE to runtime-31/, whose results/candidate.json is a
# byte copy of results/candidate-30.json; the
# earlier runtime-N/ copies stay bound to their runtimes.
HOST.HERE = HERE / 'runtime-31'
HOST.ROOT = ROOT
HOST.CAPTURE = CAPTURE
HOST.DOMAIN.HERE = HERE
HOST.DOMAIN.ROOT = ROOT
HOST.DOMAIN.RELEASE = RELEASE
HOST.DOMAIN.HOST.HERE = HERE
HOST.DOMAIN.HOST.ROOT = ROOT
HOST.DOMAIN.HOST.REPO = PRIVATE_REPO
HOST.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
C2 = runpy.run_path(str(HERE / 'c2-session.py'))
# Runtime 31: the custodian's laptop-wifi-ssh.py receipt, when the combined
# session includes the Wi-Fi SSH exchange; absent, the session stays a C2 one.
WIFI_SSH_RECEIPT = (Path(os.environ['GEMINI_WIFI_SSH_RECEIPT']).resolve()
                    if os.environ.get('GEMINI_WIFI_SSH_RECEIPT') else None)
BOOT_ID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
C2_SCRIPT = C2['is_c2_script'](SCAN.SCAN_SOURCE.read_bytes())
WIPHY_PREPARE = SCAN.PREPARE


def c2_prepare(candidate):
    """The wiphy-probe prepare plus the C2 session pieces, applied before the
    scan-tuning prepare captures the phase invoker: a 130 s budget for the
    supplicant-owned join (its 100 s loop plus setup and phrase counts), one
    bounded private export of the complete supplicant log between the join
    script and the log seal, and no hash of the PSK-bound script in the claim.
    """
    prepared = WIPHY_PREPARE(candidate)
    if not C2_SCRIPT:
        return prepared
    globals_ = prepared['execute'].__globals__
    invoke = globals_['invoke']
    globals_['BUDGETS']['supplicant-log'] = (20, C2['LOG_LIMIT'] + 4096)
    prepared['claim']['phase_budgets']['supplicant-log'] = {
        'connections': 1, 'seconds': 20, 'stdout_bytes': C2['LOG_LIMIT'] + 4096, 'stderr_bytes': 16384}
    exported = False

    def invoke_with_supplicant_log(active, label, script, *, network_status=None):
        nonlocal exported
        if label == 'log-export' and not exported:
            exported = True
            observation = json.loads((ROOT / 'observation-result.json').read_bytes())
            boot = observation['boot_id']
            try:
                raw, err, process = invoke(active, 'supplicant-log', C2['log_script'](boot))
                result = C2['log_result'](raw, err, process, boot)
            except (OSError, ValueError, KeyError, TypeError) as error:
                result = {'complete': False, 'reason': str(error)}
            active['collector'].write_new(ROOT / 'supplicant-log-result.json',
                                           HOST.DOMAIN.HOST.encoded(result))
        return invoke(active, label, script, network_status=network_status)

    globals_['invoke'] = invoke_with_supplicant_log
    return prepared


def prepare_with_c2(candidate):
    prepared = SCAN.prepare(candidate)
    if C2_SCRIPT:
        globals_ = prepared['execute'].__globals__
        # Phase C3: the join script's wait grows to 100 ticks (the driver's 60 s
        # data phase with the bounded data checks inside it, then the teardown).
        globals_['BUDGETS']['passive-scan'] = (130, 262144)
        prepared['claim']['phase_budgets']['passive-scan']['seconds'] = 130
        # The bound script carries the PSK; its digest is private evidence only.
        prepared['claim']['passive_scan_script_sha256'] = 'private-psk-bound'
    return prepared


SCAN.PREPARE = c2_prepare


def select_prepare(ready):
    """Scan only after a ready lifetime; otherwise the same session without it.

    SCAN.PREPARE is the wiphy-probe prepare the scan-tuning host wrapped. It
    keeps observation, log sealing, the A53 regression and reviewed recovery,
    and injects no scan. Its wiphy probe records an absent wiphy without
    failing the session.
    """
    HOST.DOMAIN.prepare = prepare_with_c2 if ready else SCAN.PREPARE
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


def phase_b_scan_success(root, c2=False):
    """Phase B success from the session's own records, with the renamed marker.

    Mirrors the inherited host's exit condition and replaces only its obsolete
    'one-shot WLAN after WMT' count; the scan must also be demonstrated. Under
    C2 there is no standard iw scan, so only that demonstration is replaced,
    by the join phase's complete process under the authenticated boot with
    an empty stderr; phase and process errors still fail.
    """
    try:
        deferred = json.loads((root / 'deferred-start-result.json').read_bytes())
        scan = json.loads((root / 'passive-scan-result.json').read_bytes())
        if c2:
            userspace = json.loads((root / 'passive-scan-userspace.json').read_bytes())
            scan = {'passive_scan_demonstrated': userspace.get('transport_complete') is True and
                    userspace.get('standard_scan_succeeded') is True}
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
    # Runtime 31 is the supplicant-owned C2+C3 session with the private log export.
    if not C2_SCRIPT:
        parser.exit(2, 'runtime 31 requires the PSK-bound C2 join script\n')
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
    if rc == 1 and ready and phase_b_scan_success(ROOT, C2_SCRIPT):
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
    verdict = combined['join'].get('bounded_join_pass') and combined['join']['session_verified']
    if C2_SCRIPT:
        combined['c2'] = c2_result(combined['join'], combined['join']['session_verified'])
        verdict = combined['c2']['c2_session_pass']
        if WIFI_SSH_RECEIPT is not None:
            combined['c3'] = c3_result(combined['join'], combined['c2'])
            verdict = combined['c3']['c3_session_pass']
    with (ROOT / 'phase-b-session-result.json').open('x') as stream:
        stream.write(json.dumps(combined, indent=2, sort_keys=True) + '\n')
    return rc or (0 if verdict else 1)


def c3_result(join, c2):
    """Runtime 21: the laptop's Wi-Fi SSH receipt (statuses, counts and the boot
    ID it was bound to; never an address) read from the custodian's file named
    by GEMINI_WIFI_SSH_RECEIPT, required to name the session's boot, and the C3
    conjunction over the C2 pieces. A missing, malformed or foreign receipt is
    recorded and fails; nothing is retried.
    """
    receipt = None
    try:
        loaded = json.loads(WIFI_SSH_RECEIPT.read_bytes())
        if isinstance(loaded, dict) and isinstance(loaded.get('boot_id'), str):
            receipt = loaded
    except (OSError, ValueError):
        receipt = None
    # The retained session results carry the mainline boot as `mainline_boot`
    # (equal to the authenticated observation receipt's boot_id).
    deferred = ROOT / 'deferred-start-result.json'
    boot = json.loads(deferred.read_bytes()).get('mainline_boot') if deferred.is_file() else None
    bound = (receipt is not None and isinstance(boot, str) and bool(BOOT_ID.match(boot)) and
             receipt.get('boot_id') == boot)
    export = ROOT / 'supplicant-log-result.json'
    log = json.loads(export.read_bytes()) if export.is_file() else {'complete': False}
    phase = ROOT / 'passive-scan-userspace.json'
    userspace = json.loads(phase.read_bytes()) if phase.is_file() else {}
    return {'wifi_ssh': receipt, 'wifi_ssh_boot_bound': bound,
            'c3_session_pass': bool(bound and C2['c3_session_pass'](
                join, c2['supplicant'], log, userspace, join.get('session_verified'), receipt))}


def c2_result(join, session_verified):
    """Fixed-phrase counts from the private framed stdout, the join phase's
    process completeness, the export's completeness (count, digest and phrase
    counts, never the log) and the session conjunction. The PSK-bound script
    is never digested here.
    """
    stdout = ROOT / 'passive-scan/stdout.txt'
    fields = C2['body_fields'](stdout.read_bytes() if stdout.is_file() else b'')
    export = ROOT / 'supplicant-log-result.json'
    log = json.loads(export.read_bytes()) if export.is_file() else {'complete': False}
    phase = ROOT / 'passive-scan-userspace.json'
    userspace = json.loads(phase.read_bytes()) if phase.is_file() else {}
    return {'supplicant': fields, 'supplicant_log': log,
            'join_phase_complete': userspace.get('transport_complete') is True and
            userspace.get('standard_scan_succeeded') is True,
            'c2_session_pass': C2['session_pass'](join, fields, log, userspace, session_verified)}


if __name__ == '__main__':
    raise SystemExit(main())
