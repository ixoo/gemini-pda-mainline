#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Synthetic differential checks; explicit pinned oracle, no firmware files."""
import argparse
import ctypes as C
import hashlib
import importlib.util
import random
import struct
import subprocess
import tempfile
from pathlib import Path
import zlib

PIN = '4d8b57da9dabf20070aff27f6a5cc21f1f958c8b127af70ced8620a9be5c1f98'
HERE = Path(__file__).resolve().parent

class Context(C.Structure):
    _fields_ = [('data', C.c_void_p), ('size', C.c_size_t),
                ('count', C.c_uint), ('valid', C.c_int)]

class View(C.Structure):
    _fields_ = [('data', C.c_void_p)] + [(x, C.c_uint32) for x in
                ('offset', 'length', 'destination', 'emi_offset')] + [
                (x, C.c_uint) for x in ('emi', 'raw_encrypted', 'raw_key_index', 'encrypted', 'key_index')]

def crc(data):
    data = bytearray(data)
    struct.pack_into('<I', data, 4, zlib.crc32(data[8:]))
    return bytes(data)

def make(count=4):
    data = bytearray(24 + count * 16 + count * 8)
    data[:4] = b'MTKE'
    struct.pack_into('<I', data, 8, count)
    for i in range(count):
        struct.pack_into('<IBBHII', data, 24 + i * 16,
                         24 + count * 16 + i * 8, 255, 128, 0, 8,
                         0x1000 + i * 8 if i < 2 else 0x90000000 + i * 8)
    return crc(data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--oracle', type=Path, required=True)
    args = ap.parse_args()
    if hashlib.sha256(args.oracle.read_bytes()).hexdigest() != PIN:
        raise SystemExit('oracle digest mismatch')
    spec = importlib.util.spec_from_file_location('oracle', args.oracle)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    # All generated binaries are scoped to this managed temporary directory.
    with tempfile.TemporaryDirectory(prefix='mtke-parser-') as tmp:
        tmp = Path(tmp)
        adapter = tmp / 'crc-host.c'
        adapter.write_text('#include <zlib.h>\n#include "mtke.h"\n'
                           'u32 mtke_crc32(const u8 *p, size_t n) '
                           '{ return (u32)crc32(0, p, (uInt)n); }\n')
        library = tmp / 'parser.so'
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                        '-Wconversion', '-pedantic', '-shared', '-fPIC',
                        '-I', str(HERE), str(HERE / 'mtke.c'), str(adapter),
                        '-lz', '-o', str(library)], check=True)
        lib = C.CDLL(str(library))
        lib.mtke_parse.argtypes = [C.POINTER(Context), C.c_void_p, C.c_size_t]
        lib.mtke_get.argtypes = [C.POINTER(Context), C.c_uint, C.POINTER(View)]
        ctx = Context()
        total = accepted = 0
        def check(data):
            nonlocal total, accepted
            total += 1
            try:
                result = oracle.parse_mtke(data)
                good = result['status'] == 'structurally_valid'
            except oracle.Refusal:
                good = False
            buf = C.create_string_buffer(data)
            got = lib.mtke_parse(C.byref(ctx), buf, len(data)) == 0
            assert got == good, (total, len(data))
            view = View()
            if not good:
                assert not ctx.valid and not ctx.count and not ctx.data and not ctx.size
                assert lib.mtke_get(C.byref(ctx), 0, C.byref(view)) == -1
                assert not any(bytes(view))
                return
            accepted += 1
            assert ctx.count == result['section_count']
            encrypted_count = 0
            for i in range(ctx.count):
                assert lib.mtke_get(C.byref(ctx), i, C.byref(view)) == 0
                off, key, enc, _, length, dst = struct.unpack_from('<IBBHII', data, 24 + 16*i)
                emi = i >= 2
                encrypted = not emi and bool(enc)
                assert (view.offset, view.length, view.destination, view.emi,
                        view.emi_offset, view.encrypted, view.key_index) == (
                        off, result['section_lengths'][i], dst, emi,
                        dst & 0xfffff if emi else 0, encrypted, key & 3 if encrypted else 0)
                assert (view.raw_encrypted, view.raw_key_index) == (enc, key)
                assert length == view.length
                assert view.data == C.addressof(buf) + off
                assert C.string_at(view.data, length) == data[off:off+length]
                encrypted_count += encrypted
            assert encrypted_count == result['hif_encrypted_section_count']
            assert lib.mtke_get(C.byref(ctx), ctx.count, C.byref(view)) == -1
            assert not any(bytes(view))
            assert bytes(buf)[:-1] == data
        for count in (1, 2, 3, 4, 256):
            check(make(count))
        base = make()
        for end in range(len(base)):
            check(base[:end])
        check(base + bytes(1024*1024 + 1 - len(base)))
        for pos in range(len(base)):
            for value in (0, 1, 3, 127, 255):
                b = bytearray(base); b[pos] = value
                check(bytes(b)); check(crc(b))
        for pos in (8, 20, 24, 32, 36, 40, 48, 52, 56, 64, 68):
            for value in (0, 1, 24, 87, 88, 120, 256, 257, 0x7ffff,
                          0x80000, 0xfffff, 0xfffffff8, 0xfffffff9, 0xffffffff):
                b = bytearray(base); struct.pack_into('<I', b, pos, value)
                check(crc(b))
        # Exact 32-bit endpoint, source adjacency and masked EMI alias cases.
        for dst in (0xfffffff8, 0xfffffff9):
            b = bytearray(base); struct.pack_into('<I', b, 36, dst); check(crc(b))
        for dst in (0x10000010, 0x10000018, 0x1007fff8, 0x1007fff9, 0x10080000):
            b = bytearray(base); struct.pack_into('<I', b, 84, dst); check(crc(b))
        rng = random.Random(6797)
        for _ in range(3000):
            b = bytearray(make(rng.randrange(1, 12)))
            for _ in range(rng.randrange(1, 6)):
                b[rng.randrange(len(b))] = rng.randrange(256)
            check(crc(b))
        assert lib.mtke_parse(C.byref(ctx), None, 24) == -1
        assert lib.mtke_parse(None, None, 0) == -1
        assert lib.mtke_get(None, 0, C.byref(View())) == -1
        print(f'PASS: {total} differential cases; {accepted} accepted with all views compared')

if __name__ == '__main__':
    main()
