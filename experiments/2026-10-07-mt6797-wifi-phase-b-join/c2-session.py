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
# (letters lowered; ':', ' ', '-' and '/' to '_'). CTRL-EVENT-SCAN-RESULTS is
# never in the debug log (wpa_msg_ctrl reaches attached monitors only), so the
# one scan is the nl80211 driver's debug line; the handshake messages are the
# supplicant's own debug lines; message 3 carries the "RSN:" prefix on the
# WPA2 path (wpa_supplicant_process_3_of_4) and "WPA:" on the WPA path, so its
# phrase has no prefix.
PHRASES = {'nl80211__received_scan_results': b'nl80211: Received scan results',
           'associated_with': b'Associated with',
           'wpa__rx_message_1_of_4_way_handshake': b'WPA: RX message 1 of 4-Way Handshake',
           'wpa__sending_eapol_key_2_4': b'WPA: Sending EAPOL-Key 2/4',
           'rx_message_3_of_4_way_handshake': b'RX message 3 of 4-Way Handshake',
           'wpa__sending_eapol_key_4_4': b'WPA: Sending EAPOL-Key 4/4',
           'wpa__installing_ptk': b'WPA: Installing PTK',
           'wpa__installing_gtk': b'WPA: Installing GTK',
           'wpa__key_negotiation_completed': b'WPA: Key negotiation completed',
           'ctrl_event_connected': b'CTRL-EVENT-CONNECTED',
           'ctrl_event_disconnected': b'CTRL-EVENT-DISCONNECTED'}
FIELDS = ('supplicant_exit', 'supplicant_log_bytes', 'channel40_ir_after_beacon', 'channel40_query_exit',
          'channel40_lines', 'channel40_ir_during_join', 'channel40_ir_ticks', 'connect_exit', 'join_terminal',
          # Phase C3 data checks on the device: fixed counts and statuses, never an address.
          'data_phase_seen', 'tool_udhcpc', 'tool_ping', 'dhcp_exit', 'dhcp_bound', 'dhcp_prefix', 'lease_written',
          'dropbear_digest_ok', 'wifi_sshd_started', 'wifi_sshd_ready', 'wifi_sshd_exit', 'ping_transmitted', 'ping_received')
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
    supplicant exited cleanly with one nl80211 scan result set, each of the
    four handshake messages exactly once, key negotiation completed and
    connected; the channel-40 IR flag was observed 1 while the
    supplicant owned the connection (cfg80211 restores the world-domain no-IR
    flag once every interface is idle after the disconnection, so the
    after-exit flag is recorded, not gated); the join reached its terminal record; the driver's handshake path
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
                fields.get('channel40_ir_during_join') == 1 and fields.get('join_terminal') == 1 and
                counts['supplicant_nl80211__received_scan_results'] == 1 and
                counts['supplicant_wpa__rx_message_1_of_4_way_handshake'] == 1 and
                counts['supplicant_wpa__sending_eapol_key_2_4'] == 1 and
                counts['supplicant_rx_message_3_of_4_way_handshake'] == 1 and
                counts['supplicant_wpa__sending_eapol_key_4_4'] == 1 and
                (counts['supplicant_wpa__key_negotiation_completed'] or 0) >= 1 and
                (counts['supplicant_ctrl_event_connected'] or 0) >= 1 and
                log.get('complete') is True and log.get('bytes') and
                log.get('bytes') == fields.get('supplicant_log_bytes') and
                log.get('phrases') == counts)


def c3_session_pass(join, fields, log, userspace, session_verified, wifi_ssh):
    """The C3 session conjunction: the C2 conjunction, the driver's data-path
    pass (channel released, data phase ended by its budget or a disconnect,
    frames acknowledged and delivered at the firmware boundary), the device's
    bounded network checks (the data phase seen, udhcpc bound through the
    validating hook with a prefix length of 8..30, the retained Dropbear by
    digest started on wlan0's address and ready, stopped at the terminal, at
    least one ping reply from the router) and the laptop's one bounded
    authenticated SSH exchange over Wi-Fi bound to the same boot (its receipt
    carries statuses and byte counts, never the address). No throughput,
    replay-protection or operational claim.
    """
    wifi_ssh = wifi_ssh or {}
    prefix = fields.get('dhcp_prefix')
    return bool(session_pass(join, fields, log, userspace, session_verified) and
                join.get('driver_data_path_pass') and
                fields.get('data_phase_seen') == 1 and fields.get('tool_udhcpc') == 1 and fields.get('tool_ping') == 1 and
                fields.get('dhcp_bound') == 1 and fields.get('lease_written') == 1 and
                isinstance(prefix, int) and 8 <= prefix <= 30 and
                fields.get('dropbear_digest_ok') == 1 and fields.get('wifi_sshd_started') == 1 and
                fields.get('wifi_sshd_ready') == 1 and fields.get('wifi_sshd_exit') is not None and
                (fields.get('ping_received') or 0) >= 1 and
                wifi_ssh.get('ready_seen') is True and wifi_ssh.get('ssh_exit') == 0 and
                wifi_ssh.get('boot_match') is True)


def two_lifetime_fields(raw):
    """Parse the authored join-twice.sh stdout grammar (the real tokens, not invented
    scalars) into the two-lifetime fields: the framing, the __JOIN_END__ summary
    (connect_exit, cycles_completed, rearms_observed, terminals_observed, overall_rc), the
    supplicant exit/log size, the supplicant phrase counts, and the per-cycle device line plus
    its host-ack presence.
    """
    text = raw.decode('ascii', 'replace') if isinstance(raw, (bytes, bytearray)) else raw
    fields = {'framed': '__JOIN_BEGIN__\n' in text and '__JOIN_END__\n' in text}
    for name in ('connect_exit', 'cycles_completed', 'rearms_observed', 'terminals_observed',
                 'overall_rc', 'supplicant_exit', 'supplicant_log_bytes'):
        match = re.search(r'^' + name + r'=(\d{1,9})$', text, re.M)
        fields[name] = int(match[1]) if match else None
    fields['supplicant_counts'] = {
        'supplicant_' + name: (int(m[1]) if (m := re.search(r'^supplicant_' + name + r'=(\d{1,6})$', text, re.M)) else None)
        for name in PHRASES}
    cycles = {}
    line = (r'^cycle=(\d+) dhcp_exit=(\S+) dhcp_bound=(\d+) dhcp_prefix=(\S+) lease_written=(\d+) '
            r'dropbear_digest_ok=(\d+) wifi_sshd_started=(\d+) wifi_sshd_ready=(\d+) '
            r'ping_transmitted=(\d+) ping_received=(\d+)$')
    for m in re.finditer(line, text, re.M):
        cycles[int(m[1])] = {'dhcp_exit': m[2], 'dhcp_bound': int(m[3]), 'dhcp_prefix': m[4],
                             'lease_written': int(m[5]), 'dropbear_digest_ok': int(m[6]),
                             'wifi_sshd_started': int(m[7]), 'wifi_sshd_ready': int(m[8]),
                             'ping_transmitted': int(m[9]), 'ping_received': int(m[10]), 'host_ack': False}
    for m in re.finditer(r'^cycle=(\d+) host_ack=present$', text, re.M):
        if int(m[1]) in cycles:
            cycles[int(m[1])]['host_ack'] = True
    fields['cycles'] = cycles
    return fields


def two_lifetime_device_pass(fields, log, userspace):
    """The device+supplicant half of the two-lifetime verdict, from the authored join-twice
    output: the join phase's transport completed with a standard scan (the inherited
    userspace conjunction, so a framed stdout cannot coexist with an incomplete transport);
    the run is framed and healthy (exactly two completed cycles, one re-arm, two terminal
    observations, connect and supplicant exits zero, overall_rc zero); each of the two cycles
    had a clean udhcpc (dhcp_exit 0) that bound a lease (prefix 8..30), ran the digest-checked
    Dropbear listener, attempted the bounded three pings with at least one reply (the
    reachability threshold; the bounded protocol transmits three), and carried a present
    host-ack; the surviving supplicant shows the four-way handshake twice (connected and key
    negotiation at least twice, two scan sets); and the complete private export reproduces
    those doubled counts and its reported size.
    """
    counts = fields.get('supplicant_counts') or {}
    cycles = fields.get('cycles') or {}
    if not ((userspace or {}).get('transport_complete') is True and
            (userspace or {}).get('standard_scan_succeeded') is True):
        return False
    if not (fields.get('framed') and fields.get('cycles_completed') == 2 and
            fields.get('rearms_observed') == 1 and fields.get('terminals_observed') == 2 and
            fields.get('overall_rc') == 0 and fields.get('connect_exit') == 0 and
            fields.get('supplicant_exit') == 0 and set(cycles) == {1, 2}):
        return False
    for n in (1, 2):
        c = cycles[n]
        if not (c.get('dhcp_exit') == '0' and c['dhcp_bound'] == 1 and c['lease_written'] == 1 and
                c['dropbear_digest_ok'] == 1 and c['wifi_sshd_started'] == 1 and c['wifi_sshd_ready'] == 1 and
                re.fullmatch(r'\d{1,2}', str(c['dhcp_prefix'])) and 8 <= int(c['dhcp_prefix']) <= 30 and
                c['ping_transmitted'] == 3 and c['ping_received'] >= 1 and c['host_ack'] is True):
            return False
    if not (counts.get('supplicant_nl80211__received_scan_results') == 2 and
            counts.get('supplicant_wpa__rx_message_1_of_4_way_handshake') == 2 and
            counts.get('supplicant_wpa__sending_eapol_key_2_4') == 2 and
            counts.get('supplicant_rx_message_3_of_4_way_handshake') == 2 and
            counts.get('supplicant_wpa__sending_eapol_key_4_4') == 2 and
            (counts.get('supplicant_wpa__key_negotiation_completed') or 0) >= 2 and
            (counts.get('supplicant_ctrl_event_connected') or 0) >= 2):
        return False
    return bool(log.get('complete') is True and log.get('bytes') and
                log.get('bytes') == fields.get('supplicant_log_bytes') and
                log.get('phrases') == counts)


def c3_two_lifetime_pass(lifetimes, fields, log, userspace, session_verified, wifi_ssh):
    """The two-lifetime C3 conjunction: the kernel two-lifetime pass (classify_lifetimes:
    exactly two lifetimes and one re-arm, each a healthy bounded data-path join with exactly
    one admitted scan), the authored device+supplicant two-lifetime pass, the session seal,
    and the host aggregate (both cycles validated over Wi-Fi and acknowledged over USB, none
    closed). Bounded milestone; no throughput, replay-protection or operational claim.
    """
    wifi_ssh = wifi_ssh or {}
    cycles = wifi_ssh.get('cycles') or []
    host_ok = bool(wifi_ssh.get('all_pass') is True and
                   isinstance(wifi_ssh.get('cycles_expected'), int) and
                   wifi_ssh.get('cycles_expected') == len(cycles) == 2 and
                   all(c.get('boot_match') and c.get('ack_written') and not c.get('closed') for c in cycles))
    return bool((lifetimes or {}).get('two_lifetime_pass') and session_verified and
                two_lifetime_device_pass(fields, log, userspace) and host_ok)


CYCLE_DIR = '/tmp/mt6797-wifi-phase-b-1'
CYCLE_FILES = ('hook-status', 'prefix', 'lease', 'router', 'udhcpc.log',
               'dropbear.log', 'ping.log', 'ready', 'host-ack')
CYCLE_EXPORT_LIMIT = 131072


def cycles_export_script(boot):
    """One bounded read-only export, in RAM, of the two cycles' retained per-cycle evidence
    (hook status, lease/prefix/router, the udhcpc/dropbear/ping logs, the ready block and the
    host-ack), so the custodian can pull it into the private evidence root BEFORE the seal and
    the recovery that wipes the mainline RAM. Identity is checked before and after; each file
    is framed with its byte length; nothing is written on the device. The private evidence
    root retains it at mode 0600; it is never published (it names addresses).
    """
    if not re.fullmatch(BOOT_RE, boot):
        raise ValueError('boot identity is malformed')
    files = ' '.join(CYCLE_DIR + '/c$c/' + name for name in CYCLE_FILES)
    return ("#!/bin/sh\nset -u\nBB=/bin/busybox\n"
            "[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = '" + boot + "' ] || exit 3\n"
            "$BB printf '__CYCLES_BEGIN__\\nboot=%s\\n' '" + boot + "'\n"
            "for c in 1 2; do\n"
            "  for f in " + files + "; do\n"
            "    if [ -f \"$f\" ] && [ ! -L \"$f\" ]; then\n"
            "      n=$($BB wc -c < \"$f\" 2>/dev/null || echo -1)\n"
            "      $BB printf '__FILE__ path=%s bytes=%s\\n' \"$f\" \"$n\"\n"
            "      $BB dd if=\"$f\" bs=1 count=" + str(CYCLE_EXPORT_LIMIT) + " 2>/dev/null\n"
            "      $BB printf '\\n__END__\\n'\n"
            "    fi\n"
            "  done\n"
            "done\n"
            "$BB printf '__CYCLES_END__\\nboot_after=%s\\n' \"$($BB cat /proc/sys/kernel/random/boot_id)\"\n").encode()


def cycles_export_result(raw, err, process, boot):
    """Validate the framed cycles export: the read-only transport actually completed (no
    stderr, a clean process, the whole stdout accounted for), identity before and after,
    framed, both cycles' key evidence present (a bound lease and a present host-ack for each),
    and NO file truncated by the per-file dd cap. Records per-file presence and byte counts
    only (no contents), so the result json carries no address; the raw framed bytes are the
    private sealed capture and are retained regardless of completeness.
    """
    text = raw.decode('ascii', 'replace') if isinstance(raw, (bytes, bytearray)) else raw
    result = {'complete': False, 'boot_match': False, 'transport_ok': False,
              'truncated': False, 'cycles': {}, 'bytes': len(raw)}
    head = re.match(r"__CYCLES_BEGIN__\nboot=(" + BOOT_RE + r")\n", text)
    tail = re.search(r"\n__CYCLES_END__\nboot_after=(" + BOOT_RE + r")\n$", text)
    if not head or not tail:
        return result
    result['boot_match'] = head[1] == boot and tail[1] == boot
    process = process or {}
    result['transport_ok'] = bool(not err and process.get('exit_status') == 0 and
                                  process.get('reason') is None and process.get('stdin_complete') is True and
                                  process.get('stdout_bytes') == len(raw) and process.get('stderr_bytes', 0) == 0)
    present = {}
    truncated = False
    for m in re.finditer(r"^__FILE__ path=(\S+) bytes=(-?\d+)$", text, re.M):
        path, n = m[1], int(m[2])
        cyc = re.search(r'/c(\d+)/', path)
        name = path.rsplit('/', 1)[1]
        # The device dd copies at most CYCLE_EXPORT_LIMIT bytes; a reported length above the
        # cap means the file was truncated in transit, and a -1 means an unreadable file.
        if n < 0 or n > CYCLE_EXPORT_LIMIT:
            truncated = True
        if cyc:
            present.setdefault(int(cyc[1]), {})[name] = n
    result['cycles'] = present
    result['truncated'] = truncated
    result['complete'] = bool(result['boot_match'] and result['transport_ok'] and not truncated and
                              all(c in present and present[c].get('lease', -1) >= 0 and
                                  present[c].get('host-ack', -1) >= 0 for c in (1, 2)))
    return result


def quiescence_script(boot):
    """One bounded read-only export of the boot-bound quiescence record the leaf
    join writes on exit (the owned children -- the Wi-Fi listener and the
    supplicant -- it could not terminate). Framed and identity-checked; nothing
    is written on the device.
    """
    if not re.fullmatch(BOOT_RE, boot):
        raise ValueError('boot identity is malformed')
    return ("#!/bin/sh\nset -u\nBB=/bin/busybox\n"
            "[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = '" + boot + "' ] || exit 3\n"
            "$BB printf '__QUIESCENCE_BEGIN__\\n'\n"
            "[ -f /tmp/mt6797-wifi-phase-b-1/quiescence ] && "
            "$BB cat /tmp/mt6797-wifi-phase-b-1/quiescence\n"
            "$BB printf '__QUIESCENCE_END__\\nboot_after=%s\\n' "
            "\"$($BB cat /proc/sys/kernel/random/boot_id)\"\n").encode()


def quiescence_result(raw, boot):
    """Parse the framed quiescence record. 'quiesced' is true only when the record
    is present, boot-bound before and after, and its faults line is empty; a
    missing, boot-mismatched or non-empty-faults record is NOT quiesced, so the
    host refuses the seal and the RAM-wiping recovery. The named faults (owned
    pid:identity list) are retained for diagnosis.
    """
    text = raw.decode('ascii', 'replace') if isinstance(raw, (bytes, bytearray)) else raw
    result = {'quiesced': False, 'boot_match': False, 'faults': None, 'bytes': len(raw)}
    head = re.match(r"__QUIESCENCE_BEGIN__\n", text)
    tail = re.search(r"\n__QUIESCENCE_END__\nboot_after=(" + BOOT_RE + r")\n$", text)
    if not head or not tail:
        return result
    body = re.search(r"boot=(" + BOOT_RE + r")\nfaults=([^\n]*)\n", text)
    result['boot_match'] = bool(body and body[1] == boot and tail[1] == boot)
    if body:
        result['faults'] = body[2]
    result['quiesced'] = bool(result['boot_match'] and body and body[2] == '')
    return result
