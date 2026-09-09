#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replay the guard patch and exercise its real functions with injected timing."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

SHIM = r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <limits.h>
#include <string.h>
#include <strings.h>
#include <sys/types.h>
#define NAME_MAX 255
#define __user
#define WMT_STAT_CMD 0
#define WMT_LOUD_FUNC(...) ((void)0)
#define WMT_DBG_FUNC(...) ((void)0)
#define WMT_WARN_FUNC(...) ((void)0)
typedef int INT32;
typedef char UINT8;
typedef char *PUINT8;
typedef long long loff_t;
struct file { int unused; };
typedef struct { int timeoutValue, completed; } SIGNAL, *P_OSAL_SIGNAL;
typedef struct { unsigned long state; char cCmd[256]; SIGNAL cmdResp; int cmdReq, cmdResult; } DEV, *P_DEV_WMT;
static DEV gDevWmt;
static unsigned long jiffies;
/* Checked lock shim: sequential boundary interleavings, not a scheduler test. */
#define DEFINE_MUTEX(name) int name
static void mutex_lock(int *m) { assert(!*m); *m = 1; }
static void mutex_unlock(int *m) { assert(*m); *m = 0; }
#define time_after_eq(a,b) ((long)((a)-(b)) >= 0)
#define msecs_to_jiffies(x) ((unsigned long)(x))
#define osal_strcmp strcmp
#define osal_strncpy strncpy
static int osal_test_bit(int b, unsigned long *p) { return !!(*p & (1UL << b)); }
static void osal_set_bit(int b, unsigned long *p) { *p |= 1UL << b; }
static void osal_clear_bit(int b, unsigned long *p) { *p &= ~(1UL << b); }
static void osal_signal_init(SIGNAL *s) { s->completed = 0; }
static void osal_raise_signal(SIGNAL *s) { s->completed++; }
static int copy_from_user(void *d, const void *s, size_t n) { memcpy(d,s,n); return 0; }
static void osal_trigger_event(int *e);
static int osal_wait_for_signal_timeout(SIGNAL *s);
'''
TEST = r'''
static int scenario;
static void osal_trigger_event(int *e)
{
    assert(e == &gDevWmt.cmdReq && !wmt_cmd_lock);
    assert(!strcmp(gDevWmt.cCmd, "srh_patch"));
    assert(wmt_ctrl_ul_cmd(&gDevWmt, "srh_patch") == -EBUSY);
    assert(!gDevWmt.cmdResp.completed && gDevWmt.cmdResp.timeoutValue == 2000);
    assert(WMT_write(NULL, "ok", 2, NULL) == -EAGAIN);
    assert(!gDevWmt.cmdResp.completed);
    osal_clear_bit(WMT_STAT_CMD, &gDevWmt.state);
    if (scenario == 3) return;
    if (scenario == 1 || scenario == 2) {
        jiffies = wmt_cmd_deadline + (scenario == 2);
        assert(WMT_write(NULL, "ok", 2, NULL) == -ETIMEDOUT);
        assert(!gDevWmt.cmdResp.completed);
    } else {
        jiffies = wmt_cmd_deadline - 1;
        assert(WMT_write(NULL, scenario == 4 ? "no" : "ok", 2, NULL) == 2);
        assert(gDevWmt.cmdResp.completed == 1);
    }
    assert(WMT_write(NULL, "ok", 2, NULL) == -ESTALE);
}
static int osal_wait_for_signal_timeout(SIGNAL *s)
{
    assert(!wmt_cmd_lock);
    if (!s->completed) jiffies += 2000;
    return s->completed;
}
static void reset(void)
{
    memset(&gDevWmt, 0, sizeof(gDevWmt));
    wmt_cmd_used = wmt_cmd_active = false;
    jiffies = 100;
}
int main(void)
{
    for (scenario = 0; scenario < 6; scenario++) {
        reset();
        if (scenario == 5) jiffies = ULONG_MAX - 1000;
        assert(WMT_write(NULL, "ok", 2, NULL) == -ESTALE);
        int ret = wmt_ctrl_ul_cmd(&gDevWmt, "srh_patch");
        assert(ret == (scenario >= 1 && scenario <= 3 ? -ETIMEDOUT : scenario == 4 ? -1 : 0));
        assert(!wmt_cmd_active && !gDevWmt.state);
        assert(WMT_write(NULL, "ok", 2, NULL) == -ESTALE);
        assert(wmt_ctrl_ul_cmd(&gDevWmt, "srh_patch") == -EBUSY);
    }
    reset();
    assert(wmt_ctrl_ul_cmd(NULL, "srh_patch") == -EINVAL);
    assert(wmt_ctrl_ul_cmd(&gDevWmt, NULL) == -EINVAL);
    assert(!wmt_cmd_used);
    assert(wmt_ctrl_ul_cmd(&gDevWmt, "open_stp") == -EINVAL);
    assert(wmt_ctrl_ul_cmd(&gDevWmt, "srh_patch") == -EBUSY);
    reset();
    gDevWmt.state = 1;
    assert(wmt_ctrl_ul_cmd(&gDevWmt, "srh_patch") == -EINVAL);
    assert(wmt_cmd_used && !wmt_cmd_active);
    assert(WMT_write(NULL, "", 0, NULL) == 0);
    return 0;
}
'''


def function(text, signature):
    start = text.index(signature + '\n{')
    return text[start:text.index('\n}\n', start) + 3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root', type=Path, help='public source tree at the pinned revision')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    receipt = json.loads((here / 'results/command-guard-sources.json').read_text())
    with tempfile.TemporaryDirectory(prefix='wmt-command-test-') as tmp:
        root = Path(tmp)
        for entry in receipt['sources']:
            data = (args.source_root / entry['path']).read_bytes()
            assert len(data) == entry['bytes']
            assert hashlib.sha256(data).hexdigest() == entry['sha256']
            target = root / entry['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        patch = here / 'patches/0003-wmt-guard-single-patch-reply.patch'
        subprocess.run(['git', 'apply', '--check', str(patch)], cwd=root, check=True)
        subprocess.run(['git', 'apply', str(patch)], cwd=root, check=True)
        base = root / 'drivers/misc/mediatek/connectivity/common/common_main'
        ctrl = (base / 'core/wmt_ctrl.c').read_text()
        start = ctrl.index('/* One patch-search transaction')
        end = ctrl.index('\nINT32 wmt_ctrl_hw_rst', start)
        lib = function((base / 'core/wmt_lib.c').read_text(),
                       'INT32 wmt_lib_trigger_cmd_signal(INT32 result)')
        dev = function((base / 'linux/wmt_dev.c').read_text(),
                       'ssize_t WMT_write(struct file *filp, const char __user *buf, size_t count, loff_t *f_pos)')
        fixture = root / 'guard.c'
        fixture.write_text(SHIM + ctrl[start:end] + lib + dev + TEST)
        executable = root / 'guard'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', str(fixture), '-o', str(executable)], check=True)
        subprocess.run([str(executable)], check=True, timeout=3)
    print('PASS: early/unread, accepted, duplicate, negative, deadline, late, absent reply, wraparound')
    print('PASS: terminal reuse, invalid command/device, occupied buffer, write errno propagation')
    print('Scope: extracted functions with injected sequential timing; no kernel scheduling or hardware test')


if __name__ == '__main__':
    main()
