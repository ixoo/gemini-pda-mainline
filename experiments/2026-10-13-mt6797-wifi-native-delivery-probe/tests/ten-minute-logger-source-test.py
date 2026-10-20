#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The extended observer derives only its reviewed time constant; no compilation."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent.parent
m = runpy.run_path(str(HERE / 'build-ten-minute-logger.py'))
source = (m['BASELINE'] / 'src/kmsg-capture.c').read_bytes()
derived = m['derive'](source)
assert derived.replace(m['NEW'], m['OLD']) == source
assert derived.count(m['NEW']) == 1
assert b'#define LOG_LIMIT (2U * 1024U * 1024U)' in derived
assert b'#define RECORD_LIMIT 65536U' in derived
for altered in [source + b'\n', source.replace(b'600000', b'900000'),
                source.replace(b'1024U', b'1025U', 1)]:
    try:
        m['derive'](altered)
    except ValueError:
        pass
    else:
        raise AssertionError('modified baseline accepted')
print('900-second observer: exact one-constant derivation and source mutation refusal PASS')
