#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the exact power-on function with simulated initialization failures."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile


SHIM = r"""
#include <assert.h>
#include <string.h>
typedef int INT32;
typedef unsigned long ULONG;
typedef struct { unsigned u4InfoBit; } WMT_OP, *P_WMT_OP;
#define WMT_PWRON_RTY_DFT 2
#define WMT_OP_HIF_BIT 1
#define WMTDRV_TYPE_WMT 0
#define DRV_STS_POWER_OFF 0
#define DRV_STS_POWER_ON 1
#define DRV_STS_FUNC_ON 2
#define WMT_CTRL_HW_PWR_ON 3
#define WMT_ERR_FUNC(...) ((void)0)
#define WMT_INFO_FUNC(...) ((void)0)
#define WMT_DBG_FUNC(...) ((void)0)
/* The pinned osal_assert logs and returns. */
#define osal_assert(condition) ((void)(condition))
static struct { int eDrvStatus[1]; } gMtkWmtCtx;
static int scenario, configured, events;
static char trace[32];
static void event(char value)
{
    assert(events < (int)sizeof(trace) - 1);
    trace[events++] = value;
}
static int opfunc_hif_conf(P_WMT_OP op)
{
    assert(op->u4InfoBit == WMT_OP_HIF_BIT);
    configured++;
    return 0;
}
static int wmt_core_ctrl(int command, ULONG *a, ULONG *b)
{
    assert(command == WMT_CTRL_HW_PWR_ON && !*a && !*b);
    event('P');
    return scenario == 1 ? -5 : 0;
}
static int wmt_core_stp_init(void)
{
    event('I');
    return scenario == 2 || scenario == 3 ? -8 : 0;
}
static int wmt_core_stp_deinit(void)
{
    event('D');
    return 0;
}
static int opfunc_pwr_off(P_WMT_OP op)
{
    assert(op->u4InfoBit == WMT_OP_HIF_BIT);
    event('O');
    if (scenario == 3) return -5;
    gMtkWmtCtx.eDrvStatus[0] = DRV_STS_POWER_OFF;
    return 0;
}
"""

TEST = r"""
int main(void)
{
    WMT_OP op = { WMT_OP_HIF_BIT };
    for (scenario = 0; scenario < 5; scenario++) {
        configured = events = 0;
        memset(trace, 0, sizeof(trace));
        gMtkWmtCtx.eDrvStatus[0] = scenario == 4 ? DRV_STS_POWER_ON : DRV_STS_POWER_OFF;
        int result = opfunc_pwr_on(&op);
        assert(configured == (scenario != 4));
        if (scenario == 0) {
            assert(!result && !strcmp(trace, "PI"));
            assert(gMtkWmtCtx.eDrvStatus[0] == DRV_STS_FUNC_ON);
        } else if (scenario == 1) {
            assert(result == -1 && !strcmp(trace, "P"));
        } else if (scenario == 4) {
            assert(result == -1 && !trace[0]);
        } else {
            assert(result == -2);
            assert(!strcmp(trace, FIXED ? "PIDO" : "PIDOPIDOPIDO"));
        }
    }
    return 0;
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="pinned public wmt_core.c")
    args = parser.parse_args()
    raw = args.source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "e9f438c5c6033f0bf831347c69d656ec917b3e705648d3d27fb1b27409334f1e")
    patch = Path(__file__).resolve().parent / "patches/0002-wmt-use-one-startup-attempt.patch"
    relative = "drivers/misc/mediatek/connectivity/common/common_main/core/wmt_core.c"
    with tempfile.TemporaryDirectory(prefix="wmt-startup-test-") as tmp:
        root = Path(tmp)
        source = root / relative
        source.parent.mkdir(parents=True)
        source.write_bytes(raw)
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=root, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=root, check=True)
        for fixed, text in enumerate((raw.decode(), source.read_text())):
            start = text.index("static INT32 opfunc_pwr_on(P_WMT_OP pWmtOp)\n{")
            end = text.index("\n}\n", start) + 3
            fixture = root / f"case-{fixed}.c"
            fixture.write_text(SHIM + text[start:end] + TEST)
            executable = root / f"case-{fixed}"
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            f"-DFIXED={fixed}", str(fixture), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True, timeout=3)
    print("PASS: original triple attempt reproduced; changed function makes one attempt")
    print("PASS: success, power failure, init failure, cleanup failure, already powered")


if __name__ == "__main__":
    main()
