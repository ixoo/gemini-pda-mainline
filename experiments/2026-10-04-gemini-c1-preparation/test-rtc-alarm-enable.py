#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise RTC alarm enable and the actual class AIE_OFF delegation path."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path, help='prepared rtc-mt6397.c')
parser.add_argument('interface', type=Path, help='same-tree drivers/rtc/interface.c')
args = parser.parse_args()
source, interface = args.source.read_text(), args.interface.read_text()
if not re.search(r'\.alarm_irq_enable\s*=\s*mtk_rtc_alarm_irq_enable', source):
    raise SystemExit('RTC class callback is not registered')


def function(text, declaration):
    start = text.index(declaration)
    end = text.index('\n}\n', start) + 3
    return text[start:end]


callback = function(source, 'static int mtk_rtc_alarm_irq_enable(')
disable = function(interface, 'static void rtc_alarm_disable(')
core = function(interface, 'int rtc_alarm_irq_enable(')
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdbool.h>
#define RTC_IRQ_EN 4
#define RTC_IRQ_EN_ONESHOT_AL 5
#define RTC_FEATURE_ALARM 0
#define test_bit(bit, features) ((features) & 1)
#define trace_rtc_alarm_irq_enable(...) ((void)0)
#define dev_err_ratelimited(dev, ...) ((void)(dev), (void)reports++)
struct device { struct device *parent; };
struct rtc_timer { unsigned int enabled; };
struct rtc_class_ops { int (*alarm_irq_enable)(struct device *, unsigned int); };
struct rtc_device {
    struct device dev;
    struct rtc_timer aie_timer;
    const struct rtc_class_ops *ops;
    int ops_lock;
    unsigned int features;
};
struct mt6397_rtc { void *regmap; unsigned int addr_base; int lock; };
static struct mt6397_rtc driver = { .addr_base = 0x4000 };
static unsigned int enables, reads, writes, triggers, reports, removals;
static int fault;
static void *dev_get_drvdata(struct device *dev) { return &driver; }
static void mutex_lock(int *lock) { assert(!*lock); *lock = 1; }
static void mutex_unlock(int *lock) { assert(*lock); *lock = 0; }
static int mutex_lock_interruptible(int *lock) { mutex_lock(lock); return 0; }
static int regmap_update_bits(void *map, unsigned int reg, unsigned int mask,
                              unsigned int value)
{
    assert(driver.lock && reg == driver.addr_base + RTC_IRQ_EN && mask == 5);
    reads++;
    if (fault == 1) return -121;
    unsigned int next = (enables & ~mask) | (value & mask);
    if (next != enables) {
        writes++;
        if (fault == 2) return -5;
        enables = next;
    }
    return 0;
}
static int mtk_rtc_write_trigger(struct mt6397_rtc *rtc)
{
    assert(rtc == &driver && driver.lock);
    triggers++;
    return fault == 3 ? -5 : fault == 4 ? -110 : 0;
}
static int rtc_timer_enqueue(struct rtc_device *rtc, struct rtc_timer *timer)
{ assert(0); return 0; } /* This integration fixture exercises disable only. */
static void rtc_alarm_disable(struct rtc_device *rtc);
static void rtc_timer_remove(struct rtc_device *rtc, struct rtc_timer *timer)
{
    assert(rtc->ops_lock && timer->enabled);
    timer->enabled = 0;
    removals++;
    /* Model removal of the sole timer; real core then disables the alarm. */
    rtc_alarm_disable(rtc);
}
'''
tests = r'''
int main(void)
{
    struct device dev = {0};
    const unsigned int initial[] = {0, 1, 4, 5, 8, 9, 12, 13, 0x8001, 0xffff};
    unsigned int cases = 0;
    for (unsigned int enabled = 0; enabled < 2; enabled++) {
        for (unsigned int i = 0; i < sizeof(initial) / sizeof(initial[0]); i++) {
            for (fault = 0; fault < 5; fault++) {
                unsigned int target = (initial[i] & ~5u) | (enabled ? 5 : 0);
                int changed = target != initial[i];
                int update_ok = fault != 1 && !(fault == 2 && changed);
                enables = initial[i]; reads = writes = triggers = reports = 0;
                int expected = fault == 1 ? -121 : !update_ok || fault == 3 ? -5 :
                               fault == 4 ? -110 : 0;
                assert(mtk_rtc_alarm_irq_enable(&dev, enabled) == expected);
                assert(!driver.lock && reads == 1);
                assert(writes == (unsigned int)(fault != 1 && changed));
                assert(triggers == (unsigned int)update_ok);
                assert(reports == (unsigned int)(expected != 0));
                assert(enables == (update_ok ? target : initial[i]));
                cases++;
            }
        }
    }
    const struct rtc_class_ops ops = { .alarm_irq_enable = mtk_rtc_alarm_irq_enable };
    for (unsigned int cached = 0; cached < 2; cached++) {
        for (fault = 0; fault < 5; fault++) {
            struct rtc_device rtc = { .dev.parent = &dev, .ops = &ops,
                                     .features = 1, .aie_timer.enabled = cached };
            enables = 13; reads = writes = triggers = reports = removals = 0;
            int expected = fault == 1 ? -121 : fault == 2 || fault == 3 ? -5 :
                           fault == 4 ? -110 : 0;
            assert(rtc_alarm_irq_enable(&rtc, 0) == expected);
            assert(!rtc.ops_lock && !driver.lock && !rtc.aie_timer.enabled);
            assert(removals == cached && reads == 1 + cached);
            assert(reports == (expected ? 1 + cached : 0));
            if (!expected) assert(enables == 8);
            cases++;
        }
    }
    /* Reproduce the old missing callback: timer removal alone is not a disable. */
    struct rtc_class_ops missing = {0};
    struct rtc_device rtc = { .dev.parent = &dev, .ops = &missing,
                             .features = 1, .aie_timer.enabled = 1 };
    enables = 13; reads = removals = 0;
    assert(rtc_alarm_irq_enable(&rtc, 0) == -EINVAL);
    assert(removals == 1 && reads == 0 && enables == 13);
    cases++;
    printf("PASS: %u alarm enable/error/class-delegation cases\n", cases);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='mt6397-alarm-enable-') as directory:
    root = Path(directory)
    (root / 'test.c').write_text(prefix + callback + '\n' + disable + '\n' + core + tests)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', str(root / 'test.c'),
                    '-o', str(root / 'test')], check=True)
    subprocess.run([str(root / 'test')], check=True)
