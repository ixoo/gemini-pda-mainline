#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the actual before/after IRQ init bodies with injected write errors."""

import argparse
from pathlib import Path
import re
import subprocess
import tempfile


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("before", type=Path)
parser.add_argument("after", type=Path)
args = parser.parse_args()
old, new = args.before.read_text(), args.after.read_text()


def body(source, name):
    # IRQ initialization is the final function in the reviewed source file.
    return "static int " + name + source.split("int mt6397_irq_init", 1)[1]


# Distinct fake register addresses test ordering, not physical register values.
tokens = sorted(set(re.findall(r"\bMT\d+_(?:CHIP_ID|INT_[A-Z0-9_]+|IRQ_NR)\b",
                              body(old, "before_init") + body(new, "after_init"))))
defines = []
for index, token in enumerate(tokens):
    if token.endswith("CHIP_ID"):
        value = int(re.match(r"MT(\d+)", token)[1][-2:], 16)
    elif token.endswith("IRQ_NR"):
        value = {"MT6328_IRQ_NR": 47, "MT6351_IRQ_NR": 64, "MT6397_IRQ_NR": 32}[token]
    else:
        value = 0x100 + index * 2
    defines.append(f"#define {token} {value}\n")

prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#define IRQF_ONESHOT 1
#define dev_err(...) ((void)0)
#define dev_err_probe(dev, error, ...) (error)
struct notifier_block { void (*notifier_call)(void); };
struct mt6397_chip {
    void *dev, *regmap, *irq_domain;
    unsigned int chip_id, num_irq_regs, int_con[4], int_status[4];
    int irqlock, irq;
    struct notifier_block pm_nb;
};
static unsigned int writes, fail_at, domains, requests, notifiers, domain_size;
static int domain, mt6397_irq_domain_ops;
static void mt6397_irq_thread(void) {}
static void mt6397_irq_pm_notifier(void) {}
static void mutex_init(int *lock) { *lock = 0; }
static void *dev_fwnode(void *dev) { return dev; }
static int regmap_write(void *map, unsigned int reg, unsigned int value)
{
    assert(reg >= 0x100 && value == 0);
    return ++writes == fail_at ? -121 : 0;
}
static void *irq_domain_create_linear(void *node, unsigned int size, void *ops, void *chip)
{ domains++; domain_size = size; return &domain; }
static void irq_domain_remove(void *pointer) { assert(0); }
static int devm_request_threaded_irq(void *dev, int irq, void *top,
                                    void (*thread)(void), int flags, const char *name, void *chip)
{ requests++; return 0; }
static int register_pm_notifier(struct notifier_block *nb)
{ notifiers++; return 0; }
'''
test = r'''
int main(void)
{
    const struct { unsigned int id, banks, sources; } chips[] = {
        {MT6323_CHIP_ID, 2, 32}, {MT6328_CHIP_ID, 3, 47},
        {MT6331_CHIP_ID, 2, 32}, {MT6351_CHIP_ID, 4, 64},
        {MT6391_CHIP_ID, 2, 32}, {MT6397_CHIP_ID, 2, 32},
    };
    unsigned int failures = 0;
    for (unsigned int i = 0; i < sizeof(chips) / sizeof(chips[0]); i++) {
        for (fail_at = 1; fail_at <= chips[i].banks; fail_at++) {
            struct mt6397_chip old_chip = {.chip_id = chips[i].id};
            struct mt6397_chip new_chip = {.chip_id = chips[i].id};
            writes = domains = requests = notifiers = 0;
            assert(before_init(&old_chip) == 0);
            assert(writes == chips[i].banks && domains == 1 && requests == 1 && notifiers == 1);
            writes = domains = requests = notifiers = 0;
            assert(after_init(&new_chip) == -121);
            assert(writes == fail_at && domains == 0 && requests == 0 && notifiers == 0);
            failures++;
        }
        struct mt6397_chip chip = {.chip_id = chips[i].id};
        fail_at = writes = domains = requests = notifiers = 0;
        assert(after_init(&chip) == 0);
        assert(writes == chips[i].banks && domain_size == chips[i].sources);
        assert(domains == 1 && requests == 1 && notifiers == 1);
    }
    printf("PASS: %u write failures reproduced before fix and refused afterward; six success paths preserved\n", failures);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="mt6351-irq-mask-") as directory:
    root = Path(directory)
    (root / "test.c").write_text("".join(defines) + prefix + body(old, "before_init")
                                 + body(new, "after_init") + test)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-unused-parameter", str(root / "test.c"),
                    "-o", str(root / "test")], check=True)
    subprocess.run([str(root / "test")], check=True)
