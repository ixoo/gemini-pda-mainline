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
# Non-DMA event payloads and cross-record lifecycle semantics remain unfinished.
KINDS = {IDENTITY, 2, 3, 4, 5, 6, 7, 8, 9, 10, TERMINAL}
TERMINAL_STATUSES = {1, 2, 3}  # producer-reported complete, failed, overflow


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
    validate_dma_payload(kind, transaction, payload)
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
