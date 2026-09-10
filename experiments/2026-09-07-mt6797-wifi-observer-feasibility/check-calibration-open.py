#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise complete pinned NVRAM helpers with fake file operations; no device I/O."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

PARENT = 'f6c8b02d1af757c91143ebee83f240469a274a4c9949f96543a649281f0d2090'
UNIT = 'drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/platform.c'
PATCH = Path(__file__).resolve().parent / 'patches/calibration-open/0001-wlan-restore-address-limit-after-NVRAM-open-failure.patch'

STUBS = r'''
#include <assert.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdio.h>
#include <sys/types.h>
#define CFG_SUPPORT_NVRAM 1
#define FALSE 0
#define DBGLOG(...) ((void)0)
#define KERNEL_DS 99
#define IS_ERR(p) ((p) == (struct file *)-1)
typedef int mm_segment_t;
struct file;
struct file_operations {
 ssize_t (*read)(struct file *, char *, size_t, off_t *);
 ssize_t (*write)(struct file *, char *, size_t, off_t *);
 off_t (*llseek)(struct file *, off_t, int);
};
struct file { struct file_operations *f_op; off_t f_pos; };
static int limit, scenario, opened, closed, ios, seeks;
static mm_segment_t get_fs(void) { return limit; }
static void set_fs(mm_segment_t value) { limit = value; }
static ssize_t io(struct file *f, char *b, size_t n, off_t *p)
{ assert(limit == KERNEL_DS); ios++; if (scenario == 5) return -5; if (scenario == 6) return 1; return (ssize_t)n; }
static off_t seek(struct file *f, off_t p, int w)
{ assert(limit == KERNEL_DS); seeks++; return scenario == 3 ? -1 : p; }
static struct file *filp_open(char *name, int flags, int mode)
{
 static struct file_operations ops;
 static struct file f;
 assert(limit == KERNEL_DS); opened++;
 ops = (struct file_operations){io, io, seek};
 if (scenario == 2) ops.read = ops.write = NULL;
 if (scenario == 4) ops.llseek = NULL;
 f = (struct file){scenario == 1 ? NULL : &ops, 0};
 return scenario == 0 ? (struct file *)-1 : &f;
}
static int filp_close(struct file *f, void *unused)
{ assert(limit == KERNEL_DS); closed++; return 0; }
'''
TEST = r'''
int main(void)
{
 int (*functions[])(char *, char *, ssize_t, int) = {nvram_read, nvram_write};
 int cases = 0;
 for (int fn = 0; fn < 2; fn++)
 for (int initial = 7; initial <= KERNEL_DS; initial += KERNEL_DS - 7)
 for (scenario = 0; scenario < 8; scenario++) {
  char buffer[2] = {0};
  limit = initial; opened = closed = ios = seeks = 0;
  int value = functions[fn]("fake", buffer, 2, 10);
  assert(value == (scenario <= 3 ? -1 : scenario == 5 ? -5 : scenario == 6 ? 1 : 2));
  assert(opened == 1 && closed == (scenario != 0));
  assert(ios == (scenario >= 4));
  assert(seeks == (scenario == 3 || scenario >= 5));
  assert(limit == (PARENT_LEAK && scenario == 0 ? KERNEL_DS : initial));
  cases++;
 }
 printf("cases=%d\n", cases);
 return 0;
}
'''


def main():
    source = Path(sys.argv[1]) / UNIT
    original = source.read_bytes()
    assert hashlib.sha256(original).hexdigest() == PARENT
    with tempfile.TemporaryDirectory(prefix='wifi-calibration-open-') as tmp:
        root = Path(tmp)
        changed = root / UNIT
        changed.parent.mkdir(parents=True)
        changed.write_bytes(original)
        subprocess.run(['git', 'apply', str(PATCH)], cwd=root, check=True)
        parent, child = original.decode(), changed.read_text()
        assert child.replace('\t\tset_fs(old_fs);\n', '') == parent
        assert child.count('\t\tset_fs(old_fs);\n') == 2
        for label, text, leak in [('parent', parent, 1), ('corrected', child, 0)]:
            functions = text[text.index('static int nvram_read'):text.index('BOOLEAN kalCfgDataRead16')]
            test = root / (label + '.c')
            test.write_text(STUBS + functions + TEST)
            binary = root / label
            subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Wno-unused-parameter',
                            '-Werror', '-DPARENT_LEAK=' + str(leak), str(test), '-o', str(binary)], check=True)
            result = subprocess.check_output([str(binary)], text=True).strip()
            print(label + ': ' + result)
        print('parent_open_failure_leak=reproduced corrected_all_paths_restore=pass')


if __name__ == '__main__':
    main()
