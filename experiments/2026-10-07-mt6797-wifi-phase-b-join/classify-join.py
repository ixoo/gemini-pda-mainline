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
        'peer': rb'peer: ready=1 sequence=(\d+)',
        'grant': rb'grant: channel=40 interval_ms=(\d+)',
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
        rb' g4ta=[01] translated=[01] first=0x[0-9a-f]{1,5})?',
        rb'cleanup refused: stage=[0-3] phase=\d{1,2} free=\d{1,5} limit=\d{1,5} pending_cpu=\d{1,5} pending_ffa=\d{1,5} sequences=[01] locked=[01]',
        rb'credit overflow: pages=\d{1,5} debt=\d{1,3}',
        # An element of a mac80211 frame outside this admission (one record per lifetime).
        rb'frame element refused: subtype=\d{1,2} id=0x[0-9a-f]{2} len=' + byte + rb' count=[0-2]',
    )
    notifications = (rb'bss absence: bss=0 absent=[01] quota=' + byte + rb' reserved=' + byte,
                     # Phase C1: a clear EAPOL-Key frame from the target, decoded and dropped.
                     rb'eapol observed: translated=[01] frame=\d{1,4} activated=[01] vector=[01] bss=(?:0|15)')
    diagnostics = refusals + notifications
    rows = {name: [] for name in patterns}
    diagnostic_lines = []
    absence_rows = []
    eapol_rows = []
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
                rows[name].append((index, *(int(v) for v in match.groups())))
                break
        else:
            if any(re.fullmatch(pattern, body) for pattern in diagnostics):
                diagnostic_lines.append(body.split(b':', 1)[0].decode())
                if body.startswith(b'bss absence:'):
                    absence_rows.append(index)
                elif body.startswith(b'eapol observed:'):
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
    association = [row for row in rx if row[1] == 1]
    auth = [row for row in rx if row[1] == 11]
    accepted = len(association) == 1 and association[0][2] == 0
    expected = [11, 0, 12] if accepted else [11, 0]
    sequence_ok = ([row[1] for row in tx] == expected and
                   len({row[2] for row in tx}) == len(tx) and
                   all(1 <= row[2] <= 127 and 1 <= row[3] <= 19 for row in tx))
    acknowledged = (len(done) == len(tx) and
                    {row[1] for row in done} == {row[2] for row in tx} and
                    all(row[2] == 0 for row in done) and
                    all(len([d for d in done if d[1] == t[2] and d[0] > t[0]]) == 1
                        for t in tx))
    exchange = (sequence_ok and acknowledged and len(auth) == 1 and auth[0][2] == 0 and
                len(association) == 1 and tx[0][0] < auth[0][0] < tx[1][0] < association[0][0])
    credits = rows['credit']
    expected_pages = 7 + (3 if accepted else 0) + sum(row[3] for row in tx)
    credit_ok = (bool(credits) and all(row[1] > 0 and row[2] <= 19 for row in credits) and
                 sum(row[1] for row in credits) == expected_pages and credits[-1][2] == 0)
    cleanup_ok = (len(rows['cleanup']) == 1 and
                  rows['cleanup'][0][1] == int(accepted) and
                  [row[1] for row in rows['cleanup_submission']] == [0, 1, 2] and
                  rows['cleanup'][-1][0] > rows['cleanup_submission'][-1][0] and credit_ok)
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
    if eapol_rows:
        deauth_tx = [row for row in tx if row[1] == 12]
        deauth_done = [row[0] for row in done if deauth_tx and row[1] == deauth_tx[0][2] and row[0] > deauth_tx[0][0]]
        association_at = association[0][0] if len(association) == 1 else None
        activation_at = rows['activation'][0][0] if len(rows['activation']) == 1 else None
        if (len(eapol_rows) > 2 or not accepted or association_at is None or activation_at is None or
                len(deauth_tx) != 1 or len(deauth_done) != 1):
            malformed = True
        else:
            for index, translated, frame, activated, _vector, bss in eapol_rows:
                # No hardware BSS match (15) is admitted only before activation.
                if bss == 15 and activated:
                    malformed = True
                low, high = (99, 2052) if translated else (131, 2084)
                if (not (association_at < index < deauth_done[0]) or not (low <= frame <= high) or
                        activated != int(index > activation_at)):
                    malformed = True
    healthy = (not malformed and not stopped and not refused and len(rows['peer']) == 1 and
               len(rows['grant']) == 1 and 0 < rows['grant'][0][1] <= 9000)
    # RX can precede TX done. Advancing to another submission cannot.
    order_ok = False
    if exchange and healthy and cleanup_ok and activation_ok:
        completion = {row[1]: row[0] for row in done}
        stages = [row[0] for row in rows['cleanup_submission']]
        terminal = rows['cleanup'][0][0]

        def pages_between(begin, end):
            return sum(row[1] for row in credits if begin < row[0] < end)

        peer = rows['peer'][0][0]
        order_ok = (rows['grant'][0][0] < peer < tx[0][0] and
                    pages_between(-1, peer) == 4 and
                    completion[tx[0][2]] < tx[1][0] and
                    pages_between(peer, tx[1][0]) == tx[0][3] and
                    association[0][0] < stages[0] and
                    completion[tx[-1][2]] < stages[0] and
                    pages_between(-1, stages[0]) == expected_pages - 3 and
                    stages[0] < stages[1] < stages[2] < terminal and
                    all(pages_between(begin, end) == 1 for begin, end in
                        zip(stages, stages[1:] + [terminal])))
        if accepted:
            order_ok = (order_ok and completion[tx[1][2]] < rows['activation'][0][0] and
                        pages_between(tx[1][0], tx[2][0]) == tx[1][3] + 3)
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
        'eapol_observations': [{'translated': t, 'frame': f, 'activated': a, 'vector': v, 'bss': b} for _, t, f, a, v, b in eapol_rows],
        'terminal_failure_recorded': stopped,
        'wifi_operational': False,
    }
    result['bounded_join_pass'] = bool(exchange and healthy and cleanup_ok and activation_ok and order_ok)
    return result
