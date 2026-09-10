#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual WMT ownership, waiter and worker code with directed schedules."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

SHIM = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sched.h>
#include <stdio.h>
typedef int INT32;
typedef unsigned UINT32;
typedef void VOID;
typedef void *PVOID;
typedef char *PUINT8;
typedef bool MTK_WCN_BOOL;
#define MTK_WCN_BOOL_FALSE false
#define MTK_WCN_BOOL_TRUE true
#define WMT_OP_BUF_SIZE 2
#define WMT_OPID_HW_RST 1
#define WMT_OPID_SW_RST 2
#define WMT_OPID_GPIO_STATE 3
#define WMT_OPID_FUNC_ON 4
#define WMT_OPID_FUNC_OFF 5
#define WMT_OPID_EXIT 6
#define WMT_STAT_RST_ON 0
#define WMT_DBG_FUNC(...) ((void)0)
#define WMT_WARN_FUNC(...) ((void)0)
#define WMT_ERR_FUNC(...) ((void)0)
#define WMT_INFO_FUNC(...) ((void)0)
#define osal_assert assert
#define osal_strlen strlen
#define osal_memset memset
#define osal_sizeof sizeof
#define RB_EMPTY(q) (!(q)->count)
#define DEFINE_MUTEX(n) pthread_mutex_t n = PTHREAD_MUTEX_INITIALIZER
#define mutex_lock(m) assert(pthread_mutex_lock(m) == 0)
#define mutex_unlock(m) assert(pthread_mutex_unlock(m) == 0)
typedef struct { int opId; } OPDATA;
typedef struct { int timeoutValue; atomic_int done; } SIGNAL, *P_OSAL_SIGNAL;
typedef struct { OPDATA op; SIGNAL signal; int result; } OP, *P_OSAL_OP;
typedef struct { pthread_mutex_t lock; OP *items[2]; int count; } QUEUE, *P_OSAL_OP_Q;
typedef struct { int timeoutValue; } EVENT, *P_OSAL_EVENT;
typedef struct { atomic_int stop; } THREAD, *P_OSAL_THREAD;
typedef struct {
    QUEUE rFreeOpQ, rActiveOpQ;
    EVENT rWmtdWq;
    THREAD thread;
    unsigned long state;
    OP arQue[WMT_OP_BUF_SIZE];
    OP *pCurOP;
} DEV_WMT, *P_DEV_WMT;
static atomic_int entered, finish_core, finished, waiter_done, allow_waiter;
static atomic_int free_puts, core_result, fail_queue, coredump, wait_mode;
static bool waiter_result;
static OP *subject;
static void await(atomic_int *v) { while (!atomic_load(v)) sched_yield(); }
static bool wmt_lib_put_op(QUEUE *q, OP *op);
static OP *wmt_lib_get_op(QUEUE *q);
static void osal_raise_signal(SIGNAL *s) { atomic_fetch_add(&s->done, 1); }
static bool osal_op_is_wait_for_signal(OP *op) { return op && op->signal.timeoutValue; }
static void osal_op_raise_signal(OP *op, int result)
{
    if (op) { op->result = result; osal_raise_signal(&op->signal); }
}
static void osal_signal_init(SIGNAL *s) { atomic_store(&s->done, 0); }
static int osal_wait_for_signal_timeout(SIGNAL *s)
{
    if (atomic_load(&wait_mode)) return atomic_load(&wait_mode) == 1 ? 0 : -1;
    while (!atomic_load(&s->done)) sched_yield();
    await(&allow_waiter);
    return 1;
}
static bool mtk_wcn_stp_coredump_start_get(void) { return atomic_load(&coredump); }
static void osal_thread_show_stack(THREAD *t) { (void)t; }
static void stp_dbg_trigger_collect_ftrace(char *s, int n) { assert((int)strlen(s) == n); }
static bool osal_test_bit(int bit, unsigned long *state) { return (*state >> bit) & 1; }
static void osal_trigger_event(EVENT *event) { (void)event; }
static bool wmt_lib_wait_event_checker(void) { return true; }
static void osal_thread_wait_for_event(THREAD *t, EVENT *e, bool (*check)(void));
static bool osal_thread_should_stop(THREAD *t) { return atomic_load(&t->stop); }
static void wmt_lib_set_current_op(P_DEV_WMT d, OP *op);
static int wmt_core_opid(OPDATA *op)
{
    assert(op == &subject->op);
    atomic_store(&entered, 1);
    await(&finish_core);
    return atomic_load(&core_result);
}
'''
QUEUE_AND_TEST = r'''
static bool wmt_lib_put_op(QUEUE *q, OP *op)
{
    if (q == &gDevWmt.rActiveOpQ && atomic_load(&fail_queue)) return false;
    mutex_lock(&q->lock);
    assert(q->count < WMT_OP_BUF_SIZE);
    for (int i = 0; i < q->count; i++) assert(q->items[i] != op);
    q->items[q->count++] = op;
    mutex_unlock(&q->lock);
    if (q == &gDevWmt.rFreeOpQ) atomic_fetch_add(&free_puts, 1);
    return true;
}
static OP *wmt_lib_get_op(QUEUE *q)
{
    mutex_lock(&q->lock);
    OP *op = q->count ? q->items[--q->count] : NULL;
    mutex_unlock(&q->lock);
    return op;
}
static void osal_thread_wait_for_event(THREAD *t, EVENT *e, bool (*check)(void))
{
    (void)e; (void)check;
    for (;;) {
        mutex_lock(&gDevWmt.rActiveOpQ.lock);
        bool ready = gDevWmt.rActiveOpQ.count;
        mutex_unlock(&gDevWmt.rActiveOpQ.lock);
        if (ready || atomic_load(&t->stop)) return;
        sched_yield();
    }
}
static void *worker(void *unused)
{
    (void)unused;
    wmtd_thread(&gDevWmt);
    atomic_store(&finished, 1);
    return NULL;
}
static void *waiter(void *unused)
{
    (void)unused;
    waiter_result = wmt_lib_put_act_op(subject);
    atomic_store(&waiter_done, 1);
    return NULL;
}
static unsigned users(OP *op)
{
    mutex_lock(&wmt_op_lock);
    unsigned n = wmt_op_state[op - gDevWmt.arQue].users;
    mutex_unlock(&wmt_op_lock);
    return n;
}
static void setup(int timeout)
{
    assert(!pthread_mutex_init(&gDevWmt.rFreeOpQ.lock, NULL));
    assert(!pthread_mutex_init(&gDevWmt.rActiveOpQ.lock, NULL));
    gDevWmt.rFreeOpQ.count = gDevWmt.rActiveOpQ.count = 0;
    gDevWmt.pCurOP = NULL; gDevWmt.state = 0;
    memset(wmt_op_state, 0, sizeof(wmt_op_state));
    atomic_store(&gDevWmt.thread.stop, 0);
    atomic_store(&entered, 0); atomic_store(&finish_core, 0);
    atomic_store(&finished, 0); atomic_store(&waiter_done, 0);
    atomic_store(&allow_waiter, 1); atomic_store(&core_result, 0);
    atomic_store(&fail_queue, 0); atomic_store(&coredump, 0);
    atomic_store(&wait_mode, 0);
    for (int i = 0; i < WMT_OP_BUF_SIZE; i++)
        assert(wmt_lib_put_op(&gDevWmt.rFreeOpQ, &gDevWmt.arQue[i]));
    atomic_store(&free_puts, 0);
    subject = wmt_lib_get_free_op(); assert(subject);
    subject->signal.timeoutValue = timeout;
    subject->op.opId = WMT_OPID_FUNC_OFF;
    assert(users(subject) == 1);
}
static void teardown(void)
{
    assert(!pthread_mutex_destroy(&gDevWmt.rFreeOpQ.lock));
    assert(!pthread_mutex_destroy(&gDevWmt.rActiveOpQ.lock));
}
static void no_subject_available(void)
{
    OP *other = wmt_lib_get_free_op(); assert(other && other != subject);
    assert(!wmt_lib_get_free_op());
    assert(!wmt_lib_put_op_to_free_queue(other));
}
int main(void)
{
    /* Real waiter/worker threads; barriers select each relevant completion order. */
    for (int scenario = 0; scenario < 8; scenario++) {
        pthread_t w, c;
        setup(scenario == 4 ? 0 : 4000);
        if (scenario == 1) atomic_store(&core_result, -5);
        if (scenario == 3) atomic_store(&allow_waiter, 0);
        if (scenario == 5 || scenario == 6) atomic_store(&wait_mode, scenario - 4);
        if (scenario == 7) subject->op.opId = WMT_OPID_EXIT;
        assert(!pthread_create(&w, NULL, worker, NULL));
        assert(!pthread_create(&c, NULL, waiter, NULL));
        await(&entered);
        assert(wmt_op_current_is_func() == (scenario != 7));
        if (scenario == 2 || scenario == 3) {
            wmt_op_reset_signal();
            if (scenario == 2) {
                await(&waiter_done); assert(!waiter_result && users(subject) == 1);
                no_subject_available();
            }
        }
        if (scenario == 4 || scenario == 5 || scenario == 6) {
            await(&waiter_done);
            assert(waiter_result == (scenario == 4));
            assert(users(subject) == (scenario == 4 ? 1 : 2));
            no_subject_available();
        }
        atomic_store(&finish_core, 1);
        if (scenario == 3) {
            /* Worker completes after reset, before waiter reads the result. */
            while (users(subject) != 1) sched_yield();
            atomic_store(&allow_waiter, 1);
        }
        assert(!pthread_join(c, NULL));
        atomic_store(&gDevWmt.thread.stop, 1);
        assert(!pthread_join(w, NULL));
        assert(!gDevWmt.pCurOP);
        assert(waiter_result == (scenario == 0 || scenario == 4 || scenario == 7));
        bool retained = scenario == 5 || scenario == 6;
        assert(users(subject) == (retained ? 1 : 0));
        if (retained) no_subject_available();
        else { OP *again = wmt_lib_get_free_op(); assert(again == subject); assert(users(again) == 1); }
        teardown();
    }
    /* No worker: refusal, early block, queue draining and explicit caller release. */
    for (int scenario = 0; scenario < 5; scenario++) {
        setup(scenario == 2 ? 0 : 4000);
        if (scenario == 0) atomic_store(&fail_queue, 1);
        if (scenario == 1) atomic_store(&coredump, 1);
        if (scenario < 2) {
            assert(!wmt_lib_put_act_op(subject)); assert(users(subject) == 0);
        } else if (scenario == 2) {
            assert(wmt_lib_put_act_op(subject)); assert(users(subject) == 1);
            wmt_lib_state_init(); assert(users(subject) == 0);
        } else if (scenario == 3) {
            assert(wmt_lib_put_op_to_free_queue(NULL) == -1);
            assert(users(subject) == 1);
            assert(!wmt_lib_put_op_to_free_queue(subject)); assert(users(subject) == 0);
        } else {
            pthread_t c;
            assert(!pthread_create(&c, NULL, waiter, NULL));
            for (;;) {
                mutex_lock(&gDevWmt.rActiveOpQ.lock);
                bool ready = gDevWmt.rActiveOpQ.count;
                mutex_unlock(&gDevWmt.rActiveOpQ.lock);
                if (ready) break;
                sched_yield();
            }
            wmt_lib_state_init();
            assert(!pthread_join(c, NULL));
            assert(!waiter_result && users(subject) == 0);
        }
        assert(atomic_load(&free_puts) == 1);
        teardown();
    }
    puts("PASS: 13 directed WMT ownership paths, including reset-before-worker and reset-before-waiter-read");
    return 0;
}
'''


def function(text, signature):
    start = text.index(signature + '\n{')
    return text[start:text.index('\n}', start) + 2] + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='ownership-patched wmt_lib.c')
    args = parser.parse_args()
    raw = args.source.read_bytes()
    pins = json.loads((Path(__file__).parent / 'results/operation-ownership-sources.json').read_text())
    source_path = 'drivers/misc/mediatek/connectivity/common/common_main/core/wmt_lib.c'
    assert hashlib.sha256(raw).hexdigest() == pins['outputs'][source_path]
    text = raw.decode()
    reset = function(text, 'ENUM_WMTRSTRET_TYPE_T wmt_lib_cmb_rst(ENUM_WMTRSTSRC_TYPE_T src)')
    assert reset.count('wmt_op_reset_signal();') == 1
    assert 'osal_op_raise_signal(' not in reset and 'wmt_lib_get_current_op(' not in reset
    declarations = text[text.index('DEV_WMT gDevWmt;'):text.index('/*******************************************************************************', text.index('DEV_WMT gDevWmt;'))]
    helpers = ['static void wmt_op_get(P_OSAL_OP op)', 'static INT32 wmt_op_put(P_OSAL_OP op)',
               'static void wmt_op_complete(P_OSAL_OP op, INT32 result)', 'static void wmt_op_reset_signal(void)',
               'static bool wmt_op_current_is_func(void)',
               'INT32 wmt_lib_set_current_op(P_DEV_WMT pWmtDev, P_OSAL_OP pOp)',
               'static INT32 wmtd_thread(void *pvData)', 'VOID wmt_lib_state_init(VOID)',
               'INT32 wmt_lib_put_op_to_free_queue(P_OSAL_OP pOp)',
               'P_OSAL_OP wmt_lib_get_free_op(VOID)', 'MTK_WCN_BOOL wmt_lib_put_act_op(P_OSAL_OP pOp)']
    code = SHIM.replace('static void wmt_lib_set_current_op(P_DEV_WMT d, OP *op);',
                        'INT32 wmt_lib_set_current_op(P_DEV_WMT d, OP *op);')
    code += declarations + '\n'.join(function(text, signature) for signature in helpers) + QUEUE_AND_TEST
    with tempfile.TemporaryDirectory(prefix='wmt-ownership-') as tmp:
        c = Path(tmp) / 'test.c'; binary = Path(tmp) / 'test'
        c.write_text(code)
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pthread', str(c), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=10)
    print('Scope: actual WMT functions, pthread locks and directed injected scheduling; no kernel/reset/hardware execution')


if __name__ == '__main__':
    main()
