#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the source Schmitt switch cases with injected lookup/write results."""
import pathlib
import subprocess
import sys
import tempfile

source = pathlib.Path(sys.argv[1]).read_text()
setter = source[source.index("static int mtk_pinconf_set"):]
cases = setter[setter.index("\tcase PIN_CONFIG_INPUT_SCHMITT:"):]
cases = cases[:cases.index("\tcase PIN_CONFIG_DRIVE_STRENGTH:")]
program = r"""
#include <assert.h>
#include <stdio.h>
#define PIN_CONFIG_INPUT_SCHMITT 1
#define PIN_CONFIG_INPUT_SCHMITT_ENABLE 2
#define PINCTRL_PIN_REG_DIR 0
#define PINCTRL_PIN_REG_SMT 1
struct mtk_pin_field { int unused; };
static int lookup_error, dir_error, direction, smt, writes, fields[2];
static int mtk_hw_pin_field_get(void *hw, void *desc, int field,
                               struct mtk_pin_field *pf)
{
    (void)hw; (void)desc; (void)pf;
    assert(field == PINCTRL_PIN_REG_SMT);
    return lookup_error;
}
static int mtk_hw_set_value(void *hw, void *desc, int field, int value)
{
    (void)hw; (void)desc;
    if (field == PINCTRL_PIN_REG_DIR && dir_error) return dir_error;
    if (field == PINCTRL_PIN_REG_SMT && lookup_error) return lookup_error;
    assert(writes < 2);
    fields[writes++] = field;
    if (field == PINCTRL_PIN_REG_DIR) direction = value;
    else smt = value;
    return 0;
}
static int run(int param, unsigned int arg)
{
    void *hw = 0, *desc = 0;
    struct mtk_pin_field pf;
    int err = -524;
    (void)pf;
    (void)mtk_hw_pin_field_get;
    switch (param) {
""" + cases + r"""
    }
    return err;
}
int main(void)
{
    int n = 0;
    const int errors[] = {0, -524, -22};
    for (int param = 1; param <= 2; param++)
    for (int initial = 0; initial <= 1; initial++)
    for (unsigned int arg = 0; arg <= 2; arg++)
    for (int e = 0; e < 3; e++)
    for (int d = 0; d <= 1; d++) {
        lookup_error = errors[e]; dir_error = d ? -22 : 0;
        direction = initial; smt = 1; writes = 0;
        int result = run(param, arg);
        assert(result == (lookup_error ? lookup_error : dir_error));
        if (lookup_error || dir_error) {
            assert(writes == 0 && direction == initial && smt == 1);
        } else {
            assert(writes == 2 && fields[0] == 0 && fields[1] == 1);
            assert(direction == !arg && smt == !!arg);
        }
        n++;
    }
    printf("schmitt_refusal_cases=%d result=pass\n", n);
}
"""
with tempfile.TemporaryDirectory(prefix="schmitt-refusal-") as scratch:
    src = pathlib.Path(scratch) / "test.c"
    exe = pathlib.Path(scratch) / "test"
    src.write_text(program)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    str(src), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
