#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the real MSDC voltage callback and MMC core caller with injected errors."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("driver", type=Path, help="prepared drivers/mmc/host/mtk-sd.c")
parser.add_argument("core", type=Path, help="prepared drivers/mmc/core/core.c")
args = parser.parse_args()


def function(path, signature):
    source = path.read_text()
    start = source.index(signature)
    return source[start:source.index("\n}\n", start) + 3]


prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#define MMC_SIGNAL_VOLTAGE_330 0
#define MMC_SIGNAL_VOLTAGE_180 1
#define MMC_SIGNAL_VOLTAGE_120 2
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define dev_err(...) ((void)0)
#define dev_dbg(...) ((void)0)
struct mmc_ios { int signal_voltage; };
struct mmc_host;
struct mmc_host_ops {
    int (*start_signal_voltage_switch)(struct mmc_host *, struct mmc_ios *);
};
struct mmc_host {
    struct { void *vqmmc; } supply;
    struct mmc_ios ios;
    const struct mmc_host_ops *ops;
    void *private;
};
struct msdc_host { void *dev, *pinctrl, *pins_uhs, *pins_default; };
static struct msdc_host msdc;
static int regulator_result, pinctrl_result, regulator_calls, pinctrl_calls;
static int applied_voltage;
static void *selected_state;
static void *mmc_priv(struct mmc_host *mmc) { return mmc->private; }
static int mmc_regulator_set_vqmmc(struct mmc_host *mmc, struct mmc_ios *ios)
{
    assert(mmc->private == &msdc && regulator_calls == 0 && pinctrl_calls == 0);
    regulator_calls++;
    if (regulator_result >= 0)
        applied_voltage = ios->signal_voltage;
    return regulator_result;
}
static int pinctrl_select_state(void *controller, void *state)
{
    assert(controller == msdc.pinctrl && regulator_calls == 1 && pinctrl_calls == 0);
    pinctrl_calls++;
    selected_state = state;
    return pinctrl_result;
}
'''

tests = r'''
int main(void)
{
    static const struct mmc_host_ops ops = {
        .start_signal_voltage_switch = msdc_ops_switch_volt,
    };
    int regulator, controller, uhs, normal;
    msdc.pinctrl = &controller;
    msdc.pins_uhs = &uhs;
    msdc.pins_default = &normal;
    const int regulator_results[] = { 0, 1, -EIO };
    const int pinctrl_results[] = { 0, -EINVAL, -EIO };
    unsigned int cases = 0;
    for (int supply = 0; supply < 2; supply++) {
        for (int voltage = 0; voltage < 3; voltage++) {
            for (unsigned int r = 0; r < 3; r++) {
                for (unsigned int p = 0; p < 3; p++) {
                    int old_voltage = voltage == MMC_SIGNAL_VOLTAGE_330 ? 1 : 0;
                    struct mmc_host mmc = {
                        .supply.vqmmc = supply ? &regulator : (void *)(intptr_t)-ENODEV,
                        .ios.signal_voltage = old_voltage,
                        .ops = &ops, .private = &msdc,
                    };
                    regulator_result = regulator_results[r];
                    pinctrl_result = pinctrl_results[p];
                    regulator_calls = pinctrl_calls = 0;
                    applied_voltage = old_voltage;
                    selected_state = NULL;
                    int valid = supply && voltage != MMC_SIGNAL_VOLTAGE_120;
                    int pins = valid && regulator_result >= 0;
                    int expected = !supply ? 0 : !valid ? -EINVAL :
                                   regulator_result < 0 ? regulator_result : pinctrl_result;
                    int ret = mmc_set_signal_voltage(&mmc, voltage);
                    if (ret != expected) {
                        fprintf(stderr, "FAIL: supply=%d voltage=%d regulator=%d pins=%d "
                                "got=%d expected=%d\n", supply, voltage, regulator_result,
                                pinctrl_result, ret, expected);
                        return 1;
                    }
                    assert(mmc.ios.signal_voltage == (ret ? old_voltage : voltage));
                    assert(regulator_calls == valid && pinctrl_calls == pins);
                    assert(selected_state == (!pins ? NULL : voltage == 1 ? &uhs : &normal));
                    /* Error reporting is not a claim of electrical rollback. */
                    assert(applied_voltage == (pins ? voltage : old_voltage));
                    cases++;
                }
            }
        }
    }
    printf("PASS: %u supply/voltage/regulator/pinctrl cases with MMC core propagation\n", cases);
    return 0;
}
'''

driver = function(args.driver, "static int msdc_ops_switch_volt(")
core = function(args.core, "int mmc_set_signal_voltage(")
with tempfile.TemporaryDirectory(prefix="mtk-sd-voltage-") as directory:
    path = Path(directory)
    (path / "test.c").write_text(prefix + driver + core + tests)
    subprocess.run([
        "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
        str(path / "test.c"), "-o", str(path / "test"),
    ], check=True)
    subprocess.run([str(path / "test")], check=True)
