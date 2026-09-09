#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the pinned persistent-ring write ordering and truncation behavior."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

SHIM = r'''
#include <assert.h>
#include <stddef.h>
#include <string.h>
#define notrace
#define unlikely(x) (x)
struct persistent_ram_zone { size_t buffer_size, start, size; unsigned char data[16]; };
static int copies;
static void buffer_size_add(struct persistent_ram_zone *p, size_t n)
{ p->size = p->size + n > p->buffer_size ? p->buffer_size : p->size + n; }
static size_t buffer_start_add(struct persistent_ram_zone *p, size_t n)
{ size_t old = p->start; p->start = (old + n) % p->buffer_size; return old; }
static void persistent_ram_update(struct persistent_ram_zone *p, const void *s, unsigned start, unsigned count)
{
    if (!copies++) {
        /* Snapshot at interruption immediately before the first payload copy. */
        assert(p->size > 0);
        for (unsigned i = 0; i < 16; i++) assert(p->data[i] == 0xa5);
    }
    memcpy(p->data + start, s, count);
}
static void persistent_ram_update_header_ecc(struct persistent_ram_zone *p) { (void)p; }
'''
TEST = r'''
int main(void)
{
    struct persistent_ram_zone p = { .buffer_size = 16 };
    const unsigned char input[] = "abcdefghijklmnopqrst";
    memset(p.data, 0xa5, sizeof(p.data));
    assert(persistent_ram_write(&p, input, 20) == 20);
    assert(p.size == 16 && p.start == 0);
    assert(!memcmp(p.data, input + 4, 16));
    /* A second write overwrites the oldest bytes and again reports all bytes. */
    assert(persistent_ram_write(&p, "XYZ", 3) == 3);
    assert(p.size == 16 && p.start == 3);
    assert(!memcmp(p.data, "XYZ", 3));
    assert(!memcmp(p.data + 3, input + 7, 13));
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='pinned public fs/pstore/ram_core.c')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    receipt = json.loads((here / 'results/persistent-capture-sources.json').read_text())
    expected = next(row['sha256'] for row in receipt['sources'] if row['path'] == 'fs/pstore/ram_core.c')
    raw = args.source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    text = raw.decode()
    start = text.index('int notrace persistent_ram_write(')
    end = text.index('\n}\n', start) + 3
    with tempfile.TemporaryDirectory(prefix='wifi-persistent-ring-') as tmp:
        source = Path(tmp) / 'ring.c'
        executable = Path(tmp) / 'ring'
        source.write_text(SHIM + text[start:end] + TEST)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-sign-compare',
                        str(source), '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True, timeout=3)
    print('PASS: oversized write returns original count after truncation; later writes overwrite')
    print('PASS: metadata updated before first payload copy; partial-write snapshot reproduced')
    print('Scope: actual ring writer with injected storage helpers; no physical persistence test')


if __name__ == '__main__':
    main()
