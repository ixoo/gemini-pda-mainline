#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check the pinned private WLAN image against the C MTKE planner, without I/O."""

import argparse
import ctypes as c
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / 'experiments/2026-09-05-mt6797-whole-image-plan'
PARSER = ROOT / 'experiments/2026-09-05-mt6797-hif-parser-compile/src'
IMAGE_SHA256 = 'a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd'


class Context(c.Structure):
    _fields_ = [('data', c.c_void_p), ('size', c.c_size_t),
                ('count', c.c_uint), ('valid', c.c_int)]


class Plan(c.Structure):
    _fields_ = [('image', Context), ('sections', c.c_uint),
                ('ordinary_sections', c.c_uint), ('emi_sections', c.c_uint),
                ('ordinary_bytes', c.c_size_t), ('emi_bytes', c.c_size_t),
                ('valid', c.c_int)]


class Description(c.Structure):
    _fields_ = [(name, c.c_uint32) for name in
                ('offset', 'length', 'destination', 'emi_offset')] + [
                    (name, c.c_uint) for name in
                    ('emi', 'raw_encrypted', 'raw_key_index', 'encrypted', 'key_index')]


class View(c.Structure):
    _fields_ = [('data', c.c_void_p)] + Description._fields_


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    spec = json.loads((PLAN / 'inputs.json').read_text())
    for name, expected in spec['plan_files'].items():
        assert sha256((PLAN / 'src' / name).read_bytes()) == expected
    for name in ('mtke.c', 'mtke.h'):
        assert sha256((PARSER / name).read_bytes()) == spec['parser_files'][name]
    data = args.image.read_bytes()
    assert sha256(data) == IMAGE_SHA256 and len(data) == 411632

    with tempfile.TemporaryDirectory(prefix='mt6797-plan-') as directory:
        temp = Path(directory)
        (temp / 'crc-host.c').write_text(
            '#include <zlib.h>\n#include "mtke.h"\n'
            'u32 mtke_crc32(const u8 *p, size_t n) '
            '{ return (u32)crc32(0, p, (uInt)n); }\n')
        library = temp / 'plan.so'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-Wconversion', '-pedantic', '-shared', '-fPIC',
                        '-I', str(PARSER), '-I', str(PLAN / 'src'),
                        str(PLAN / 'src/image-plan.c'), str(PARSER / 'mtke.c'),
                        str(temp / 'crc-host.c'), '-lz', '-o', str(library)],
                       check=True, capture_output=True)
        lib = c.CDLL(str(library))
        lib.mt6797_image_plan_prepare.argtypes = [c.POINTER(Plan), c.c_void_p, c.c_size_t]
        lib.mt6797_image_plan_describe.argtypes = [c.POINTER(Plan), c.c_uint, c.POINTER(Description)]
        lib.mt6797_image_plan_admit.argtypes = [c.POINTER(Plan)]
        lib.mt6797_image_plan_get_ordinary.argtypes = [c.POINTER(Plan), c.c_uint, c.POINTER(View)]
        lib.mt6797_image_plan_invalidate.argtypes = [c.POINTER(Plan)]
        storage = c.create_string_buffer(data)
        plan = Plan()
        assert lib.mt6797_image_plan_prepare(c.byref(plan), storage, len(data)) == 0
        assert plan.valid and (plan.sections, plan.ordinary_sections,
                               plan.emi_sections) == (4, 2, 2)
        assert (plan.ordinary_bytes, plan.emi_bytes) == (14832, 396688)
        sections = []
        for index in range(plan.sections):
            section = Description()
            assert lib.mt6797_image_plan_describe(c.byref(plan), index,
                                                   c.byref(section)) == 0
            sections.append({'index': index, 'route': 'emi' if section.emi else 'ordinary',
                             'length': section.length, 'encrypted': bool(section.encrypted)})
        assert lib.mt6797_image_plan_admit(c.byref(plan)) == -3
        view = View()
        c.memset(c.byref(view), 0xff, c.sizeof(view))
        assert lib.mt6797_image_plan_get_ordinary(c.byref(plan), 0,
                                                   c.byref(view)) == -3
        assert c.string_at(c.byref(view), c.sizeof(view)) == bytes(c.sizeof(view))
        lib.mt6797_image_plan_invalidate(c.byref(plan))
    print(json.dumps({'image_sha256': IMAGE_SHA256, 'image_bytes': len(data),
                      'planner_result': 'complete-plan-valid',
                      'ordinary_sections': 2, 'emi_sections': 2,
                      'ordinary_bytes': 14832, 'emi_bytes': 396688,
                      'sections': sections,
                      'admission_without_emi_owner': 'refused-minus-3-no-executable-view',
                      'hardware_access': False}, indent=2))


if __name__ == '__main__':
    main()
