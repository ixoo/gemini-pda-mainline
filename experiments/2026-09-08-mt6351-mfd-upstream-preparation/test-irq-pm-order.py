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


has_recovery = 'static int mt6397_irq_restore_masks(' in new
helpers = ''.join(function(new, declaration) for declaration in [
    'static int mt6397_irq_restore_masks(', 'static int mt6397_irq_disable_wake(',
    'static void mt6397_irq_release_wake(']) if has_recovery else ''
functions = (helpers + function(old, 'static int mt6397_irq_pm_notifier(')
             + function(new, 'static int mt6397_irq_set_wake(')
             + function(new, 'int mt6397_irq_suspend(')
             + function(new, 'int mt6397_irq_resume('))
assert function(old, 'static int mt6397_irq_set_wake(') == function(new, 'static int mt6397_irq_set_wake(')
prefix = r'''
#include <assert.h>
#include <stddef.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#define BIT(n) (1U << (n))
#define NOTIFY_DONE 0
#define dev_err(...) ((void)errors++)
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
    int irq, irqlock;
    bool irq_wake_enabled;
};
struct irq_data { unsigned int hwirq; struct mt6397_chip *chip; };
static struct mt6397_chip *irq_data_get_irq_chip_data(struct irq_data *d) { return d->chip; }
static void *dev_get_drvdata(struct device *d) { return d->data; }
static unsigned int hardware[4], writes, enables, disables;
static int wake_live;
static unsigned int fail_write, fail_write_second, fail_enable, fail_disable;
#if HAS_RECOVERY
static unsigned int errors;
static void mutex_lock(int *lock) { assert(!*lock); *lock = 1; }
static void mutex_unlock(int *lock) { assert(*lock); *lock = 0; }
static void reset_faults(void)
{
    writes = enables = disables = errors = 0;
    fail_write = fail_write_second = fail_enable = fail_disable = 0;
}
#endif
static int regmap_write(void *map, unsigned int reg, unsigned int value)
{
    assert(reg < 4);
    writes++;
    if (writes == fail_write_second)
        return -EIO;
    /* A failed transaction may already have changed the register. */
    hardware[reg] = value;
    return writes == fail_write ? -121 : 0;
}
static int enable_irq_wake(int irq)
{ assert(!wake_live); enables++; if (fail_enable) return -ENXIO; wake_live = 1; return 0; }
static int disable_irq_wake(int irq)
{ assert(wake_live); disables++; if (fail_disable) return -EAGAIN; wake_live = 0; return 0; }
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
#if HAS_RECOVERY
    unsigned int recovery_cases = 0;
    for (unsigned int banks = 2; banks <= 4; banks++) {
        struct mt6397_chip chip = { .num_irq_regs = banks };
        struct device dev = { .data = &chip };
        for (unsigned int i = 0; i < banks; i++) {
            chip.int_con[i] = i;
            chip.irq_masks_cur[i] = BIT(i);
            chip.wake_mask[i] = BIT(15);
        }
        for (unsigned int at = 1; at <= banks; at++) {
            for (unsigned int rollback = 0; rollback <= banks; rollback++) {
                reset_faults();
                fail_write = at;
                fail_write_second = rollback ? at + rollback : 0;
                assert(mt6397_irq_suspend(&dev) == -121);
                assert(writes == at + banks && !enables && !disables);
                assert(errors == 1 + (rollback != 0));
                assert(!chip.irq_wake_enabled && !chip.irqlock && !wake_live);
                if (!rollback)
                    for (unsigned int i = 0; i < banks; i++)
                        assert(hardware[i] == chip.irq_masks_cur[i]);
                recovery_cases++;
            }
        }
        for (unsigned int rollback = 0; rollback <= banks; rollback++) {
            reset_faults();
            fail_enable = 1;
            fail_write_second = rollback ? banks + rollback : 0;
            assert(mt6397_irq_suspend(&dev) == -ENXIO);
            assert(writes == 2 * banks && enables == 1 && !disables);
            assert(errors == 1 + (rollback != 0));
            assert(!chip.irq_wake_enabled && !chip.irqlock && !wake_live);
            recovery_cases++;
        }
        for (unsigned int bank = 0; bank <= banks; bank++) {
            for (unsigned int wake_error = 0; wake_error <= 1; wake_error++) {
                reset_faults();
                assert(mt6397_irq_suspend(&dev) == 0);
                assert(chip.irq_wake_enabled && wake_live);
                reset_faults();
                fail_write = bank;
                fail_disable = wake_error;
                assert(mt6397_irq_resume(&dev) == (bank ? -121 : wake_error ? -EAGAIN : 0));
                assert(writes == banks && !enables && disables == 1);
                assert(errors == (bank != 0) + wake_error && !chip.irqlock);
                assert(chip.irq_wake_enabled == wake_error && wake_live == (int)wake_error);
                if (wake_error) {
                    reset_faults();
                    assert(mt6397_irq_suspend(&dev) == -EBUSY);
                    assert(!writes && !enables && !disables && !chip.irqlock);
                    mt6397_irq_release_wake(&chip);
                    assert(disables == 1 && !chip.irq_wake_enabled && !wake_live);
                }
                recovery_cases++;
            }
        }
        reset_faults();
        assert(mt6397_irq_suspend(&dev) == 0);
        reset_faults();
        mt6397_irq_release_wake(&chip);
        assert(!writes && !enables && disables == 1 && !wake_live);
        assert(!chip.irq_wake_enabled && !chip.irqlock);
        recovery_cases++;
    }
    reset_faults();
    printf("PASS: %u suspend/recovery/wake-ownership cases\n", recovery_cases);
#endif
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
    (root / 'test.c').write_text(f'#define HAS_RECOVERY {int(has_recovery)}\n' + prefix + functions + tests)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', str(root / 'test.c'), '-o', str(root / 'test')], check=True)
    subprocess.run([str(root / 'test')], check=True)
