#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline Wi-Fi capture framing only; never classifies hardware success."""
import struct
import zlib

RECORD_BYTES = 128
ZONE_PAYLOAD_BYTES = 65524
MAX_RECORDS = ZONE_PAYLOAD_BYTES // RECORD_BYTES
MAX_ORDINARY_RECORDS = MAX_RECORDS - 1
HEADER = struct.Struct('<4sHHI16sII')
PAYLOAD_BYTES = 120 - HEADER.size
COMMIT = 0x57464331
IDENTITY = 1
TERMINAL = 255
# Firmware load and other non-DMA lifecycle semantics remain unfinished.
KINDS = {IDENTITY, 2, 3, 4, 5, 6, 7, 8, 9, 10, TERMINAL}
TERMINAL_STATUSES = {1, 2, 3}  # producer-reported complete, failed, overflow


HIF_BIND = struct.Struct('<4I')
HIF_UNBIND = struct.Struct('<3I')


def validate_hif_payload(transaction, payload):
    if not transaction or len(payload) < 4:
        raise ValueError('HIF binding requires an initialization ordinal')
    subtype = int.from_bytes(payload[:4], 'little')
    layout = {1: HIF_BIND, 2: HIF_UNBIND}.get(subtype)
    if layout is None or len(payload) != layout.size:
        raise ValueError('invalid HIF binding subtype or payload size')
    values = layout.unpack(payload)
    if values[1] != transaction:
        raise ValueError('HIF binding ordinal disagrees with envelope')
    if subtype == 1 and (values[2] not in (1, 2) or values[3] not in (0, 1)):
        raise ValueError('invalid HIF device route or presence')


DMA_MAP = struct.Struct('<IIIIQII')
DMA_PROGRAM = struct.Struct('<IIQQ13I')
DMA_POLL = struct.Struct('<IIIIQII')
DMA_UNMAP = struct.Struct('<IIQII')


def validate_dma_payload(kind, transaction, payload):
    layout = {3: DMA_MAP, 4: DMA_PROGRAM, 5: DMA_POLL, 6: DMA_UNMAP}.get(kind)
    if layout is None:
        return
    if not transaction or len(payload) != layout.size:
        raise ValueError('DMA record requires transaction and exact payload size')
    values = layout.unpack(payload)
    if kind == 3:
        device, direction, requested, rounded, address, port, branch = values
        if not device or direction not in (0, 1) or branch not in (1, 2):
            raise ValueError('invalid DMA acquisition discriminator')
    elif kind == 4:
        device, phase, source, destination, *registers = values
        if not device or phase not in (1, 2):
            raise ValueError('invalid DMA programming phase')
        if phase == 2 and (source or destination or any(registers[4:])):
            raise ValueError('nonzero unused shutdown programming fields')
    elif kind == 5:
        phase, stage, reason, reserved, count, last, valid = values
        if phase not in (1, 2) or stage not in (1, 2) or reserved or valid not in (0, 1):
            raise ValueError('invalid poll discriminator')
        if stage == 1:
            if reason or count or last or valid:
                raise ValueError('poll entry contains a result')
        elif reason not in (1, 2, 3, 4, 5) or bool(count) != bool(valid) or (not valid and last):
            raise ValueError('invalid poll summary')
    else:
        stage, device, address, rounded, direction = values
        if stage not in (1, 2) or not device or direction not in (0, 1):
            raise ValueError('invalid DMA unmap discriminator')


# Kind 7 has stop records and image/section identity records.
FW_STOP_ENTRY = struct.Struct('<7I')
FW_STOP_COMMAND = struct.Struct('<4I')
FW_STOP_POLL = struct.Struct('<III4QIII')
FW_STOP_RETURN = struct.Struct('<2I')
FW_IMAGE = struct.Struct('<5I32s')
FW_SECTION = struct.Struct('<9I')
FW_IMAGE_RETURN = struct.Struct('<4I')
FW_STOP_LAYOUTS = {1: FW_STOP_ENTRY, 2: FW_STOP_COMMAND,
                   3: FW_STOP_POLL, 4: FW_STOP_RETURN,
                   5: FW_IMAGE, 6: FW_SECTION, 7: FW_IMAGE_RETURN}


def validate_stop_payload(transaction, payload):
    if not transaction or len(payload) < 4:
        raise ValueError('stop requires an invocation ID and subtype')
    subtype = int.from_bytes(payload[:4], 'little')
    layout = FW_STOP_LAYOUTS.get(subtype)
    if layout is None or len(payload) != layout.size:
        raise ValueError('unsupported stop subtype or payload size')
    values = layout.unpack(payload)
    if subtype >= 5:
        if not values[1] or not values[2]:
            raise ValueError('image record requires adapter and image IDs')
        if subtype == 5 and (not values[3] or values[4] < 2 or not any(values[5])):
            raise ValueError('invalid divided image identity')
        if subtype == 6 and (values[7] > 255 or values[8] > 255):
            raise ValueError('invalid native section flag byte')
        return
    if subtype == 1:
        _, adapter, caller, hif_present, d0, no_ack, removed = values
        if not adapter or caller not in (1, 2) or any(x not in (0, 1) for x in values[3:]):
            raise ValueError('invalid stop entry')
    elif subtype == 2:
        _, fw_own, attempted, status = values
        if fw_own not in (0, 1) or attempted not in (0, 1) or (not attempted and status):
            raise ValueError('invalid stop command')
    elif subtype == 3:
        _, dispatch, branch, requests, completions, last_request, fallbacks, offset, actual, consumed = values
        if dispatch not in (0, 1, 2, 3) or branch not in (1, 2, 3, 4):
            raise ValueError('invalid stop poll branch')
        if completions > requests or last_request > requests or bool(completions) != bool(last_request):
            raise ValueError('invalid stop read attribution')
        if not completions and actual:
            raise ValueError('accessor value without completion')


EMI_SECTION = struct.Struct('<IIIQ5I')
EMI_PROTECTION = struct.Struct('<IIIIQQIi')
EMI_MAPPING = struct.Struct('<IIQI')
EMI_COPY = struct.Struct('<6I')
EMI_LAYOUTS = {1: EMI_SECTION, 2: EMI_PROTECTION, 3: EMI_MAPPING, 4: EMI_COPY}
EMI_WINDOW = 512 * 1024
EMI_OPEN = 18 << 27
EMI_RESTRICT = EMI_OPEN | sum(5 << (3 * domain) for domain in range(8) if domain != 2)


def validate_emi_payload(transaction, payload):
    if not transaction or len(payload) < 4:
        raise ValueError('EMI requires a section-operation ID and subtype')
    subtype = int.from_bytes(payload[:4], 'little')
    layout = EMI_LAYOUTS.get(subtype)
    if layout is None or len(payload) != layout.size:
        raise ValueError('unsupported EMI subtype or payload size')
    values = layout.unpack(payload)
    if subtype == 1 and (not values[1] or not values[2]):
        raise ValueError('EMI section requires adapter and image IDs')
    if subtype == 2:
        _, phase, stage, branch, start, end, policy, status = values
        if phase not in (1, 2) or stage not in (1, 2) or branch not in (1, 2):
            raise ValueError('invalid EMI protection discriminator')
        if stage == 1 and status:
            raise ValueError('EMI protection entry contains a result')
    if subtype == 4 and values[1] not in (1, 2):
        raise ValueError('invalid EMI copy stage')


# Shared-OFF records preserve provider operations and the terminal condition loop.
OFF_POLL = struct.Struct('<IIIQQIIII')
OFF_ENTRY = struct.Struct('<5I')
OFF_STATE = struct.Struct('<6I')
OFF_DISPATCH = struct.Struct('<4I')
OFF_PROTECT_ENTRY = struct.Struct('<4I')
OFF_PROTECT_RESULT = struct.Struct('<IIIIIIQIIIi')
OFF_CONTROL = struct.Struct('<12I')
OFF_RETURN = struct.Struct('<IIii')
OFF_LAYOUTS = {1: OFF_POLL, 2: OFF_POLL, 3: OFF_ENTRY, 4: OFF_STATE,
               5: OFF_DISPATCH, 6: OFF_PROTECT_ENTRY, 7: OFF_PROTECT_RESULT,
               8: OFF_CONTROL, 9: OFF_RETURN}


def validate_off_payload(transaction, payload):
    if not transaction or len(payload) < 4:
        raise ValueError('OFF requires invocation ID and subtype')
    subtype = int.from_bytes(payload[:4], 'little')
    layout = OFF_LAYOUTS.get(subtype)
    if layout is None or len(payload) != layout.size:
        raise ValueError('unsupported OFF subtype or payload size')
    values = layout.unpack(payload)
    if not values[1]:
        raise ValueError('OFF requires provider ID')
    if subtype > 2:
        if subtype == 3 and (values[3] not in (1, 2, 3) or values[4] not in (0, 1)):
            raise ValueError('invalid OFF entry route or callback flag')
        if subtype == 4 and (values[4] not in (0, 1) or values[5] not in (1, 2)):
            raise ValueError('invalid OFF state decision')
        if subtype == 7:
            _, provider, before, stored, readback, reason, count, last, valid, returned, status = values
            if reason not in (1, 2, 3, 4) or valid not in (0, 1) or returned not in (0, 1):
                raise ValueError('invalid protection summary')
            if bool(count) != bool(valid) or (not valid and last) or (not returned and status):
                raise ValueError('protection result without read or return')
        return
    stage, provider, reason, primary_count, secondary_count, primary, secondary, primary_valid, secondary_valid = OFF_POLL.unpack(payload)
    if stage not in (1, 2) or not provider or primary_valid not in (0, 1) or secondary_valid not in (0, 1):
        raise ValueError('invalid OFF poll discriminator')
    if stage == 1:
        if any((reason, primary_count, secondary_count, primary, secondary, primary_valid, secondary_valid)):
            raise ValueError('OFF poll entry contains a result')
    elif reason not in (1, 2, 3):
        raise ValueError('invalid OFF poll exit reason')
    if (secondary_count > primary_count or primary_valid > bool(primary_count) or
            secondary_valid > bool(secondary_count) or secondary_valid > primary_valid or
            (not primary_valid and primary) or (not secondary_valid and secondary)):
        raise ValueError('invalid OFF condition read attribution')
    if primary_valid and primary & 2 and secondary_valid:
        raise ValueError('secondary condition read violates short-circuit order')


def encode(kind, sequence, cycle, transaction, payload):
    if len(cycle) != 16 or not any(cycle):
        raise ValueError('requires a nonzero 16-byte cycle identity')
    if kind not in KINDS or not 0 <= sequence < MAX_RECORDS:
        raise ValueError('unsupported kind or sequence')
    if not 0 <= transaction <= 0xffffffff or len(payload) > PAYLOAD_BYTES:
        raise ValueError('invalid transaction or oversized payload')
    if sequence == MAX_ORDINARY_RECORDS and kind != TERMINAL:
        raise ValueError('last slot is reserved for a terminal')
    if (sequence == 0) != (kind == IDENTITY):
        raise ValueError('identity must be the first and only identity record')
    if kind == IDENTITY and (transaction or len(payload) != 80):
        raise ValueError('identity requires candidate hash, boot ID and input hash')
    if kind == TERMINAL and (transaction or len(payload) != 4 or
                             int.from_bytes(payload, 'little') not in TERMINAL_STATUSES):
        raise ValueError('invalid terminal payload')
    if kind == 2:
        validate_hif_payload(transaction, payload)
    validate_dma_payload(kind, transaction, payload)
    if kind == 7:
        validate_stop_payload(transaction, payload)
    if kind == 8:
        validate_emi_payload(transaction, payload)
    if kind == 9:
        validate_off_payload(transaction, payload)
    body = HEADER.pack(b'WFC1', 1, kind, sequence, cycle, transaction, len(payload))
    body += payload + bytes(PAYLOAD_BYTES - len(payload))
    return body + struct.pack('<II', zlib.crc32(body), COMMIT)


def decode(data, expected_cycle):
    """Decode an exact record stream; no resynchronization, suffix or raw-zone scan."""
    if not data or len(data) % RECORD_BYTES or len(data) > MAX_RECORDS * RECORD_BYTES:
        raise ValueError('empty, partial or oversized record stream')
    records = []
    for offset in range(0, len(data), RECORD_BYTES):
        block = data[offset:offset + RECORD_BYTES]
        magic, version, kind, sequence, cycle, transaction, size = HEADER.unpack_from(block)
        if magic != b'WFC1' or version != 1 or sequence != len(records) or cycle != expected_cycle:
            raise ValueError('identity, version or ordering mismatch')
        if size > PAYLOAD_BYTES:
            raise ValueError('invalid payload size')
        payload = block[HEADER.size:HEADER.size + size]
        if block != encode(kind, sequence, cycle, transaction, payload):
            raise ValueError('padding, checksum or commit mismatch')
        if records and records[-1]['kind'] == TERMINAL:
            raise ValueError('record after terminal')
        records.append({'kind': kind, 'sequence': sequence, 'transaction': transaction,
                        'payload': payload})
    # A committed prefix without terminal is useful partial evidence, never completion.
    return records


def decode_pmsg(payload, expected_cycle, expected_identity):
    """Decode a fixed-slot no-ECC pmsg payload; no resynchronization or success verdict."""
    if len(payload) != ZONE_PAYLOAD_BYTES or len(expected_identity) != 80:
        raise ValueError('requires exact pmsg payload and independent identity')
    limit = MAX_RECORDS * RECORD_BYTES
    if any(payload[limit:]):
        raise ValueError('nonzero unused pmsg tail')
    end = limit
    interrupted_slot = None
    for offset in range(0, limit, RECORD_BYTES):
        block = payload[offset:offset + RECORD_BYTES]
        if int.from_bytes(block[124:128], 'little') == COMMIT:
            continue
        end = offset
        if any(payload[offset + RECORD_BYTES:]):
            raise ValueError('data after an uncommitted slot')
        if any(block):
            interrupted_slot = offset // RECORD_BYTES
        break
    records = decode(payload[:end], expected_cycle)
    if records[0]['payload'] != expected_identity:
        raise ValueError('candidate, boot or input identity mismatch')
    terminal = records[-1]['kind'] == TERMINAL
    if terminal and interrupted_slot is not None:
        raise ValueError('partial record after terminal')
    return {'records': records, 'interrupted_slot': interrupted_slot,
            'framing': 'terminal-recorded' if terminal else 'incomplete',
            'producer_status': int.from_bytes(records[-1]['payload'], 'little') if terminal else None}


def decode_pmsg_zone(raw, expected_cycle, expected_identity):
    """Decode the capture-mode raw snapshot, including its unchanged native header."""
    if len(raw) != ZONE_PAYLOAD_BYTES + 12:
        raise ValueError('requires exact 64-KiB raw capture zone')
    if struct.unpack('<III', raw[:12]) != (0x43474244, 0, ZONE_PAYLOAD_BYTES):
        raise ValueError('raw capture header does not match the fixed no-ECC layout')
    return decode_pmsg(raw[12:], expected_cycle, expected_identity)


def check_dma_bindings(data, expected_cycle):
    """Join DMA records to one closed software HIF lifetime, not a bus identity proof."""
    live, seen, transfers, used = {}, set(), {}, set()
    for row in decode(data, expected_cycle):
        kind, transaction, payload = row['kind'], row['transaction'], row['payload']
        if kind == 2:
            subtype = int.from_bytes(payload[:4], 'little')
            if subtype == 1:
                _, device, route, present = HIF_BIND.unpack(payload)
                if device in seen or route != 1 or not present:
                    raise ValueError('reused HIF lifetime or unsupported device binding')
                seen.add(device)
                live[device] = True
            else:
                _, device, pending = HIF_UNBIND.unpack(payload)
                if device not in live or pending or device in transfers.values():
                    raise ValueError('HIF release without a closed DMA lifetime')
                del live[device]
        elif kind == 3:
            device = DMA_MAP.unpack(payload)[0]
            if device not in live or transaction in used:
                raise ValueError('DMA acquisition outside a live HIF binding')
            used.add(transaction)
            transfers[transaction] = device
        elif kind in (4, 5, 6):
            if transaction not in transfers or transfers[transaction] not in live:
                raise ValueError('DMA event outside its binding lifetime')
            device = (DMA_PROGRAM.unpack(payload)[0] if kind == 4 else
                      DMA_UNMAP.unpack(payload)[1] if kind == 6 else transfers[transaction])
            if device != transfers[transaction]:
                raise ValueError('DMA device changed within its transaction')
            if kind == 6 and DMA_UNMAP.unpack(payload)[0] == 2:
                del transfers[transaction]
    if len(seen) != 1 or live or transfers or not used:
        raise ValueError('requires one complete HIF binding with DMA evidence')
    return {'checked_device': next(iter(seen)), 'checked_transactions': sorted(used),
            'scope': 'software HIF lifetime join only; use the separate DMA consistency check'}


def check_dma(data, expected_cycle):
    """Check complete recorded DMA lifetimes, not endpoint translation or Wi-Fi success."""
    transactions = {}
    for record in decode(data, expected_cycle):
        if record['kind'] in (3, 4, 5, 6):
            transactions.setdefault(record['transaction'], []).append(record)
    if not transactions:
        raise ValueError('no DMA lifetime recorded')
    for transaction, rows in transactions.items():
        if [row['kind'] for row in rows] != [3, 4, 5, 5, 4, 5, 5, 6, 6]:
            raise ValueError('incomplete, reordered or reused DMA transaction')
        device, direction, requested, rounded, address, port, branch = DMA_MAP.unpack(rows[0]['payload'])
        if branch != 1 or not requested or not requested <= rounded <= 0xfffff:
            raise ValueError('missing DMA API mapping or invalid transfer length')
        program_device, phase, source, destination, *regs = DMA_PROGRAM.unpack(rows[1]['payload'])
        if program_device != device or phase != 1 or (destination if direction == 0 else source) != address:
            raise ValueError('DMA mapping/programming identity mismatch')
        con_in, con_out, src_low, dst_low, length, src2_in, src2_out, dst2_in, dst2_out, irq_in, irq_out, en_in, en_out = regs
        # Native RX is 1 and TX is 0; observer direction uses RX=0, TX=1.
        expected_con = (con_in & ~0x30003) | 0x80030000 | (1 - direction)
        if (con_out != expected_con or src_low != source & 0xffffffff or
                dst_low != destination & 0xffffffff or length != rounded or
                src2_out != src2_in | 1 or dst2_out != dst2_in | 1 or
                irq_out != irq_in | 1 or en_out != en_in | 1):
            raise ValueError('recorded programming differs from the native operation')
        for entry_index, exit_index, poll_phase in ((2, 3, 1), (5, 6, 2)):
            entry = DMA_POLL.unpack(rows[entry_index]['payload'])
            result = DMA_POLL.unpack(rows[exit_index]['payload'])
            if entry[:2] != (poll_phase, 1) or result[:3] != (poll_phase, 2, 1):
                raise ValueError('missing successful native poll sequence')
            if not result[4] or not result[6] or bool(result[5] & 1) != (poll_phase == 1):
                raise ValueError('completion or positive idle read missing')
        stop_device, stop_phase, _, _, *stop = DMA_PROGRAM.unpack(rows[4]['payload'])
        if stop_device != device or stop_phase != 2 or stop[1] != stop[0] & ~1 or stop[3] != stop[2] & ~1:
            raise ValueError('ACK/interrupt-stop programming mismatch')
        for index, stage in ((7, 1), (8, 2)):
            if DMA_UNMAP.unpack(rows[index]['payload']) != (stage, device, address, rounded, direction):
                raise ValueError('unmap does not match the idle DMA mapping')
    return {'checked_transactions': list(transactions),
            'scope': 'recorded DMA API/programming/poll/unmap consistency only'}


def check_stop(data, expected_cycle):
    """Check a recorded ordinary direct-read stop, not thread quiescence or shared OFF."""
    stops = {}
    for record in decode(data, expected_cycle):
        if record['kind'] == 7 and int.from_bytes(record['payload'][:4], 'little') in (1, 2, 3, 4):
            stops.setdefault(record['transaction'], []).append(record['payload'])
    if not stops:
        raise ValueError('no firmware stop recorded')
    for payloads in stops.values():
        if [int.from_bytes(p[:4], 'little') for p in payloads] != [1, 2, 3, 4]:
            raise ValueError('incomplete, reordered or reused stop invocation')
        _, adapter, caller, hif_present, d0, no_ack, removed = FW_STOP_ENTRY.unpack(payloads[0])
        if (caller, hif_present, d0, no_ack, removed) != (1, 0, 1, 0, 0):
            raise ValueError('not an ordinary eligible remove invocation')
        if FW_STOP_COMMAND.unpack(payloads[1]) != (2, 0, 1, 0):
            raise ValueError('stop command skipped, firmware-owned or failed')
        _, dispatch, branch, requests, completions, last_request, fallbacks, offset, actual, consumed = FW_STOP_POLL.unpack(payloads[2])
        if (dispatch, branch, fallbacks, offset) != (1, 1, 0, 0):
            raise ValueError('not a direct WCIR condition exit without fallback')
        if not requests or requests != completions or last_request != requests:
            raise ValueError('missing attributable final accessor completion')
        if actual != consumed or actual & (1 << 21):
            raise ValueError('consumed READY-clear read not established')
        if FW_STOP_RETURN.unpack(payloads[3]) != (4, 0):
            raise ValueError('adapter stop did not return success')
    return {'checked_stops': list(stops),
            'scope': 'recorded ordinary direct-read firmware-stop consistency only'}


def check_emi(data, expected_cycle):
    """Check recorded native section operations; does not grant EMI ownership."""
    sections = {}
    for record in decode(data, expected_cycle):
        if record['kind'] == 8:
            sections.setdefault(record['transaction'], []).append(record['payload'])
    if not sections:
        raise ValueError('no EMI section recorded')
    for payloads in sections.values():
        if [int.from_bytes(p[:4], 'little') for p in payloads] != [1, 2, 2, 3, 4, 4, 2, 2]:
            raise ValueError('incomplete, reordered or reused EMI operation')
        _, adapter, image, base, index, source_offset, length, destination, image_bytes = EMI_SECTION.unpack(payloads[0])
        destination_offset = destination & 0xfffff
        if (not base or base > 0xffffffffffffffff - (EMI_WINDOW - 1) or index < 2 or
                not length or source_offset > image_bytes or length > image_bytes - source_offset or
                destination_offset > EMI_WINDOW or length > EMI_WINDOW - destination_offset):
            raise ValueError('EMI source or destination span is invalid')
        for entry, result, phase, policy in ((1, 2, 1, EMI_OPEN), (6, 7, 2, EMI_RESTRICT)):
            for row, stage in ((entry, 1), (result, 2)):
                if EMI_PROTECTION.unpack(payloads[row]) != (2, phase, stage, 1, base, base + EMI_WINDOW - 1, policy, 0):
                    raise ValueError('EMI lower protection call/result mismatch or failure')
        _, mapping, mapped_base, mapped_length = EMI_MAPPING.unpack(payloads[3])
        if not mapping or mapped_base != base or mapped_length != EMI_WINDOW:
            raise ValueError('missing or mismatched EMI mapping')
        for row, stage in ((4, 1), (5, 2)):
            if EMI_COPY.unpack(payloads[row]) != (4, stage, mapping, destination_offset, source_offset, length):
                raise ValueError('EMI copy does not match section and mapping')
    return {'checked_sections': list(sections),
            'scope': 'recorded native EMI section-operation consistency only'}


def check_off_poll(data, expected_cycle):
    """Check the recorded final CONN status condition, not the complete provider OFF."""
    polls = {}
    for record in decode(data, expected_cycle):
        if record['kind'] == 9 and int.from_bytes(record['payload'][:4], 'little') in (1, 2):
            polls.setdefault(record['transaction'], []).append(OFF_POLL.unpack(record['payload']))
    if not polls:
        raise ValueError('no OFF condition poll recorded')
    for rows in polls.values():
        if len(rows) != 2 or rows[0][0] != 1 or rows[1][0] != 2 or rows[0][1] != rows[1][1]:
            raise ValueError('incomplete, reordered or reused OFF poll')
        _, provider, reason, primary_count, secondary_count, primary, secondary, primary_valid, secondary_valid = rows[1]
        if reason != 1 or not primary_count or not secondary_count or (primary_valid, secondary_valid) != (1, 1):
            raise ValueError('missing complete terminal OFF condition evaluation')
        if (primary | secondary) & 2:
            raise ValueError('terminal CONN power-status pair is not clear')
    return {'checked_polls': list(polls),
            'scope': 'recorded terminal CONN OFF condition consistency only'}


def check_provider_off(data, expected_cycle):
    """Check recorded provider OFF operations, not shared-consumer ownership."""
    check_off_poll(data, expected_cycle)
    operations = {}
    for record in decode(data, expected_cycle):
        if record['kind'] == 9:
            operations.setdefault(record['transaction'], []).append(record['payload'])
    for payloads in operations.values():
        if [int.from_bytes(p[:4], 'little') for p in payloads] != [3, 4, 5, 6, 7, 8, 1, 2, 9]:
            raise ValueError('incomplete, reordered or reused provider OFF operation')
        _, provider, native_id, route, callback = OFF_ENTRY.unpack(payloads[0])
        if (native_id, route) != (1, 1):
            raise ValueError('not the normal CONN provider route')
        if any(int.from_bytes(p[4:8], 'little') != provider for p in payloads):
            raise ValueError('provider identity mismatch')
        _, _, primary, secondary, state, decision = OFF_STATE.unpack(payloads[1])
        if (not primary & 2 or not secondary & 2 or state != 1 or decision != 1):
            raise ValueError('provider was not dispatched from observed ON state')
        if OFF_DISPATCH.unpack(payloads[2]) != (5, provider, 0, 0x0b160001):
            raise ValueError('CONN power-down dispatch or SPM key mismatch')
        if OFF_PROTECT_ENTRY.unpack(payloads[3]) != (6, provider, 0x60000, 1):
            raise ValueError('wrong bus-protection request')
        _, _, before, stored, readback, reason, count, last, valid, returned, status = OFF_PROTECT_RESULT.unpack(payloads[4])
        if (stored != before | 0x60000 or readback & 0x60000 != 0x60000 or
                reason != 1 or not count or not valid or last & 0x60000 != 0x60000 or
                not returned or status):
            raise ValueError('bus-protection programming or completion missing')
        values = OFF_CONTROL.unpack(payloads[5])[2:]
        for index, (mask, set_bit) in enumerate(((2, True), (16, True), (1, False), (4, False), (8, False))):
            before, stored = values[2 * index:2 * index + 2]
            if stored != (before | mask if set_bit else before & ~mask):
                raise ValueError('CONN control store differs from native operation')
        if OFF_RETURN.unpack(payloads[8]) != (9, provider, 0, 0):
            raise ValueError('provider operation did not return success')
    return {'checked_provider_operations': list(operations),
            'scope': 'recorded CONN provider OFF operation consistency only'}


def check_image_sections(data, expected_cycle, expected_hash, expected_image_bytes, expected_sections):
    """Join independently supplied image metadata to recorded sections and EMI copies."""
    if len(expected_hash) != 32 or not any(expected_hash) or len(expected_sections) < 3:
        raise ValueError('requires reviewed image hash and section metadata including EMI')
    records = decode(data, expected_cycle)
    image_rows = [row for row in records if row['kind'] == 7 and
                  int.from_bytes(row['payload'][:4], 'little') in (5, 6, 7)]
    if [int.from_bytes(row['payload'][:4], 'little') for row in image_rows] != [5] + [6] * len(expected_sections) + [7]:
        raise ValueError('missing, repeated or reordered image metadata')
    _, adapter, image_id, image_bytes, count, digest = FW_IMAGE.unpack(image_rows[0]['payload'])
    if digest != expected_hash or image_bytes != expected_image_bytes or count != len(expected_sections):
        raise ValueError('image identity or section count mismatch')
    invocation = image_rows[0]['transaction']
    if any(row['transaction'] != invocation for row in image_rows):
        raise ValueError('mixed image invocations')
    for index, (row, expected) in enumerate(zip(image_rows[1:-1], expected_sections)):
        values = FW_SECTION.unpack(row['payload'])
        if values != (6, adapter, image_id, index, *expected):
            raise ValueError('section differs from independently supplied image metadata')
        source, length, destination, enc, key = expected
        if not length or source > image_bytes or length > image_bytes - source or destination + length > 0x100000000:
            raise ValueError('invalid image section span')
    if FW_IMAGE_RETURN.unpack(image_rows[-1]['payload']) != (7, adapter, image_id, 0):
        raise ValueError('divided image loader did not return success')
    check_emi(data, expected_cycle)
    emi = {}
    for row in records:
        if row['kind'] == 8:
            emi.setdefault(row['transaction'], []).append(row)
    seen = set()
    bases = set()
    for rows in emi.values():
        _, emi_adapter, emi_image, base, index, source, length, destination, size = EMI_SECTION.unpack(rows[0]['payload'])
        if emi_adapter != adapter or emi_image != image_id or size != image_bytes or index in seen or not 2 <= index < count:
            raise ValueError('unexpected or duplicate EMI section identity')
        if (source, length, destination) != tuple(expected_sections[index][:3]):
            raise ValueError('EMI operation differs from the image section')
        if not image_rows[index + 1]['sequence'] < rows[0]['sequence'] <= rows[-1]['sequence'] < image_rows[index + 2]['sequence']:
            raise ValueError('EMI operation is outside its native section interval')
        seen.add(index)
        bases.add(base)
    if len(bases) != 1:
        raise ValueError('EMI base changed within the image operation')
    if seen != set(range(2, count)):
        raise ValueError('not every required EMI section has complete operations')
    return {'checked_image': image_id, 'checked_emi_indices': sorted(seen),
            'scope': 'recorded image metadata and EMI coverage only; HIF submission and execution unchecked'}
