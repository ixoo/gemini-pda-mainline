#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce operation reuse and late-success behavior in the actual waiter."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

SHIM = r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
typedef int INT32;
typedef char *PUINT8;
typedef bool MTK_WCN_BOOL;
#define MTK_WCN_BOOL_FALSE false
#define MTK_WCN_BOOL_TRUE true
#define WMT_OPID_HW_RST 1
#define WMT_OPID_SW_RST 2
#define WMT_OPID_GPIO_STATE 3
#define WMT_DBG_FUNC(...) ((void)0)
#define WMT_WARN_FUNC(...) ((void)0)
#define WMT_ERR_FUNC(...) ((void)0)
#define osal_assert(x) assert(x)
#define osal_strlen strlen
typedef struct { int timeoutValue; } SIGNAL, *P_OSAL_SIGNAL;
typedef struct { SIGNAL signal; int result; struct { int opId; } op; } OP, *P_OSAL_OP;
typedef int *P_OSAL_THREAD;
typedef struct { int rActiveOpQ, rFreeOpQ, rWmtdWq, thread; } DEV, *P_DEV_WMT;
static DEV gDevWmt;
static OP *active;
static int scenario, free_puts, active_puts, wakes, diagnostics;
static int mtk_wcn_stp_coredump_start_get(void) { return scenario == 6; }
static void osal_signal_init(SIGNAL *s) { assert(s->timeoutValue); }
static bool wmt_lib_put_op(int *queue, OP *op)
{
    if (queue == &gDevWmt.rFreeOpQ) { free_puts++; return true; }
    assert(queue == &gDevWmt.rActiveOpQ);
    active_puts++;
    if (scenario == 5) return false;
    active = op;
    return true;
}
static void osal_trigger_event(int *event) { assert(event == &gDevWmt.rWmtdWq); wakes++; }
static int osal_wait_for_signal_timeout(SIGNAL *s)
{
    assert(s == &active->signal);
    if (scenario == 2 || scenario == 3) return 0;
    active->result = scenario == 1 ? -5 : 0;
    return scenario == 4 ? -4 : 1;
}
static void osal_thread_show_stack(P_OSAL_THREAD t) { assert(t == &gDevWmt.thread); }
static void stp_dbg_trigger_collect_ftrace(PUINT8 buf, INT32 len)
{
    assert((int)strlen(buf) == len);
    diagnostics++;
    /* Worker completes after the waiter reports timeout, during diagnostics. */
    if (scenario == 3) active->result = 0;
}
'''
TEST = r'''
int main(void)
{
    for (scenario = 0; scenario < 8; scenario++) {
        OP op = { .signal.timeoutValue = scenario == 7 ? 0 : 4000,
                  .op.opId = 4 };
        active = NULL;
        free_puts = active_puts = wakes = diagnostics = 0;
        bool result = wmt_lib_put_act_op(&op);
        bool expired = scenario >= 2 && scenario <= 4;
        bool success = scenario == 0 || scenario == 7 || (!FIXED && (scenario == 3 || scenario == 4));
        assert(result == success);
        assert(free_puts == (scenario == 7 || (FIXED && expired) ? 0 : 1));
        assert(active_puts == (scenario == 6 ? 0 : 1));
        assert(wakes == (scenario == 5 || scenario == 6 ? 0 : 1));
        assert(diagnostics == (scenario == 2 || scenario == 3 || (FIXED && scenario == 4)));
        if (expired) {
            /* A later worker write has a retained object, never returned by this waiter. */
            active->result = 0;
            assert(free_puts == (FIXED ? 0 : 1));
        }
    }
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='pinned public wmt_lib.c')
    args = parser.parse_args()
    raw = args.source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'e363d3377aab1de6f81d94dd482bcdba5eb55884792f45e1688ebf850f991e4f'
    here = Path(__file__).resolve().parent
    relative = 'drivers/misc/mediatek/connectivity/common/common_main/core/wmt_lib.c'
    with tempfile.TemporaryDirectory(prefix='wmt-operation-timeout-') as tmp:
        root = Path(tmp)
        source = root / relative
        source.parent.mkdir(parents=True)
        source.write_bytes(raw)
        for name in ('0003-wmt-guard-single-patch-reply.patch', '0004-wmt-retain-timed-out-operation.patch'):
            subprocess.run(['git', 'apply', '--include=' + relative, str(here / 'patches' / name)],
                           cwd=root, check=True)
        for fixed, text in enumerate((raw.decode(), source.read_text())):
            start = text.index('MTK_WCN_BOOL wmt_lib_put_act_op(P_OSAL_OP pOp)\n{')
            end = text.index('\n}\n', start) + 3
            fixture = root / f'case-{fixed}.c'
            fixture.write_text(SHIM + text[start:end] + TEST)
            executable = root / f'case-{fixed}'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            f'-DFIXED={fixed}', str(fixture), '-o', str(executable)], check=True)
            subprocess.run([str(executable)], check=True, timeout=3)
    print('PASS: original recycles on timeout and can report late success; patch retains and fails')
    print('PASS: success, worker error, timeout, late success, interrupted wait, queue refusal, coredump block, async')
    print('Scope: actual waiter with injected dependencies; no cancellation, scheduler, or hardware proof')


if __name__ == '__main__':
    main()
