#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify sanitized join stage records; raw captures remain private."""

import re


def classify(raw):
    patterns = {
        'tx': rb'TX: subtype=(\d+) pid=(\d+) pages=(\d+)',
        'done': rb'TX done: pid=(\d+) status=(\d+) advanced=([01]) count=(\d+)',
        'rx': rb'RX: subtype=(\d+) status=(\d+)',
        'credit': rb'credit: pages=(\d+) remaining=(\d+)',
        'activation': rb'activation: sequence=(\d+) state=3',
        'cleanup': rb'cleanup: stage=3 credits=returned slots=retired deauth=([01])',
        'cleanup_submission': rb'cleanup submission: stage=(\d+)',
        # Phase C3: the channel privilege released after the group key (the stage-1
        # abort then submits nothing), the bounded data phase and its end.
        'cleanup_released': rb'cleanup submission: stage=1 released=1',
        'channel_released': rb'channel released: sequence=(\d+)',
        'data_phase': rb'data phase: budget_ms=(\d+) teardown_margin_ms=(\d+)',
        'data_end': rb'data phase end: reason=(budget|disconnect|txfail|pidbudget) elapsed_ms=(\d+) rx_unicast=(\d+) rx_group=(\d+) rx_dropped=(\d+) tx_queued=(\d+) tx_done=(\d+) tx_failed=(\d+)',
        'peer': rb'peer: ready=1 sequence=(\d+)',
        'grant': rb'grant: channel=40 interval_ms=(\d+)',
        # Phase C2: control-port EAPOL transmitted as a security frame, and the
        # key commands; "submitted" and "credit returned" are the only claims.
        'eapol_tx': rb'eapol sent: pid=(\d+) pages=(\d+) bytes=(\d+)',
        'key_command': rb'key command: (pairwise|group) submitted sequence=(\d+)',
        'key_credit': rb'key credit returned: (pairwise|group)',
        'key_removal': rb'key removal: (pairwise|group) submitted sequence=(\d+)',
        # Phase C2: the firmware's unsolicited add-key-done event for the pairwise key (pinned gen3 0x24).
        # Runtime 20 (proposal 0162) wrote 'pairwise'; 0163 writes the window.
        'key_done': rb'key done: (first after=pairwise|pairwise|second after=group) bss=0 peer=1',
    }
    # Diagnostic records name a refusal or an admitted indication; they are
    # neither stage records nor malformed. Health is decided by the stage grammar.
    byte = rb'(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)'  # exactly one unsigned byte, 0..255
    # Refusals end the lifetime and make the join unhealthy on their own; the
    # admitted BSS absence indication is a notification, not a refusal.
    refusals = (
        rb'control event refused: status=-\d{1,3} bytes=\d{1,5} type=0x[0-9a-f]{1,5} id=0x[0-9a-f]{2} seq=' + byte,
        rb'frame refused: bytes=\d{1,5} type=0x[0-9a-f]{1,5} allowed=0x[0-9a-f]{1,8}'
        rb'(?: hdr=[0-9a-f]{16} groups=0x[0-9a-f] at=\d{1,4} g4fc=0x[0-9a-f]{1,5} g4seq=0x[0-9a-f]{1,5}'
        rb' g4ta=[01] translated=[01] first=0x[0-9a-f]{1,5}(?: sec=\d{1,2} to=[01] from=[01])?)?',
        # A key the supplicant installed that the driver refused (state flags and status only).
        rb'key command refused: (?:pairwise|group) status=-\d{1,3} running=[01] active=[01] configured=[01] first=-?\d{1,3}',
        # An add-key-done event outside its owned window, named by index, peer flags and key state.
        rb'key done refused: bss=' + byte + rb' peer=[01] broadcast=[01] seq=' + byte + rb' submitted=[01][01] recorded=[01][01]',
        rb'cleanup refused: stage=[0-3] phase=\d{1,2} free=\d{1,5} limit=\d{1,5} pending_cpu=\d{1,5} pending_ffa=\d{1,5} sequences=[01] locked=[01]',
        rb'credit overflow: pages=\d{1,5} debt=\d{1,3}',
        rb'data credit overflow: pages=\d{1,5} debt=\d{1,3}',
        # An element of a mac80211 frame outside this admission (one record per lifetime).
        rb'frame element refused: subtype=\d{1,2} id=0x[0-9a-f]{2} len=' + byte + rb' count=[0-2]',
    )
    notifications = (rb'bss absence: bss=0 absent=[01] quota=' + byte + rb' reserved=' + byte,
                     # Phase C3: the first delivered data frame and the first submitted data frame, metadata only.
                     rb'data RX: first group=[01] tid=\d{1,2} keyid=[0-3] bytes=\d{1,4} vector=[01]',
                     rb'data TX: first pid=\d{1,3} pages=\d{1,2} bytes=\d{1,4}',
                     # Phase C3: owned protected data outside the open phase, dropped and counted (first, then the total).
                     rb'data RX outside: first phase=[01] ended=[01] group=[01] bytes=\d{1,4}',
                     rb'data RX outside: dropped=\d{1,3}',
                     # Phase C1: a clear EAPOL-Key frame from the target, decoded and dropped.
                     rb'eapol (?:observed|delivered): translated=[01] frame=\d{1,4} activated=[01] vector=[01] bss=(?:1|15)',
                     # Phase C2: protected group-addressed data from the target, discarded undelivered (first eight recorded).
                     rb'group data discarded: bytes=\d{1,4} fc=0x[0-9a-f]{1,4} match=0x[0-9a-f]{2} wlan=\d{1,3} bss=\d{1,2} sec=\d{1,2} status=0x[0-9a-f]{4} count=[1-8]',
                     # Runtime 21 (0168): a clear broadcast Action frame whose descriptor names no WLAN table entry, discarded undelivered (each of at most eight recorded, at any stage).
                     rb'group action frame discarded: bytes=\d{1,4} fc=0x[0-9a-f]{1,4} match=0x08 wlan=255 bss=\d{1,2} sec=0 status=0xe000 count=[1-8]',
                     # Phase C2: the target's directed clear Action frame, discarded undelivered (each of at most eight recorded).
                     rb'action frame discarded: bytes=\d{1,4} fc=0x[0-9a-f]{1,4} match=0x[0-9a-f]{2} wlan=\d{1,3} bss=\d{1,2} sec=\d{1,2} status=0x[0-9a-f]{4} count=[1-8]')
    diagnostics = refusals + notifications
    rows = {name: [] for name in patterns}
    diagnostic_lines = []
    absence_rows = []
    eapol_rows = []
    group_rows = []
    action_rows = []
    group_action_rows = []
    refused = False
    stopped_index = None
    malformed = False
    stopped = False
    for index, line in enumerate(raw.splitlines()):
        prefix = b'one-shot WLAN join '
        if prefix not in line:
            continue
        body = line.split(prefix, 1)[1]
        if body.startswith(b'stopped:'):
            stopped = True
            stopped_index = index
            continue
        for name, pattern in patterns.items():
            if match := re.fullmatch(pattern, body):
                rows[name].append((index, *(int(v) if v.isdigit() else v.decode() for v in match.groups())))
                break
        else:
            if any(re.fullmatch(pattern, body) for pattern in diagnostics):
                diagnostic_lines.append(body.split(b':', 1)[0].decode())
                if body.startswith(b'bss absence:'):
                    absence_rows.append(index)
                elif body.startswith(b'group data discarded:'):
                    group_rows.append((index, int(body.rsplit(b'count=', 1)[1])))
                elif body.startswith(b'action frame discarded:'):
                    action_rows.append((index, int(body.rsplit(b'count=', 1)[1])))
                elif body.startswith(b'group action frame discarded:'):
                    group_action_rows.append((index, int(body.rsplit(b'count=', 1)[1])))
                elif body.startswith(b'data TX: first') or body.startswith(b'data RX: first') or body.startswith(b'data RX outside:'):
                    pass  # Phase C3 first-frame notifications: metadata, neither refusal nor stage
                elif body.startswith(b'eapol observed:') or body.startswith(b'eapol delivered:'):
                    fields = dict(part.split(b'=') for part in body.split(b': ', 1)[1].split(b' '))
                    eapol_rows.append((index, int(fields[b'translated']), int(fields[b'frame']),
                                       int(fields[b'activated']), int(fields[b'vector']), int(fields[b'bss'])))
                else:
                    refused = True
            else:
                malformed = True
    # The admitted indication is valid at most twice, and only between the
    # stage-2 cleanup submission and the cleanup terminal (the stage-3 line or
    # the stopped footer); any other placement is malformed.
    stage2 = [row[0] for row in rows['cleanup_submission'] if row[1] == 2]
    terminal = [row[0] for row in rows['cleanup']] + ([stopped_index] if stopped_index is not None else [])
    if absence_rows:
        if (len(absence_rows) > 2 or len(stage2) != 1 or not terminal or
                any(not (stage2[0] < i < min(terminal)) for i in absence_rows)):
            malformed = True
    tx, done, rx = rows['tx'], rows['done'], rows['rx']
    eapol_tx, key_commands, key_credits, key_removals = rows['eapol_tx'], rows['key_command'], rows['key_credit'], rows['key_removal']
    key_done = rows['key_done']
    keys_ok = True
    # An add-key-done record without a pairwise key command has no owner.
    if key_done and not key_commands:
        keys_ok = False
        malformed = True
    first_done = [row for row in key_done if row[1].startswith('first') or row[1] == 'pairwise']
    second_done = [row for row in key_done if row[1].startswith('second')]
    if key_commands or key_credits or key_removals:
        # Bounded key ownership: pairwise then group, each command followed by its
        # credit record, and on the healthy path exactly one ordered removal per
        # submitted key (a partial handshake with its exact removals is a healthy
        # teardown but not a handshake pass). Command and removal sequences are
        # 1..255, unique and increasing, as the driver assigns them.
        kinds = [row[1] for row in key_commands]
        credit_kinds = [row[1] for row in key_credits]
        removal_kinds = [row[1] for row in key_removals]
        sequences = [row[2] for row in key_commands] + [row[2] for row in key_removals]
        # The firmware's add-key-done events are attributed by window, not by key
        # (the event names no key): the first once after the pairwise command and
        # the activation and before the group command, the second at most once after
        # the group command and the first record, both before the deauthentication's
        # TX. The second may be the group key's completion or a delayed repeat.
        key_deauth_tx = [row for row in tx if row[1] == 12]
        key_done_bound = key_deauth_tx[0][0] if key_deauth_tx else None
        group_command = [row for row in key_commands if row[1] == 'group']
        keys_ok = (kinds in (['pairwise'], ['pairwise', 'group']) and credit_kinds == kinds and
                   len(first_done) <= 1 and len(second_done) <= 1 and
                   all(d[0] > key_commands[0][0] and
                       (len(rows['activation']) == 1 and d[0] > rows['activation'][0][0]) and
                       (not group_command or d[0] < group_command[0][0]) and
                       (key_done_bound is None or d[0] < key_done_bound) for d in first_done) and
                   all(bool(group_command) and bool(first_done) and d[0] > group_command[0][0] and
                       d[0] > first_done[0][0] and (key_done_bound is None or d[0] < key_done_bound)
                       for d in second_done) and
                   all(c[0] > k[0] for k, c in zip(key_commands, key_credits)) and
                   removal_kinds == kinds and
                   all(1 <= s <= 255 for s in sequences) and sequences == sorted(set(sequences)))
        if not keys_ok:
            malformed = True
    association = [row for row in rx if row[1] == 1]
    auth = [row for row in rx if row[1] == 11]
    accepted = len(association) == 1 and association[0][2] == 0
    expected = [11, 0, 12] if accepted else [11, 0]
    # Security frames share the PID space and the TX done path with management.
    all_tx = sorted(tx + [(row[0], 16, row[1], row[2]) for row in eapol_tx])
    sequence_ok = ([row[1] for row in tx] == expected and
                   len(eapol_tx) <= 2 and
                   len({row[2] for row in all_tx}) == len(all_tx) and
                   all(1 <= row[2] <= 127 and 1 <= row[3] <= 19 for row in all_tx) and
                   all(14 + 4 <= row[3] <= 1518 and row[2] == (28 + row[3] + 127) // 128 for row in eapol_tx) and
                   (not eapol_tx or (accepted and len(rows['activation']) == 1 and
                                     all(rows['activation'][0][0] < row[0] < tx[-1][0] for row in eapol_tx))))
    acknowledged = (len(done) == len(all_tx) and
                    {row[1] for row in done} == {row[2] for row in all_tx} and
                    all(row[2] == 0 for row in done) and
                    all(len([d for d in done if d[1] == t[2] and d[0] > t[0]]) == 1
                        for t in all_tx))
    exchange = (sequence_ok and acknowledged and len(auth) == 1 and auth[0][2] == 0 and
                len(association) == 1 and tx[0][0] < auth[0][0] < tx[1][0] < association[0][0])
    credits = rows['credit']
    # Phase C3 lifetime: at most one channel release (one page), only after the
    # group key's credit; the data phase record right after it; one end record
    # with its reason before the deauthentication TX; the stage-1 release record
    # only when the channel was released, and then no stage-1 command.
    released = rows['channel_released']
    data_phase = rows['data_phase']
    data_end = rows['data_end']
    group_credit = [row for row in key_credits if row[1] == 'group']
    deauth_tx_rows = [row for row in tx if row[1] == 12]
    lifetime_ok = (len(released) <= 1 and len(data_phase) == len(released) and len(data_end) <= len(released) and
                   len(rows['cleanup_released']) == len(released) and
                   all(bool(group_credit) and r[0] > group_credit[0][0] for r in released) and
                   all(released and p[0] > released[0][0] and p[1] == 60000 and p[2] == 5000 for p in data_phase) and
                   all(data_phase and e[0] > data_phase[0][0] and
                       (not deauth_tx_rows or e[0] < deauth_tx_rows[0][0]) for e in data_end))
    if not lifetime_ok:
        malformed = True
    expected_pages = (7 + (3 if accepted else 0) + sum(row[3] for row in tx) + sum(row[2] for row in eapol_tx) +
                      len(key_commands) + len(key_removals) + len(released) - len(rows['cleanup_released']))
    credit_ok = (bool(credits) and all(row[1] > 0 and row[2] <= 19 for row in credits) and
                 sum(row[1] for row in credits) == expected_pages and credits[-1][2] == 0)
    stage_rows = sorted(rows['cleanup_submission'] + [(row[0], 1) for row in rows['cleanup_released']])
    cleanup_ok = (len(rows['cleanup']) == 1 and
                  rows['cleanup'][0][1] == int(accepted) and
                  [row[1] for row in stage_rows] == [0, 1, 2] and
                  rows['cleanup'][-1][0] > stage_rows[-1][0] and credit_ok)
    activation_ok = (len(rows['activation']) == int(accepted) and
                     (not accepted or association[0][0] < rows['activation'][0][0] < tx[-1][0]))
    # EAPOL framing observations (0140 decoder: layout, peer, channel, complete
    # EAPOL-Key framing; not message 1, nonce, MIC or handshake state) are valid
    # at most twice, only between the status-0 association response and the
    # deauthentication's matched TX done (the driver's window), with the frame
    # length in the decoder's exact range for the layout (native 32+4+length,
    # translated 4+length, declared length 95..2048) and the activated field
    # agreeing with the activation record's placement. They are reported
    # separately and never form part of the association verdict.
    # Runtime 21 (0168): the broadcast Action discards are admitted at any stage
    # of the lifetime, including the cleanup stages, up to its terminal record:
    # rows['cleanup'] is the stage-3 terminal line only (the stage submissions
    # are 'cleanup_submission'), so the window closes at that line or at the
    # stopped footer, exactly the driver's join_cleanup_done; numbered 1..8 in
    # order, each once.
    stage3_terminal = [row[0] for row in rows['cleanup']]
    lifetime_end = min(stage3_terminal + ([stopped_index] if stopped_index is not None else []), default=None)
    if group_action_rows and (
            [count for _, count in group_action_rows] != list(range(1, len(group_action_rows) + 1)) or
            (lifetime_end is not None and any(index >= lifetime_end for index, _ in group_action_rows))):
        malformed = True
    if eapol_rows or group_rows or action_rows:
        deauth_tx = [row for row in tx if row[1] == 12]
        deauth_done = [row[0] for row in done if deauth_tx and row[1] == deauth_tx[0][2] and row[0] > deauth_tx[0][0]]
        association_at = association[0][0] if len(association) == 1 else None
        activation_at = rows['activation'][0][0] if len(rows['activation']) == 1 else None
        # The window closes at the deauthentication's matched TX done; a lifetime
        # that fail-stopped before its deauthentication (the stopped footer with
        # no deauthentication TX) closes at the footer instead: the records are
        # then placed, not malformed, and the refusal decides the verdict.
        if len(deauth_tx) == 1 and len(deauth_done) == 1:
            window_end = deauth_done[0]
        elif not deauth_tx and stopped_index is not None:
            window_end = stopped_index
        else:
            window_end = None
        if (len(eapol_rows) > 2 or not accepted or association_at is None or activation_at is None or
                window_end is None):
            malformed = True
        else:
            # Discards are admitted only after the activation and before the
            # window's end, numbered 1..8 in order, each once.
            for discard_rows in (group_rows, action_rows):
                if [count for _, count in discard_rows] != list(range(1, len(discard_rows) + 1)) or any(
                        not (activation_at < index < window_end) for index, _ in discard_rows):
                    malformed = True
            for index, translated, frame, activated, _vector, bss in eapol_rows:
                # Tag 15 is admitted only before the activation and tag 1 only
                # after it: the two measured values (runtimes 12 and 15), with
                # no meaning claimed for the firmware-filled field.
                if (bss == 15 and activated) or (bss == 1 and not activated):
                    malformed = True
                low, high = (99, 2052) if translated else (131, 2084)
                if (not (association_at < index < window_end) or not (low <= frame <= high) or
                        activated != int(index > activation_at)):
                    malformed = True
    healthy = (not malformed and not stopped and not refused and len(rows['peer']) == 1 and
               len(rows['grant']) == 1 and 0 < rows['grant'][0][1] <= 9000)
    # RX can precede TX done. Advancing to another submission cannot.
    order_ok = False
    if exchange and healthy and cleanup_ok and activation_ok:
        completion = {row[1]: row[0] for row in done}
        stages = [row[0] for row in stage_rows]
        terminal = rows['cleanup'][0][0]
        stage_pages = [1, 0 if rows['cleanup_released'] else 1, 1]

        def pages_between(begin, end):
            return sum(row[1] for row in credits if begin < row[0] < end)

        peer = rows['peer'][0][0]
        order_ok = (rows['grant'][0][0] < peer < tx[0][0] and
                    pages_between(-1, peer) == 4 and
                    completion[tx[0][2]] < tx[1][0] and
                    pages_between(peer, tx[1][0]) == tx[0][3] and
                    association[0][0] < stages[0] and
                    completion[tx[-1][2]] < stages[0] and
                    pages_between(-1, stages[0]) == expected_pages - sum(stage_pages) and
                    stages[0] < stages[1] < stages[2] < terminal and
                    all(pages_between(begin, end) == pages for (begin, end), pages in
                        zip(zip(stages, stages[1:] + [terminal]), stage_pages)))
        if accepted:
            # Between the association TX and the deauthentication TX: the association's
            # pages, the BSS and station configuration (3), each security frame's pages
            # and one page per key command; key commands sit after activation and before
            # the deauthentication TX, removals after its TX done and before stage 0.
            # The deauthentication's page may return before or after its TX done, so
            # the window from its TX to stage 0 holds its pages plus one per removal.
            order_ok = (order_ok and completion[tx[1][2]] < rows['activation'][0][0] and
                        pages_between(tx[1][0], tx[2][0]) == tx[1][3] + 3 + sum(row[2] for row in eapol_tx) + len(key_commands) + len(released) and
                        all(rows['activation'][0][0] < row[0] < tx[2][0] for row in key_commands + key_credits) and
                        all(completion[tx[2][2]] < row[0] < stages[0] for row in key_removals) and
                        pages_between(tx[2][0], stages[0]) == tx[2][3] + len(key_removals))
    result = {
        'association_response_status': association[0][2] if len(association) == 1 else None,
        'host_management_submissions': len(tx),
        'unique_tx_acknowledgements': acknowledged,
        'management_exchange_demonstrated': bool(exchange),
        'associated_station_activation_demonstrated': bool(exchange and accepted and activation_ok),
        'healthy_cleanup_demonstrated': bool(healthy and cleanup_ok and activation_ok and order_ok),
        'stage_and_credit_order_verified': bool(order_ok),
        'malformed_stage_record': malformed,
        'diagnostic_records': diagnostic_lines,
        'refusal_recorded': refused,
        'eapol_shape_observations': len(eapol_rows),
        'eapol_frames_sent': len(eapol_tx),
        'key_commands_submitted': [row[1] for row in key_commands],
        'key_credits_returned': [row[1] for row in key_credits],
        'key_removals_submitted': [row[1] for row in key_removals],
        'handshake_keys_submitted': bool(keys_ok and [row[1] for row in key_commands] == ['pairwise', 'group'] and
                                         [row[1] for row in key_credits] == ['pairwise', 'group']),
        # The firmware's add-key-done records as parsed (windows in order), then the
        # lifetime-gated terms: the first-window record (after the pairwise command,
        # before the group one) is required for the pass; the second-window record
        # (after the group command) is reported, not required, and not a proven
        # group-key completion: the event names no key, so the second may be a
        # delayed repeat of the first.
        'key_done_records': ['first' if row[1] == 'pairwise' else row[1].split(' ')[0] for row in key_done],
        'firmware_key_done_first_window': bool(keys_ok and len(first_done) == 1),
        'firmware_key_done_second_window': bool(keys_ok and len(second_done) == 1),
        # Phase C3 lifetime terms: the channel privilege released after the group
        # key, the data phase budget as recorded, and how the data phase ended.
        'channel_released': bool(lifetime_ok and len(released) == 1),
        'data_phase_budget_ms': data_phase[0][1] if lifetime_ok and data_phase else None,
        'data_phase_end_reason': data_end[0][1] if lifetime_ok and data_end else None,
        # Counts from the end record: protected frames delivered to and accepted
        # from mac80211 at the firmware boundary, never a network-function claim.
        'data_frames': ({'rx_unicast': data_end[0][3], 'rx_group': data_end[0][4], 'rx_dropped': data_end[0][5],
                         'tx_queued': data_end[0][6], 'tx_done': data_end[0][7], 'tx_failed': data_end[0][8]}
                        if lifetime_ok and data_end else None),
        # Driver-side C2 path: two frames delivered, two sent, both key commands with
        # their credits, both removals, healthy bounded join. The session's success
        # additionally needs the supplicant's completion phrase from the laptop
        # result; neither claims an installed key or operational Wi-Fi.
        'driver_handshake_path_pass': False,
        'eapol_observations': [{'translated': t, 'frame': f, 'activated': a, 'vector': v, 'bss': b} for _, t, f, a, v, b in eapol_rows],
        # Records only: the driver records the first eight discards and accepts up to
        # sixty-four per join; the total discarded is not in the log.
        'group_data_discard_records': len(group_rows),
        'group_data_discard_record_limit': 8,
        # Action frames: each discard is recorded and the cap is eight, so this is the total.
        'group_action_frame_discards': len(group_action_rows),
        'action_frame_discards': len(action_rows),
        'action_frame_discard_limit': 8,
        'terminal_failure_recorded': stopped,
        'wifi_operational': False,
    }
    result['bounded_join_pass'] = bool(exchange and healthy and cleanup_ok and activation_ok and order_ok)
    # Both add-key-done windows are required since the reference run 3 showed one
    # event observed within a millisecond after each key command (attribution by
    # order only; neither record names the key it completes).
    result['driver_handshake_path_pass'] = bool(result['bounded_join_pass'] and len(eapol_rows) == 2 and
                                                len(eapol_tx) == 2 and result['handshake_keys_submitted'] and
                                                result['firmware_key_done_first_window'] and
                                                result['firmware_key_done_second_window'] and
                                                [row[1] for row in key_removals] == ['pairwise', 'group'])
    # Phase C3 driver-side pass: the handshake pass, the channel released, the data
    # phase ended by its budget or a disconnect (not by transmit failures), at least
    # one data frame acknowledged and one unicast protected frame delivered. Whether
    # an address was obtained or a host answered is the session's evidence, not this.
    frames = result['data_frames']
    result['driver_data_path_pass'] = bool(result['driver_handshake_path_pass'] and result['channel_released'] and
                                           result['data_phase_end_reason'] in ('budget', 'disconnect') and frames and
                                           frames['tx_done'] >= 1 and frames['rx_unicast'] >= 1 and frames['tx_failed'] <= frames['tx_done'])
    return result
