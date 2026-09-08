#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare real notifier and device callbacks using the documented PM order."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('before', type=Path, help='nine-patch mt6397-irq.c')
parser.add_argument('after', type=Path, help='device-PM mt6397-irq.c')
args = parser.parse_args()
old, new = args.before.read_text(), args.after.read_text()


def function(source, declaration):
    start = source.index(declaration)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


functions = (function(old, 'static int mt6397_irq_pm_notifier(')
             + function(new, 'static int mt6397_irq_set_wake(')
             + function(new, 'int mt6397_irq_suspend(')
             + function(new, 'int mt6397_irq_resume('))
assert function(old, 'static int mt6397_irq_set_wake(') == function(new, 'static int mt6397_irq_set_wake(')
prefix = r'''
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#define BIT(n) (1U << (n))
#define NOTIFY_DONE 0
#define PM_SUSPEND_PREPARE 1
#define PM_POST_SUSPEND 2
#define container_of(p, type, member) ((type *)((char *)(p) - offsetof(type, member)))
struct notifier_block { int unused; };
struct device { void *data; };
struct mt6397_chip {
    struct device *dev;
    void *regmap;
    struct notifier_block pm_nb;
    unsigned int num_irq_regs, int_con[4], wake_mask[4], irq_masks_cur[4];
    int irq;
};
struct irq_data { unsigned int hwirq; struct mt6397_chip *chip; };
static struct mt6397_chip *irq_data_get_irq_chip_data(struct irq_data *d) { return d->chip; }
static void *dev_get_drvdata(struct device *d) { return d->data; }
static unsigned int hardware[4], writes, enables, disables;
static int wake_live;
static int regmap_write(void *map, unsigned int reg, unsigned int value)
{ assert(reg < 4); hardware[reg] = value; writes++; return 0; }
static int enable_irq_wake(int irq)
{ assert(!wake_live); wake_live = 1; enables++; return 0; }
static int disable_irq_wake(int irq)
{ assert(wake_live); wake_live = 0; disables++; return 0; }
'''
tests = r'''
int main(void)
{
    for (unsigned int banks = 2; banks <= 4; banks++) {
        struct mt6397_chip chip = { .num_irq_regs = banks };
        struct device dev = { .data = &chip };
        struct irq_data child = { .hwirq = banks * 16 - 1, .chip = &chip };
        for (unsigned int i = 0; i < banks; i++) {
            chip.int_con[i] = i;
            chip.irq_masks_cur[i] = BIT(i);
        }
        /* Old notifier precedes child device suspend/wake request. */
        writes = enables = disables = 0;
        assert(mt6397_irq_pm_notifier(&chip.pm_nb, PM_SUSPEND_PREPARE, NULL) == 0);
        assert(mt6397_irq_set_wake(&child, 1) == 0);
        assert(chip.wake_mask[banks - 1] == BIT(15));
        assert(hardware[banks - 1] == 0);
        assert(mt6397_irq_set_wake(&child, 0) == 0);
        assert(mt6397_irq_pm_notifier(&chip.pm_nb, PM_POST_SUSPEND, NULL) == 0);
        assert(writes == 2 * banks && enables == 1 && disables == 1);
        /* Device PM suspends children first and resumes the parent first. */
        writes = enables = disables = 0;
        assert(mt6397_irq_set_wake(&child, 1) == 0);
        assert(mt6397_irq_suspend(&dev) == 0);
        assert(hardware[banks - 1] == BIT(15));
        assert(mt6397_irq_resume(&dev) == 0);
        for (unsigned int i = 0; i < banks; i++)
            assert(hardware[i] == chip.irq_masks_cur[i]);
        assert(mt6397_irq_set_wake(&child, 0) == 0);
        assert(writes == 2 * banks && enables == 1 && disables == 1 && !wake_live);
    }
    /* Other IRQ-controller families have no legacy mask banks. */
    struct mt6397_chip modern = {0};
    struct device dev = { .data = &modern };
    writes = enables = disables = 0;
    assert(mt6397_irq_suspend(&dev) == 0 && mt6397_irq_resume(&dev) == 0);
    assert(!writes && !enables && !disables);
    puts("PASS: late child wake request missed before fix and programmed afterward for 2/3/4 banks; modern family unaffected");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='mt6397-pm-order-') as d:
    root = Path(d)
    (root / 'test.c').write_text(prefix + functions + tests)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', str(root / 'test.c'), '-o', str(root / 'test')], check=True)
    subprocess.run([str(root / 'test')], check=True)
