#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual RTC counter reader with rollover and transport faults."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path, help='prepared rtc-mt6397.c')
args = parser.parse_args()
source = args.source.read_text()
functions = []
for name in ('__mtk_rtc_read_time', 'mtk_rtc_read_time'):
    start = source.index('static int ' + name + '(')
    end = source.index('\n}\n', start) + 3
    functions.append(source[start:end])

prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
typedef unsigned short u16;
#define RTC_TC_SEC 10
#define RTC_OFFSET_SEC 0
#define RTC_OFFSET_MIN 1
#define RTC_OFFSET_HOUR 2
#define RTC_OFFSET_DOM 3
#define RTC_OFFSET_DOW 4
#define RTC_OFFSET_MTH 5
#define RTC_OFFSET_YEAR 6
#define RTC_OFFSET_COUNT 7
#define RTC_TC_MTH_MASK 15
struct device { int unused; };
struct rtc_time { int tm_sec, tm_min, tm_hour, tm_mday, tm_wday, tm_mon, tm_year; };
struct mt6397_rtc { void *regmap; unsigned int addr_base; int lock; };
static struct mt6397_rtc rtc = { .addr_base = 0x4000 };
static unsigned int attempts, seconds_reads, coherent_at, fault_at;
static int fault_phase;
static void *dev_get_drvdata(struct device *dev) { return &rtc; }
static void mutex_lock(int *lock) { assert(!*lock); *lock = 1; }
static void mutex_unlock(int *lock) { assert(*lock); *lock = 0; }
static int regmap_bulk_read(void *map, unsigned int reg, u16 *data, unsigned int count)
{
    assert(rtc.lock && reg == rtc.addr_base + RTC_TC_SEC && count == 7);
    /* Reject an unbounded implementation before it can loop indefinitely. */
    assert(++attempts <= 3);
    if (fault_phase == 1 && attempts == fault_at) return -121;
    const u16 values[] = { 59, 12, 13, 14, 3, 0x85, 126 };
    for (unsigned int i = 0; i < count; i++) data[i] = values[i];
    if (attempts == coherent_at) data[0] = 1;
    return 0;
}
static int regmap_read(void *map, unsigned int reg, int *value)
{
    assert(rtc.lock && reg == rtc.addr_base + RTC_TC_SEC);
    seconds_reads++;
    if (fault_phase == 2 && attempts == fault_at) return -5;
    *value = attempts == coherent_at ? 1 : 0;
    return 0;
}
'''
tests = r'''
int main(void)
{
    struct device dev = {0};
    unsigned int cases = 0;
    for (coherent_at = 1; coherent_at <= 4; coherent_at++) {
        struct rtc_time tm = {0};
        attempts = seconds_reads = fault_at = 0; fault_phase = 0;
        int ret = mtk_rtc_read_time(&dev, &tm);
        assert(ret == (coherent_at == 4 ? -EAGAIN : 0));
        assert(attempts == (coherent_at == 4 ? 3 : coherent_at));
        assert(seconds_reads == attempts && !rtc.lock);
        if (!ret) {
            assert(tm.tm_sec == 1 && tm.tm_min == 12 && tm.tm_hour == 13);
            assert(tm.tm_mday == 14 && tm.tm_wday == 2 && tm.tm_mon == 4);
            assert(tm.tm_year == 126);
        } else {
            assert(tm.tm_wday == 3 && tm.tm_mon == 5);
        }
        cases++;
    }
    coherent_at = 4;
    for (fault_phase = 1; fault_phase <= 2; fault_phase++) {
        for (fault_at = 1; fault_at <= 3; fault_at++) {
            struct rtc_time tm = {0};
            attempts = seconds_reads = 0;
            assert(mtk_rtc_read_time(&dev, &tm) == (fault_phase == 1 ? -121 : -5));
            assert(attempts == fault_at && !rtc.lock);
            assert(seconds_reads == fault_at - (fault_phase == 1));
            cases++;
        }
    }
    printf("PASS: %u counter-coherence/exhaustion/transport cases; three-attempt bound\n", cases);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='mt6397-read-bound-') as directory:
    root = Path(directory)
    (root / 'test.c').write_text(prefix + '\n'.join(functions) + tests)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', str(root / 'test.c'),
                    '-o', str(root / 'test')], check=True)
    subprocess.run([str(root / 'test')], check=True, timeout=2)
