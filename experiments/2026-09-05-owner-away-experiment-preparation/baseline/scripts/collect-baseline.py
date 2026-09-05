#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One admitted authenticated baseline observation; default is offline dry-run.

See ../COLLECT_BASELINE.md for the admission/custody and evidence contract.
There is no configurable remote command, address, credential path or retry.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import selectors
import signal
import stat
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
HISTORICAL = REPO / 'experiments/2026-09-04-mt6797-pwrap-reset-serviceability/scripts'
SOURCE_PINS = {
    HISTORICAL / 'remote_observe.sh': 'bfa7b11a355263f181285b12d99a07c1ca71ac6b8f13570730da7783937e9fe4',
    HISTORICAL / 'classify_observation.py': 'f628143d6a70fdda8c6da5171c69e91647a51eb3cb65fa1577d2487540cb1ca6',
    HERE / 'deployment_receipt.py': 'a2dc643ddedf5c9c93ede43598208cafd17242fccbb45db6ddaf078f30ae6f23',
}
SHA = re.compile(r'[0-9a-f]{64}')
UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
STDOUT_LIMIT = 131072
STDERR_LIMIT = 16384
TOTAL_SECONDS = 45
BEGIN = '__A53_BASELINE_V1_BEGIN__'
PRE_END = '__A53_PREFLIGHT_END__'
POST_BEGIN = '__A53_POSTFLIGHT_BEGIN__'
END = '__A53_BASELINE_V1_END__'
MEMBERS = {
    'init_sha256': 'init', 'busybox_sha256': 'bin/busybox', 'reboot_sha256': 'bin/reboot',
    'admin_shell_sha256': 'bin/admin-shell', 'usb_auth_sha256': 'bin/usb-auth',
    'console_status_sha256': 'bin/console-status', 'dropbear_sha256': 'bin/dropbear',
    'inittab_sha256': 'etc/inittab', 'map_sha256': 'etc/gemini-us.bkeymap',
    'map_verifier_sha256': 'bin/console-keymap-verify',
    'unicode_helper_sha256': 'bin/console-unicode-mode',
    'kmsg_helper_sha256': 'bin/kmsg-capture', 'keyboard_helper_sha256': 'bin/keyboard-observe',
    'kmsg_seal_helper_sha256': 'bin/kmsg-seal',
}
MAP_SHA = '02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c'
MAP_RESULT = ('keymap_readback=verified tables=8 payload_entries=1024 kernel_entries=2048 '
              'high_halves=K_HOLE table3=K_ALLOCATED undeclared_tables=K_NOSUCHMAP unicode_mode=K_UNICODE')
# Inventory is intentionally stricter than the reused historical classifier.
HISTORY_KEYS = set('''kernel_release architecture boot_id cpu_possible cpu_present cpu_online cpu_offline
pwrap_dt_resets_hex pwrap_driver pwrap_bind_count mt6351_core_bind_count mt6351_regulator_bind_count
mmc_driver mmc_bind_count regulator_count vemc_3v3_count vio18_count mmc_card_count mmc_card_type
mmcblk0_present mmcblk0_partition_count mmcblk0_sectors config_pwrap config_mt6397
config_mt6351_regulator config_mmc_mtk config_kunit_disabled config_thermal_disabled
config_cpufreq_disabled config_cpuidle_disabled config_suspend_disabled pwrap_initcall_success_count
pmic_initcall_success_count mt6351_regulator_success_count mmc_initcall_success_count mmc_card_log_count
pwrap_error_count mmc_error_count thermal_zone_count cpufreq_policy_count device_partition_reads
device_storage_writes sysfs_write_request cpu_trigger_request load_request thermal_value_read reboot_request'''.split())


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def no_duplicates(pairs):
    values = {}
    for key, value in pairs:
        require(key not in values, 'duplicate JSON field')
        values[key] = value
    return values


def regular(path, limit, private=True):
    path = Path(path)
    for component in (path, *path.parents):
        require(not component.is_symlink(), 'symlink input path')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, 'input type/size')
        if private:
            require(stat.S_IMODE(info.st_mode) == 0o600 and info.st_uid == os.getuid(), 'private input permissions')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        require(len(data) <= limit, 'input grew beyond size limit')
        return data
    finally:
        os.close(fd)


def directory(path):
    for component in (path, *path.parents):
        require(not component.is_symlink(), 'symlink directory')
    require(path.is_dir() and stat.S_IMODE(path.stat().st_mode) == 0o700 and
            path.stat().st_uid == os.getuid(), 'private directory permissions')


def ignored(repo, path):
    require(path.is_relative_to(repo / 'artifacts'), 'input is outside ignored artifacts')
    result = subprocess.run(['/usr/bin/git', '-C', str(repo), 'check-ignore', '-q', '--', str(path)],
                            env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}, timeout=5, capture_output=True)
    require(result.returncode == 0, 'input is not Git-ignored')


def source_tools():
    for path, expected in SOURCE_PINS.items():
        require(sha(regular(path, 65536, private=False)) == expected, 'historical source changed')
    return runpy.run_path(str(HISTORICAL / 'classify_observation.py'))


def prepare(repo, admission_path, deployment_path):
    """Read and validate all inputs without creating state or contacting SSH."""
    source_tools()
    repo = repo.resolve(strict=True)
    admission_path, deployment_path = map(lambda p: Path(p).absolute(), (admission_path, deployment_path))
    for path in (admission_path, deployment_path):
        ignored(repo, path)
    admission_raw = regular(admission_path, 16384)
    admission = json.loads(admission_raw, object_pairs_hook=no_duplicates)
    fields = {'schema', 'experiment', 'action', 'admission_id', 'candidate_sha256',
              'candidate_manifest_sha256', 'deployment_receipt_sha256', 'collector_sha256',
              'custodian_role', 'custody_handoff_sha256', 'custody_exclusive',
              'physical_selection_confirmed', 'no_other_device_operations', 'observation_budget'}
    require(set(admission) == fields, 'admission inventory')
    require(admission['schema'] == 1 and admission['experiment'] == 'a53-authenticated-baseline' and
            admission['action'] == 'first-baseline-observation', 'admission scope')
    require(isinstance(admission['admission_id'], str) and UUID.fullmatch(admission['admission_id']), 'admission ID')
    for name in ('candidate_sha256', 'candidate_manifest_sha256', 'deployment_receipt_sha256',
                 'collector_sha256', 'custody_handoff_sha256'):
        require(isinstance(admission[name], str) and SHA.fullmatch(admission[name]), 'admission digest')
    require(admission['collector_sha256'] == sha(Path(__file__).read_bytes()), 'collector revision differs from admission')
    require(isinstance(admission['custodian_role'], str) and
            re.fullmatch(r'[A-Za-z][A-Za-z0-9 _-]{0,63}', admission['custodian_role']), 'custodian role')
    require(all(admission[k] is True for k in ('custody_exclusive', 'physical_selection_confirmed',
                                             'no_other_device_operations')) and
            type(admission['observation_budget']) is int and admission['observation_budget'] == 1, 'custody/budget unconfirmed')
    candidate_dir = repo / 'artifacts/a53-authenticated/candidates' / ('candidate-' + admission['candidate_sha256'])
    keys = repo / 'artifacts/credentials/a53-auth'
    for path in (candidate_dir, keys):
        directory(path)
        ignored(repo, path)
    candidate_raw = regular(candidate_dir / 'candidate.json', 2097152)
    require(sha(candidate_raw) == admission['candidate_manifest_sha256'], 'candidate manifest identity')
    candidate = json.loads(candidate_raw, object_pairs_hook=no_duplicates)
    require(candidate.get('schema') == 1 and candidate.get('experiment') == 'a53-authenticated-baseline' and
            candidate.get('secret_bearing') is True, 'candidate schema')
    for name in ('boot.img', 'boot2-padded.img', 'kernel.config'):
        value = candidate['files'][name]
        require(isinstance(value, str) and SHA.fullmatch(value), 'candidate file digest')
        data = regular(candidate_dir / name, 16777216)
        require(sha(data) == value, 'candidate file checksum')
        if name == 'boot2-padded.img':
            require(len(data) == 16777216, 'candidate padded size')
    require(candidate['files']['boot.img'] == admission['candidate_sha256'], 'candidate directory identity')
    for member in MEMBERS.values():
        record = candidate['members'][member]
        require(SHA.fullmatch(str(record.get('sha256', ''))) and type(record.get('size')) is int and
                0 < record['size'] <= 16777216 and stat.S_ISREG(int(record['mode'], 8)), 'candidate member identity')
    require(candidate['members']['etc/gemini-us.bkeymap']['sha256'] == MAP_SHA, 'candidate keymap changed')
    known = regular(keys / 'known_hosts', 8192)
    require(sha(known) == candidate['known_hosts_sha256'], 'known_hosts identity')
    fields = known.decode('ascii').split()
    require(len(fields) == 3 and fields[:2] == ['10.15.19.82', 'ssh-ed25519'] and known.endswith(b'\n') and
            len(known.splitlines()) == 1, 'known_hosts must pin only the fixed USB target')
    blob = base64.b64decode(fields[2], validate=True)
    require(blob[:19] == b'\0\0\0\x0bssh-ed25519\0\0\0\x20' and len(blob) == 51, 'known_hosts Ed25519 shape')
    require(regular(keys / 'admin', 16384), 'empty administrator key')
    authorized = regular(keys / 'authorized_keys', 8192)
    require(sha(authorized) == candidate['members']['root/.ssh/authorized_keys']['sha256'], 'administrator authorization identity')
    deployment_raw = regular(deployment_path, 16384)
    require(sha(deployment_raw) == admission['deployment_receipt_sha256'], 'deployment receipt identity')
    adapter = runpy.run_path(str(HERE / 'deployment_receipt.py'))
    recovery_id = adapter['receipt'](deployment_raw.decode('ascii'), candidate['files']['boot2-padded.img'],
                                     admission['candidate_manifest_sha256'])
    require(UUID.fullmatch(recovery_id), 'deployment recovery boot ID')
    return {'repo': repo, 'candidate': candidate, 'candidate_raw': candidate_raw,
            'candidate_dir': candidate_dir, 'keys': keys, 'admission': admission,
            'admission_raw': admission_raw, 'deployment_raw': deployment_raw, 'recovery_id': recovery_id}


def remote_script(prepared):
    """Only fixed read-only commands plus the exact historical script bytes."""
    candidate = prepared['candidate']
    lines = ['#!/bin/busybox sh', 'set -u', 'export LC_ALL=C', 'BB=/bin/busybox',
             f"$BB printf '%s\\n' '{BEGIN}'",
             "check_hash() {",
             '  actual=$($BB sha256sum "$1") || exit 1',
             '  actual=${actual%% *}', '  [ "$actual" = "$2" ] || exit 1',
             '  $BB printf \'%s=%s\\n\' "$3" "$actual"', '}',
             f"$BB printf '%s\\n' 'expected_candidate_sha256={prepared['admission']['candidate_sha256']}'"]
    for field, member in MEMBERS.items():
        lines.append(f"check_hash '/{member}' '{candidate['members'][member]['sha256']}' '{field}'")
    lines += [
        'boot_before=$($BB cat /proc/sys/kernel/random/boot_id) || exit 1',
        'init_boot=$($BB cat /run/a53/boot-id) || exit 1',
        '[ "$boot_before" = "$init_boot" ] || exit 1',
        '$BB printf \'boot_id_before=%s\\ninit_boot_id=%s\\n\' "$boot_before" "$init_boot"',
        'live_config=$($BB zcat /proc/config.gz | $BB sha256sum) || exit 1',
        'live_config=${live_config%% *}',
        f"[ \"$live_config\" = '{candidate['files']['kernel.config']}' ] || exit 1",
        '$BB printf \'live_config_sha256=%s\\n\' "$live_config"',
        'console=$($BB cat /run/a53/console.status) || exit 1',
        '[ "$console" = console=ready ] || exit 1',
        '$BB printf \'console_status=ready\\n\'',
        'active=$($BB cat /sys/class/tty/tty0/active) || exit 1',
        '[ "$active" = tty1 ] || exit 1', '$BB printf \'active_vt=tty1\\n\'',
        "consoles=$($BB awk '$1 == \"tty0\" || $1 == \"tty1\" { n++ } END { print n+0 }' /proc/consoles) || exit 1",
        '[ "$consoles" = 0 ] || exit 1', '$BB printf \'kernel_vt_console_count=0\\n\'',
        'map_result=$(/bin/console-keymap-verify --verify /etc/gemini-us.bkeymap) || exit 1',
        f"[ \"$map_result\" = '{MAP_RESULT}' ] || exit 1", '$BB printf \'map_verify_before=pass\\n\'',
        'matrix=0; scanned=0',
        'for item in /sys/class/input/event*/device/name; do',
        '  [ -r "$item" ] || continue', '  scanned=$((scanned + 1))',
        '  [ "$scanned" -le 256 ] || exit 1', '  name=$($BB cat "$item") || exit 1',
        '  [ "$name" != keyboard-matrix ] || matrix=$((matrix + 1))', 'done',
        '[ "$matrix" = 1 ] || exit 1', '$BB printf \'matrix_input_count=1\\n\'',
        # These historical auto-start paths must be absent, including dangling links.
        'for path in /bin/x-probe /bin/input-event-capture /bin/usb-shell /bin/usb-net /bin/local-shell; do',
        '  [ ! -e "$path" ] && [ ! -L "$path" ] || exit 1', 'done',
        '$BB printf \'historical_auto_observers=absent\\n\'',
        f"$BB printf '%s\\n' '{PRE_END}'", '(',
    ]
    prefix = ('\n'.join(lines) + '\n').encode('ascii')
    original = regular(HISTORICAL / 'remote_observe.sh', 65536, private=False)
    postfix = [')', f"$BB printf '%s\\n' '{POST_BEGIN}'",
               'boot_after=$($BB cat /proc/sys/kernel/random/boot_id) || exit 1',
               '[ "$boot_after" = "$boot_before" ] || exit 1',
               '$BB printf \'boot_id_after=%s\\n\' "$boot_after"',
               'online=$($BB cat /sys/devices/system/cpu/online) || exit 1',
               'offline=$($BB cat /sys/devices/system/cpu/offline) || exit 1',
               '[ "$online" = 0-7 ] && [ "$offline" = 8-9 ] || exit 1',
               '$BB printf \'cpu_online_after=0-7\\ncpu_offline_after=8-9\\n\'',
               'map_result=$(/bin/console-keymap-verify --verify /etc/gemini-us.bkeymap) || exit 1',
               f"[ \"$map_result\" = '{MAP_RESULT}' ] || exit 1", '$BB printf \'map_verify_after=pass\\n\'',
               'console=$($BB cat /run/a53/console.status) || exit 1',
               '[ "$console" = console=ready ] || exit 1', '$BB printf \'console_status_after=ready\\n\'',
               'active=$($BB cat /sys/class/tty/tty0/active) || exit 1',
               '[ "$active" = tty1 ] || exit 1', '$BB printf \'active_vt_after=tty1\\n\'',
               "consoles=$($BB awk '$1 == \"tty0\" || $1 == \"tty1\" { n++ } END { print n+0 }' /proc/consoles) || exit 1",
               '[ "$consoles" = 0 ] || exit 1', '$BB printf \'kernel_vt_console_count_after=0\\n\'',
               f"$BB printf '%s\\n' '{END}'"]
    return prefix + original + b'\n' + ('\n'.join(postfix) + '\n').encode('ascii')


def ssh_command(keys, executable='/usr/bin/ssh'):
    options = ['BatchMode=yes', 'IdentitiesOnly=yes', 'IdentityAgent=none',
               'PreferredAuthentications=publickey', 'PasswordAuthentication=no',
               'KbdInteractiveAuthentication=no', 'NumberOfPasswordPrompts=0',
               'StrictHostKeyChecking=yes', f'UserKnownHostsFile={keys / "known_hosts"}',
               'GlobalKnownHostsFile=/dev/null', 'HostKeyAlgorithms=ssh-ed25519',
               'PubkeyAcceptedAlgorithms=ssh-ed25519', 'UpdateHostKeys=no', 'VerifyHostKeyDNS=no',
               'CanonicalizeHostname=no', 'ProxyCommand=none', 'ProxyJump=none',
               'ControlMaster=no', 'ControlPath=none', 'ControlPersist=no',
               'ClearAllForwardings=yes', 'ForwardAgent=no', 'ForwardX11=no',
               'ConnectionAttempts=1', 'ConnectTimeout=10', 'ServerAliveInterval=0',
               'LogLevel=ERROR', 'EscapeChar=none']
    return [str(executable), '-F', '/dev/null', '-T', '-p', '22', '-i', str(keys / 'admin')] + \
        [item for option in options for item in ('-o', option)] + ['root@10.15.19.82', '/bin/busybox sh -s']


def write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def private_root(path):
    if not path.exists():
        private_root(path.parent)
        path.mkdir(mode=0o700)
    directory(path)


def run_once(command, script, attempt, timeout=TOTAL_SECONDS, *,
             stdout_limit=STDOUT_LIMIT, stderr_limit=STDERR_LIMIT):
    """Bound one local SSH process group and stream private evidence to disk."""
    reason = None
    interrupted = []
    handlers = {}
    process = None
    streams = {}
    selector = selectors.DefaultSelector()
    sent = 0
    counts = {'stdout': 0, 'stderr': 0}
    start = time.monotonic()
    deadline = start + timeout
    require(0 < stdout_limit <= 16777216 and 0 < stderr_limit <= 16777216,
            'invalid fixed caller stream budget')
    try:
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            handlers[signum] = signal.signal(signum, lambda number, _frame: interrupted.append(number))
        for name in counts:
            fd = os.open(attempt / (name + '.txt'), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            streams[name] = os.fdopen(fd, 'wb', buffering=0)
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}, start_new_session=True)
        for file, name, event in ((process.stdin, 'stdin', selectors.EVENT_WRITE),
                                  (process.stdout, 'stdout', selectors.EVENT_READ),
                                  (process.stderr, 'stderr', selectors.EVENT_READ)):
            os.set_blocking(file.fileno(), False)
            selector.register(file, event, name)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if interrupted:
                reason = 'interrupted'
                break
            # Keep termination/reaping inside the one outer budget.
            if remaining <= min(1.0, timeout / 4):
                reason = 'outer-timeout'
                break
            for key, _event in selector.select(min(0.1, remaining)):
                name, file = key.data, key.fileobj
                if name == 'stdin':
                    try:
                        sent += os.write(file.fileno(), script[sent:sent + 4096])
                    except BlockingIOError:
                        continue
                    except (BrokenPipeError, ConnectionResetError):
                        selector.unregister(file)
                        file.close()
                        if sent != len(script):
                            reason = 'stdin-closed'
                        continue
                    if sent == len(script):
                        selector.unregister(file)
                        file.close()
                    continue
                try:
                    data = os.read(file.fileno(), 4096)
                except BlockingIOError:
                    continue
                if not data:
                    selector.unregister(file)
                    file.close()
                    continue
                limit = stdout_limit if name == 'stdout' else stderr_limit
                allowed = max(0, limit - counts[name])
                selected = data[:allowed]
                require(streams[name].write(selected) == len(selected), 'short private evidence write')
                counts[name] += min(len(data), allowed)
                if len(data) > allowed:
                    reason = name + '-limit'
                    break
            if reason:
                break
        if reason:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=max(0.01, min(0.25, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            reason = reason or 'process-did-not-exit'
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
        reason = reason or ('interrupted' if interrupted else None)
        return {'exit_status': process.returncode, 'reason': reason,
                'stdin_complete': sent == len(script), **{k + '_bytes': v for k, v in counts.items()},
                'elapsed_seconds': round(time.monotonic() - start, 3)}
    finally:
        if process is not None:
            # Reap descendants too if the leader exited while leaving a pipe open.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if process.poll() is None:
                process.wait(timeout=1)
            for file in (process.stdin, process.stdout, process.stderr):
                if file and not file.closed:
                    file.close()
        selector.close()
        for stream in streams.values():
            os.fsync(stream.fileno())
            stream.close()
        for signum, previous in handlers.items():
            signal.signal(signum, previous)


def fields(lines):
    values = {}
    for line in lines:
        key, sep, value = line.partition('=')
        require(sep and key not in values and value == value.strip(), 'malformed/duplicate frame field')
        values[key] = value
    return values


def classify_capture(prepared, stdout, stderr, process):
    result = {'classification': 'inconclusive', 'readiness': 'not-established',
              'requires_separate': ['authentication-negative', 'log-seal', 'owner-console-acceptance', 'recovery'],
              'ssh_attempts': 1}
    if len(stdout) > STDOUT_LIMIT or len(stderr) > STDERR_LIMIT:
        result['reason'] = 'stream-size-limit'
        return result
    for name, data in (('stdout', stdout), ('stderr', stderr)):
        if name + '_bytes' in process and process[name + '_bytes'] != len(data):
            result['reason'] = 'stream-count-mismatch'
            return result
    if process['reason'] or process['exit_status'] != 0 or not process['stdin_complete'] or stderr:
        result['reason'] = process['reason'] or ('ssh-nonzero' if process['exit_status'] != 0 else
                                               'unexpected-stderr-or-incomplete-stdin')
        return result
    try:
        text = stdout.decode('ascii')
        require(text.startswith(BEGIN + '\n') and text.endswith(END + '\n'), 'outer frame/trailing data')
        for marker in (BEGIN, PRE_END, POST_BEGIN, END):
            require(text.count(marker) == 1, 'outer marker count')
        before, rest = text[len(BEGIN) + 1:].split(PRE_END + '\n')
        history, after = rest.split(POST_BEGIN + '\n')
        post = fields(after[:-len(END + '\n')].splitlines())
        pre = fields(before.splitlines())
        expected = {field: prepared['candidate']['members'][member]['sha256'] for field, member in MEMBERS.items()}
        expected.update(expected_candidate_sha256=prepared['admission']['candidate_sha256'],
                        live_config_sha256=prepared['candidate']['files']['kernel.config'], console_status='ready',
                        active_vt='tty1', kernel_vt_console_count='0', map_verify_before='pass',
                        matrix_input_count='1', historical_auto_observers='absent')
        require(set(pre) == set(expected) | {'boot_id_before', 'init_boot_id'} and
                all(pre[k] == v for k, v in expected.items()), 'preflight mismatch')
        require(UUID.fullmatch(pre['boot_id_before']) and pre['boot_id_before'] == pre['init_boot_id'] !=
                prepared['recovery_id'], 'boot attribution')
        expected_post = {'boot_id_after': pre['boot_id_before'], 'cpu_online_after': '0-7',
                         'cpu_offline_after': '8-9', 'map_verify_after': 'pass',
                         'console_status_after': 'ready', 'active_vt_after': 'tty1',
                         'kernel_vt_console_count_after': '0'}
        require(post == expected_post, 'postflight mismatch')
        lines = history.splitlines()
        require(history.count('__GEMINI_PWRAP_SERVICEABILITY_BEGIN__') ==
                history.count('__GEMINI_PWRAP_SERVICEABILITY_END__') == 1, 'historical marker count')
        require(lines[0] == '__GEMINI_PWRAP_SERVICEABILITY_BEGIN__' and
                lines[-1] == '__GEMINI_PWRAP_SERVICEABILITY_END__', 'historical frame bounds')
        require(lines.count('dmesg_excerpt_begin') == lines.count('dmesg_excerpt_end') == 1,
                'historical log delimiters')
        first, last = lines.index('dmesg_excerpt_begin'), lines.index('dmesg_excerpt_end')
        require(first < last and all(line.startswith('log: ') and '=' not in line for line in lines[first + 1:last]),
                'historical log framing')
        values = fields(lines[1:first] + lines[last + 1:-1])
        require(set(values) == HISTORY_KEYS, 'historical field inventory')
        require(values['boot_id'] == pre['boot_id_before'], 'historical boot mismatch')
        legacy = source_tools()
        try:
            boot = legacy['classify'](history, prepared['recovery_id'])
        except legacy['Rejected'] as error:
            result.update(classification='baseline-observation-rejected', reason=str(error))
            return result
        result.update(classification='baseline-observation-only-pass', boot_id=boot,
                      identity_basis='verified-deployment-plus-live-kernel-config-and-initramfs-members')
    except (ValueError, KeyError, UnicodeError, IndexError) as error:
        result['reason'] = str(error)
    return result


def collect(prepared, execute=False, *, _ssh='/usr/bin/ssh', _timeout=TOTAL_SECONDS):
    script = remote_script(prepared)
    require(len(script) <= 65536, 'fixed script exceeds stdin budget')
    base = {'candidate_sha256': prepared['admission']['candidate_sha256'],
            'remote_script_sha256': sha(script), 'outer_timeout_seconds': TOTAL_SECONDS,
            'stdout_limit_bytes': STDOUT_LIMIT, 'stderr_limit_bytes': STDERR_LIMIT}
    if not execute:
        return {**base, 'classification': 'dry-run', 'network_access': 'none', 'attempt_created': False}
    os.umask(0o077)
    root = prepared['repo'] / 'artifacts/a53-authenticated/attempts'
    ignored(prepared['repo'], root)
    private_root(root)
    attempt = root / prepared['admission']['admission_id']
    attempt.mkdir(mode=0o700)  # Existing or interrupted attempts always refuse.
    # Claim is durably recorded before the first process/network operation.
    write_new(attempt / 'claim.json', (json.dumps({**base, 'budget': 'consumed', 'ssh_attempts_max': 1,
              'admission_id': prepared['admission']['admission_id'],
              'admission_sha256': sha(prepared['admission_raw']),
              'deployment_receipt_sha256': sha(prepared['deployment_raw']),
              'candidate_manifest_sha256': sha(prepared['candidate_raw']),
              'deployment_parser_sha256': sha((HERE / 'deployment_receipt.py').read_bytes()),
              'historical_sources': {str(p.relative_to(REPO)): d for p, d in SOURCE_PINS.items()}}, sort_keys=True) + '\n').encode())
    directory_fd = os.open(root, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    write_new(attempt / 'remote-observe.sh', script)
    write_new(attempt / 'admission.json', prepared['admission_raw'])
    write_new(attempt / 'deployment-summary.txt', prepared['deployment_raw'])
    write_new(attempt / 'candidate.json', prepared['candidate_raw'])
    directory_fd = os.open(attempt, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    try:
        # Recheck the fixed host pin immediately before invoking SSH.
        require(sha(regular(prepared['keys'] / 'known_hosts', 8192)) ==
                prepared['candidate']['known_hosts_sha256'], 'known_hosts changed before connection')
        process = run_once(ssh_command(prepared['keys'], _ssh), script, attempt, _timeout)
        stdout = regular(attempt / 'stdout.txt', STDOUT_LIMIT)
        stderr = regular(attempt / 'stderr.txt', STDERR_LIMIT)
        result = {**base, **classify_capture(prepared, stdout, stderr, process), 'process': process}
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result = {**base, 'classification': 'inconclusive', 'reason': type(error).__name__,
                  'budget': 'consumed', 'readiness': 'not-established'}
    write_new(attempt / 'result.json', (json.dumps(result, sort_keys=True, indent=2) + '\n').encode())
    manifest = ''.join(sha(path.read_bytes()) + '  ' + path.name + '\n' for path in sorted(attempt.iterdir()))
    write_new(attempt / 'SHA256SUMS', manifest.encode())
    return {**result, 'attempt': str(attempt.relative_to(prepared['repo']))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--deployment-summary', type=Path, required=True)
    parser.add_argument('--collect', action='store_true')
    args = parser.parse_args()
    try:
        prepared = prepare(REPO, args.admission, args.deployment_summary)
        result = collect(prepared, args.collect)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({'classification': 'refused', 'reason': str(error)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result['classification'] in ('dry-run', 'baseline-observation-only-pass') else 2


if __name__ == '__main__':
    raise SystemExit(main())
