#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise native pmsg probe preservation with injected old-log allocation failure."""
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
#define GFP_KERNEL 0
#define PERSISTENT_RAM_SIG 0x43474244
#define pr_err(...) ((void)0)
#define pr_debug(...) ((void)0)
#define pr_info(...) ((void)0)
#define dev_err(...) ((void)0)
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
typedef uint32_t u32;
typedef uint64_t phys_addr_t;
struct persistent_ram_buffer { u32 sig; int start, size; char data[65524]; };
struct persistent_ram_ecc_info { int unused; };
struct persistent_ram_zone {
    struct persistent_ram_buffer *buffer;
    size_t buffer_size, old_log_size;
    char *old_log;
};
struct ramoops_context {
    phys_addr_t phys_addr;
    size_t size;
    struct persistent_ram_ecc_info ecc_info;
    unsigned int memtype;
};
struct device { int unused; };
static struct persistent_ram_buffer retained;
static int fail_copy, zaps, live_zones;
static size_t buffer_size(struct persistent_ram_zone *p) { return p->buffer->size; }
static size_t buffer_start(struct persistent_ram_zone *p) { return p->buffer->start; }
static void persistent_ram_ecc_old(struct persistent_ram_zone *p) {}
static int persistent_ram_init_ecc(struct persistent_ram_zone *p,
                                 struct persistent_ram_ecc_info *e) { return 0; }
static void *kmalloc(size_t size, int flags) { return fail_copy ? NULL : malloc(size); }
static void *kzalloc(size_t size, int flags) { live_zones++; return calloc(1, size); }
static void persistent_ram_zap(struct persistent_ram_zone *p)
{ zaps++; p->buffer->start = p->buffer->size = 0; }
static int persistent_ram_buffer_map(phys_addr_t start, size_t size,
                                    struct persistent_ram_zone *p, unsigned int type)
{ p->buffer = &retained; p->buffer_size = sizeof(retained.data); return 0; }
static void persistent_ram_free(struct persistent_ram_zone *p)
{ if (p) { free(p->old_log); free(p); live_zones--; } }
'''
TEST = r'''
int main(void)
{
    struct ramoops_context context = { .phys_addr = 4096, .size = 65536 };
    for (int failed = 0; failed <= 1; failed++) {
        for (int empty = 0; empty <= 1; empty++) {
            struct persistent_ram_zone *zone = NULL;
            phys_addr_t address = 4096;
            retained.sig = PERSISTENT_RAM_SIG;
            retained.start = empty ? 0 : 3;
            retained.size = empty ? 0 : 8;
            memcpy(retained.data, "abcdefgh", 8);
            struct persistent_ram_buffer before = retained;
            fail_copy = failed;
            zaps = 0;
            int result = ramoops_init_prz(NULL, &context, &zone, &address, 65536, 0);
            if (FIXED && failed && !empty) {
                assert(result == -ENOMEM && IS_ERR(zone));
                assert(address == 4096 && !zaps && !live_zones);
                assert(!memcmp(&before, &retained, sizeof(retained)));
            } else {
                assert(!result && !IS_ERR(zone));
                assert(address == 69632 && zaps == 1);
                assert(!retained.start && !retained.size);
                if (!failed && !empty) {
                    assert(zone->old_log_size == 8);
                    assert(!memcmp(zone->old_log, "defghabc", 8));
                } else {
                    assert(!zone->old_log && !zone->old_log_size);
                }
                persistent_ram_free(zone);
                assert(!live_zones);
            }
        }
    }
    /* Fixed metadata causes ordinary recovery to preserve every slot byte. */
    struct persistent_ram_zone *zone = NULL;
    phys_addr_t address = 4096;
    retained.sig = PERSISTENT_RAM_SIG;
    retained.start = 0;
    retained.size = sizeof(retained.data);
    memset(retained.data, 0, sizeof(retained.data));
    memcpy(retained.data, "WFC1", 4);
    memcpy(retained.data + 128, "interrupted record", 18);
    fail_copy = zaps = 0;
    assert(ramoops_init_prz(NULL, &context, &zone, &address, 65536, 0) == 0);
    assert(zone->old_log_size == sizeof(retained.data));
    assert(!memcmp(zone->old_log, retained.data, sizeof(retained.data)));
    assert(!retained.start && !retained.size && zaps == 1);
    persistent_ram_free(zone);
    assert(!live_zones);
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
    sources = {}
    for row in receipt['sources']:
        if Path(row['path']).name not in ('ram_core.c', 'ram.c'):
            continue
        raw = (args.sources/Path(row['path']).name).read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
        sources[Path(row['path']).name] = raw.decode()
    functions = []
    for file, marker in (('ram_core.c', 'void persistent_ram_save_old('),
                         ('ram_core.c', 'static int persistent_ram_post_init('),
                         ('ram_core.c', 'struct persistent_ram_zone *persistent_ram_new('),
                         ('ram.c', 'static int ramoops_init_prz(')):
        text = sources[file]
        begin = text.index(marker)
        functions.append(text[begin:text.index('\n}\n', begin) + 3])
    with tempfile.TemporaryDirectory(prefix='wifi-pmsg-recovery-') as tmp:
        source, executable = Path(tmp)/'recovery.c', Path(tmp)/'recovery'
        source.write_text(f'#define FIXED {int(args.fixed)}\n' + SHIM + '\n'.join(functions) + TEST)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', str(source), '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True, timeout=3)
    print('PASS: allocation failure refuses initialization and preserves retained bytes' if args.fixed else
          'PASS: native allocation failure still succeeds and zaps retained metadata')
    print('PASS: successful old-log copy preserves ring order; empty ring needs no copy')
    print('PASS: fixed full-length metadata recovers all 65524 slot bytes unchanged')
    print('Scope: four exact functions, fake mapping/allocation/ECC/free; no device access')


if __name__ == '__main__':
    main()
