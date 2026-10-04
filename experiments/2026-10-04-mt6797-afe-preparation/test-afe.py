#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exercise the actual AFE helper; no device access or kernel build."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    source = Path(sys.argv[1]).read_text()
    start = source.index("static void mt6797_consys_init_afe(")
    end = source.index("\n}\n", start) + 3
    helper = source[start:end]
    reset = source[source.index("static bool mt6797_consys_probe_reset_release("):]
    reset = reset[:reset.index("\n}\n")]
    assert reset.index("mt6797_consys_init_afe(owner)") > reset.index(
        "if (after != (before | MT6797_CONSYS_MCU_ACR_MBIST))")
    assert reset.index("mt6797_consys_init_afe(owner)") < reset.index(
        "reset_control_deassert(owner->conmcu_reset)")
    probe = source[source.index("static int mt6797_consys_probe("):]
    assert probe.index("afe = devm_platform_ioremap_resource") < probe.index(
        "mt6797_consys_attach_off_domain")
    assert probe.index("mt6797_consys.afe = afe") > probe.index(
        'devm_clk_get(&pdev->dev, "ap-dma")')
    receipt = Path(__file__).resolve().parent.parent / (
        "2026-10-03-mt6797-wifi-audit/results/afe-source-join.json")
    writes = json.loads(receipt.read_text())["writes"]
    checks = "\n".join(
        f"assert(addresses[{i}] == {w['offset']}); "
        f"assert(values[{i}] == {w['value']});"
        for i, w in enumerate(writes))
    harness = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
typedef uint32_t u32;
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
struct mt6797_consys { void *afe; };
static unsigned char window[0x100];
static uintptr_t addresses[11];
static u32 values[11];
static unsigned int count;
static void writel(u32 value, void *address)
{
    assert(count < 11);
    addresses[count] = (unsigned char *)address - window;
    assert(addresses[count] < sizeof(window));
    assert(!(addresses[count] & 3));
    values[count++] = value;
}
''' + helper + r'''
int main(void)
{
    struct mt6797_consys owner = {0};
    mt6797_consys_init_afe(&owner);
    assert(count == 0);
    owner.afe = window;
    mt6797_consys_init_afe(&owner);
    assert(count == 11);
''' + checks + "\nreturn 0;\n}\n"
    with tempfile.TemporaryDirectory(prefix="gemini-afe-test-") as directory:
        path = Path(directory)
        (path / "test.c").write_text(harness)
        subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=address,undefined", str(path / "test.c"),
                        "-o", str(path / "test")], check=True)
        subprocess.run([str(path / "test")], check=True)
    print("afe_helper=pass absent_resource_writes=0 selected_writes=11")
    print("source_order=pass; not proof of kernel or MMIO behavior")


if __name__ == "__main__":
    main()
