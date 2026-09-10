#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile actual native reader bodies; reproduce and reject raw-text confusion."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('integration', HERE / 'test-capture-integration.py')
integration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integration)

SHIM = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#include <time.h>
#define GFP_KERNEL 0
#define RAMOOPS_KERNMSG_HDR "===="
typedef uint64_t u64;
enum pstore_type_id { PSTORE_TYPE_DMESG, PSTORE_TYPE_CONSOLE,
                      PSTORE_TYPE_FTRACE, PSTORE_TYPE_PMSG };
struct persistent_ram_zone { int unused; };
struct ramoops_context {
    struct persistent_ram_zone **przs, *cprz, *bprz, *fprz, *mprz;
    unsigned int dump_read_cnt, max_dump_cnt, console_read_cnt, bconsole_read_cnt,
                 ftrace_read_cnt, pmsg_read_cnt;
};
struct pstore_info { void *data; };
static unsigned char raw[65536];
static struct persistent_ram_zone zone;
static enum pstore_type_id selected;
static bool pmsg_capture, fail_alloc;
static struct persistent_ram_zone *ramoops_get_next_prz(
        struct persistent_ram_zone **p, unsigned int *cnt, unsigned int max,
        u64 *id, enum pstore_type_id *type, enum pstore_type_id requested, int update)
{
    (void)p; (void)cnt; (void)max; (void)update;
    if (requested != selected) return NULL;
    *id = 0; *type = requested; return &zone;
}
static bool prz_ok(struct persistent_ram_zone *p) { return p != NULL; }
static size_t persistent_ram_old_size(struct persistent_ram_zone *p)
{ assert(p == &zone); return sizeof(raw); }
static void *persistent_ram_old(struct persistent_ram_zone *p)
{ assert(p == &zone); return raw; }
static size_t persistent_ram_ecc_string(struct persistent_ram_zone *p, char *out, size_t size)
{ assert(p == &zone); if (out && size) *out = 0; return 0; }
static void *kmalloc(size_t size, int flags)
{ (void)flags; return fail_alloc ? NULL : malloc(size); }
'''

TEST = r'''
int main(void)
{
    struct ramoops_context context = {0};
    struct pstore_info info = { .data = &context };
    memset(raw, 'x', sizeof(raw));
    memcpy(raw, "====1.2-C\n", 10);
    for (int mode = 0; mode != 3; mode++) {
        pmsg_capture = mode != 1;
        selected = mode == 2 ? PSTORE_TYPE_DMESG : PSTORE_TYPE_PMSG;
        struct timespec time = { .tv_sec = 9, .tv_nsec = 9 };
        bool compressed = true;
        char *out = NULL;
        u64 id = 99;
        int count = 0;
        enum pstore_type_id type = PSTORE_TYPE_CONSOLE;
        assert(ramoops_pstore_read(&id, &type, &count, &time, &out, &compressed, &info) == 65536);
        assert(type == selected && id == 0 && !memcmp(raw, out, sizeof(raw)));
        if (FIXED && mode == 0) {
            assert(!compressed && !time.tv_sec && !time.tv_nsec);
        } else {
            assert(compressed && time.tv_sec == 1 && time.tv_nsec == 2);
        }
        free(out);
        fail_alloc = true;
        out = NULL;
        assert(ramoops_pstore_read(&id, &type, &count, &time, &out, &compressed, &info) == -ENOMEM);
        assert(!out && !memcmp(raw, "====1.2-C\n", 10));
        fail_alloc = false;
    }
    return 0;
}
'''


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: test-capture-reader.py PARENT_RAM_C CHILD_RAM_C')
    result = {'scope': 'native reader bodies with injected storage and allocation',
              'parent_raw_metadata_confusion': 'reproduced',
              'child_capture_raw_metadata': 'uncompressed and zero time',
              'ordinary_pmsg_and_dmesg': 'unchanged',
              'allocation_failure': 'refused with input preserved',
              'physical_device_access': False}
    for fixed, argument in enumerate(sys.argv[1:]):
        path = Path(argument)
        source = path.read_text()
        bodies = ''.join(integration.function(source, name) for name in
                         ('ramoops_read_kmsg_hdr', 'ramoops_pstore_read'))
        with tempfile.TemporaryDirectory(prefix='capture-reader-') as temp:
            work = Path(temp)
            (work / 'test.c').write_text(SHIM + bodies + TEST)
            # Native read has an unused count argument and signed-time scanf
            # formats; retain those bodies rather than rewriting the fixture.
            subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-parameter', '-Wno-format', '-DFIXED=' + str(fixed),
                            str(work / 'test.c'), '-o', str(work / 'test')], check=True)
            subprocess.run([str(work / 'test')], check=True)
        result[('child' if fixed else 'parent') + '_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
