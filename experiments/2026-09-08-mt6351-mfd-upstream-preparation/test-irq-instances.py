#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual MT6358 IRQ initialization and masks for concurrent instances."""

import argparse
from pathlib import Path
import re
import subprocess
import tempfile


def function(source, declaration):
    start = source.index(declaration)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path, help='prepared drivers/mfd/mt6358-irq.c')
args = parser.parse_args()
source = args.source.read_text()
start = re.search(r'static (?:const )?struct pmic_irq_data mt6357_irqd =', source)
if start is None:
    raise ValueError('Missing chip IRQ descriptions')
tables = source[start.start():source.index('static void pmic_irq_enable')]
callbacks = ''.join(function(source, signature) for signature in (
    'static void pmic_irq_enable(', 'static void pmic_irq_disable(',
    'static void pmic_irq_lock(', 'static void pmic_irq_sync_unlock(',
    'static void mt6358_irq_disable_wake(', 'int mt6358_irq_init(',
))
fixture = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define GFP_KERNEL 0
#define IRQF_ONESHOT 1
#define MTK_PMIC_REG_WIDTH 16
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define BIT(n) (1U << (n))
#define MT6357_CHIP_ID 0x57
#define MT6358_CHIP_ID 0x58
#define MT6359_CHIP_ID 0x59
#define MT6366_CHIP_ID 0x66
/* Register geometry is modeled; chip selection and allocations are actual source. */
#define MT6357_IRQ_NR 16
#define MT6358_IRQ_NR 16
#define MT6359_IRQ_NR 16
#define MT6357_TOP_INT_STATUS0 0x10
#define MT6358_TOP_INT_STATUS0 0x20
#define MT6359_TOP_INT_STATUS0 0x30
#define dev_err(...) ((void)0)
#define dev_err_probe(dev, error, ...) (error)
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
struct irq_top_t { int hwirq_base; unsigned int num_int_regs, en_reg, en_reg_shift; };
struct pmic_irq_data {
    unsigned int num_top, num_pmic_irqs;
    unsigned short top_int_status_reg;
    bool *enable_hwirq, *cache_hwirq;
    const struct irq_top_t *pmic_ints;
};
static const struct irq_top_t mt6357_ints[] = {{0, 1, 0x100, 2}};
static const struct irq_top_t mt6358_ints[] = {{0, 1, 0x200, 2}};
static const struct irq_top_t mt6359_ints[] = {{0, 1, 0x300, 2}};
struct device {
    void *allocations[3];
    unsigned int allocations_count, attempts, fail_at, writes, updates;
    unsigned int last_reg, last_mask, last_value;
    bool parent_requested;
};
struct irq_domain { int unused; };
struct mt6397_chip {
    struct device *dev, *regmap;
    struct pmic_irq_data *irq_data;
    struct irq_domain *irq_domain;
    unsigned int chip_id;
    int irqlock, irq;
};
struct irq_data { struct mt6397_chip *chip; unsigned int hwirq; };
struct irq_domain_info {
    void *fwnode, *ops, *host_data;
    unsigned int size, hwirq_max;
    void (*exit)(struct irq_domain *);
};
static struct { const char *name; } mt6358_irq_chip = {"fixture"};
static int mt6358_irq_domain_ops;
static void mt6397_irq_domain_exit(struct irq_domain *d) {}
static void mt6358_irq_handler(void) {}
static void *dev_fwnode(struct device *dev) { return dev; }
static unsigned int irqd_to_hwirq(struct irq_data *data) { return data->hwirq; }
static struct mt6397_chip *irq_data_get_irq_chip_data(struct irq_data *data)
{ return data->chip; }
static void mutex_init(int *lock) { *lock = 0; }
static void mutex_lock(int *lock) { assert(!*lock); *lock = 1; }
static void mutex_unlock(int *lock) { assert(*lock); *lock = 0; }
static void *devm_kcalloc(struct device *dev, size_t n, size_t size, int flags)
{
    if (++dev->attempts == dev->fail_at)
        return NULL;
    assert(dev->allocations_count < ARRAY_SIZE(dev->allocations));
    void *p = calloc(n, size);
    assert(p);
    dev->allocations[dev->allocations_count++] = p;
    return p;
}
static void *devm_kmemdup(struct device *dev, const void *src, size_t size, int flags)
{
    void *p = devm_kcalloc(dev, 1, size, flags);
    if (p)
        memcpy(p, src, size);
    return p;
}
static void release(struct device *dev)
{
    while (dev->allocations_count)
        free(dev->allocations[--dev->allocations_count]);
}
static int regmap_write(struct device *dev, unsigned int reg, unsigned int value)
{ dev->writes++; return 0; }
static int regmap_update_bits(struct device *dev, unsigned int reg,
                              unsigned int mask, unsigned int value)
{
    dev->updates++;
    dev->last_reg = reg; dev->last_mask = mask; dev->last_value = value;
    return 0;
}
static struct irq_domain *devm_irq_domain_instantiate(struct device *dev,
                                                    struct irq_domain_info *info)
{ return (struct irq_domain *)dev; }
static int devm_request_threaded_irq(struct device *dev, int irq, void *top,
                                    void (*thread)(void), int flags,
                                    const char *name, void *chip)
{ dev->parent_requested = true; return 0; }
static int enable_irq_wake(int irq) { return 0; }
static int disable_irq_wake(int irq) { return 0; }
static int devm_add_action_or_reset(struct device *dev, void (*fn)(void *), void *data)
{ return 0; }
/* SOURCE */
static void mask(struct mt6397_chip *chip, unsigned int irq, bool enable)
{
    struct irq_data data = {chip, irq};
    pmic_irq_lock(&data);
    if (enable)
        pmic_irq_enable(&data);
    else
        pmic_irq_disable(&data);
    pmic_irq_sync_unlock(&data);
    assert(!chip->irqlock);
    assert(chip->irq_data->enable_hwirq[irq] == enable);
    assert(chip->irq_data->cache_hwirq[irq] == enable);
    assert(chip->dev->last_reg == chip->irq_data->pmic_ints[0].en_reg);
    assert(chip->dev->last_mask == BIT(irq));
    assert(chip->dev->last_value == (enable ? BIT(irq) : 0));
}
int main(void)
{
    const unsigned int ids[] = {MT6357_CHIP_ID, MT6358_CHIP_ID,
                               MT6366_CHIP_ID, MT6359_CHIP_ID};
    unsigned int cases = 0;
    for (unsigned int i = 0; i < ARRAY_SIZE(ids); i++) {
        for (unsigned int j = 0; j < ARRAY_SIZE(ids); j++) {
            for (unsigned int failure = 0; failure <= 3; failure++) {
                struct device da = {0}, db = {.fail_at = failure};
                struct mt6397_chip a = {.dev = &da, .regmap = &da, .chip_id = ids[i]};
                struct mt6397_chip b = {.dev = &db, .regmap = &db, .chip_id = ids[j]};
                assert(mt6358_irq_init(&a) == 0);
                assert(da.parent_requested);
                mask(&a, 3, true);
                struct pmic_irq_data *saved = a.irq_data;
                bool *enabled = saved->enable_hwirq, *cached = saved->cache_hwirq;
                unsigned int previous_updates = da.updates;
                assert(mt6358_irq_init(&b) == (failure ? -ENOMEM : 0));
                assert(a.irq_data == saved);
                assert(saved->enable_hwirq == enabled && saved->cache_hwirq == cached);
                assert(enabled[3] && cached[3]);
                assert(da.updates == previous_updates);
                if (failure) {
                    assert(db.attempts == failure && !db.writes && !db.parent_requested);
                } else {
                    assert(a.irq_data != b.irq_data);
                    assert(enabled != b.irq_data->enable_hwirq);
                    assert(cached != b.irq_data->cache_hwirq);
                    assert(!b.irq_data->enable_hwirq[3] && !b.irq_data->cache_hwirq[3]);
                    mask(&b, 5, true);
                    assert(!enabled[5] && !cached[5]);
                    assert(da.updates == previous_updates);
                }
                release(&db);
                mask(&a, 3, false);
                mask(&a, 6, true);
                release(&da);
                assert(!mt6357_irqd.enable_hwirq && !mt6357_irqd.cache_hwirq);
                assert(!mt6358_irqd.enable_hwirq && !mt6358_irqd.cache_hwirq);
                assert(!mt6359_irqd.enable_hwirq && !mt6359_irqd.cache_hwirq);
                cases++;
            }
        }
    }
    struct device bad_dev = {0};
    struct mt6397_chip bad = {.dev = &bad_dev, .chip_id = 0xff};
    assert(mt6358_irq_init(&bad) == -ENODEV && !bad_dev.attempts && !bad_dev.writes);
    printf("PASS: %u two-instance/allocation-failure cases plus unsupported chip\n", cases);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='mt6358-irq-instances-') as directory:
    root = Path(directory)
    test = root / 'test.c'
    test.write_text(fixture.replace('/* SOURCE */', tables + callbacks))
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', '-Wno-unused-function', '-Wno-sign-compare',
                    str(test), '-o', str(root / 'test')], check=True)
    subprocess.run([str(root / 'test')], check=True)
