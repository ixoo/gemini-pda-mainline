#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The soak observer derives only its deadline and byte cap; no compilation."""
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent.parent
m = runpy.run_path(str(HERE / 'build-soak-logger.py'))
source = (m['BASELINE'] / 'src/kmsg-capture.c').read_bytes()
derived = m['derive'](source)
restored = derived
for old, new in m['EDITS']:
    assert derived.count(new) == 1
    restored = restored.replace(new, old)
assert restored == source
assert b'#define RECORD_LIMIT 65536U' in derived
assert m['DEADLINE_MS'] == 4500000 and m['LOG_LIMIT'] == 16 * 1024 * 1024
for name, edits in [('test-kmsg.py', m['PARSER_EDITS']), ('test-kmsg-io.py', m['IO_EDITS']),
                    ('tests/kmsg-io-harness.c', m['HARNESS_EDITS'])]:
    m['edit']((m['BASELINE'] / name).read_bytes(), edits, name)
for altered in [source + b'\n', source.replace(b'600000', b'900000'),
                source.replace(b'1024U', b'1025U', 1)]:
    try:
        m['derive'](altered)
    except ValueError:
        pass
    else:
        raise AssertionError('modified baseline accepted')
print('soak observer: exact two-constant derivation, fixture edits and source mutation refusal PASS')
