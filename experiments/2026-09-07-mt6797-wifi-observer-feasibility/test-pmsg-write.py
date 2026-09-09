#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise pinned native write_pmsg with injected backend failures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

SHIM = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#define __user
#define VERIFY_READ 0
#define GFP_KERNEL 0
#define PMSG_MAX_BOUNCE_BUFFER_SIZE 4
#define PSTORE_TYPE_PMSG 3
#define unlikely(x) (x)
#define min(a,b) ((a) < (b) ? (a) : (b))
typedef uint64_t u64;
typedef long long loff_t;
struct file { int unused; };
static int pmsg_lock, allocations, calls, fail_at, copied;
static int access_ok(int mode, const char *buf, size_t count) { return 1; }
static int get_order(size_t size) { return 0; }
static void *__get_free_pages(int flags, int order)
{ allocations++; return malloc(PMSG_MAX_BOUNCE_BUFFER_SIZE); }
static void free_pages(unsigned long p, int order) { allocations--; free((void *)p); }
static void mutex_lock(int *p) { assert(!*p); *p = 1; }
static void mutex_unlock(int *p) { assert(*p); *p = 0; }
static long __copy_from_user(char *to, const char *from, size_t n)
{ memcpy(to, from, n); return 0; }
struct pstore_info {
    int (*write_buf)(int, int, u64 *, int, const char *, int, size_t, struct pstore_info *);
};
static int backend(int type, int reason, u64 *id, int part, const char *buf,
                   int compressed, size_t size, struct pstore_info *psi)
{
    assert(pmsg_lock && allocations == 1);
    calls++;
    if (calls == fail_at) return -EBUSY;
    copied += size;
    return 0;
}
static struct pstore_info info = { .write_buf = backend }, *psinfo = &info;
'''
TEST = r'''
int main(void)
{
    const char input[] = "abcdefghijkl";
    for (int failure = 0; failure <= 3; failure++) {
        calls = copied = 0;
        fail_at = failure;
        ssize_t result = write_pmsg(NULL, input, 12, NULL);
        assert(result == (FIXED && failure ? (failure == 1 ? -EBUSY : (failure - 1) * 4) : 12));
        assert(calls == (FIXED && failure ? failure : 3));
        assert(copied == (FIXED && failure ? (failure - 1) * 4 : (failure ? 8 : 12)));
        assert(!allocations && !pmsg_lock);
    }
    calls = 0;
    assert(write_pmsg(NULL, input, 0, NULL) == 0);
    assert(!calls && !allocations && !pmsg_lock);
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources', type=Path)
    parser.add_argument('--fixed', action='store_true')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    receipt_name = 'pmsg-fixed-sources.json' if args.fixed else 'pmsg-ownership-sources.json'
    receipt = json.loads((here/'results'/receipt_name).read_text())
    row = next(row for row in receipt['sources'] if row['path'] == 'fs/pstore/pmsg.c')
    raw = (args.sources/'pmsg.c').read_bytes()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    text = raw.decode()
    begin = text.index('static ssize_t write_pmsg(')
    end = text.index('\n}\n', begin) + 3
    with tempfile.TemporaryDirectory(prefix='wifi-pmsg-write-') as tmp:
        source, executable = Path(tmp)/'write.c', Path(tmp)/'write'
        source.write_text(f'#define FIXED {int(args.fixed)}\n' + SHIM + text[begin:end] + TEST)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', str(source), '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True, timeout=3)
    print('PASS: first and later backend failures stop and report accepted bytes' if args.fixed else
          'PASS: native backend failures are hidden and later chunks continue')
    print('PASS: success, zero-length write, and balanced allocation/lock cleanup')
    print('Scope: exact pinned function body with fake backend; no device access')


if __name__ == '__main__':
    main()
