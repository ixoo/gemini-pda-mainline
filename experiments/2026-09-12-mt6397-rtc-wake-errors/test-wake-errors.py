#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the actual RTC suspend/resume callbacks and inject IRQ wake results."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path, help="prepared drivers/rtc/rtc-mt6397.c")
args = parser.parse_args()
source = args.source.read_text()
callbacks = []
for name in ("mt6397_rtc_suspend", "mt6397_rtc_resume"):
    start = source.index("static int " + name + "(")
    end = source.index("\n}\n", start) + 3
    callbacks.append(source[start:end])

prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
struct mt6397_rtc { unsigned int irq; };
struct device { struct mt6397_rtc *rtc; int may_wakeup; };
static int wake_result, enable_calls, disable_calls;
static void *dev_get_drvdata(struct device *dev) { return dev->rtc; }
static int device_may_wakeup(struct device *dev) { return dev->may_wakeup; }
static int enable_irq_wake(unsigned int irq)
{
    assert(irq == 47);
    enable_calls++;
    return wake_result;
}
static int disable_irq_wake(unsigned int irq)
{
    assert(irq == 47);
    disable_calls++;
    return wake_result;
}
'''
tests = r'''
int main(void)
{
    struct mt6397_rtc rtc = { .irq = 47 };
    struct device dev = { .rtc = &rtc };
    const int errors[] = { 0, -EIO, -EINVAL, -ENXIO };
    int (*callbacks[])(struct device *) = {
        mt6397_rtc_suspend, mt6397_rtc_resume
    };
    unsigned int cases = 0;

    for (unsigned int which = 0; which < 2; which++) {
        for (dev.may_wakeup = 0; dev.may_wakeup < 2; dev.may_wakeup++) {
            for (unsigned int i = 0; i < sizeof(errors) / sizeof(errors[0]); i++) {
                wake_result = errors[i];
                enable_calls = disable_calls = 0;
                int ret = callbacks[which](&dev);
                int expected = dev.may_wakeup ? wake_result : 0;
                if (ret != expected) {
                    fprintf(stderr, "%s wake=%d: expected %d, got %d\n",
                            which ? "resume" : "suspend", dev.may_wakeup,
                            expected, ret);
                    return 1;
                }
                assert(enable_calls == (dev.may_wakeup && which == 0));
                assert(disable_calls == (dev.may_wakeup && which == 1));
                cases++;
            }
        }
    }
    printf("PASS: %u RTC wake policy/error cases\n", cases);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="mt6397-rtc-wake-") as directory:
    path = Path(directory)
    (path / "test.c").write_text(prefix + "\n".join(callbacks) + tests)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    str(path / "test.c"), "-o", str(path / "test")], check=True)
    subprocess.run([str(path / "test")], check=True)
