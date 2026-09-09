#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the exact original and patched version-check function with fake reads."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile


SHIM = r"""
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
typedef int32_t INT32;
typedef uint32_t UINT32;
typedef struct { unsigned eWmtHwVer; } WMT_IC_INFO_S;
static const WMT_IC_INFO_S info = { 7 };
static const WMT_IC_INFO_S *gp_soc_info;
static struct { unsigned icId; } wmt_ic_ops_soc = { 0x0279 };
#define GEN_HVR 1
#define GEN_FVR 2
#define GEN_VER_MASK 0xffff
#define WMT_CTRL_HWIDVER_SET 3
#define WMT_LOUD_FUNC(...) ((void)0)
#define WMT_ERR_FUNC(...) ((void)0)
#define WMT_DBG_FUNC(...) ((void)0)
#define WMT_WARN_FUNC(...) ((void)0)
static int fail_read, missing_chip, reads, finds, publications;
static unsigned long published[2];
static int wmt_core_reg_rw_raw(int write, unsigned reg, UINT32 *value,
                               unsigned mask)
{
    assert(!write && mask == GEN_VER_MASK);
    assert(reg == (unsigned)++reads);
    /* Defined output even on failure exposes erroneous publication without UB. */
    *value = reg == GEN_HVR ? 0x1234 : 0x8a00;
    return reg == (unsigned)fail_read ? -5 : 0;
}
static const WMT_IC_INFO_S *mtk_wcn_soc_find_wmt_ic_info(UINT32 version)
{
    assert(version == 0x1234);
    finds++;
    return missing_chip ? NULL : &info;
}
static int wmt_core_ctrl(int command, unsigned long *a, unsigned long *b)
{
    assert(command == WMT_CTRL_HWIDVER_SET);
    publications++;
    published[0] = *a; published[1] = *b;
    return 0;
}
"""

TEST = r"""
int main(void)
{
    for (int scenario = 0; scenario < 4; scenario++) {
        reads = finds = publications = 0;
        gp_soc_info = NULL;
        fail_read = scenario < 3 ? scenario : 0;
        missing_chip = scenario == 3;
        int result = mtk_wcn_soc_ver_check();
        if (scenario == 1 || (scenario == 2 && FIXED)) {
            assert(result == -2 && reads == scenario);
            assert(!finds && !publications && !gp_soc_info);
        } else if (scenario == 3) {
            assert(result == -3 && reads == 2 && finds == 1);
            assert(!publications && !gp_soc_info);
        } else {
            assert(!result && reads == 2 && finds == 1);
            assert(publications == 1 && gp_soc_info == &info);
            assert(published[0] == 0x02791234);
            assert(published[1] == 0x00078a00);
        }
    }
    return 0;
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="pinned public wmt_ic_soc.c")
    args = parser.parse_args()
    raw = args.source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "22d98e9e5f0c9c3cae36a3099e57315ed7808524239a061bf9ab0cf97379e66f")
    patch = Path(__file__).resolve().parent / "patches/0001-wmt-check-firmware-version-read.patch"
    relative = "drivers/misc/mediatek/connectivity/common/common_main/core/wmt_ic_soc.c"
    with tempfile.TemporaryDirectory(prefix="wmt-version-test-") as tmp:
        root = Path(tmp)
        source = root / relative
        source.parent.mkdir(parents=True)
        source.write_bytes(raw)
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=root, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=root, check=True)
        for fixed, text in enumerate((raw.decode(), source.read_text())):
            start = text.index("static INT32 mtk_wcn_soc_ver_check(VOID)\n{")
            end = text.index("\n}\n", start) + 3
            fixture = root / f"case-{fixed}.c"
            fixture.write_text(SHIM + "\n#define VOID void\n" + text[start:end] + TEST)
            executable = root / f"case-{fixed}"
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            f"-DFIXED={fixed}", str(fixture), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True, timeout=3)
    print("PASS: original failed-read publication reproduced; patched read failures stop")
    print("PASS: hardware-read failure, firmware-read failure, chip mismatch, success")


if __name__ == "__main__":
    main()
