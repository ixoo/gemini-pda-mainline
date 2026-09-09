#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual advanced-pull setter with injected field errors."""
import pathlib
import subprocess
import sys
import tempfile

source = pathlib.Path(sys.argv[1]).read_text()
start = source.index("int mtk_pinconf_adv_pull_set(")
function = source[start:source.index("EXPORT_SYMBOL", start)]
program = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdint.h>
typedef uint32_t u32;
#define ENOTSUPP 524
#define PINCTRL_PIN_REG_R0 0
#define PINCTRL_PIN_REG_R1 1
#define PINCTRL_PIN_REG_PUPD 2
struct mtk_pin_desc { int unused; };
struct mtk_pinctrl;
struct soc {
    int (*bias_set)(struct mtk_pinctrl *, const struct mtk_pin_desc *, bool);
};
struct mtk_pinctrl { struct soc *soc; };
static int failed_call, injected_error, calls, writes, fallback_calls;
static int values[3];
static int mtk_hw_set_value(struct mtk_pinctrl *hw,
                           const struct mtk_pin_desc *desc, int field, int value)
{
    (void)hw; (void)desc;
    assert(field == calls++);
    if (calls == failed_call) return injected_error;
    values[field] = value; writes++;
    return 0;
}
static int mtk_pinconf_bias_set_rev1(struct mtk_pinctrl *hw,
                                   const struct mtk_pin_desc *desc, bool pullup)
{
    (void)hw; (void)desc; (void)pullup;
    fallback_calls++;
    return 0;
}
static int mtk_pinconf_bias_set(struct mtk_pinctrl *hw,
                               const struct mtk_pin_desc *desc, bool pullup)
{
    (void)hw; (void)desc; (void)pullup;
    assert(!"unexpected second fallback");
    return -ENOTSUPP;
}
""" + function + r"""
int main(void)
{
    struct soc soc = {0};
    struct mtk_pinctrl hw = {&soc};
    struct mtk_pin_desc desc = {0};
    int n = 0;
    const int errors[] = {-22, -ENOTSUPP};
    for (int pullup = 0; pullup <= 1; pullup++)
    for (u32 arg = 0; arg < 4; arg++)
    for (failed_call = 0; failed_call <= 3; failed_call++)
    for (int e = 0; e < 2; e++) {
        injected_error = errors[e]; calls = writes = fallback_calls = 0;
        values[0] = values[1] = values[2] = -1;
        int result = mtk_pinconf_adv_pull_set(&hw, &desc, pullup, arg);
        int fallback = failed_call == 3 && injected_error == -ENOTSUPP;
        assert(result == ((!failed_call || fallback) ? 0 : injected_error));
        assert(calls == (failed_call ? failed_call : 3));
        assert(writes == (failed_call ? failed_call - 1 : 3));
        assert(fallback_calls == fallback);
        if (writes > 0) assert(values[0] == (int)(arg & 1));
        if (writes > 1) assert(values[1] == !!(arg & 2));
        if (writes > 2) assert(values[2] == !pullup);
        n++;
    }
    printf("advanced_pull_cases=%d result=pass\n", n);
}
"""
with tempfile.TemporaryDirectory(prefix="advanced-pull-") as scratch:
    src = pathlib.Path(scratch) / "test.c"
    exe = pathlib.Path(scratch) / "test"
    src.write_text(program)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    str(src), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
