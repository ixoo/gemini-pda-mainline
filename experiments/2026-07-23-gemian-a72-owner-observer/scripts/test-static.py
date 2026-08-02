#!/usr/bin/env python3
"""Exercise positive validation and selected safety tripwires."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
VALIDATOR = EXPERIMENT / "scripts" / "validate.py"


def run_validator(root):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--experiment-root", str(root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def mutate(root, relative_path, old, new):
    path = root / relative_path
    text = path.read_text()
    if text.count(old) != 1:
        raise AssertionError(
            "{}: expected one mutation target {!r}, found {}".format(
                relative_path, old, text.count(old)
            )
        )
    path.write_text(text.replace(old, new, 1))


def expect_rejected(label, relative_path, old, new, expected_error):
    with tempfile.TemporaryDirectory(prefix="mt6797-a72-observer-test-") as tmp:
        copied = Path(tmp) / "experiment"
        shutil.copytree(EXPERIMENT, copied)
        mutate(copied, relative_path, old, new)
        result = run_validator(copied)
        if result.returncode == 0:
            raise AssertionError("{} mutation was accepted".format(label))
        output = result.stdout + result.stderr
        if expected_error not in output:
            raise AssertionError(
                "{} rejected for an unexpected reason:\n{}".format(label, output)
            )


def main():
    result = run_validator(EXPERIMENT)
    if result.returncode != 0:
        raise AssertionError("unmodified series failed:\n{}".format(result.stderr))

    patch1 = (
        "patches/0001-diagnostic-add-fixed-MT6797-A72-transition-ring.patch"
    )
    patch2 = (
        "patches/0002-diagnostic-add-owner-local-fixed-A72-snapshots.patch"
    )
    patch5 = (
        "patches/0005-diagnostic-bound-observer-timing-perturbation.patch"
    )
    patch6 = (
        "patches/0006-diagnostic-latch-first-complete-CPU8-cycle.patch"
    )
    patch7 = (
        "patches/0007-diagnostic-gate-observer-effects-to-first-CPU8-cycle.patch"
    )
    expect_rejected(
        "writable proc mode",
        patch1,
        "proc_create(MT6797_A72_OBS_PROC_NAME, 0400, NULL,",
        "proc_create(MT6797_A72_OBS_PROC_NAME, 0600, NULL,",
        "missing 'proc_create(MT6797_A72_OBS_PROC_NAME, 0400, NULL,'",
    )
    expect_rejected(
        "secure address drift",
        patch2,
        "0x10222470",
        "0x10222474",
        "secure address 0x10222470 count changed",
    )
    expect_rejected(
        "proc write callback",
        patch1,
        "\t.read = seq_read,\n",
        "\t.read = seq_read,\n+\t.write = seq_write,\n",
        "writable file operation",
    )
    expect_rejected(
        "toolchain package checksum drift",
        "inputs/stretch-cross-toolchain.tsv",
        "b7b3b0605b86f795f0a10d197fbfe161a281d1b081eb73c38d331c7db6b5f9dc",
        "a7b3b0605b86f795f0a10d197fbfe161a281d1b081eb73c38d331c7db6b5f9dc",
        "pinned toolchain manifest hash changed",
    )
    expect_rejected(
        "boot-candidate promotion",
        "scripts/build-on-buildbox",
        "boot_candidate: false",
        "boot_candidate: true",
        "missing 'boot_candidate: false'",
    )
    expect_rejected(
        "ring-size regression",
        patch5,
        "+#define MT6797_A72_OBS_RING_SIZE\t256",
        "+#define MT6797_A72_OBS_RING_SIZE\t512",
        "recorder: missing '#define MT6797_A72_OBS_RING_SIZE\\t256'",
    )
    expect_rejected(
        "semaphore-wait regression",
        patch5,
        "+\tif (!(hs_read32(g_reg_sema3_m0) & 0x1)) {",
        "+\tudelay(10);\n+\tif (!(hs_read32(g_reg_sema3_m0) & 0x1)) {",
        "timing-bound patch adds a semaphore wait",
    )
    expect_rejected(
        "extra-boundary-snapshot regression",
        patch5,
        "-\tmt6797_a72_obs_fixed_snapshot(cpu, MT6797_A72_PHASE_SRAM_PRE);",
        "+\tmt6797_a72_obs_fixed_snapshot(cpu, MT6797_A72_PHASE_SRAM_PRE);",
        "timing-bound fixed snapshot removal count changed",
    )
    expect_rejected(
        "CPU9 sampling gate regression",
        patch6,
        "+\taccepts = cpu == 8 &&",
        "+\taccepts = mt6797_a72_obs_is_cpu(cpu) &&",
        "first-cycle latch patch: missing 'accepts = cpu == 8 &&'",
    )
    expect_rejected(
        "overflow-before-write regression",
        patch6,
        "+\tif (mt6797_a72_obs_count == MT6797_A72_OBS_RING_SIZE) {",
        "+\tif (mt6797_a72_obs_count > MT6797_A72_OBS_RING_SIZE) {",
        "first-cycle latch patch: missing 'mt6797_a72_obs_count == MT6797_A72_OBS_RING_SIZE'",
    )
    expect_rejected(
        "wraparound-ring regression",
        patch6,
        "+\tmt6797_a72_obs_ring[mt6797_a72_obs_count++] = *record;",
        "+\tmt6797_a72_obs_ring[mt6797_a72_obs_head++] = *record;",
        "first-cycle latch patch: missing 'mt6797_a72_obs_ring[mt6797_a72_obs_count++] = *record'",
    )
    expect_rejected(
        "ABI-v1 regression",
        patch6,
        "+\tseq_printf(m, \"abi=mt6797-a72-transition-observer-v2 state=%s\",",
        "+\tseq_printf(m, \"abi=mt6797-a72-transition-observer-v1 state=%s\",",
        "recorder: missing 'abi=mt6797-a72-transition-observer-v2'",
    )
    expect_rejected(
        "terminal-state ordering regression",
        patch6,
        "+\tMT6797_A72_OBS_FROZEN_COMPLETE,\n+\tMT6797_A72_OBS_FROZEN_UP_FAILED,",
        "+\tMT6797_A72_OBS_FROZEN_UP_FAILED,\n+\tMT6797_A72_OBS_FROZEN_COMPLETE,",
        "first-cycle terminal-state ordering: missing ordered token",
    )
    expect_rejected(
        "DA9214 pure-snapshot gate regression",
        patch7,
        "+\tif (!mt6797_a72_obs_accepts_sampling(cpu))\n+\t\treturn 0;",
        "+\tif (mt6797_a72_obs_accepts_sampling(cpu))\n+\t\treturn 0;",
        "drivers/misc/mediatek/power/mt6797/da9214.c pure-snapshot early gate",
    )
    expect_rejected(
        "SPM fallback suppression regression",
        patch7,
        "+\t\treturn false;",
        "+\t\treturn true;",
        "owner-effect gate patch: missing 'return false;'",
    )
    expect_rejected(
        "BUCKB vendor-fallback regression",
        patch7,
        "+\t\t\tda9214_config_interface(0x5E, 0x1, 0x1, 0);",
        "+\t\t\tda9214_a72_obs_buckb_config(cpu, true, 0);",
        "owner-effect gate patch: missing 'da9214_config_interface(0x5E, 0x1, 0x1, 0);'",
    )
    expect_rejected(
        "DCM original-path regression",
        patch7,
        "+\t\treturn 0;\n+\t}\n+#endif",
        "+\t}\n+#endif",
        "DCM observed/original branch ordering: missing ordered token",
    )
    print("PASS: positive validation and 17 mutation tripwires")
    return 0


if __name__ == "__main__":
    sys.exit(main())
