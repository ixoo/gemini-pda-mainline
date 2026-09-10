#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the native capture/arm entry point with injected boundary failures."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = 'drivers/watchdog/mediatek/wdk/wd_common_drv.c'
HEADER = 'drivers/watchdog/mediatek/include/ext_wd_drv.h'
SHIM = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint32_t __le32;
typedef int atomic_t;
#define cpu_to_le32(x) ((uint32_t)(x))
#define READ_ONCE(x) (x)
static atomic_t capture_attempted;
static int atomic_cmpxchg(int *p, int old, int new)
{ int result = *p; if (result == old) *p = new; return result; }
static int context, idle_off, panic_timeout, lock, held, hotplug;
static int g_enable, g_kicker_init;
static struct { int ready; } api;
static typeof(api) *g_wd_api;
static int begin_error, arm_error, arm_owned, append_failure;
static int begins, arms, appends, event_count, events[12];
static uint32_t saved[2][7];
static int in_interrupt(void) { return context == 1; }
static int irqs_disabled(void) { return context == 2; }
static void might_sleep(void) { assert(!context); }
static int cpuidle_disabled(void) { return idle_off; }
static void cpu_hotplug_disable(void) { assert(!held); hotplug++; events[event_count++] = 3; }
static void cpu_hotplug_enable(void) { assert(!held && hotplug == 1); hotplug--; }
#define spin_lock_irqsave(p, f) do { (void)(p); (f) = 0; assert(!held); held = 1; } while (0)
#define spin_unlock_irqrestore(p, f) do { (void)(p); (void)(f); assert(held); held = 0; } while (0)
static int ramoops_capture_begin(const u8 *cycle, const u8 *identity)
{
    assert(cycle && identity && !held && !hotplug);
    begins++; events[event_count++] = 1; return begin_error;
}
static int ramoops_capture_append(unsigned int kind, u32 tx, const u8 *data, size_t size)
{
    assert(!held && !tx);
    appends++;
    if (kind == 255) {
        assert(size == 4 && *(const uint32_t *)data == 2);
        events[event_count++] = 6;
    } else {
        assert(kind == 11 && size == 28);
        unsigned int stage = *(const uint32_t *)data;
        assert(stage == 1 || stage == 2);
        memcpy(saved[stage - 1], data, size);
        events[event_count++] = stage == 1 ? 2 : 5;
    }
    return appends == append_failure ? -ENOSPC : 0;
}
'''
ARM = r'''
static int mtk_wdt_recovery_arm(unsigned int timeout, struct mtk_wdt_recovery_state *s)
{
    assert(timeout == 12 && held && hotplug == 1 && !g_enable);
    assert(begins == 1 && appends == 1);
    arms++; events[event_count++] = 4;
    s->owned = arm_owned;
    s->mode_before = 0x48;
    s->mode_after = 5;
    s->length_after = 12 * 64 * 32;
    return arm_error;
}
'''
CASES = r'''
int main(void)
{
    const u8 cycle[16] = {1}, identity[80] = {1};
    for (int fault = 0; fault < 15; fault++) {
        struct mtk_wdt_recovery_state s = {0}, second = {99};
        capture_attempted = context = panic_timeout = held = hotplug = 0;
        begin_error = arm_error = append_failure = 0;
        begins = arms = appends = event_count = 0;
        idle_off = g_enable = g_kicker_init = api.ready = arm_owned = 1;
        g_wd_api = &api;
        memset(saved, 0, sizeof(saved));
        if (fault >= 1 && fault <= 2) context = fault;
        if (fault == 3) panic_timeout = -1;
        if (fault == 4) idle_off = 0;
        if (fault == 5) panic_timeout = 1;
        if (fault == 6) begin_error = -EBUSY;
        if (fault == 7) append_failure = 1;
        if (fault == 8) g_kicker_init = 0;
        if (fault == 9) g_wd_api = NULL;
        if (fault == 10) api.ready = 0;
        if (fault == 11) g_enable = 0;
        if (fault == 12) { arm_error = -ENODEV; arm_owned = 0; }
        if (fault == 13) arm_error = -EIO;
        if (fault == 14) append_failure = 2;
        int ret = mtk_wdt_capture_begin(cycle, identity, &s);
        assert(!held);
        assert((ret == 0) == (fault == 0));
        if (fault >= 1 && fault <= 5) assert(!begins && !arms && !appends);
        if (fault == 6) assert(begins == 1 && !arms && !appends);
        if (fault == 7) assert(!arms && appends == 2);
        if (fault >= 8 && fault <= 11) assert(!arms && appends == 3);
        if (fault == 0 || fault >= 12) {
            const int expected[] = {1, 2, 3, 4, 5};
            assert(!memcmp(events, expected, sizeof(expected)) && arms == 1);
            assert(saved[1][2] == (unsigned int)arm_owned);
            assert((int32_t)saved[1][6] == arm_error);
        }
        if (fault == 0 || fault >= 13) assert(s.owned && hotplug == 1 && !g_enable);
        else assert(!s.owned && !hotplug && g_enable == (fault == 11 ? 0 : 1));
        if (fault == 0 || fault >= 3) {
            int old_events = event_count;
            assert(mtk_wdt_capture_begin(cycle, identity, &second) == -EALREADY);
            assert(second.owned == 99 && event_count == old_events);
        }
    }
    struct mtk_wdt_recovery_state untouched = {99};
    assert(mtk_wdt_capture_begin(NULL, identity, &untouched) == -EINVAL);
    assert(untouched.owned == 99);
    puts("PASS: 15 capture/arm boundary cases, one-shot and invalid argument refusal");
}
'''


def main():
    tree = Path(sys.argv[1])
    pins = json.loads((HERE / 'results/recovery-gate-sources.json').read_text())
    for path, expected in pins['outputs'].items():
        assert hashlib.sha256((tree / path).read_bytes()).hexdigest() == expected
    source = (tree / SOURCE).read_text()
    start = source.index('int mtk_wdt_capture_begin(')
    body = source[start:source.index('\n}', start) + 2]
    state = re.search(r'struct mtk_wdt_recovery_state \{.*?\};',
                      (tree / HEADER).read_text(), re.S).group()
    with tempfile.TemporaryDirectory(prefix='wifi-recovery-gate-') as directory:
        cfile, binary = Path(directory) / 'gate.c', Path(directory) / 'gate'
        cfile.write_text(SHIM + state + ARM + body + CASES)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-missing-field-initializers', '-DCONFIG_CPU_IDLE',
                        str(cfile), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=10)


if __name__ == '__main__':
    main()
