#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the real RTC alarm handler against a small register/IRQ fixture."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path, help="prepared drivers/rtc/rtc-mt6397.c")
args = parser.parse_args()
source = args.source.read_text()
start = source.index("static irqreturn_t mtk_rtc_irq_handler_thread(")
end = source.index("\n}\n", start) + 3
handler = source[start:end]

prefix = r'''
#include <assert.h>
#include <stdio.h>
typedef unsigned int u32;
typedef int irqreturn_t;
#define RTC_IRQ_STA 2
#define RTC_IRQ_EN 4
#define RTC_IRQ_STA_AL 1
#define RTC_IRQ_EN_AL 1
#define RTC_IRQF 0x80
#define RTC_AF 0x20
#define IRQ_NONE 0
#define IRQ_HANDLED 1
struct mt6397_rtc { void *regmap, *rtc_dev; unsigned int addr_base; int lock; };
static struct mt6397_rtc rtc = { .addr_base = 0x4000 };
static unsigned int status, enables, reads, writes, triggers, notifications;
static int fault;
static void mutex_lock(int *lock) { assert(!*lock); *lock = 1; }
static void mutex_unlock(int *lock) { assert(*lock); *lock = 0; }
static int regmap_read(void *map, unsigned int reg, u32 *value)
{
    reads++;
    if (reg == rtc.addr_base + RTC_IRQ_STA) {
        if (fault == 1) return -5;
        *value = status;
    } else {
        assert(rtc.lock && reg == rtc.addr_base + RTC_IRQ_EN);
        if (fault == 2) return -121;
        *value = enables;
    }
    return 0;
}
static int regmap_write(void *map, unsigned int reg, unsigned int value)
{
    assert(rtc.lock && reg == rtc.addr_base + RTC_IRQ_EN);
    writes++;
    if (fault == 3) return -121;
    enables = value;
    return 0;
}
static int regmap_update_bits(void *map, unsigned int reg,
                              unsigned int mask, unsigned int value)
{
    unsigned int old, next;
    int ret = regmap_read(map, reg, &old);
    if (ret) return ret;
    next = (old & ~mask) | (value & mask);
    return next == old ? 0 : regmap_write(map, reg, next);
}
static int mtk_rtc_write_trigger(struct mt6397_rtc *data)
{
    assert(data == &rtc && rtc.lock);
    triggers++;
    return 0;
}
static void rtc_update_irq(void *dev, int count, int flags)
{
    assert(count == 1 && flags == (RTC_IRQF | RTC_AF));
    notifications++;
}
'''
tests = r'''
int main(void)
{
    /* Alarm, one-shot, low-power and unrelated bits vary independently. */
    const unsigned int initial[] = { 13, 0, 1, 4, 5, 8, 9, 12, 0x8001, 0xffff };
    const unsigned int statuses[] = { 1, 0, 8, 9 };
    unsigned int cases = 0;
    for (unsigned int i = 0; i < sizeof(initial) / sizeof(initial[0]); i++) {
        for (unsigned int j = 0; j < sizeof(statuses) / sizeof(statuses[0]); j++) {
            for (fault = 0; fault < 4; fault++) {
                unsigned int original = initial[i];
                enables = original;
                status = statuses[j];
                reads = writes = triggers = notifications = 0;
                int handled = fault != 1 && (status & 1);
                int update_ok = handled && fault != 2 &&
                                (fault != 3 || !(original & 1));
                int ret = mtk_rtc_irq_handler_thread(7, &rtc);
                assert(ret == (handled ? IRQ_HANDLED : IRQ_NONE));
                assert(!rtc.lock && notifications == (unsigned int)handled);
                assert(enables == (update_ok ? (original & ~1u) : original));
                assert(triggers == (unsigned int)update_ok);
                assert(reads == (handled ? 2u : 1u));
                assert(writes == (unsigned int)(handled && fault != 2 && (original & 1)));
                cases++;
            }
        }
    }
    printf("PASS: %u alarm/status/enable/transport cases\n", cases);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="mt6397-alarm-mask-") as directory:
    path = Path(directory)
    (path / "test.c").write_text(prefix + handler + tests)
    subprocess.run([
        "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
        "-Wno-unused-parameter", "-Wno-unused-function",
        str(path / "test.c"), "-o", str(path / "test"),
    ], check=True)
    subprocess.run([str(path / "test")], check=True)
