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
# Exact stdout emitted by the wrapper identified above, before reboot(2).
REBOOT_ANNOUNCEMENT = b'Candidate AB: kernel restart requested now (BusyBox reboot -n -f).\n'


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
# Claim once, including failed/pre-exited loggers. Never restart an observer.
$BB mkdir /run/a53/log-seal-attempt
stop=preexisting-terminal
signal_attempts=0
signal_status=none
if [ ! -e /run/a53/kmsg.status ] && [ ! -L /run/a53/kmsg.status ] &&
   [ ! -e /run/a53/kmsg-exit ] && [ ! -L /run/a53/kmsg-exit ]; then
  signal_attempts=1
  if /bin/kmsg-seal; then signal_status=0; stop=signalled
  else signal_status=$?; stop=signal-failed; fi
fi
count=0
while [ ! -e /run/a53/kmsg-exit ] && [ ! -L /run/a53/kmsg-exit ]; do
  if [ "$count" -ge 10 ]; then
    [ "$stop" != signalled ] || stop=wait-timeout
    break
  fi
  $BB sleep 1 || break
  count=$((count + 1))
done
terminal_before_export=no
exit_path=/run/a53/kmsg-exit
if [ ! -L "$exit_path" ] && [ -f "$exit_path" ]; then
  expected_exit=$($BB stat -c '%d:%i' "$exit_path") || expected_exit=-
  if command exec 3<"$exit_path"; then
    held_exit=$($BB stat -Lc '%d:%i' /proc/self/fd/3) || held_exit=-
    exit_size=$($BB stat -Lc '%s' /proc/self/fd/3) || exit_size=-
    if [ "$expected_exit" != - ] && [ "$held_exit" = "$expected_exit" ] &&
       [ ! -L "$exit_path" ] && [ -f /proc/self/fd/3 ]; then
      case "$exit_size" in 2|3|4)
        encoded_exit=$($BB head -c 5 <&3 | $BB base64) || encoded_exit=invalid
        exit_value=$($BB printf '%s' "$encoded_exit" | $BB base64 -d) || exit_value=invalid
        case "$exit_value" in 0|[1-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])
          expected_encoding=$($BB printf '%s\n' "$exit_value" | $BB base64) || expected_encoding=invalid
          if [ "$encoded_exit" = "$expected_encoding" ] &&
             [ "$($BB stat -Lc '%s' /proc/self/fd/3)" = "$exit_size" ] &&
             [ ! -L "$exit_path" ] && [ "$($BB stat -c '%d:%i' "$exit_path")" = "$expected_exit" ]; then
            terminal_before_export=yes
          fi;;
        esac;;
      esac
    fi
  fi
  exec 3<&-
fi
$BB printf '__A53_LOG_EXPORT_BEGIN__\nschema=gemini-log-export-v2\nstop=%s\nsignal_attempts=%s\nsignal_status=%s\nterminal_before_export=%s\n__A53_LOG_EXPORT_FILES__\n' "$stop" "$signal_attempts" "$signal_status" "$terminal_before_export"
export_file() {
  name=$1; ceiling=$2; path=/run/a53/$name
  state=missing; before=-; after=-; read_status=none; encode_status=none
  stable=not-applicable; truncated=no; identity=-
  if [ -L "$path" ]; then state=symlink
  elif [ ! -e "$path" ]; then state=missing
  elif [ ! -f "$path" ]; then state=nonregular
  else
    state=unreadable
    identity=$($BB stat -c '%d:%i' "$path") || identity=-
    if command exec 3<"$path"; then
      # Read only a held regular descriptor matching the non-symlink source.
      held=$($BB stat -Lc '%d:%i' /proc/self/fd/3) || held=-
      if [ "$identity" != - ] && [ "$held" = "$identity" ] &&
         [ ! -L "$path" ] && [ -f /proc/self/fd/3 ]; then
        state=regular
        before=$($BB stat -Lc '%s' /proc/self/fd/3) || before=-
      else state=changed; fi
    fi
  fi
  $BB printf '__A53_LOG_FILE_BEGIN__\nname=%s\nstate=%s\nsize_before=%s\nlimit=%s\n__A53_LOG_FILE_BASE64__\n' "$name" "$state" "$before" "$ceiling"
  if [ "$state" = regular ]; then
    if (set +e; $BB head -c "$ceiling" <&3
        read_status=$?
        $BB printf '%s\n' "$read_status" >"/run/a53/log-seal-attempt/$name.read-exit") | $BB base64; then
      encode_status=0
    else encode_status=$?; fi
    read_status=$($BB cat "/run/a53/log-seal-attempt/$name.read-exit") || read_status=unknown
    after=$($BB stat -Lc '%s' /proc/self/fd/3) || after=-
    current=$($BB stat -c '%d:%i' "$path") || current=-
    stable=no
    if [ ! -L "$path" ] && [ "$current" = "$identity" ] && [ "$before" = "$after" ]; then stable=yes; fi
    case "$before:$after" in *[!0-9:]*|:*) truncated=unknown;;
      *) if [ "$before" -gt "$ceiling" ] || [ "$after" -gt "$ceiling" ]; then truncated=yes; fi;;
    esac
  fi
  exec 3<&-
  $BB printf '\n__A53_LOG_FILE_META__\nsize_after=%s\nread_status=%s\nencode_status=%s\nstable=%s\ntruncated=%s\n__A53_LOG_FILE_END__\n' "$after" "$read_status" "$encode_status" "$stable" "$truncated"
}
export_file kmsg.log 2097152
export_file kmsg.status 8192
export_file kmsg.status.partial 8192
export_file kmsg-exit 8192
$BB printf '__A53_LOG_EXPORT_END__\n'
'''
    return script.encode()


def parse_seal(raw, stderr, process):
    exported = parse_log_export(raw, stderr, process)
    require(exported['result']['classification'] == 'complete-log-through-seal',
            exported['result']['reason'])
    return exported['files']['kmsg.log'], b'logger_exit=0\n' + exported['files']['kmsg.status'], exported['result']['log']


EXPORT_FILES = {'kmsg.log': LIMIT, 'kmsg.status': 8192, 'kmsg.status.partial': 8192, 'kmsg-exit': 8192}


def parse_log_export(raw, stderr, process):
    """Retain parsed file prefixes even when framing/transport/log acceptance fails."""
    files, metadata = {}, {}
    result = {'classification': 'log-export-inconclusive', 'export_complete': False,
              'logger_terminal': False, 'preservation_complete': False,
              'terminal_before_export': False,
              'transport_complete': not stderr and type(process.get('exit_status')) is int and
              process.get('exit_status') == 0 and process.get('reason') is None and
              process.get('stdin_complete') is True, 'files': metadata, 'signal_attempts': None,
              'signal_status': None, 'stop': None, 'reason': 'export incomplete', 'log': None}
    try:
        require(len(raw) <= 3 * 1024 * 1024, 'export stream bound')
        begin, header_end = b'__A53_LOG_EXPORT_BEGIN__\n', b'__A53_LOG_EXPORT_FILES__\n'
        require(raw.startswith(begin) and raw.count(header_end) == 1, 'export header framing')
        header_raw, remainder = raw[len(begin):].split(header_end, 1)
        header = fields(header_raw)
        require(set(header) == {'schema', 'stop', 'signal_attempts', 'signal_status', 'terminal_before_export'} and
                header['schema'] == 'gemini-log-export-v2' and
                header['terminal_before_export'] in ('yes', 'no') and
                header['stop'] in ('preexisting-terminal', 'signalled', 'signal-failed', 'wait-timeout') and
                header['signal_attempts'] in ('0', '1'), 'export header fields')
        if header['signal_attempts'] == '0':
            require(header['stop'] == 'preexisting-terminal' and header['signal_status'] == 'none', 'terminal signal fields')
        else:
            require(re.fullmatch(r'0|[1-9][0-9]{0,2}', header['signal_status']) and
                    int(header['signal_status']) <= 255 and
                    ((header['stop'] in ('signalled', 'wait-timeout') and header['signal_status'] == '0') or
                     (header['stop'] == 'signal-failed' and header['signal_status'] != '0')), 'signal result fields')
        result.update(stop=header['stop'], signal_attempts=int(header['signal_attempts']), signal_status=header['signal_status'],
                      terminal_before_export=header['terminal_before_export'] == 'yes')
        for name, ceiling in EXPORT_FILES.items():
            file_begin, data_begin = b'__A53_LOG_FILE_BEGIN__\n', b'__A53_LOG_FILE_BASE64__\n'
            meta_begin, file_end = b'__A53_LOG_FILE_META__\n', b'__A53_LOG_FILE_END__\n'
            require(remainder.startswith(file_begin) and data_begin in remainder, 'file header incomplete')
            pre_raw, remainder = remainder[len(file_begin):].split(data_begin, 1)
            pre = fields(pre_raw)
            require(set(pre) == {'name', 'state', 'size_before', 'limit'} and pre['name'] == name and
                    pre['limit'] == str(ceiling) and pre['state'] in
                    ('regular', 'missing', 'symlink', 'nonregular', 'unreadable', 'changed'), 'file header fields')
            require(meta_begin in remainder, 'file data incomplete')
            encoded, remainder = remainder.split(meta_begin, 1)
            require(encoded.endswith(b'\n'), 'file data terminator')
            data = base64.b64decode(b''.join(encoded.splitlines()), validate=True)
            require(len(data) <= ceiling and encoded == base64.encodebytes(data) + b'\n', 'file base64 framing/bound')
            if pre['state'] == 'regular':
                files[name] = data
            else:
                require(not data, 'nonregular file exported data')
            require(file_end in remainder, 'file metadata incomplete')
            post_raw, remainder = remainder.split(file_end, 1)
            post = fields(post_raw)
            require(set(post) == {'size_after', 'read_status', 'encode_status', 'stable', 'truncated'}, 'file metadata fields')
            for value in (pre['size_before'], post['size_after']):
                require(value == '-' or re.fullmatch(r'0|[1-9][0-9]{0,19}', value), 'file size framing')
            if pre['state'] == 'regular':
                require(post['stable'] in ('yes', 'no') and post['truncated'] in ('yes', 'no', 'unknown') and
                        all(value == 'unknown' or (re.fullmatch(r'0|[1-9][0-9]{0,2}', value) and int(value) <= 255)
                            for value in (post['read_status'], post['encode_status'])), 'regular file metadata')
                if '-' not in (pre['size_before'], post['size_after']):
                    truncated = max(int(pre['size_before']), int(post['size_after'])) > ceiling
                    require(post['truncated'] == ('yes' if truncated else 'no'), 'truncation marker mismatch')
                else:
                    require(post['truncated'] == 'unknown', 'unknown size truncation marker')
                if post['stable'] == 'yes':
                    require(pre['size_before'] == post['size_after'] != '-', 'stable size mismatch')
                    if post['read_status'] == post['encode_status'] == '0':
                        require(len(data) == min(int(pre['size_before']), ceiling), 'captured byte count')
            else:
                require(pre['size_before'] == post['size_after'] == '-' and post['read_status'] == post['encode_status'] == 'none' and
                        post['stable'] == 'not-applicable' and post['truncated'] == 'no', 'absent file metadata')
            metadata[name] = {'state': pre['state'], 'size_before': pre['size_before'], **post,
                              'captured_bytes': len(data), 'sha256': digest(data) if pre['state'] == 'regular' else None}
        require(remainder == b'__A53_LOG_EXPORT_END__\n', 'export footer/trailing records')
        result['export_complete'] = True
        def full_file(name):
            item = metadata[name]
            return (item['state'] == 'regular' and item['stable'] == 'yes' and item['truncated'] == 'no' and
                    item['read_status'] == item['encode_status'] == '0')
        if full_file('kmsg-exit'):
            value = files['kmsg-exit']
            result['logger_terminal'] = bool(re.fullmatch(rb'(0|[1-9][0-9]{0,2})\n', value) and int(value) <= 255)
        if full_file('kmsg.status'):
            try:
                terminal = fields(files['kmsg.status'])
                numeric = {'first_seq', 'last_seq', 'records', 'bytes', 'elapsed_ms', 'byte_limit', 'deadline_ms'}
                valid = (set(terminal) == {'schema', 'sealed', 'result', 'reason'} | numeric and
                         terminal['schema'] == 'gemini-kmsg-v1' and terminal['sealed'] == 'yes' and
                         terminal['result'] in ('pass', 'failed') and re.fullmatch(r'[a-z][a-z-]{0,63}', terminal['reason']) and
                         all(re.fullmatch(r'0|[1-9][0-9]{0,19}', terminal[key]) for key in numeric))
                result['logger_terminal'] = result['logger_terminal'] or bool(valid)
            except (ValueError, UnicodeError):
                pass
        result['preservation_complete'] = bool(result['transport_complete'] and result['logger_terminal'] and
                                              result['terminal_before_export'] and
                                              full_file('kmsg.log') and all(item['state'] == 'missing' or full_file(name)
                                              for name, item in metadata.items()))
        require(result['transport_complete'], 'log transport incomplete')
        require(result['terminal_before_export'], 'logger termination was not proved before reading the log')
        require(result['stop'] == 'signalled' and result['signal_status'] == '0', 'logger was not explicitly sealed by this attempt')
        require(metadata['kmsg.status.partial']['state'] == 'missing', 'partial status remains')
        for name in ('kmsg.log', 'kmsg.status', 'kmsg-exit'):
            item = metadata[name]
            require(item['state'] == 'regular' and item['stable'] == 'yes' and item['truncated'] == 'no' and
                    item['read_status'] == item['encode_status'] == '0', 'incomplete logger file: ' + name)
        require(files['kmsg-exit'] == b'0\n', 'logger did not exit zero')
        result['log'] = classify_log(files['kmsg.log'], b'logger_exit=0\n' + files['kmsg.status'])
        result.update(classification='complete-log-through-seal', reason=None)
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        result['reason'] = str(error)
    return {'files': files, 'result': result}


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
    require(raw == expected + REBOOT_ANNOUNCEMENT, 'native request/wrapper output mismatch')
    require(process['stdin_complete'] and process['reason'] is None and
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
