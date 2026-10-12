#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""After the Phase B trigger: one passive scan, sealed logs, reviewed recovery."""

import argparse
import importlib.util
import json
import os
import re
import runpy
import signal
import subprocess
import time
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
# Runtime identity: 33 is the C2+C3 run on candidate 32 (the default, unchanged);
# 34 is the successor two-lifetime run on candidate 33. A narrow R34 wrapper sets
# GEMINI_PHASE_B_SESSION=34; nothing else about the orchestration differs.
_SID = os.environ.get('GEMINI_PHASE_B_SESSION', '33')
if _SID not in ('33', '34'):
    raise SystemExit('GEMINI_PHASE_B_SESSION must be 33 or 34')
ROOT = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / ('wifi-phase-b/session-' + _SID)
CAPTURE = Path(os.environ['GEMINI_RUNTIME_ROOT']).resolve(strict=True) / ('wifi-phase-b/capture-' + _SID)
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
# identity check. Runtime 33 compares against the candidate-32 receipt, so bind
# only that module's HERE to runtime-33/, whose results/candidate.json is a byte
# copy of results/candidate-32.json; the earlier runtime-N/ copies stay bound to
# their runtimes.
HOST.HERE = HERE / 'runtime-33'
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
# Runtime 32: the custodian's laptop-wifi-ssh.py receipt, when the combined
# session includes the Wi-Fi SSH exchange; absent, the session stays a C2 one.
WIFI_SSH_RECEIPT = (Path(os.environ['GEMINI_WIFI_SSH_RECEIPT']).resolve()
                    if os.environ.get('GEMINI_WIFI_SSH_RECEIPT') else None)
BOOT_ID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
# Runtime 33: the host OWNS the laptop-wifi-ssh helper when the custodian names the
# retained credential directory and the launch boot (the device session only observes the
# boot after it starts, so the boot is supplied at launch). The helper then writes its
# receipt here and the host reads it back for the verdict. If GEMINI_WIFI_SSH_RECEIPT is set
# instead, the custodian runs the helper themselves and the host only consumes that receipt.
WIFI_SSH_KEYS = (Path(os.environ['GEMINI_WIFI_SSH_KEYS']).resolve()
                 if os.environ.get('GEMINI_WIFI_SSH_KEYS') else None)
WIFI_SSH_BOOT = os.environ.get('GEMINI_WIFI_SSH_BOOT')
if WIFI_SSH_RECEIPT is None and WIFI_SSH_KEYS is not None and WIFI_SSH_BOOT and \
        BOOT_ID.match(WIFI_SSH_BOOT):
    WIFI_SSH_RECEIPT = ROOT / 'wifi-ssh-receipt.json'


class WifiHelper:
    """Own the laptop-wifi-ssh child for the verified boot: start it once, concurrently with
    the device session, then join it and stop its WHOLE process group before any export, seal
    or recovery, and record its real exit. The group is addressed by the PGID cached at start
    (start_new_session makes the child the group leader, so PGID == its PID); this is used for
    the kill and the quiescence probe INDEPENDENT of leader liveness, because once the leader
    is reaped os.getpgid(pid) would raise and lingering ssh children would escape. A SIGTERM
    is not taken as sufficient: the group is bounded-probed, SIGKILL'd if still present, and
    the transition is marked unsafe (so the caller refuses the export/seal) on any kill/probe
    error or a group that will not go quiescent. One start, no blind retry.
    """

    def __init__(self, keys, boot, receipt_path, cycles=2, poll=90,
                 spawn=subprocess.Popen, join_timeout=45, grace=5.0,
                 poll_interval=0.2, sleep=time.sleep):
        self.keys, self.boot, self.receipt_path = keys, boot, receipt_path
        self.cycles, self.poll, self.spawn = cycles, poll, spawn
        self.join_timeout, self.grace, self.poll_interval, self.sleep = join_timeout, grace, poll_interval, sleep
        self.proc = None
        self.pgid = None
        self.record = {'owned': self.enabled(), 'started': False, 'exit': None,
                       'timed_out': False, 'signals': [], 'group_quiescent': None,
                       'kill_error': False, 'probe_error': False, 'safe': not self.enabled(),
                       'receipt': str(receipt_path) if receipt_path else None}

    def enabled(self):
        return bool(self.keys and self.boot and self.receipt_path)

    def start(self):
        if not self.enabled() or self.record['started']:
            return
        argv = [sys.executable, str(HERE / 'laptop-wifi-ssh.py'), str(self.keys), self.boot,
                '--cycles', str(self.cycles), '--poll-seconds', str(self.poll),
                '--receipt', str(self.receipt_path)]
        self.proc = self.spawn(argv, start_new_session=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.pgid = self.proc.pid  # leader of its own session: PGID == PID, cached while live
        self.record['started'] = True

    def _killpg(self, sig):
        try:
            os.killpg(self.pgid, sig)
            self.record['signals'].append(int(sig))
            return True
        except ProcessLookupError:
            return True  # the group is already gone
        except OSError:
            self.record['kill_error'] = True
            return False

    def _group_gone(self):
        """True if the cached group is gone, False if still present, None on a probe error."""
        try:
            os.killpg(self.pgid, 0)
            return False
        except ProcessLookupError:
            return True
        except OSError:
            self.record['probe_error'] = True
            return None

    def _await_gone(self):
        waited = 0.0
        while True:
            gone = self._group_gone()
            if gone is not False or waited >= self.grace:
                return gone
            self.sleep(self.poll_interval)
            waited += self.poll_interval

    def _reap(self):
        """Reap the leader if it has exited, so a zombie leader does not keep killpg(PGID,0)
        succeeding (which would make the group look non-quiescent forever)."""
        if self.record['exit'] is not None:
            return
        try:
            self.record['exit'] = self.proc.wait(timeout=self.grace)
        except (subprocess.TimeoutExpired, OSError):
            pass

    def join_and_record(self, active):
        if self.record['started'] and self.proc is not None:
            try:
                self.record['exit'] = self.proc.wait(timeout=self.join_timeout)
            except subprocess.TimeoutExpired:
                self.record['timed_out'] = True
            # Stop the whole group by its cached PGID, independent of leader liveness.
            self._killpg(signal.SIGTERM)
            self._reap()                 # reap a now-terminated leader before probing
            gone = self._await_gone()
            if gone is False:
                self._killpg(signal.SIGKILL)
                self._reap()             # SIGKILL ends the leader; reap it so the probe is true
                gone = self._await_gone()
            self.record['group_quiescent'] = (gone is True)
            self.record['safe'] = bool(gone is True and not self.record['kill_error'] and
                                       not self.record['probe_error'])
        active['collector'].write_new(ROOT / 'wifi-ssh-helper.json',
                                       HOST.DOMAIN.HOST.encoded(self.record))


HELPER = WifiHelper(WIFI_SSH_KEYS, WIFI_SSH_BOOT, WIFI_SSH_RECEIPT)
C2_SCRIPT = C2['is_c2_script'](SCAN.SCAN_SOURCE.read_bytes())
WIPHY_PREPARE = SCAN.PREPARE


def c2_prepare(candidate):
    """The wiphy-probe prepare plus the C2 session pieces, applied before the
    scan-tuning prepare captures the phase invoker: a 330 s budget for the
    supplicant-owned two-lifetime join (its 300 s wall plus control readiness), one
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
    # The two cycles' retained per-cycle evidence, exported in the same pre-seal window.
    cycles_cap = 2 * len(C2['CYCLE_FILES']) * C2['CYCLE_EXPORT_LIMIT'] + 65536
    globals_['BUDGETS']['cycles-export'] = (20, cycles_cap)
    prepared['claim']['phase_budgets']['cycles-export'] = {
        'connections': 1, 'seconds': 20, 'stdout_bytes': cycles_cap, 'stderr_bytes': 16384}
    # The boot-bound quiescence record is a tiny framed read; register its narrow
    # budget so the real BUDGETS[label] lookup in invoke resolves (an unregistered
    # phase would KeyError and refuse every run).
    globals_['BUDGETS']['quiescence'] = (20, 4096)
    prepared['claim']['phase_budgets']['quiescence'] = {
        'connections': 1, 'seconds': 20, 'stdout_bytes': 4096, 'stderr_bytes': 16384}
    exported = False

    def invoke_with_supplicant_log(active, label, script, *, network_status=None):
        nonlocal exported
        if label == 'passive-scan' and HELPER.enabled():
            HELPER.start()
            try:
                return invoke(active, label, script, network_status=network_status)
            finally:
                # Join and stop the helper group before any export, seal or recovery.
                HELPER.join_and_record(active)
        if label == 'log-export' and not exported:
            exported = True
            if HELPER.record.get('owned') and not HELPER.record.get('safe'):
                raise RuntimeError('Wi-Fi helper process group not confirmed quiescent; '
                                   'refusing export, seal and recovery')
            observation = json.loads((ROOT / 'observation-result.json').read_bytes())
            boot = observation['boot_id']
            try:
                raw, err, process = invoke(active, 'supplicant-log', C2['log_script'](boot))
                result = C2['log_result'](raw, err, process, boot)
            except (OSError, ValueError, KeyError, TypeError) as error:
                result = {'complete': False, 'reason': str(error)}
            active['collector'].write_new(ROOT / 'supplicant-log-result.json',
                                           HOST.DOMAIN.HOST.encoded(result))
            # Refuse the seal and the RAM-wiping recovery if the owned supplicant is
            # not confirmed quiesced: a non-zero (effectful process still running) or
            # an unknown count (the log could not be framed to confirm it). The leaf
            # on_exit reaps it on every exit, so a legitimately failed cycle reports
            # zero here and still recovers; completeness itself never gates recovery.
            if result.get('supplicant_processes') != 0:
                raise RuntimeError('owned supplicant not confirmed quiesced '
                                   '(supplicant_processes=%r); refusing seal and '
                                   'recovery' % result.get('supplicant_processes'))
            # Authoritative, boot-bound: the leaf writes a quiescence record naming
            # any owned child -- the Wi-Fi listener as well as the supplicant -- it
            # could not terminate. Refuse the seal and the RAM-wiping recovery unless
            # the record is present, boot-bound and fault-free, so a still-live
            # listener cannot pass merely because wpa is gone.
            try:
                qraw, qerr, qprocess = invoke(active, 'quiescence', C2['quiescence_script'](boot))
                qresult = C2['quiescence_result'](qraw, qerr, qprocess, boot)
            except (OSError, ValueError, KeyError, TypeError) as error:
                qresult = {'quiesced': False, 'reason': str(error)}
            active['collector'].write_new(ROOT / 'quiescence-result.json',
                                           HOST.DOMAIN.HOST.encoded(qresult))
            if not qresult.get('quiesced'):
                raise RuntimeError('owned children not confirmed quiesced '
                                   '(faults=%r); refusing seal and recovery' %
                                   qresult.get('faults'))
            # The two cycles' retained per-cycle evidence, pulled off-device (RAM) into the
            # private evidence root before the seal and the RAM-wiping recovery. The raw
            # framed bytes (which name addresses) stay private; the result records presence
            # and byte counts only.
            try:
                craw, cerr, cprocess = invoke(active, 'cycles-export', C2['cycles_export_script'](boot))
            except (OSError, TypeError) as error:
                # The export transport failed before any device read (nothing was
                # captured). Refuse the seal and the RAM-wiping recovery rather than
                # silently losing the per-cycle RAM evidence.
                raise RuntimeError('cycles-export transport failed before capture; '
                                   'refusing seal and recovery to preserve device RAM '
                                   'evidence: ' + str(error))
            # Retain the raw framed capture regardless of result completeness.
            active['collector'].write_new(ROOT / 'cycles-evidence.raw', craw)
            try:
                cresult = C2['cycles_export_result'](craw, cerr, cprocess, boot)
            except (ValueError, KeyError, TypeError) as error:
                cresult = {'complete': False, 'reason': str(error)}
            active['collector'].write_new(ROOT / 'cycles-evidence-result.json',
                                           HOST.DOMAIN.HOST.encoded(cresult))
            # Refuse the seal and the RAM-wiping recovery on a transport, boot or
            # framing failure, or if any produced file was truncated -- the
            # evidence is not trustworthy and must stay for a re-pull. A
            # legitimately failed cycle (transport/boot/framing intact but a
            # missing lease or host-ack, so complete is false) is NOT a reason to
            # refuse: recovery still runs. Completeness alone never gates recovery.
            if (not cresult.get('boot_match') or not cresult.get('transport_ok') or
                    cresult.get('truncated')):
                raise RuntimeError('cycles-export transport/boot/framing failed or a '
                                   'file was truncated; refusing seal and recovery to '
                                   'preserve device RAM evidence')
        return invoke(active, label, script, network_status=network_status)

    globals_['invoke'] = invoke_with_supplicant_log
    return prepared


def prepare_with_c2(candidate):
    prepared = SCAN.prepare(candidate)
    if C2_SCRIPT:
        globals_ = prepared['execute'].__globals__
        # Phase C3: the join script's wait grows to 100 ticks (the driver's 60 s
        # data phase with the bounded data checks inside it, then the teardown).
        # The two-lifetime join's wall is <= 300 s plus up to ~10 s control-socket
        # readiness; the host phase budget must cover the whole admitted device run.
        globals_['BUDGETS']['passive-scan'] = (330, 262144)
        prepared['claim']['phase_budgets']['passive-scan']['seconds'] = 330
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
    # Runtime 32 is the supplicant-owned C2+C3 session with the private log export.
    if not C2_SCRIPT:
        parser.exit(2, 'runtime 32 requires the PSK-bound C2 join script\n')
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
    classify_mod = runpy.run_path(str(HERE / 'classify-join.py'))
    join = classify_mod['classify']
    classify_lifetimes = classify_mod['classify_lifetimes']
    deferred = json.loads((ROOT / 'deferred-start-result.json').read_bytes())
    complete = deferred.get('preservation', {}).get('log_complete') is True
    kmsg = (ROOT / 'kmsg.log').read_bytes() if complete else b''
    combined['join'] = join(kmsg) if complete else {'bounded_join_pass': False}
    session_verified = bool(complete and deferred.get('regression_pass') and deferred.get('recovery_confirmed'))
    combined['join']['session_verified'] = session_verified
    # Runtime 33: the two-lifetime verdict is the per-lifetime classification (two healthy
    # bounded data-path joins, one scan each), not the single-lifetime classify() of the
    # whole log (which sees two of everything and does not pass).
    combined['lifetimes'] = classify_lifetimes(kmsg) if complete else {'two_lifetime_pass': False, 'lifetimes': 0}
    verdict = bool(combined['lifetimes'].get('two_lifetime_pass') and session_verified)
    if C2_SCRIPT:
        combined['c2'] = c2_result(combined['join'], session_verified)
        if WIFI_SSH_RECEIPT is not None:
            combined['c3'] = c3_result(combined['join'], combined['c2'], combined['lifetimes'])
            verdict = combined['c3']['c3_session_pass']
    with (ROOT / 'phase-b-session-result.json').open('x') as stream:
        stream.write(json.dumps(combined, indent=2, sort_keys=True) + '\n')
    if C2_SCRIPT:
        # The inherited single-scan rc (SCAN.main) sees a two-lifetime run as two
        # scans and eight tuning samples and does not represent it, so it must not
        # force a healthy two-lifetime result to exit 1. The two-cycle lifetime /
        # C3 classifier above is authoritative; session health (transport,
        # regression, recovery) is already folded into the verdict through
        # session_verified. A hard parser/setup error (rc == 2) still fails.
        return rc if rc == 2 else (0 if verdict else 1)
    return rc or (0 if verdict else 1)


def c3_result(join, c2, lifetimes):
    """The two-lifetime C3 result: the custodian's aggregate laptop-wifi-ssh receipt
    (per-cycle statuses, the boot it was bound to and all_pass; never an address) read from
    GEMINI_WIFI_SSH_RECEIPT, required to name the session's boot, and the two-lifetime C3
    conjunction (the kernel two-lifetime pass, the doubled supplicant handshake, both host
    acknowledgments). A missing, malformed or foreign receipt is recorded and fails; nothing
    is retried.
    """
    receipt = None
    try:
        loaded = json.loads(WIFI_SSH_RECEIPT.read_bytes())
        if (isinstance(loaded, dict) and isinstance(loaded.get('boot_id'), str) and
                isinstance(loaded.get('cycles'), list)):
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
    # The two-lifetime verdict is derived from the authored join-twice.sh stdout grammar
    # plus the inherited userspace transport/scan conjunction.
    phase = ROOT / 'passive-scan-userspace.json'
    userspace = json.loads(phase.read_bytes()) if phase.is_file() else {}
    stdout = ROOT / 'passive-scan/stdout.txt'
    device = C2['two_lifetime_fields'](stdout.read_bytes() if stdout.is_file() else b'')
    return {'wifi_ssh': receipt, 'wifi_ssh_boot_bound': bound,
            'c3_session_pass': bool(bound and C2['c3_two_lifetime_pass'](
                lifetimes, device, log, userspace, join.get('session_verified'), receipt))}


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
