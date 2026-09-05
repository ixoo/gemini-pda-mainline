#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixed authenticated baseline finishing steps and independent log parsing."""
import base64
import hashlib
import re

RELEASE = '7.1.3-gemini-mt6797-pwrap-reset'
UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
SHA = re.compile(r'[0-9a-f]{64}')
LIMIT = 2097152
REBOOT_SHA = '3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fields(raw):
    result = {}
    for line in raw.decode('ascii').splitlines():
        key, sep, value = line.partition('=')
        require(sep and key and key not in result and value == value.strip(), 'field framing')
        result[key] = value
    return result


def identity_script(candidate, boot):
    require(UUID.fullmatch(boot), 'boot ID')
    lines = ['BB=/bin/busybox', 'export LC_ALL=C', 'set -eu',
             f'[ "$($BB uname -r)" = {RELEASE} ]',
             f'[ "$($BB cat /proc/sys/kernel/random/boot_id)" = {boot} ]',
             f'[ "$($BB cat /run/a53/boot-id)" = {boot} ]',
             'for pair in online:0-7 offline:8-9 possible:0-9 present:0-9; do',
             '  [ "$($BB cat /sys/devices/system/cpu/${pair%:*})" = "${pair#*:}" ]', 'done']
    for member in ('init', 'bin/busybox', 'bin/reboot', 'bin/kmsg-capture', 'bin/kmsg-seal'):
        expected = candidate['members'][member]['sha256']
        require(SHA.fullmatch(expected), 'member hash')
        lines.extend([f'value=$($BB sha256sum /{member})', f'[ "${{value%% *}}" = {expected} ]'])
    require(candidate['members']['bin/reboot']['sha256'] == REBOOT_SHA, 'native reboot changed')
    return '\n'.join(lines) + '\n'


def probe_script(candidate, boot):
    return (identity_script(candidate, boot) + f"$BB printf 'authenticated_boot_id={boot}\\n'\n").encode()


def ram_guard_script():
    """Refuse before creating either claim unless the visible paths remain RAM."""
    return r'''
[ -d /run ]
[ ! -L /run ]
[ -d /run/a53 ]
[ ! -L /run/a53 ]
[ "$($BB awk 'END {print NR}' /proc/swaps)" = 1 ]
[ "$($BB awk '$2 == "/run" {n++; if ($3 == "tmpfs") t++} END {print n+0 ":" t+0}' /proc/mounts)" = 1:1 ]
[ "$($BB awk 'index($2, "/run/") == 1 {n++} END {print n+0}' /proc/mounts)" = 0 ]
[ "$($BB awk '$2 == "/" {n++; if ($3 == "rootfs" || $3 == "tmpfs" || $3 == "ramfs") r++} END {print n+0 ":" r+0}' /proc/mounts)" = 1:1 ]
[ "$($BB stat -c '%u:%g:%a' /run)" = 0:0:700 ]
[ "$($BB stat -c '%u:%g:%a' /run/a53)" = 0:0:700 ]
'''


def seal_script(candidate, boot):
    script = identity_script(candidate, boot) + ram_guard_script() + r'''
# Only RAM state and the identified logger are affected. Claim before signalling.
$BB mkdir /run/a53/log-seal-attempt
[ ! -e /run/a53/kmsg.status ]
[ ! -L /run/a53/kmsg.status ]
[ ! -e /run/a53/kmsg-exit ]
[ ! -L /run/a53/kmsg-exit ]
/bin/kmsg-seal
count=0
while [ ! -e /run/a53/kmsg-exit ]; do
  [ "$count" -lt 10 ] || exit 1
  $BB sleep 1
  count=$((count + 1))
done
[ -f /run/a53/kmsg-exit ]
[ ! -L /run/a53/kmsg-exit ]
[ "$($BB cat /run/a53/kmsg-exit)" = 0 ]
[ ! -e /run/a53/kmsg.status.partial ]
[ ! -L /run/a53/kmsg.status.partial ]
[ -f /run/a53/kmsg.status ]
[ ! -L /run/a53/kmsg.status ]
[ -f /run/a53/kmsg.log ]
[ ! -L /run/a53/kmsg.log ]
[ "$($BB wc -c </run/a53/kmsg.log)" -le 2097152 ]
$BB printf '__A53_LOG_SEAL_BEGIN__\n'
$BB printf 'logger_exit=0\n'
$BB cat /run/a53/kmsg.status
$BB printf '__A53_LOG_BASE64__\n'
$BB base64 /run/a53/kmsg.log
$BB printf '__A53_LOG_SEAL_END__\n'
'''
    return script.encode()


def parse_seal(raw, stderr, process):
    require(not stderr and process['exit_status'] == 0 and process['reason'] is None and
            process['stdin_complete'], 'log transport incomplete')
    begin, middle, end = b'__A53_LOG_SEAL_BEGIN__\n', b'__A53_LOG_BASE64__\n', b'__A53_LOG_SEAL_END__\n'
    require(len(raw) <= 3 * 1024 * 1024 and raw.startswith(begin) and raw.endswith(end) and
            all(raw.count(mark) == 1 for mark in (begin, middle, end)), 'log stream framing')
    status_raw, encoded = raw[len(begin):-len(end)].split(middle)
    require(encoded.endswith(b'\n'), 'base64 terminator')
    require(all(re.fullmatch(rb'[A-Za-z0-9+/=]{1,76}', line) for line in encoded.splitlines()), 'base64 lines')
    log = base64.b64decode(b''.join(encoded.splitlines()), validate=True)
    value = classify_log(log, status_raw)
    return log, status_raw, value


def classify_log(log, status_raw):
    status = fields(status_raw)
    exact = {'logger_exit': '0', 'schema': 'gemini-kmsg-v1', 'sealed': 'yes', 'result': 'pass',
             'reason': 'sealed-on-sigterm', 'first_seq': '0', 'byte_limit': str(LIMIT), 'deadline_ms': '600000'}
    numeric = {'last_seq', 'records', 'bytes', 'elapsed_ms'}
    require(set(status) == set(exact) | numeric and all(status[k] == v for k, v in exact.items()),
            'logger did not seal successfully')
    require(all(re.fullmatch(r'0|[1-9][0-9]*', status[k]) for k in numeric), 'log numeric framing')
    require(0 < len(log) <= LIMIT and int(status['bytes']) == len(log) and
            int(status['elapsed_ms']) < 600000 and log.endswith(b'\n') and b'\0' not in log, 'log bounds')
    count = 0
    for line in log.splitlines(keepends=True):
        if line.startswith(b' '):
            require(count > 0, 'orphan kmsg metadata')
            continue
        match = re.fullmatch(rb'([0-9]+),([0-9]+),([0-9]+),([\x21-\x7e]+);[^\n]*\n', line)
        require(match is not None, 'kmsg record framing')
        priority, sequence, timestamp, flags = match.groups()
        require(int(priority) <= 2047 and int(sequence) == count and int(timestamp) <= 2**64 - 1 and
                not flags.startswith(b','), 'kmsg sequence/header')
        count += 1
    require(count > 0 and int(status['records']) == count and int(status['last_seq']) == count - 1,
            'kmsg record count')
    return {'classification': 'complete-log-through-seal', 'records': count, 'bytes': len(log),
            'sha256': digest(log), 'status_sha256': digest(status_raw), 'coverage': 'sequence-zero-through-explicit-seal'}


def recovery_script(candidate, boot):
    script = identity_script(candidate, boot) + ram_guard_script()
    script += f'''$BB mkdir /run/a53/native-recovery-attempt
$BB printf '__A53_NATIVE_RECOVERY_BEGIN__\\nboot_id={boot}\\nreboot_sha256={REBOOT_SHA}\\nrequest_count=1\\npartition_access=none\\nsync_requested=no\\n__A53_NATIVE_RECOVERY_END__\\n'
/bin/reboot
exit 94
'''
    return script.encode()


def parse_recovery_request(raw, process, boot):
    expected = (f'__A53_NATIVE_RECOVERY_BEGIN__\nboot_id={boot}\nreboot_sha256={REBOOT_SHA}\n'
                'request_count=1\npartition_access=none\nsync_requested=no\n__A53_NATIVE_RECOVERY_END__\n').encode()
    require(raw == expected and process['stdin_complete'] and process['reason'] is None and
            process['exit_status'] == 255, 'native request/SSH disconnect unconfirmed')
    return {'classification': 'native-recovery-requested', 'boot_id': boot, 'request_count': 1,
            'recovery_confirmed': False}


GEMIAN_PROBE = b'''set -eu
printf 'kernel=%s\narchitecture=%s\nboot_id=%s\n' "$(uname -r)" "$(uname -m)" "$(cat /proc/sys/kernel/random/boot_id)"
'''


def parse_gemian(raw, stderr, process, previous, mainline):
    require(not stderr and process['exit_status'] == 0 and process['reason'] is None and
            process['stdin_complete'], 'known-good transport')
    values = fields(raw)
    require(set(values) == {'kernel', 'architecture', 'boot_id'} and values['kernel'] == '3.18.41+' and
            values['architecture'] == 'aarch64' and UUID.fullmatch(values['boot_id']) and
            values['boot_id'] not in (previous, mainline), 'changed-ID Gemian unconfirmed')
    return {'classification': 'changed-ID-Gemian', 'boot_id': values['boot_id']}
