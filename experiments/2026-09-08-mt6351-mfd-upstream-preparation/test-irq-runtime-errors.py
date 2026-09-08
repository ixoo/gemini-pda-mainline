#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual IRQ mask/status callbacks with injected transport errors."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path, help='prepared mt6397-irq.c')
args = parser.parse_args()
source = args.source.read_text()


def function(declaration):
    start = source.index(declaration)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


prefix = r'''
#include <assert.h>
#include <stdio.h>
#define BIT(n) (1U << (n))
#define dev_err(...) ((void)reports++)
#define dev_err_ratelimited(...) ((void)reports++)
struct mt6397_chip {
    void *dev, *regmap, *irq_domain;
    unsigned int num_irq_regs, int_con[4], irq_masks_cur[4];
    int irqlock;
};
struct irq_data { struct mt6397_chip *chip; };
static unsigned int reads, writes, reports, dispatched, fail_write, status, base;
static int fail_read, mask_phase;
static struct mt6397_chip *irq_data_get_irq_chip_data(struct irq_data *d) { return d->chip; }
static void mutex_unlock(int *lock) { assert(*lock == 1); *lock = 0; }
static int regmap_read(void *map, unsigned int reg, unsigned int *value)
{
    reads++;
    assert(!mask_phase && reg == 16 + base / 16);
    *value = fail_read ? 0xffff : status;
    return fail_read ? -121 : 0;
}
static int regmap_write(void *map, unsigned int reg, unsigned int value)
{
    writes++;
    if (mask_phase)
        assert(reg == writes - 1 && value == BIT(reg));
    else {
        assert(reg == 16 + base / 16 && value == status);
        assert(dispatched == (status ? 2u : 0u));
    }
    return writes == fail_write ? -121 : 0;
}
static unsigned int irq_find_mapping(void *domain, unsigned int irq)
{
    assert(irq >= base && irq < base + 16);
    return irq == base || irq == base + 15 ? irq + 100 : 0;
}
static void handle_nested_irq(unsigned int irq)
{
    assert(!writes && irq == base + 100 + (dispatched ? 15 : 0));
    dispatched++;
}
'''
tests = r'''
int main(void)
{
    struct mt6397_chip chip = { .num_irq_regs = 4 };
    struct irq_data data = { .chip = &chip };
    unsigned int cases = 0;
    for (unsigned int i = 0; i < 4; i++) {
        chip.int_con[i] = i;
        chip.irq_masks_cur[i] = BIT(i);
    }
    mask_phase = 1;
    for (fail_write = 0; fail_write <= 4; fail_write++) {
        reads = writes = reports = dispatched = 0;
        chip.irqlock = 1;
        mt6397_irq_sync_unlock(&data);
        assert(writes == 4 && !reads && !dispatched && !chip.irqlock);
        assert(reports == (fail_write != 0));
        for (unsigned int i = 0; i < 4; i++)
            assert(chip.irq_masks_cur[i] == BIT(i));
        cases++;
    }
    mask_phase = 0;
    for (base = 0; base < 64; base += 16) {
        for (unsigned int scenario = 0; scenario < 4; scenario++) {
            reads = writes = reports = dispatched = 0;
            fail_read = scenario == 0;
            fail_write = scenario == 1;
            status = scenario == 3 ? 0 : BIT(0) | BIT(1) | BIT(15);
            mt6397_irq_handle_reg(&chip, 16 + base / 16, base);
            assert(reads == 1);
            assert(writes == !fail_read);
            assert(dispatched == (fail_read || !status ? 0u : 2u));
            assert(reports == (scenario < 2));
            cases++;
        }
    }
    printf("PASS: %u mask/read/acknowledgement cases; no retry or dispatch change\n", cases);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='mt6397-irq-runtime-') as d:
    root = Path(d)
    (root / 'test.c').write_text(prefix + function('static void mt6397_irq_sync_unlock(')
                                 + function('static void mt6397_irq_handle_reg(') + tests)
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', str(root / 'test.c'), '-o', str(root / 'test')], check=True)
    subprocess.run([str(root / 'test')], check=True)
