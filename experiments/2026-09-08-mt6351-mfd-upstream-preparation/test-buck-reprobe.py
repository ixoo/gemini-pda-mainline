#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the exact old/new selector helpers with an injected regmap."""

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "patches/v7.1.3/0015-regulator-mt6351-add-regulator-driver.patch"
NEW = ROOT / "patches/upstream-4d7d9486/mt6351/0005-regulator-mt6351-add-E2-rails-with-device-local-desc.patch"


def driver(patch):
    section = patch.read_text().split(
        "+++ b/drivers/regulator/mt6351-regulator.c\n", 1)[1].split("\ndiff --git", 1)[0]
    return "\n".join(line[1:] for line in section.splitlines() if line.startswith("+"))


def helper(source, name):
    body = source.split("static int mt6351_select_buck_vsel_regs", 1)[1]
    body = body.split("\nstatic int mt6351_regulator_probe", 1)[0]
    return "static int " + name + body


old, new = driver(OLD), driver(NEW)
assert "static const struct mt6351_regulator_info mt6351_regulators[]" in new
assert "regulators = devm_kmemdup(&pdev->dev, mt6351_regulators," in new
assert "sizeof(mt6351_regulators), GFP_KERNEL);" in new
assert "&regulators[i].desc, &config" in new
assert "config.driver_data = &regulators[i];" in new

# This is a helper-level host test, not a kernel build or regulator-core test.
# Representative buck rows share the real 39-entry iteration bound; LDO rows
# have no selector-control register and must not be read by this helper.
prefix = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define MT6351_ID_VREG_MAX 39
#define MT6351_BUCK_VOSEL_CTRL 2
#define dev_err(...) ((void)0)
struct device { int unused; };
struct regmap { unsigned int value; unsigned int fail_reg; unsigned int reads; };
struct mt6351_regulator_info {
    struct { const char *name; unsigned int vsel_reg; } desc;
    unsigned short qi, vsel_on_reg, vsel_ctrl_reg;
};
static struct mt6351_regulator_info mt6351_regulators[MT6351_ID_VREG_MAX];
static int regmap_read(struct regmap *map, unsigned int reg, unsigned int *value)
{
    map->reads++;
    if (reg == map->fail_reg)
        return -5;
    *value = map->value;
    return 0;
}
'''
test = r'''
int main(void)
{
    struct device dev = {0};
    struct regmap on = {2, 0, 0}, off = {0, 0, 0}, failed = {2, 2, 0};
    struct mt6351_regulator_info original[39] = {
        {{"first", 10}, 0, 11, 1},
        {{"second", 20}, 0, 21, 2},
    };
    struct mt6351_regulator_info first[39], second[39];
    memcpy(mt6351_regulators, original, sizeof(original));
    assert(old_select(&dev, &on) == 0);
    assert(old_select(&dev, &off) == 0);
    assert(mt6351_regulators[0].desc.vsel_reg == 11);
    puts("reproduced: old helper retains on-register after control clears");
    memcpy(first, original, sizeof(first));
    memcpy(second, original, sizeof(second));
    on.reads = off.reads = 0;
    assert(new_select(&dev, &on, first) == 0);
    assert(new_select(&dev, &off, second) == 0);
    assert(first[0].desc.vsel_reg == 11 && first[1].desc.vsel_reg == 21);
    assert(second[0].desc.vsel_reg == 10 && second[1].desc.vsel_reg == 20);
    assert(original[0].desc.vsel_reg == 10 && original[1].desc.vsel_reg == 20);
    assert(on.reads == 2 && off.reads == 2);
    puts("passed: fresh probe selects default and preserves the other instance");
    memcpy(second, original, sizeof(second));
    assert(new_select(&dev, &failed, second) == -5);
    assert(failed.reads == 2 && second[1].desc.vsel_reg == 20);
    puts("passed: read failure propagates before the failed rail is changed");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="mt6351-vsel-") as directory:
    path = Path(directory)
    source = path / "test.c"
    binary = path / "test"
    source.write_text(prefix + helper(old, "old_select") + helper(new, "new_select") + test)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-Wno-unused-parameter", str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
