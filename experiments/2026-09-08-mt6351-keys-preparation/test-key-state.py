#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual PMIC key callbacks and MT6351 data without hardware."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path, help="prepared mtk-pmic-keys.c")
args = parser.parse_args()
source = args.source.read_text()
header = args.source.resolve().parents[3] / "include/linux/mfd/mt6351/registers.h"


def block(declaration):
    start = source.index(declaration)
    end = source.index("\n}", start) + 2
    if source[end:end + 1] == ";":
        end += 1
    return source[start:end] + "\n"


prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
typedef unsigned int u32;
typedef int irqreturn_t;
#define BIT(n) (1U << (n))
#define GENMASK(h, l) ((~0U << (l)) & (~0U >> (31 - (h))))
#define ffs(n) __builtin_ffs(n)
#define fallthrough __attribute__((__fallthrough__))
#define IRQ_HANDLED 1
#define dev_dbg(...) ((void)0)
#define dev_err_ratelimited(...) ((void)reports++)
struct device { void *of_node; };
struct input_dev { int unused; };
static unsigned int input_events, syncs, reports, reads, updates;
static unsigned int read_value, reset_value, last_reg, last_code, last_pressed;
static unsigned int mode, debounce;
static bool properties_present;
static int bus_error;
static int regmap_read(void *map, unsigned int reg, u32 *value)
{
    reads++;
    last_reg = reg;
    *value = read_value;
    return bus_error;
}
static int regmap_update_bits(void *map, unsigned int reg,
                              unsigned int mask, unsigned int value)
{
    updates++;
    last_reg = reg;
    if (bus_error) return bus_error;
    reset_value = (reset_value & ~mask) | (value & mask);
    return 0;
}
static void input_report_key(void *dev, unsigned int code, unsigned int pressed)
{
    input_events++;
    last_code = code;
    last_pressed = pressed;
}
static void input_sync(void *dev) { syncs++; }
static int of_property_read_u32(void *node, const char *name, u32 *value)
{
    if (!properties_present) return -22;
    if (!strcmp(name, "power-off-time-sec")) *value = debounce;
    else {
        assert(!strcmp(name, "mediatek,long-press-mode"));
        *value = mode;
    }
    return 0;
}
'''
tests = r'''
int main(void)
{
    struct device dev = { 0 };
    struct mtk_pmic_keys keys = { .dev = &dev };
    const int errors[] = { 0, -5, -110 };
    const unsigned int values[] = { 0, 2, 4, 0xffff };
    unsigned int cases = 0;
    assert(mt6351_regs.key_release_irq);
    assert(mt6351_regs.keys_regs[0].deb_reg == 0x220);
    assert(mt6351_regs.keys_regs[1].deb_reg == 0x220);
    assert(mt6351_regs.keys_regs[0].deb_mask == 2);
    assert(mt6351_regs.keys_regs[1].deb_mask == 4);
    assert(mt6351_regs.keys_regs[0].intsel_reg == 0x2da);
    assert(mt6351_regs.keys_regs[1].intsel_reg == 0x2da);
    assert(mt6351_regs.keys_regs[0].intsel_mask == 4);
    assert(mt6351_regs.keys_regs[1].intsel_mask == 2);
    for (unsigned int key = 0; key < 2; key++) {
        struct mtk_pmic_keys_info info = {
            .keys = &keys, .regs = &mt6351_regs.keys_regs[key],
            .keycode = 116 + key,
        };
        for (unsigned int i = 0; i < 4; i++) {
            for (unsigned int e = 0; e < 3; e++) {
                input_events = syncs = reports = reads = 0;
                read_value = values[i]; bus_error = errors[e];
                assert(mtk_pmic_keys_irq_handler_thread(7, &info) == IRQ_HANDLED);
                assert(reads == 1 && last_reg == 0x220);
                assert(input_events == !bus_error && syncs == !bus_error);
                assert(reports == (bus_error != 0));
                if (!bus_error) {
                    assert(last_code == 116 + key);
                    assert(last_pressed == !(read_value & (2U << key)));
                }
                cases++;
            }
        }
    }
    for (unsigned int policy = 0; policy < 6; policy++) {
        properties_present = policy != 0;
        mode = policy / 2;
        debounce = policy & 1 ? 3 : 0;
        for (unsigned int e = 0; e < 3; e++) {
            updates = 0; reset_value = 0xffff; bus_error = errors[e];
            int ret = mtk_pmic_keys_lp_reset_setup(&keys, &mt6351_regs);
            unsigned int bits = debounce << 12;
            if (mode) bits |= 0x200;
            if (mode == 2) bits |= 0x100;
            assert(ret == bus_error && updates == 1 && last_reg == 0x2b6);
            assert(reset_value == (bus_error ? 0xffff : ((0xffff & ~0x3300) | bits)));
            cases++;
        }
    }
    printf("PASS: %u key-state/reset-policy/transport cases\n", cases);
    return 0;
}
'''
definitions = source[source.index("#define MTK_PMIC_RST_DU_MASK"):
                     source.index("static const struct mtk_pmic_regs mt6397_regs")]
structs = source[source.index("struct mtk_pmic_keys_info {"):
                 source.index("static int mtk_pmic_keys_lp_reset_setup")]
with tempfile.TemporaryDirectory(prefix="mt6351-keys-") as directory:
    path = Path(directory)
    text = prefix + "\n#include " + json.dumps(str(header)) + "\n" + definitions
    text += block("static const struct mtk_pmic_regs mt6351_regs") + structs
    text += block("static int mtk_pmic_keys_lp_reset_setup")
    text += block("static irqreturn_t mtk_pmic_keys_irq_handler_thread") + tests
    (path / "test.c").write_text(text)
    subprocess.run([
        "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
        "-Wno-unused-parameter", str(path / "test.c"), "-o", str(path / "test"),
    ], check=True)
    subprocess.run([str(path / "test")], check=True)
