#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Phase C2 session pieces for the host adapter: the fixed-phrase fields the
join script prints, the bounded private export of the complete supplicant log,
the same phrase counts derived from that export, and the session success
conjunction. No identifier, secret or log line is interpreted beyond fixed
phrase counts; the exported log stays in the private runtime root.
"""
import hashlib
import re

# The join script counts these fixed phrases; the keys are its own derivation
# (letters lowered; ':', ' ' and '-' to '_').
PHRASES = {'ctrl_event_scan_results': b'CTRL-EVENT-SCAN-RESULTS',
           'associated_with': b'Associated with',
           'wpa__key_negotiation_completed': b'WPA: Key negotiation completed',
           'ctrl_event_connected': b'CTRL-EVENT-CONNECTED',
           'ctrl_event_disconnected': b'CTRL-EVENT-DISCONNECTED'}
FIELDS = ('supplicant_exit', 'supplicant_log_bytes', 'channel40_ir_after_beacon', 'connect_exit', 'join_terminal')
LOG_PATH = '/tmp/mt6797-wifi-phase-b-1/wpa.log'
LOG_LIMIT = 2 * 1024 * 1024
BOOT_RE = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'


def is_c2_script(source):
    """True when the private bound script carries a PSK (never printed)."""
    return b'\nWPA_PSK_HEX=' in source


def body_fields(raw):
    """Supplicant fields from the framed body: counts and small integers only."""
    fields = {}
    for name in PHRASES:
        match = re.search(rb'^supplicant_' + name.encode() + rb'=(\d{1,6})$', raw, re.MULTILINE)
        fields['supplicant_' + name] = int(match[1]) if match else None
    for name in FIELDS:
        match = re.search(rb'^' + name.encode() + rb'=(\d{1,9})$', raw, re.MULTILINE)
        fields[name] = int(match[1]) if match else None
    fields['framed'] = b'__JOIN_BEGIN__\n' in raw and b'__JOIN_END__\n' in raw
    return fields


def phrase_counts(log):
    """The join script's fixed-phrase counts, recomputed from the exported log."""
    return {'supplicant_' + name: log.count(phrase) for name, phrase in PHRASES.items()}


def log_script(boot):
    """One bounded read-only export of the complete supplicant log, in RAM, after
    the join script has stopped the supplicant: identity before and after, the
    size before and after the copy, the supplicant process count, and no copy
    at all when the file is absent, not regular or over the bound. Nothing is
    written on the device.
    """
    if not re.fullmatch(BOOT_RE, boot):
        raise ValueError('boot identity is malformed')
    return ("#!/bin/sh\nset -u\nBB=/bin/busybox\nlog=" + LOG_PATH + "\n"
            "[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = '" + boot + "' ] || exit 3\n"
            "processes=$($BB ps | $BB grep -c '[w]pa_supplicant' || true)\n"
            "size=absent\n"
            "if [ ! -L \"$log\" ] && [ -f \"$log\" ]; then size=$($BB stat -c %s \"$log\"); fi\n"
            "case \"$size\" in\n"
            "  absent) ;;\n"
            "  0) size=empty ;;\n"
            "  *) [ \"$size\" -le " + str(LOG_LIMIT) + " ] || size=oversize ;;\n"
            "esac\n"
            "$BB printf '__SUPPLICANT_LOG_BEGIN__\\nboot_id=%s\\nbytes=%s\\nsupplicant_processes=%s\\n' '" + boot + "' \"$size\" \"$processes\"\n"
            "case \"$size\" in *[!0-9]*) ;; *) $BB cat \"$log\" ;; esac\n"
            "after=absent\n"
            "if [ ! -L \"$log\" ] && [ -f \"$log\" ]; then after=$($BB stat -c %s \"$log\"); fi\n"
            "$BB printf '\\n__SUPPLICANT_LOG_END__\\nbytes_after=%s\\nboot_after=%s\\n' \"$after\" \"$($BB cat /proc/sys/kernel/random/boot_id)\"\n").encode()


def log_result(raw, err, process, boot):
    """Completeness of the exported log: process, boot, size and markers; the
    log must be present, non-empty, within the bound and unchanged across the
    copy. The log bytes stay in the phase's private stdout file; only their
    count, digest and fixed-phrase counts are reported.
    """
    result = {'complete': False, 'bytes': None, 'size_report': None, 'supplicant_processes': None,
              'boot_match': False, 'log_sha256': None, 'phrases': None}
    head = re.match(rb'__SUPPLICANT_LOG_BEGIN__\nboot_id=(' + BOOT_RE.encode() + rb')\n'
                    rb'bytes=(\d{1,9}|absent|empty|oversize)\nsupplicant_processes=(\d{1,4})\n', raw)
    tail = re.search(rb'\n__SUPPLICANT_LOG_END__\nbytes_after=(\d{1,9}|absent)\nboot_after=(' +
                     BOOT_RE.encode() + rb')\n$', raw)
    if head is None or tail is None or tail.start() < head.end():
        return result
    result['boot_match'] = head[1] == boot.encode() and tail[2] == boot.encode()
    result['supplicant_processes'] = int(head[3])
    result['size_report'] = head[2].decode()
    if not head[2].isdigit():
        result['bytes'] = 0
        return result
    log = raw[head.end():tail.start()]
    result['bytes'] = len(log)
    if not log or len(log) > LOG_LIMIT:
        return result
    result['log_sha256'] = hashlib.sha256(log).hexdigest()
    result['phrases'] = phrase_counts(log)
    result['complete'] = bool(result['boot_match'] and not err and tail[1].isdigit() and
                              process.get('exit_status') == 0 and process.get('reason') is None and
                              process.get('stdin_complete') is True and
                              process.get('stdout_bytes') == len(raw) and
                              process.get('stderr_bytes', 0) == 0 and
                              int(head[2]) == len(log) == int(tail[1]) and
                              result['supplicant_processes'] == 0)
    return result


def session_pass(join, fields, log, userspace, session_verified):
    """The C2 session conjunction: the join phase's process completed with its
    framed stdout under the authenticated boot and an empty stderr; the
    supplicant exited cleanly with one scan result set, key negotiation
    completed and connected; the channel-40 IR flag was exactly 1 after the
    beacon; the join reached its terminal record; the driver's handshake path
    passed (two frames delivered, two sent, both key commands with credits,
    both removals, healthy bounded join); the complete private export has the
    byte count the join reported and reproduces its phrase counts; and the
    session is sealed, regression-passed and recovered. No installed-key or
    operational claim.
    """
    counts = {key: fields.get(key) for key in ('supplicant_' + name for name in PHRASES)}
    return bool(join.get('driver_handshake_path_pass') and session_verified and
                userspace.get('transport_complete') is True and
                userspace.get('standard_scan_succeeded') is True and
                fields.get('framed') and
                fields.get('supplicant_exit') == 0 and fields.get('connect_exit') == 0 and
                fields.get('channel40_ir_after_beacon') == 1 and fields.get('join_terminal') == 1 and
                counts['supplicant_ctrl_event_scan_results'] == 1 and
                (counts['supplicant_wpa__key_negotiation_completed'] or 0) >= 1 and
                (counts['supplicant_ctrl_event_connected'] or 0) >= 1 and
                log.get('complete') is True and log.get('bytes') and
                log.get('bytes') == fields.get('supplicant_log_bytes') and
                log.get('phrases') == counts)
