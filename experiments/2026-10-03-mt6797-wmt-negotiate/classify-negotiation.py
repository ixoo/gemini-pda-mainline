#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify bounded private wire evidence without returning raw bytes."""
import re


PREFIX = b'WMT negotiation '
LIMITS = {'default TX': 11, 'default RX': 17, 'set TX': 15,
          'set RX': 13, 'full TX': 11, 'full ACK TX': 4, 'full RX': 1043}


def crc(data):
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xa001 if value & 1 else 0)
    return value


def full_wire(raw):
    """One exact event and peer credit, with bounded prior ACKs; no resync."""
    offset = frames = events = 0
    peer = 7
    while offset < len(raw):
        if len(raw) - offset < 4 or frames == 8:
            return False, frames
        header = raw[offset:offset + 4]
        first, kind, low, check = header
        length = ((kind & 15) << 8) | low
        size = length + 6 if length else 4
        if (first & 0xc0 != 0x80 or kind & 0x80 or
                sum(header[:3]) & 255 != check or size > len(raw) - offset):
            return False, frames
        ack = first & 7
        if ack not in (peer, 0):
            return False, frames
        if length:
            payload = raw[offset + 4:offset + 4 + length]
            if (kind & 0x70 != 0x40 or first >> 3 & 7 != 0 or events or
                    payload != bytes.fromhex('020406000004df0e6801') or
                    int.from_bytes(raw[offset + size - 2:offset + size], 'little') != crc(payload)):
                return False, frames
            events += 1
        elif kind:
            return False, frames
        if ack == 0:
            peer = 0
        frames += 1
        offset += size
        # The owner retires once the event and credit are both received.
        if events and peer == 0 and offset != len(raw):
            return False, frames
    return events == 1 and peer == 0, frames


def classify(log):
    result = {'matched_response': False, 'radio_action': False}
    patterns = [
        rb'one-shot WMT negotiation: result=(-?\d+) phase=(\d+) clocks-held=([01])$',
        rb'WMT negotiation mandatory: default-rx=(\d+) default-irqs=(\d+) set-tx=(\d+) set-rx=(\d+) set-services=(\d+)$',
        rb'WMT negotiation full: tx=(\d+) rx=(\d+) services=(\d+) frames=(\d+) tx-seq=(\d+) rx-seq=(\d+) peer-ack=(\d+) local-ack=(\d+)$']
    values = []
    markers = [b'one-shot WMT negotiation:', b'WMT negotiation mandatory:', b'WMT negotiation full:']
    for pattern, marker in zip(patterns, markers):
        lines = [line for line in log.splitlines() if marker in line]
        records = [m for line in lines if (m := re.search(pattern, line))]
        if len(lines) != 1 or len(records) != 1:
            result['reason'] = 'missing, duplicate or malformed terminal record'
            return result
        values.append(tuple(map(int, records[0].groups())))
    status, phase, held = values[0]
    drx, irq, stx, srx, service = values[1]
    tx, rx, services, frames, txseq, rxseq, peer, local = values[2]
    result.update(status=status, phase=phase, clocks_held=bool(held),
                  default_rx=drx, default_irqs=irq, set_tx=stx, set_rx=srx,
                  set_services=service, full_tx=tx, full_rx=rx,
                  full_services=services, full_frames=frames,
                  tx_sequence=txseq, rx_sequence=rxseq, peer_ack=peer, local_ack=local)
    wire = {name: bytearray() for name in LIMITS}
    for line in log.splitlines():
        for name, maximum in LIMITS.items():
            marker = PREFIX + name.encode() + b': '
            if marker not in line:
                continue
            suffix = line.split(marker, 1)[1]
            match = re.fullmatch(rb'([0-9a-f]{8}): ((?:[0-9a-f]{2}(?: |$))+)', suffix)
            if not match:
                result['reason'] = 'malformed wire record'
                return result
            chunk = bytes.fromhex(match[2].decode())
            if (int(match[1], 16) != len(wire[name]) or len(wire[name]) % 16 or
                    not 1 <= len(chunk) <= 16 or
                    len(wire[name]) + len(chunk) > maximum):
                result['reason'] = 'duplicate, discontinuous or oversized wire record'
                return result
            wire[name].extend(chunk)
    full_ok, observed_frames = full_wire(bytes(wire['full RX']))
    default = wire['default RX']
    set_reply = wire['set RX']
    checks = {
        'terminal': status == 0 and phase == 5 and held == 1,
        'bounded_counts': drx == 16 and 1 <= irq < 32 and stx == 15 and srx == 12 and
            1 <= service <= 32 and tx == 15 and rx == len(wire['full RX']) and
            1 <= services <= 512 and 1 <= frames <= 8 and frames == observed_frames,
        'final_state': (txseq, rxseq, peer, local) == (1, 1, 0, 0),
        'default_wire': wire['default TX'] == bytes.fromhex('8040050001040100040000') and
            len(default) == 16 and default[0] & 0x80 and
            default[1:] == bytes.fromhex('400a00020406000004110000000000'),
        'set_wire': wire['set TX'] == bytes.fromhex('804009000104050003df0e68010000') and
            len(set_reply) == 12 and set_reply[0] & 0x80 and
            set_reply[1:] == bytes.fromhex('4006000204020000030000'),
        'full_command': wire['full TX'] == bytes.fromhex('874005cc0104010004') +
            crc(bytes.fromhex('0104010004')).to_bytes(2, 'little'),
        'full_event_and_credit': full_ok,
        'host_ACK': wire['full ACK TX'] == bytes.fromhex('80000080'),
        'no_WLAN_continuation': not any(marker in log for marker in
            [b'one-shot WLAN ', b'one-shot EMI ', b'one-shot HIF ']),
    }
    result['checks'] = {key: bool(value) for key, value in checks.items()}
    result['matched_response'] = all(checks.values())
    return result
