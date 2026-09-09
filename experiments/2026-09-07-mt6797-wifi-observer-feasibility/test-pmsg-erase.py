#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce native pmsg erase ownership using pinned functions and fake storage."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

SHIM = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <time.h>
typedef uint64_t u64;
enum pstore_type_id { PSTORE_TYPE_DMESG, PSTORE_TYPE_CONSOLE, PSTORE_TYPE_FTRACE, PSTORE_TYPE_PMSG };
struct buffer { int start, size; };
struct persistent_ram_zone { struct buffer *buffer; bool old; };
struct pstore_info {
    void *data;
    int (*erase)(enum pstore_type_id, u64, int, struct timespec, struct pstore_info *);
};
struct ramoops_context {
    struct persistent_ram_zone **przs, *cprz, *fprz, *mprz;
    unsigned int max_dump_cnt;
};
struct pstore_private { struct pstore_info *psi; enum pstore_type_id type; u64 id; int count; };
struct inode { struct pstore_private *i_private; struct timespec i_ctime; };
struct dentry { struct inode *d_inode; };
static int unlinks, header_updates;
static void atomic_set(int *p, int value) { *p = value; }
static void persistent_ram_update_header_ecc(struct persistent_ram_zone *p)
{ (void)p; header_updates++; }
static void persistent_ram_free_old(struct persistent_ram_zone *p) { p->old = false; }
static int simple_unlink(struct inode *i, struct dentry *d)
{ (void)i; (void)d; unlinks++; return 0; }
static int refuse_erase(enum pstore_type_id t, u64 id, int n, struct timespec time, struct pstore_info *p)
{ (void)t; (void)id; (void)n; (void)time; (void)p; return -EBUSY; }
'''
TEST = r'''
int main(void)
{
    struct buffer current = { .start = 128, .size = 128 };
    struct persistent_ram_zone zone = { .buffer = &current, .old = true };
    struct ramoops_context context = { .mprz = &zone };
    struct pstore_info psi = { .data = &context, .erase = ramoops_pstore_erase };
    struct pstore_private record = { .psi = &psi, .type = PSTORE_TYPE_PMSG };
    struct inode inode = { .i_private = &record };
    struct dentry entry = { .d_inode = &inode };
    assert(pstore_unlink(&inode, &entry) == 0);
    assert(!zone.old && current.start == 0 && current.size == 0);
    assert(unlinks == 1 && header_updates == 1);
    current.start = current.size = 128;
    zone.old = true;
    psi.erase = refuse_erase;
    assert(pstore_unlink(&inode, &entry) == 0);
    assert(zone.old && current.start == 128 && current.size == 128);
    assert(unlinks == 2 && header_updates == 1);
    psi.erase = NULL;
    assert(pstore_unlink(&inode, &entry) == -EPERM);
    assert(unlinks == 2);
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', type=Path, help='directory containing the pinned C source files')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    receipt = json.loads((here/'results/pmsg-ownership-sources.json').read_text())
    sources = {}
    for row in receipt['sources']:
        raw = (args.sources/Path(row['path']).name).read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
        sources[Path(row['path']).name] = raw.decode()
    functions = []
    for file, marker in (('ram_core.c', 'void persistent_ram_zap('),
                         ('ram.c', 'static int ramoops_pstore_erase('),
                         ('inode.c', 'static int pstore_unlink(')):
        text = sources[file]
        begin = text.index(marker)
        end = text.index('\n}\n', begin) + 3
        functions.append(text[begin:end])
    with tempfile.TemporaryDirectory(prefix='wifi-pmsg-erase-') as tmp:
        source, executable = Path(tmp)/'erase.c', Path(tmp)/'erase'
        source.write_text(SHIM + '\n'.join(functions) + TEST)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', str(source), '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True, timeout=3)
    print('PASS: unlink of old pmsg snapshot also clears current ring metadata')
    print('PASS: backend erase refusal is ignored and unlink still succeeds')
    print('PASS: missing erase callback refuses unlink')
    print('Scope: pinned function bodies with fake storage; no physical memory or device access')


if __name__ == '__main__':
    main()
