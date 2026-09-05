#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Differential section plans only; no Python step/START or hardware callbacks."""
import argparse
import ctypes as C
from pathlib import Path
import random
import struct
import subprocess
import sys
import zlib


class Context(C.Structure):
    _fields_ = [('data', C.c_void_p), ('size', C.c_size_t),
                ('count', C.c_uint), ('valid', C.c_int)]


class Plan(C.Structure):
    _fields_ = [('image', Context), ('sections', C.c_uint),
                ('ordinary_sections', C.c_uint), ('emi_sections', C.c_uint),
                ('ordinary_bytes', C.c_size_t), ('emi_bytes', C.c_size_t),
                ('valid', C.c_int)]


class Description(C.Structure):
    _fields_ = [(key, C.c_uint32) for key in ('offset', 'length', 'destination', 'emi_offset')] + [
        (key, C.c_uint) for key in ('emi', 'raw_encrypted', 'raw_key_index', 'encrypted', 'key_index')]


class View(C.Structure):
    _fields_ = [('data', C.c_void_p)] + Description._fields_


def fixture(count):
    data = bytearray(24 + count * 20)
    data[:4] = b'MTKE'
    struct.pack_into('<I', data, 8, count)
    for index in range(count):
        offset = 24 + count * 16 + index * 4
        struct.pack_into('<IBBHII', data, 24 + index * 16, offset,
                         255, 128, 0, 4, 0x1000 + index * 4 if index < 2 else 0xF0000000 + index * 4)
        data[offset:offset + 4] = bytes([index % 256]) * 4
    return crc(data)


def crc(data):
    data = bytearray(data)
    struct.pack_into('<I', data, 4, zlib.crc32(data[8:]))
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scratch', type=Path, required=True)
    args = ap.parse_args()
    scratch = args.scratch
    sys.path.insert(0, str(scratch))
    from wifi_whole_image import EmiOwner, OrdinaryTransport, WholeImage, Refusal

    class NoOwner(EmiOwner):
        def acquire(self, session):
            raise AssertionError('planning must not acquire resources')

    class NoTransport(OrdinaryTransport):
        def submit(self, *args):
            raise AssertionError('planning must not transfer')
        def start(self, *args):
            raise AssertionError('planning must not START')

    source = Path(__file__).resolve().parents[1] / 'src'
    adapter = scratch / 'crc-host.c'
    adapter.write_text('#include <zlib.h>\n#include "mtke.h"\n'
                       'u32 mtke_crc32(const u8 *p, size_t n) '
                       '{ return (u32)crc32(0, p, (uInt)n); }\n')
    library = scratch / 'plan.so'
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wconversion',
                    '-pedantic', '-shared', '-fPIC', '-I', str(scratch),
                    '-I', str(source), str(source / 'image-plan.c'),
                    str(scratch / 'mtke.c'), str(adapter), '-lz', '-o', str(library)], check=True)
    lib = C.CDLL(str(library))
    lib.mt6797_image_plan_prepare.argtypes = [C.POINTER(Plan), C.c_void_p, C.c_size_t]
    lib.mt6797_image_plan_describe.argtypes = [C.POINTER(Plan), C.c_uint, C.POINTER(Description)]
    lib.mt6797_image_plan_admit.argtypes = [C.POINTER(Plan)]
    lib.mt6797_image_plan_get_ordinary.argtypes = [C.POINTER(Plan), C.c_uint, C.POINTER(View)]
    lib.mt6797_image_plan_invalidate.argtypes = [C.POINTER(Plan)]
    cases = accepted = refused = described = 0
    plan = Plan()

    def check(data):
        nonlocal cases, accepted, refused, described
        cases += 1
        raw = C.create_string_buffer(bytes(data), max(1, len(data)))
        try:
            python = WholeImage(data, NoOwner(), NoTransport())
        except Refusal:
            python = None
        result = lib.mt6797_image_plan_prepare(C.byref(plan), raw, len(data))
        if python is None:
            assert result in (-1, -2) and not plan.valid
            assert not plan.sections and not plan.image.data and not plan.ordinary_bytes and not plan.emi_bytes
            refused += 1
        else:
            assert result == 0 and plan.valid
            count = len(python._sections)
            assert plan.sections == count
            assert plan.ordinary_sections == min(count, 2)
            assert plan.emi_sections == max(count - 2, 0)
            assert plan.ordinary_bytes == sum(len(x.data) for x in python._sections[:2])
            assert plan.emi_bytes == sum(len(x.data) for x in python._sections[2:])
            assert lib.mt6797_image_plan_admit(C.byref(plan)) == (-3 if count > 2 else 0)
            for index, section in enumerate(python._sections):
                view = View()
                description = Description()
                assert lib.mt6797_image_plan_describe(C.byref(plan), index, C.byref(description)) == 0
                offset, key, encrypted, _, length, destination = struct.unpack_from('<IBBHII', data, 24 + index * 16)
                assert description.offset == offset and description.length == length
                assert description.destination == destination == section.destination
                assert bytes(data[offset:offset + length]) == section.data
                assert description.raw_encrypted == encrypted and description.raw_key_index == key
                assert description.emi == (index >= 2)
                assert description.emi_offset == (destination & 0xfffff if index >= 2 else 0)
                assert description.encrypted == (index < 2 and bool(encrypted))
                assert description.key_index == (key & 3 if index < 2 and encrypted else 0)
                result = lib.mt6797_image_plan_get_ordinary(C.byref(plan), index, C.byref(view))
                if count > 2:
                    assert result == -3 and not any(getattr(view, name) for name, _ in View._fields_)
                else:
                    assert result == 0 and C.string_at(view.data, view.length) == section.data
                described += 1
            accepted += 1
        invalid = Description()
        C.memset(C.byref(invalid), 0xff, C.sizeof(invalid))
        assert lib.mt6797_image_plan_describe(C.byref(plan), 256, C.byref(invalid)) != 0
        assert not any(bytes(invalid))
        lib.mt6797_image_plan_invalidate(C.byref(plan))
        assert lib.mt6797_image_plan_admit(C.byref(plan)) == -1
        output = View()
        C.memset(C.byref(output), 0xff, C.sizeof(output))
        assert lib.mt6797_image_plan_get_ordinary(C.byref(plan), 0, C.byref(output)) == -1
        assert not any(getattr(output, name) for name, _ in View._fields_)

    for count in range(1, 257):
        check(fixture(count))
    baseline = fixture(4)
    for end in range(len(baseline)):
        check(baseline[:end])
    rng = random.Random(6797)
    for _ in range(1000):
        data = bytearray(baseline)
        data[rng.randrange(len(data))] ^= rng.randrange(1, 256)
        check(data)
        check(crc(data))
    print(f'PASS differential_plans={cases} accepted={accepted} refused={refused} all_section_descriptions={described}')
    print('mixed_image_admission=unresolved-owner; executable_views_on_refusal=0; hardware_callbacks=0')


if __name__ == '__main__':
    main()
