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
# Firmware execution and whole-cycle lifecycle semantics remain unfinished.
KINDS = {IDENTITY, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, TERMINAL}
TERMINAL_STATUSES = {1, 2, 3}  # producer-reported complete, failed, overflow

RECOVERY = struct.Struct('<6Ii')


def validate_recovery_payload(transaction, payload):
    if transaction or len(payload) != RECOVERY.size:
        raise ValueError('recovery requires transaction zero and exact payload size')
    stage, timeout, owned, before, after, length, status = RECOVERY.unpack(payload)
    if stage not in (1, 2) or timeout != 12 or owned not in (0, 1) or status > 0:
        raise ValueError('invalid recovery discriminator')
    if stage == 1 and any((owned, before, after, length, status)):
        raise ValueError('recovery entry contains a result')
    if stage == 2 and not status and (not owned or after & 0x4d != 5 or
                                     length & 0xffe0 != 12 * 64 * 32):
        raise ValueError('successful recovery result lacks verified arm state')


def check_recovery_prefix(records):
    """Require recorded takeover before activity; no hardware-recovery verdict."""
    if (len(records) < 3 or records[0]['kind'] != IDENTITY or
            [r['kind'] for r in records[1:3]] != [11, 11] or
            any(r['kind'] == 11 for r in records[3:])):
        raise ValueError('missing, misplaced or repeated recovery prefix')
    for record in records[1:3]:
        validate_recovery_payload(record['transaction'], record['payload'])
    entry, result = [RECOVERY.unpack(r['payload']) for r in records[1:3]]
    if entry[0] != 1 or result[0] != 2 or result[-1]:
        raise ValueError('recovery prefix does not record successful takeover')


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
FW_READ_ENTRY = struct.Struct('<2I')
FW_READ_ALLOCATION = struct.Struct('<5I')
FW_READ_RESULT = struct.Struct('<4Iq')
FW_READ_RETURN = struct.Struct('<5I')
FW_TX_PAYLOAD = struct.Struct('<8I32s')
FW_TX_DMA = struct.Struct('<5I')
FW_TX_RETURN = struct.Struct('<6I')
FW_STOP_WORKERS = struct.Struct('<3Ii3Q')
FW_STOP_LAYOUTS = {1: FW_STOP_ENTRY, 2: FW_STOP_COMMAND,
                   3: FW_STOP_POLL, 4: FW_STOP_RETURN,
                   5: FW_IMAGE, 6: FW_SECTION, 7: FW_IMAGE_RETURN,
                   8: FW_READ_ENTRY, 9: FW_READ_ALLOCATION,
                   10: FW_READ_RESULT, 11: FW_READ_RETURN,
                   12: FW_TX_PAYLOAD, 13: FW_TX_DMA, 14: FW_TX_RETURN,
                   15: FW_STOP_WORKERS}


def validate_stop_payload(transaction, payload):
    if not transaction or len(payload) < 4:
        raise ValueError('stop requires an invocation ID and subtype')
    subtype = int.from_bytes(payload[:4], 'little')
    layout = FW_STOP_LAYOUTS.get(subtype)
    if layout is None or len(payload) != layout.size:
        raise ValueError('unsupported stop subtype or payload size')
    values = layout.unpack(payload)
    if subtype == 15:
        if values[1] != transaction or values[2] not in (0, 1):
            raise ValueError('invalid worker-wait binding or configuration')
        if not values[2] and any(values[4:6]):
            raise ValueError('unselected worker waits contain results')
        return
    if subtype >= 12:
        if not values[1] or not values[2] or not 1 <= values[3] <= 8 or values[3] != transaction:
            raise ValueError('payload witness requires adapter, image and matching chunk ordinal')
        if subtype == 12 and (values[4] > 1 or not 1 <= values[6] <= 2048 or
                              values[7] != values[6] + 8 or not any(values[8])):
            raise ValueError('invalid payload extent or digest')
        if subtype >= 13 and not values[4]:
            raise ValueError('payload witness requires a DMA transaction')
        if subtype == 14 and values[5] not in (0, 1):
            raise ValueError('invalid native port result')
        return
    if subtype >= 8:
        if not values[1]:
            raise ValueError('firmware read requires an adapter ID')
        if subtype == 9 and values[4] not in (0, 1):
            raise ValueError('invalid allocation presence')
        if subtype == 10 and (values[3] not in (0, 1) or (not values[3] and values[4])):
            raise ValueError('invalid firmware read result attribution')
        if subtype == 11 and (values[2] not in (0, 1) or values[4] not in (0, 1) or
                              (not values[2] and any(values[3:]))):
            raise ValueError('invalid firmware mapping publication')
        return
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
    if kind == 11:
        validate_recovery_payload(transaction, payload)
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


def check_stop_workers(data, expected_cycle):
    """Require successful native removal waits, not exited tasks or safe teardown."""
    stop = check_stop(data, expected_cycle)
    if len(stop['checked_stops']) != 1:
        raise ValueError('requires one ordinary stop for worker-wait attribution')
    rows = decode(data, expected_cycle)
    waits = [row for row in rows if row['kind'] == 7 and
             int.from_bytes(row['payload'][:4], 'little') == 15]
    entry = next(row for row in rows if row['kind'] == 7 and
                 int.from_bytes(row['payload'][:4], 'little') == 1)
    if len(waits) != 1:
        raise ValueError('missing or repeated worker-wait summary')
    _, device, multithread, halt, hif, rx, main = FW_STOP_WORKERS.unpack(waits[0]['payload'])
    if device != FW_STOP_ENTRY.unpack(entry['payload'])[1] or waits[0]['sequence'] >= entry['sequence']:
        raise ValueError('worker waits do not precede their adapter stop')
    if multithread != 1 or halt or not all((hif, rx, main)):
        raise ValueError('native halt lock or worker completion wait failed')
    return {'checked_device': device, 'checked_stop': stop['checked_stops'][0],
            'scope': 'successful recorded native removal waits only; worker exit and quiescence unchecked'}


def check_firmware_read(data, expected_cycle):
    """Check allocation/read/publication sizes, not actual buffer identity or contents."""
    reads = {}
    for row in decode(data, expected_cycle):
        if row['kind'] == 7 and int.from_bytes(row['payload'][:4], 'little') in (8, 9, 10, 11):
            reads.setdefault(row['transaction'], []).append(row['payload'])
    if not reads:
        raise ValueError('no firmware file read recorded')
    for payloads in reads.values():
        if [int.from_bytes(p[:4], 'little') for p in payloads] != [8, 9, 10, 11]:
            raise ValueError('incomplete, reordered or reused firmware read invocation')
        device = FW_READ_ENTRY.unpack(payloads[0])[1]
        if any(int.from_bytes(p[4:8], 'little') != device for p in payloads):
            raise ValueError('firmware read adapter changed')
        _, _, requested, allocated, present = FW_READ_ALLOCATION.unpack(payloads[1])
        if not requested or allocated < requested or allocated != (requested + 3) & ~3 or not present:
            raise ValueError('missing allocation or invalid native allocation extent')
        if FW_READ_RESULT.unpack(payloads[2]) != (10, device, requested, 1, requested):
            raise ValueError('firmware read failed, was skipped or did not fill the requested extent')
        if FW_READ_RETURN.unpack(payloads[3]) != (11, device, 1, requested, 1):
            raise ValueError('firmware mapping did not publish the complete read')
    return {'checked_reads': list(reads),
            'scope': 'recorded firmware allocation/read/publication extents only; no buffer identity proof'}


def check_shutdown_bindings(data, expected_cycle):
    """Join one ordinary stop and checked DMA to a closed software HIF lifetime."""
    binding = check_dma_bindings(data, expected_cycle)
    check_dma(data, expected_cycle)
    stop = check_stop(data, expected_cycle)
    if len(stop['checked_stops']) != 1:
        raise ValueError('requires exactly one ordinary stop in the HIF lifetime')
    device = binding['checked_device']
    live = stopped = False
    for row in decode(data, expected_cycle):
        kind, payload = row['kind'], row['payload']
        if kind == 2:
            subtype = int.from_bytes(payload[:4], 'little')
            if subtype == 1:
                live = True
            else:
                if not stopped:
                    raise ValueError('HIF released before ordinary stop returned')
                live = False
        elif kind in (3, 4, 5, 6) and stopped:
            raise ValueError('DMA activity recorded after adapter stop returned')
        elif kind == 7:
            subtype = int.from_bytes(payload[:4], 'little')
            if subtype not in (1, 2, 3, 4):
                continue
            if not live:
                raise ValueError('stop record outside the live HIF binding')
            if subtype == 1 and FW_STOP_ENTRY.unpack(payload)[1] != device:
                raise ValueError('stop adapter differs from the DMA HIF binding')
            if subtype == 4:
                stopped = True
    return {'checked_device': device, 'checked_stop': stop['checked_stops'][0],
            'checked_transactions': binding['checked_transactions'],
            'scope': 'recorded DMA and ordinary stop within one software HIF lifetime only'}


def check_firmware_bindings(data, expected_cycle):
    """Join recorded file reads to the DMA/stop binding; no loaded-byte proof."""
    shutdown = check_shutdown_bindings(data, expected_cycle)
    reads = check_firmware_read(data, expected_cycle)
    live = stopping = False
    for row in decode(data, expected_cycle):
        kind, payload = row['kind'], row['payload']
        subtype = int.from_bytes(payload[:4], 'little')
        if kind == 2:
            live = subtype == 1
        elif kind == 7 and subtype == 1:
            stopping = True
        elif kind == 7 and subtype in (8, 9, 10, 11):
            if not live or stopping:
                raise ValueError('firmware read outside the pre-stop HIF lifetime')
            if int.from_bytes(payload[4:8], 'little') != shutdown['checked_device']:
                raise ValueError('firmware read adapter differs from the DMA/stop binding')
    return {**shutdown, 'checked_reads': reads['checked_reads'],
            'scope': 'recorded file reads, DMA and stop share one software HIF lifetime only'}


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


COMMON_OFF_LAYOUTS = {1: struct.Struct('<IIIi'), 2: struct.Struct('<3I'),
                      3: struct.Struct('<4I'), 4: struct.Struct('<2I'),
                      5: struct.Struct('<2I'), 6: struct.Struct('<IIii')}

REQUEST_LAYOUTS = {16: struct.Struct('<3I'), 17: struct.Struct('<5I'),
                   18: struct.Struct('<2I'), 19: struct.Struct('<4I'),
                   20: struct.Struct('<IIi'), 21: struct.Struct('<IIiIiI'),
                   22: struct.Struct('<3I'), 23: struct.Struct('<3I'),
                   24: struct.Struct('<IIi'), 25: struct.Struct('<4I'),
                   26: struct.Struct('<4I'), 27: struct.Struct('<4Ii')}


def request_values(row):
    """Decode a typed request record without changing opaque kind-10 framing."""
    subtype = int.from_bytes(row['payload'][:4], 'little')
    layout = REQUEST_LAYOUTS.get(subtype)
    if layout is None or len(row['payload']) != layout.size:
        raise ValueError('invalid request subtype or payload size')
    values = layout.unpack(row['payload'])
    if row['transaction'] not in (1, 2) or values[1] != row['transaction']:
        raise ValueError('request identity disagrees with envelope')
    return values


def check_common_off(data, expected_cycle):
    """Join the synchronous common/CCF/provider scope; no outer ioctl proof."""
    check_provider_off(data, expected_cycle)
    decoded = decode(data, expected_cycle)
    if any(row['kind'] == TERMINAL and int.from_bytes(row['payload'], 'little') != 1 for row in decoded):
        raise ValueError('common OFF capture has a failed producer terminal')
    records = []
    for row in decoded:
        if row['kind'] == 10 and int.from_bytes(row['payload'][:4], 'little') in REQUEST_LAYOUTS:
            request_values(row)
        elif row['kind'] in (9, 10):
            records.append(row)
    order = [(10, n) for n in (1, 2, 3)] + [(9, n) for n in (3, 4, 5, 6, 7, 8, 1, 2, 9)] + [(10, n) for n in (4, 5, 6)]
    if [(row['kind'], int.from_bytes(row['payload'][:4], 'little')) for row in records] != order:
        raise ValueError('missing, repeated or reordered common/provider scope')
    transaction = records[0]['transaction']
    common_id = int.from_bytes(records[0]['payload'][4:8], 'little')
    if not transaction or not common_id:
        raise ValueError('common OFF requires invocation and owner ordinals')
    values = {}
    for row in records:
        if row['transaction'] != transaction or int.from_bytes(row['payload'][4:8], 'little') != common_id:
            raise ValueError('common/provider identity mismatch')
        if row['kind'] == 10:
            subtype = int.from_bytes(row['payload'][:4], 'little')
            layout = COMMON_OFF_LAYOUTS[subtype]
            if len(row['payload']) != layout.size:
                raise ValueError('invalid common OFF payload size')
            values[subtype] = layout.unpack(row['payload'])
    expected = {1: (1, common_id, 3, 0), 2: (2, common_id, 1),
                3: (3, common_id, 1, 1), 4: (4, common_id),
                5: (5, common_id), 6: (6, common_id, 0, 0)}
    if values != expected:
        raise ValueError('common OFF route, binding or result rejected')
    return {'checked_common_operation': transaction, 'checked_provider_operation': transaction,
            'scope': 'recorded synchronous common/CCF/provider attribution; outer ioctl and isolation unchecked'}


def check_request_cycle(data, expected_cycle):
    """Join native request records to common OFF; no whole-cycle admission."""
    common = check_common_off(data, expected_cycle)
    rows = [row for row in decode(data, expected_cycle) if row['kind'] in (9, 10) and
            not (row['kind'] == 10 and int.from_bytes(row['payload'][:4], 'little') in (25, 26, 27))]
    lower = [(10, n) for n in (1, 2, 3)] + [(9, n) for n in (3, 4, 5, 6, 7, 8, 1, 2, 9)] + [(10, n) for n in (4, 5, 6)]
    order = ([(10, n) for n in (16, 17, 18, 19, 20, 21, 24, 16, 17, 18, 19, 22)] +
             lower + [(10, n) for n in (23, 20, 21, 24)])
    if [(row['kind'], int.from_bytes(row['payload'][:4], 'little')) for row in rows] != order:
        raise ValueError('missing, repeated or reordered request/common scope')
    requests = [row for row in rows if row['kind'] == 10 and
                int.from_bytes(row['payload'][:4], 'little') in REQUEST_LAYOUTS]
    for index, row in enumerate(requests):
        values = request_values(row)
        subtype, request = values[:2]
        expected_request = 1 if index < 7 else 2
        if request != expected_request:
            raise ValueError('wrong ON/OFF request identity')
        opid = 3 if request == 1 else 4
        expected = {16: (0x80000003 if request == 1 else 3,),
                    17: (opid, 3, 4000), 18: (), 19: (opid, 3),
                    20: (0,), 22: (1,), 23: (1,), 24: (0,)}
        if subtype == 21:
            if values[2] <= 0 or values[3:] != (1, 0, 1):
                raise ValueError('native waiter did not observe successful completion')
        elif values[2:] != expected[subtype]:
            raise ValueError('request argument, route, link or result rejected')
    if common['checked_common_operation'] != 1:
        raise ValueError('request references a different common operation')
    return {'checked_requests': [1, 2], 'checked_common_operation': 1,
            'scope': 'recorded native ioctl/worker/common attribution only; firmware causality and isolation unchecked'}


def check_request_firmware(data, expected_cycle, expected_hash, expected_image_bytes, expected_sections):
    """Join request workers to read/image and teardown records, not hardware bytes."""
    check_request_cycle(data, expected_cycle)
    binding = check_firmware_bindings(data, expected_cycle)
    image = check_image_read(data, expected_cycle, expected_hash, expected_image_bytes, expected_sections)
    check_image_sections(data, expected_cycle, expected_hash, expected_image_bytes, expected_sections)
    device, image_id = binding['checked_device'], image['checked_image']
    if binding['checked_reads'] != [image_id]:
        raise ValueError('requires exactly the request-bound firmware read')
    rows = decode(data, expected_cycle)
    links = [row for row in rows if row['kind'] == 10 and
             int.from_bytes(row['payload'][:4], 'little') in (25, 26, 27)]
    expected = [(25, 1, device, image_id), (26, 1, device, image_id),
                (27, 1, device, image_id, 0)]
    if [request_values(row) for row in links] != expected:
        raise ValueError('missing, repeated or mismatched request/firmware links')

    def sequence(kind, subtype, transaction=None):
        selected = [row['sequence'] for row in rows if row['kind'] == kind and
                    int.from_bytes(row['payload'][:4], 'little') == subtype and
                    (transaction is None or row['transaction'] == transaction)]
        if len(selected) != 1:
            raise ValueError('ambiguous request/firmware boundary')
        return selected[0]

    on_begin, on_end = sequence(10, 19, 1), sequence(10, 20, 1)
    off_begin, off_end = sequence(10, 19, 2), sequence(10, 20, 2)
    read_begin, image_begin, image_end = [row['sequence'] for row in links]
    reads = [row['sequence'] for row in rows if row['kind'] == 7 and
             int.from_bytes(row['payload'][:4], 'little') in (8, 9, 10, 11)]
    images = [row['sequence'] for row in rows if row['kind'] == 7 and
              int.from_bytes(row['payload'][:4], 'little') in (5, 6, 7)]
    if not (on_begin < sequence(2, 1) < read_begin < min(reads) <= max(reads) <
            image_begin < min(images) <= max(images) < image_end < on_end):
        raise ValueError('firmware read/image is outside its recorded ON worker scope')
    if not (off_begin < sequence(7, 1) < sequence(7, 4) < sequence(2, 2) <
            sequence(10, 22, 2) < off_end):
        raise ValueError('stop/release is outside the recorded OFF worker scope')
    if any(row['kind'] in (3, 4, 5, 6) and not
           (on_begin < row['sequence'] < on_end or off_begin < row['sequence'] < off_end)
           for row in rows):
        raise ValueError('DMA activity recorded outside either request worker interval')
    return {'checked_requests': [1, 2], 'checked_image': image_id, 'checked_device': device,
            'scope': 'recorded request/read/image/EMI and teardown joins; submitted byte identity, quiescence and isolation unchecked'}


def _image_metadata(data, expected_cycle, expected_hash, expected_image_bytes, expected_sections):
    """Validate one successful image operation against independently supplied metadata."""
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
    return records, image_rows, adapter, image_id, image_bytes, count


def check_image_read(data, expected_cycle, expected_hash, expected_image_bytes, expected_sections):
    """Join image records to a completed read; no interval immutability proof."""
    records, image_rows, adapter, image_id, image_bytes, _ = _image_metadata(
        data, expected_cycle, expected_hash, expected_image_bytes, expected_sections)
    check_firmware_read(data, expected_cycle)
    reads = [row for row in records if row['kind'] == 7 and
             row['transaction'] == image_id and
             int.from_bytes(row['payload'][:4], 'little') in (8, 9, 10, 11)]
    if image_rows[0]['transaction'] != image_id or len(reads) != 4:
        raise ValueError('image does not identify its recorded read')
    if FW_READ_RETURN.unpack(reads[-1]['payload']) != (11, adapter, 1, image_bytes, 1):
        raise ValueError('image adapter or extent differs from its read')
    if reads[-1]['sequence'] >= image_rows[0]['sequence']:
        raise ValueError('image began before its read completed')
    return {'checked_image': image_id, 'checked_read': image_id,
            'scope': 'recorded read/image lineage only; immutability, HIF and EMI execution unchecked'}


def check_image_sections(data, expected_cycle, expected_hash, expected_image_bytes, expected_sections):
    """Join independently supplied image metadata to recorded sections and EMI copies."""
    records, image_rows, adapter, image_id, image_bytes, count = _image_metadata(
        data, expected_cycle, expected_hash, expected_image_bytes, expected_sections)
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


def check_image_tx(data, expected_cycle, expected_hash, expected_image_bytes,
                   expected_sections, expected_payload_hashes):
    """Join eight pre-map payload digests to complete DMA; no interval immutability proof."""
    rows, images, device, image_id, _, _ = _image_metadata(
        data, expected_cycle, expected_hash, expected_image_bytes, expected_sections)
    binding = check_dma_bindings(data, expected_cycle)
    check_dma(data, expected_cycle)
    if binding['checked_device'] != device or images[0]['transaction'] != image_id:
        raise ValueError('payload image does not identify the live HIF binding')
    spans = []
    for section, (offset, length, *_) in enumerate(expected_sections[:2]):
        for relative in range(0, length, 2048):
            spans.append((section, offset + relative, min(2048, length - relative)))
    if len(spans) != 8 or len(expected_payload_hashes) != 8 or any(
            len(digest) != 32 or not any(digest) for digest in expected_payload_hashes):
        raise ValueError('requires independently reviewed digests for exactly eight chunks')
    tx_rows = [row for row in rows if row['kind'] == 7 and
               int.from_bytes(row['payload'][:4], 'little') in (12, 13, 14)]
    if [int.from_bytes(row['payload'][:4], 'little') for row in tx_rows] != [12, 13, 14] * 8:
        raise ValueError('missing, repeated or reordered payload witnesses')
    used = set()
    for index, ((section, offset, length), digest) in enumerate(zip(spans, expected_payload_hashes)):
        chunk = index + 1
        payload, link, returned = tx_rows[index * 3:index * 3 + 3]
        if any(row['transaction'] != chunk for row in (payload, link, returned)):
            raise ValueError('payload chunk ordinal changed')
        if FW_TX_PAYLOAD.unpack(payload['payload']) != (
                12, device, image_id, chunk, section, offset, length, length + 8, digest):
            raise ValueError('pre-map payload differs from independently supplied image chunk')
        _, link_device, link_image, link_chunk, transaction = FW_TX_DMA.unpack(link['payload'])
        if (link_device, link_image, link_chunk) != (device, image_id, chunk) or transaction in used:
            raise ValueError('mismatched or reused payload DMA join')
        used.add(transaction)
        if FW_TX_RETURN.unpack(returned['payload']) != (14, device, image_id, chunk, transaction, 1):
            raise ValueError('native payload port did not return true for the joined transfer')
        transfers = [row for row in rows if row['kind'] in (3, 4, 5, 6) and
                     payload['sequence'] < row['sequence'] < returned['sequence']]
        if len(transfers) != 9 or any(row['transaction'] != transaction for row in transfers):
            raise ValueError('payload span does not enclose exactly its complete DMA transaction')
        mapped = transfers[0]
        dma_device, direction, requested, rounded, _, port, branch = DMA_MAP.unpack(mapped['payload'])
        logical = length + 8
        if (dma_device, direction, requested, rounded, port, branch) != (
                device, 1, logical, ((logical + 511) // 512) * 512, 0x34, 1):
            raise ValueError('payload DMA extent, direction or selected native route changed')
        if not (images[section + 1]['sequence'] < payload['sequence'] < mapped['sequence'] <
                link['sequence'] < transfers[1]['sequence'] < transfers[-1]['sequence'] <
                returned['sequence'] < images[section + 2]['sequence']):
            raise ValueError('payload witness is outside its section or DMA phase')
    return {'checked_image': image_id, 'checked_device': device,
            'checked_payload_chunks': list(range(1, 9)), 'checked_payload_dma': sorted(used),
            'scope': 'pre-map payload digests joined to recorded DMA completion; buffer immutability and firmware execution unchecked'}


def check_request_tx(data, expected_cycle, expected_hash, expected_image_bytes,
                     expected_sections, expected_payload_hashes):
    """Compose request/read/image/EMI/stop checks with the pre-map payload witness."""
    check_request_firmware(data, expected_cycle, expected_hash, expected_image_bytes, expected_sections)
    result = check_image_tx(data, expected_cycle, expected_hash, expected_image_bytes,
                            expected_sections, expected_payload_hashes)
    return {**result, 'checked_requests': [1, 2],
            'scope': 'recorded request, firmware, pre-map payload, DMA, EMI and stop joins; immutability, quiescence, isolation and execution unchecked'}
