#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the exact native backend callbacks with injected RAM operations."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

SOURCE_SHA256 = '20a043ba3c420f3aae0ffc056344370ac427b27d0204f3a52f439513d31c0165'
SHIM = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <time.h>
#include <pthread.h>
#define notrace
#define KMSG_DUMP_OOPS 1
#define KMSG_DUMP_PANIC 2
#define min(a,b) ((a) < (b) ? (a) : (b))
typedef uint64_t u64;
enum pstore_type_id { PSTORE_TYPE_DMESG, PSTORE_TYPE_CONSOLE,
                      PSTORE_TYPE_FTRACE, PSTORE_TYPE_PMSG };
enum kmsg_dump_reason { reason_none, reason_oops, reason_panic };
struct persistent_ram_zone { size_t buffer_size; int writes, frees, zaps; };
struct ramoops_context {
    struct persistent_ram_zone *cprz, *bprz, *fprz, *mprz, **przs;
    unsigned int dump_write_cnt, max_dump_cnt;
    int dump_oops;
};
struct pstore_info { void *data; };
static bool pmsg_capture;
static unsigned long pmsg_capture_denials;
static void set_bit(unsigned int bit, unsigned long *value)
{ __atomic_fetch_or(value, 1UL << bit, __ATOMIC_SEQ_CST); }
static void persistent_ram_write(struct persistent_ram_zone *p, const void *s, size_t n)
{ assert(p && s && n); p->writes++; }
static void persistent_ram_free_old(struct persistent_ram_zone *p)
{ assert(p); p->frees++; }
static void persistent_ram_zap(struct persistent_ram_zone *p)
{ assert(p); p->zaps++; }
static size_t ramoops_write_kmsg_hdr(struct persistent_ram_zone *p, bool compressed)
{ assert(p); (void)compressed; return 0; }
'''
TEST = r'''
static struct persistent_ram_zone message = { .buffer_size = 65524 };
static struct persistent_ram_zone other = { .buffer_size = 1024 };
static struct persistent_ram_zone *zones[] = { &other };
static struct ramoops_context context = {
    .mprz = &message, .cprz = &other, .bprz = &other, .fprz = &other,
    .przs = zones, .max_dump_cnt = 1, .dump_oops = 1,
};
static struct pstore_info info = { .data = &context };
static int write_one(enum pstore_type_id type)
{ return ramoops_pstore_write_buf(type, reason_none, NULL, 0, "x", false, 1, &info); }
static int erase_one(enum pstore_type_id type)
{ return ramoops_pstore_erase(type, 0, 0, (struct timespec){0}, &info); }
static void *denied_writer(void *unused)
{
    (void)unused;
    for (int i = 0; i < 1000; i++) assert(write_one(PSTORE_TYPE_PMSG) == -EBUSY);
    return NULL;
}
static void *denied_eraser(void *unused)
{
    (void)unused;
    for (int i = 0; i < 1000; i++) assert(erase_one(PSTORE_TYPE_PMSG) == -EBUSY);
    return NULL;
}
int main(void)
{
    assert(!pmsg_capture);
    assert(!write_one(PSTORE_TYPE_PMSG));
    assert(message.writes == 1 && !pmsg_capture_denials);
    assert(!erase_one(PSTORE_TYPE_PMSG));
    assert(message.frees == 1 && message.zaps == 1 && !pmsg_capture_denials);
    struct persistent_ram_zone before = message;
    /* Models a separate boot selected before backend registration. */
    pmsg_capture = true;
    assert(write_one(PSTORE_TYPE_PMSG) == -EBUSY && pmsg_capture_denials == 1);
    assert(erase_one(PSTORE_TYPE_PMSG) == -EBUSY && pmsg_capture_denials == 3);
    assert(!memcmp(&before, &message, sizeof(before)));
    context.mprz = NULL;
    assert(write_one(PSTORE_TYPE_PMSG) == -EBUSY);
    assert(erase_one(PSTORE_TYPE_PMSG) == -EBUSY);
    context.mprz = &message;
    assert(!write_one(PSTORE_TYPE_CONSOLE));
    assert(!write_one(PSTORE_TYPE_FTRACE));
    assert(!erase_one(PSTORE_TYPE_CONSOLE));
    assert(!erase_one(PSTORE_TYPE_FTRACE));
    assert(other.writes == 2 && other.frees == 2 && other.zaps == 2);
    assert(pmsg_capture_denials == 3);
    /* Fresh modeled boot for the concurrent denial test. */
    pmsg_capture_denials = 0;
    pthread_t writer, eraser;
    assert(!pthread_create(&writer, NULL, denied_writer, NULL));
    assert(!pthread_create(&eraser, NULL, denied_eraser, NULL));
    assert(!pthread_join(writer, NULL) && !pthread_join(eraser, NULL));
    assert(pmsg_capture_denials == 3 && !memcmp(&before, &message, sizeof(before)));
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256
    text = raw.decode()
    assert 'module_param(pmsg_capture, bool, 0400);' in text
    assert '.get = param_get_ulong,' in text and '.set =' not in text
    assert 'ramoops_driver.driver.suppress_bind_attrs = true;' in text
    assert '#ifdef MODULE\n\t/* Capture exclusion must last for the boot, without unload/reload. */\n\tif (pmsg_capture)\n\t\treturn -EINVAL;\n#endif' in text
    begin = text.index('static int notrace ramoops_pstore_write_buf(')
    end = text.index('\nstatic struct ramoops_context oops_cxt', begin)
    with tempfile.TemporaryDirectory(prefix='wifi-pmsg-owner-') as tmp:
        source, binary = Path(tmp)/'owner.c', Path(tmp)/'owner'
        source.write_text(SHIM + text[begin:end] + TEST)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', '-pthread', str(source), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=5)
    print('PASS: default behavior, rejected PMSG writes/erases, unchanged storage and sticky denial bits')
    print('PASS: missing-zone refusal, unaffected console/ftrace, concurrent rejected callbacks')
    print('Scope: exact callback bodies with injected RAM/atomic operations; no hardware or persistence claim')


if __name__ == '__main__':
    main()
