#!/usr/bin/env python3
"""Validate fixed safety and provenance invariants of the observer patchset."""

import argparse
import hashlib
import re
import sys
from pathlib import Path


EXPECTED_SERIES = [
    "0001-diagnostic-add-fixed-MT6797-A72-transition-ring.patch",
    "0002-diagnostic-add-owner-local-fixed-A72-snapshots.patch",
    "0003-diagnostic-record-A72-power-mutations-under-owners.patch",
    "0004-diagnostic-correlate-A72-hotplug-lifecycle.patch",
    "0005-diagnostic-bound-observer-timing-perturbation.patch",
    "0006-diagnostic-latch-first-complete-CPU8-cycle.patch",
    "0007-diagnostic-gate-observer-effects-to-first-CPU8-cycle.patch",
]

EXPECTED_COMMITS = [
    "7bddafa6756e415a371e5cf14383c96b8469ded0",
    "c8475b569567bf71f3ffcca09d27f0c025d6d208",
    "429afb35a3b5ccaec976d31288dd52148855ef79",
    "349f24b6e10df6e1d24c79a23d75c8361ac68b28",
    "718f297ae97ab3738d624129b814e921a8371227",
    "e6ccc7d8bbe968d1da1a99cd9f3e96be4e8a0136",
    "65e3b72839c5ce6b8c5d68667062c1fb1561e216",
]

EXPECTED_DIFF_PATHS = {
    "arch/arm64/kernel/psci.c",
    "arch/arm64/kernel/smp.c",
    "drivers/misc/mediatek/base/power/Kconfig",
    "drivers/misc/mediatek/base/power/mt6797/Makefile",
    "drivers/misc/mediatek/base/power/mt6797/mt_a72_transition_observer.c",
    "drivers/misc/mediatek/base/power/mt6797/mt_dcm.c",
    "drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c",
    "drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c",
    "drivers/misc/mediatek/base/power/spm_v2/mt_spm.c",
    "drivers/misc/mediatek/freqhopping/mt6797/mt_freqhopping.c",
    "drivers/misc/mediatek/power/mt6797/da9214.c",
    "drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c",
    "include/linux/mt6797_a72_transition_observer.h",
}

ACTIVE_HASHES = {
    "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d",
    "14b4e079bf87b10b14df09a83673f065a342566daed509767bba08420f6c5257",
    "9e26929563f7682d1f7545d6007f0092c7e085a4edbd6e7be0ac8eaa5159b2f9",
    "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4",
    "53b53b62fa5a111cb7d6ea4f513aec1e8a6b436c8c17bfd86cb00a9bc4bf6ae1",
    "231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4",
}

ACTIVE_CONFIG_SHA256 = (
    "231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4"
)
TOOLCHAIN_MANIFEST_SHA256 = (
    "a45d945f092461a611d276ad7d0a0fea1ea8a7f93db413908bcb892c12817d14"
)

SECURE_ADDRESSES = [
    "0x10222470",
    "0x10222498",
    "0x1022249c",
    "0x102224a0",
    "0x102224a4",
    "0x102224ac",
    "0x102224b0",
    "0x102224b4",
    "0x102224cc",
    "0x102222b0",
    "0x102222b4",
    "0x10222274",
]


class ValidationError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def require_tokens(text, tokens, scope):
    for token in tokens:
        require(token in text, "{}: missing {!r}".format(scope, token))


def ordered(text, tokens, scope):
    cursor = -1
    for token in tokens:
        position = text.find(token, cursor + 1)
        require(position >= 0, "{}: missing ordered token {!r}".format(scope, token))
        require(
            position > cursor,
            "{}: token is out of order {!r}".format(scope, token),
        )
        cursor = position


def added_lines(path):
    additions = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if line.startswith("+") and not line.startswith("+++"):
            additions.append((line_number, line[1:]))
    return additions


def patch_for_path(patches, source_path):
    marker = "diff --git a/{0} b/{0}".format(source_path)
    matches = [text for text in patches if marker in text]
    require(matches, "{}: missing from patch series".format(source_path))
    return "\n".join(matches)


def patch_section_for_path(patch, source_path):
    marker = "diff --git a/{0} b/{0}".format(source_path)
    start = patch.find(marker)
    require(start >= 0, "{}: missing patch section".format(source_path))
    end = patch.find("\ndiff --git ", start + len(marker))
    return patch[start:] if end < 0 else patch[start:end]


def validate(root):
    config_path = root / "inputs" / "active-gemian.config"
    require(config_path.is_file(), "missing exact active Gemian configuration")
    config_bytes = config_path.read_bytes()
    require(
        hashlib.sha256(config_bytes).hexdigest() == ACTIVE_CONFIG_SHA256,
        "active Gemian configuration hash changed",
    )
    require(
        b"CONFIG_MTK_A72_TRANSITION_OBSERVER" not in config_bytes,
        "baseline configuration already contains observer option",
    )

    toolchain_manifest = root / "inputs" / "stretch-cross-toolchain.tsv"
    require(toolchain_manifest.is_file(), "missing pinned toolchain manifest")
    manifest_bytes = toolchain_manifest.read_bytes()
    require(
        hashlib.sha256(manifest_bytes).hexdigest() == TOOLCHAIN_MANIFEST_SHA256,
        "pinned toolchain manifest hash changed",
    )
    manifest_rows = toolchain_manifest.read_text().splitlines()
    require(
        manifest_rows[0] == "package\tversion\tarchitecture\tfilename\tsha256",
        "pinned toolchain manifest header changed",
    )
    require(len(manifest_rows) == 40, "pinned toolchain package count changed")
    packages = [row.split("\t") for row in manifest_rows[1:]]
    require(
        all(len(fields) == 5 for fields in packages),
        "malformed pinned toolchain row",
    )
    require(
        len({fields[0] for fields in packages}) == 39,
        "duplicate pinned toolchain package",
    )
    require(
        len({fields[3] for fields in packages}) == 39,
        "duplicate pinned toolchain filename",
    )
    require(
        all(re.fullmatch(r"[0-9a-f]{64}", fields[4]) for fields in packages),
        "malformed pinned toolchain package checksum",
    )
    versions = {fields[0]: fields[1] for fields in packages}
    require(
        versions.get("gcc-6-aarch64-linux-gnu") == "6.3.0-18cross1",
        "pinned cross-GCC package version changed",
    )
    require(
        versions.get("binutils-aarch64-linux-gnu") == "2.28-5",
        "pinned cross-binutils package version changed",
    )
    require(
        versions.get("python2.7") == "2.7.13-2",
        "pinned Python package version changed",
    )

    build_script = root / "scripts" / "build-on-buildbox"
    require(build_script.is_file(), "missing Buildbox observer build driver")
    require(
        build_script.stat().st_mode & 0o111,
        "Buildbox observer build driver is not executable",
    )
    build_text = build_script.read_text()
    require_tokens(
        build_text,
        [
            "https://snapshot.debian.org/archive/debian/20170618T000000Z",
            "6.3.0 20170516",
            "GNU ld (GNU Binutils for Debian) 2.28",
            "Python 2.7.13",
            "7a7eb416499346afff30c15f967ccb9cf79323c076204b6a953515db74811632",
            "1970-01-01 00:00:00",
            "HOST_EXTRACFLAGS=-fcommon",
            'host_extra_cflags: "-fcommon"',
            'TARGET_EXTRA_CFLAGS=-fstack-usage',
            'target_extra_cflags: "-fstack-usage"',
            "baseline configuration delta is not exact ANBOX normalization",
            "observer and baseline compiler diagnostics differ",
            "unpatched baseline unexpectedly contains observer symbols",
            "outputs/stack-usage.tar",
            "outputs/stack-usage-files.nul",
            "baseline_comparison: true",
            "diagnostics_identical: true",
            "baseline_source_unpatched: true",
            "stack_usage_captured: true",
            "stack_usage_file_count: $stack_usage_file_count",
            "sha256sum --check --strict SHA256SUMS",
            "configuration delta is not exact observer-plus-ANBOX-normalization",
            'purpose: "compile-review-only"',
            "boot_candidate: false",
            "Image.gz-dtb",
        ],
        "Buildbox observer build driver",
    )
    for forbidden in ["scripts/dev-vm", "--backend vm", "scp ", "rsync "]:
        require(
            forbidden not in build_text,
            "Buildbox observer build driver contains forbidden path {!r}".format(
                forbidden
            ),
        )

    patch_dir = root / "patches"
    series_path = patch_dir / "series"
    require(series_path.is_file(), "missing patches/series")
    series = [
        line.strip()
        for line in series_path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(series == EXPECTED_SERIES, "patch series names/order changed")

    patch_paths = [patch_dir / name for name in series]
    require(all(path.is_file() for path in patch_paths), "series names a missing patch")
    patch_texts = [path.read_text() for path in patch_paths]
    combined = "\n".join(patch_texts)

    for path, text, commit in zip(patch_paths, patch_texts, EXPECTED_COMMITS):
        match = re.search(r"\AFrom ([0-9a-f]{40}) ", text)
        require(match is not None, "{}: missing format-patch From line".format(path.name))
        require(match.group(1) == commit, "{}: source commit changed".format(path.name))

    changed_paths = set(
        re.findall(r"^diff --git a/(\S+) b/\1$", combined, flags=re.MULTILINE)
    )
    require(changed_paths == EXPECTED_DIFF_PATHS, "unexpected or missing source path")

    additions = []
    for path in patch_paths:
        additions.extend(
            (path.name, line_number, line)
            for line_number, line in added_lines(path)
        )
    additions_text = "\n".join(line for _, _, line in additions)

    forbidden_patterns = {
        r"\bBUG(?:_ON)?\s*\(": "new BUG path",
        r"\bWARN(?:_ON(?:_ONCE)?)?\s*\(": "new WARN path",
        r"\bpanic\s*\(": "new panic path",
        r"\bpr_warn\s*\(": "new warning print",
        r"\bmodule_param": "module control",
        r"\bdebugfs_create": "debugfs control/surface",
        r"\bcopy_from_user\b": "userspace write input",
        r"\bkstrto(?:u|s)": "parsed userspace control",
        r"\.(?:write|unlocked_ioctl|compat_ioctl)\s*=": "writable file operation",
        r"\bSEC_BIGIDVFS_WRITE\b": "secure write",
        r"\bDEVICE_ATTR.*(?:S_IW|0200|0220|0600|0640|0660)": "writable sysfs ABI",
        r"\bmsleep\s*\(": "new sleeping delay",
        r"\bmdelay\s*\(": "new millisecond busy delay",
    }
    for pattern, reason in forbidden_patterns.items():
        match = re.search(pattern, additions_text)
        require(match is None, "{}: {!r}".format(reason, match.group(0) if match else ""))

    core = patch_for_path(patch_texts, "drivers/misc/mediatek/base/power/mt6797/mt_a72_transition_observer.c")
    kconfig = patch_for_path(patch_texts, "drivers/misc/mediatek/base/power/Kconfig")
    require_tokens(
        kconfig,
        [
            "config MTK_A72_TRANSITION_OBSERVER",
            "depends on ARCH_MT6797 && ARM64 && SMP && HOTPLUG_CPU && PROC_FS",
            "default n",
        ],
        "Kconfig",
    )
    require_tokens(
        core,
        [
            "#define MT6797_A72_OBS_RING_SIZE\t256",
            "static struct mt6797_a72_obs_record",
            "static DEFINE_SPINLOCK(mt6797_a72_obs_lock)",
            "static u64 mt6797_a72_obs_transactions[2]",
            "snapshot = vzalloc(sizeof(*snapshot));",
            "single_open(file, mt6797_a72_obs_proc_show, snapshot)",
            "proc_create(MT6797_A72_OBS_PROC_NAME, 0400, NULL,",
            ".open = mt6797_a72_obs_proc_open",
            ".read = seq_read",
            ".llseek = seq_lseek",
            ".release = mt6797_a72_obs_proc_release",
            "abi=mt6797-a72-transition-observer-v2",
        ],
        "recorder",
    )
    require("EXPORT_SYMBOL" not in additions_text, "observer unexpectedly exported")
    require(
        re.search(r"\.(?:write|unlocked_ioctl|compat_ioctl)\s*=", core) is None,
        "proc ABI gained a control operation",
    )
    require(
        combined.count("proc_create(MT6797_A72_OBS_PROC_NAME, 0400, NULL,") == 1,
        "proc mode or creation count changed",
    )

    latch = patch_texts[5]
    require_tokens(
        latch,
        [
            "MT6797_A72_OBS_WAIT_UP",
            "MT6797_A72_OBS_CAPTURE_UP",
            "MT6797_A72_OBS_WAIT_DOWN",
            "MT6797_A72_OBS_CAPTURE_DOWN",
            "MT6797_A72_OBS_FROZEN_COMPLETE",
            "MT6797_A72_OBS_FROZEN_UP_FAILED",
            "MT6797_A72_OBS_FROZEN_DOWN_FAILED",
            "MT6797_A72_OBS_FROZEN_CPU9",
            "MT6797_A72_OBS_FROZEN_PROTOCOL",
            "MT6797_A72_OBS_FROZEN_OVERFLOW",
            "mt6797_a72_obs_up_transaction",
            "mt6797_a72_obs_down_transaction",
            "mt6797_a72_obs_is_terminal(mt6797_a72_obs_state)",
            "record->header.target_cpu == 9",
            "mt6797_a72_obs_count == MT6797_A72_OBS_RING_SIZE",
            "mt6797_a72_obs_ring[mt6797_a72_obs_count++] = *record",
            "bool mt6797_a72_obs_accepts_sampling(unsigned int cpu)",
            "accepts = cpu == 8 &&",
            "abi=mt6797-a72-transition-observer-v2",
            'return "frozen-complete"',
            "state=%s count=%u overflow=%u up_tx=%llu",
            "snapshot->down_transaction = mt6797_a72_obs_down_transaction",
        ],
        "first-cycle latch patch",
    )
    ordered(
        latch,
        [
            "+\tMT6797_A72_OBS_WAIT_UP,",
            "+\tMT6797_A72_OBS_CAPTURE_UP,",
            "+\tMT6797_A72_OBS_WAIT_DOWN,",
            "+\tMT6797_A72_OBS_CAPTURE_DOWN,",
            "+\tMT6797_A72_OBS_FROZEN_COMPLETE,",
            "+\tMT6797_A72_OBS_FROZEN_UP_FAILED,",
            "+\tMT6797_A72_OBS_FROZEN_DOWN_FAILED,",
            "+\tMT6797_A72_OBS_FROZEN_CPU9,",
            "+\tMT6797_A72_OBS_FROZEN_PROTOCOL,",
            "+\tMT6797_A72_OBS_FROZEN_OVERFLOW,",
        ],
        "first-cycle terminal-state ordering",
    )
    latch_additions = "\n".join(line for _, line in added_lines(patch_paths[5]))
    for obsolete in [
        "mt6797_a72_obs_overwritten",
        "mt6797_a72_obs_head",
        "observer-v1",
        "snapshot->overwritten",
    ]:
        require(
            re.search(
                r"(?<![A-Za-z0-9_]){}(?![A-Za-z0-9_])".format(
                    re.escape(obsolete)
                ),
                latch_additions,
            )
            is None,
            "first-cycle latch retains obsolete token {!r}".format(obsolete),
        )
    require(
        "mt6797_a72_obs_ring[mt6797_a72_obs_head]" not in latch_additions,
        "first-cycle latch reintroduces wraparound storage",
    )
    require(
        latch.count("+\tmt6797_a72_obs_state = next_state;") == 1,
        "first-cycle latch terminal transition is not singular",
    )

    owner_gate = patch_texts[6]
    require_tokens(
        owner_gate,
        [
            "if (!mt6797_a72_obs_accepts_sampling(cpu))",
            "if (mt6797_a72_obs_accepts_sampling(cpu)) {",
            "da9214_config_interface(0x0, 0x0, 0xF, 0);",
            "da9214_config_interface(0x5E, 0x1, 0x1, 0);",
            "ret = da9214_config_interface(0x5E, 0x0, 0x1, 0);",
            "return false;",
            "cpu = mt6797_a72_obs_active_cpu();",
            "if (mt6797_a72_obs_is_cpu(cpu)) {",
            "return 0;",
        ],
        "owner-effect gate patch",
    )
    owner_gate_additions = "\n".join(
        line for _, line in added_lines(patch_paths[6])
    )
    require(
        owner_gate_additions.count("mt6797_a72_obs_accepts_sampling(cpu)") == 10,
        "owner-effect sampling-gate call count changed",
    )
    require(
        re.search(r"\bBUG(?:_ON)?\s*\(", owner_gate_additions) is None,
        "owner-effect gate adds an assertion path",
    )
    ordered(
        owner_gate,
        [
            "+\tif (!mt6797_a72_obs_accepts_sampling(cpu))",
            "+\t\treturn;",
            " \tda9214_a72_obs_snapshot(cpu, phase);",
        ],
        "composite snapshot early gate",
    )
    for source_path, first_hardware_token in [
        ("drivers/misc/mediatek/power/mt6797/da9214.c", " \tif (!new_client)"),
        ("drivers/misc/mediatek/base/power/spm_v2/mt_spm.c", " \tbase = mt6797_a72_obs_spm_base"),
        ("drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c", " \tfor (i = 0; i < ARRAY_SIZE"),
        ("drivers/misc/mediatek/freqhopping/mt6797/mt_freqhopping.c", " \tif (!spin_trylock_irqsave"),
    ]:
        owner_text = patch_section_for_path(owner_gate, source_path)
        ordered(
            owner_text,
            [
                "+\tif (!mt6797_a72_obs_accepts_sampling(cpu))",
                first_hardware_token,
            ],
            "{} pure-snapshot early gate".format(source_path),
        )
    dcm_gate = patch_section_for_path(
        owner_gate, "drivers/misc/mediatek/base/power/mt6797/mt_dcm.c"
    )
    ordered(
        dcm_gate,
        [
            " \tcpu = mt6797_a72_obs_active_cpu();",
            "+\tif (mt6797_a72_obs_is_cpu(cpu)) {",
            "+\t\treturn 0;",
            "+#endif",
            " \tif (on == MCUSYS_DCM_ON) {",
        ],
        "DCM observed/original branch ordering",
    )

    da = patch_for_path(patch_texts, "drivers/misc/mediatek/power/mt6797/da9214.c")
    require_tokens(
        da,
        [
            "#define DA9214_A72_REG_PAGE\t\t0x00",
            "#define DA9214_A72_REG_BUCKB\t\t0x5e",
            "#define DA9214_A72_REG_BUCKB_VSEL\t0xd9",
            "#define DA9214_A72_PAGE_REVERT\t\t0x80",
            "mutex_lock(&da9214_i2c_access)",
            "mutex_unlock(&da9214_i2c_access)",
            "da9214_a72_write_locked(DA9214_A72_REG_PAGE,",
            "snapshot.page_before",
            "if (!(snapshot.page_before & DA9214_A72_PAGE_REVERT) && ret >= 0)",
            "leaves the selector in the same page-zero state as the old path",
        ],
        "DA9214 owner",
    )
    require(
        da.count("mutex_lock(&da9214_i2c_access)") == 2
        and da.count("mutex_unlock(&da9214_i2c_access)") == 2,
        "DA9214 snapshot/mutation lock coverage changed",
    )

    spm = patch_for_path(patch_texts, "drivers/misc/mediatek/base/power/spm_v2/mt_spm.c")
    require_tokens(
        spm,
        [
            "#define MT6797_A72_SPM_PHYS\t0x10006000",
            "0x180, 0x184, 0x188, 0x18c, 0x218, 0x290",
            "base = mt6797_a72_obs_spm_base(&temporary);",
            "spin_lock_irqsave(&__spm_lock, flags)",
            "spin_unlock_irqrestore(&__spm_lock, flags)",
            "mutation.before = readl_relaxed(base + offset)",
            "mutation.after = readl_relaxed(base + offset)",
            "return false;",
        ],
        "SPM owner",
    )
    require(
        combined.count("mt6797_a72_obs_spm_rmw(cpu,") == 2,
        "SPM owner helper callsite count changed",
    )
    require_tokens(
        combined,
        [
            "0x218, BIT(0), BIT(0)",
            "0x290, 0x3, 0",
            "if (!mt6797_a72_obs_spm_rmw(cpu,",
        ],
        "SPM mutations",
    )

    idvfs = patch_for_path(patch_texts, "drivers/misc/mediatek/base/power/mt6797/mt_idvfs.c")
    for address in SECURE_ADDRESSES:
        require(idvfs.count(address) == 1, "secure address {} count changed".format(address))
    require_tokens(
        idvfs,
        [
            "static const u32 mt6797_a72_secure_registers[]",
            "ARRAY_SIZE(mt6797_a72_secure_registers)",
            "SEC_BIGIDVFS_READ(",
            "snapshot.sentinel_after",
            "snapshot.sentinel_after == snapshot.values[0]",
        ],
        "secure snapshot",
    )
    require("SEC_BIGIDVFS_WRITE" not in idvfs, "secure snapshot gained a write")

    clock = patch_for_path(
        patch_texts,
        "drivers/misc/mediatek/freqhopping/mt6797/mt_freqhopping.c",
    )
    require_tokens(
        clock,
        [
            "#define MT6797_A72_CLOCK_PLL_CON1\t0x224",
            "#define MT6797_A72_CLOCK_MUXSEL\t\t0x270",
            "#define MT6797_A72_CLOCK_CKDIV\t\t0x274",
            "spin_trylock_irqsave(&g_mt6797_0x1001AXXX_lock, flags)",
            "spin_unlock_irqrestore(&g_mt6797_0x1001AXXX_lock, flags)",
        ],
        "clock owner",
    )
    require(
        "mt6797_0x1001AXXX_get_semaphore(" not in "\n".join(
            line for _, line in added_lines(patch_paths[1])
        ),
        "clock snapshot calls owner's fatal semaphore helper",
    )

    bounded = patch_texts[4]
    require_tokens(
        bounded,
        [
            "-#define MT6797_A72_OBS_RING_SIZE\t2048",
            "+#define MT6797_A72_OBS_RING_SIZE\t256",
            "-\tfor (i = 0; i < DIV_ROUND_UP(SEMA_GET_TIMEOUT, 10); i++) {",
            "-\t\tudelay(10);",
            "-\t\tsnapshot.status = -ETIMEDOUT;",
            "+\ths_write32(g_reg_sema3_m0, 0x1);",
            "+\tif (!(hs_read32(g_reg_sema3_m0) & 0x1)) {",
            "+\t\tsnapshot.status = -EBUSY;",
        ],
        "timing-bound patch",
    )
    require(
        bounded.count("-\tmt6797_a72_obs_fixed_snapshot(cpu,") == 4,
        "timing-bound fixed snapshot removal count changed",
    )
    require(
        "\n".join(patch_texts[:4]).count(
            "mt6797_a72_obs_fixed_snapshot(cpu,"
        )
        == 8,
        "pre-bound fixed snapshot call count changed",
    )
    bounded_additions = "\n".join(line for _, line in added_lines(patch_paths[4]))
    require(
        "mt6797_a72_obs_fixed_snapshot(cpu," not in bounded_additions,
        "timing-bound patch adds a fixed snapshot",
    )
    require(
        re.search(r"\budelay\s*\(", bounded_additions) is None,
        "timing-bound patch adds a semaphore wait",
    )

    dcm = patch_for_path(patch_texts, "drivers/misc/mediatek/base/power/mt6797/mt_dcm.c")
    require_tokens(
        dcm,
        [
            "static DEFINE_SPINLOCK(mt6797_a72_obs_mp2_dcm_lock)",
            "spin_lock_irqsave(&mt6797_a72_obs_mp2_dcm_lock, flags)",
            "MCUCFG_SYNC_DCM_MP2_TOG1",
            "snapshot.toggle = reg_read(MCUCFG_SYNC_DCM_MP2_CONFIG)",
            "MCUCFG_SYNC_DCM_MP2_TOG0",
            "snapshot.final = reg_read(MCUCFG_SYNC_DCM_MP2_CONFIG)",
            "spin_unlock_irqrestore(&mt6797_a72_obs_mp2_dcm_lock, flags)",
            "MT6797_A72_PHASE_DCM_ENABLE",
            "MT6797_A72_PHASE_DCM_DISABLE",
        ],
        "MP2 DCM owner",
    )

    toprgu = patch_for_path(
        patch_texts, "drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c"
    )
    ordered(
        toprgu,
        [
            "spin_lock(&rgu_reg_operation_spinlock)",
            "snapshot.before = wdt_sys_val",
            "snapshot.requested = wdt_sys_val",
            "mt_reg_sync_writel(wdt_sys_val, MTK_WDT_SWSYSRST)",
            "snapshot.after = __raw_readl(MTK_WDT_SWSYSRST)",
            "spin_unlock(&rgu_reg_operation_spinlock)",
            "mt6797_a72_obs_toprgu(observer_cpu,",
        ],
        "TOPRGU owner ordering",
    )

    psci = patch_for_path(patch_texts, "arch/arm64/kernel/psci.c")
    ordered(
        psci,
        [
            "err = invoke_psci_fn(fn, cpuid, entry_point, 0)",
            "mt6797_a72_obs_psci_raw(cpuid, entry_point, err)",
            "return psci_to_linux_errno(err)",
        ],
        "raw PSCI ordering",
    )
    ordered(
        psci,
        [
            "err = psci_ops.cpu_on(cpu_logical_map(cpu), __pa(secondary_entry))",
            "MT6797_A72_PHASE_PSCI_MAPPED",
        ],
        "mapped PSCI ordering",
    )
    require_tokens(
        psci,
        [
            "MT6797_A72_PHASE_IDVFS_ENABLE",
            "MT6797_A72_PHASE_LAST_A72_OFFLINE",
            "MT6797_A72_PHASE_IDVFS_DISABLE",
            "MT6797_A72_PHASE_AFFINITY_RETRY",
            "MT6797_A72_PHASE_OFFLINE_FINAL",
        ],
        "PSCI lifecycle",
    )

    smp = patch_for_path(patch_texts, "arch/arm64/kernel/smp.c")
    ordered(
        smp,
        [
            "set_cpu_online(cpu, true)",
            "MT6797_A72_PHASE_SECONDARY_ONLINE",
            "complete(&cpu_running)",
        ],
        "secondary-online ordering",
    )
    ordered(
        smp,
        [
            "set_cpu_online(cpu, false)",
            "MT6797_A72_PHASE_CPU_DISABLE",
        ],
        "offline-disable ordering",
    )

    hps = patch_for_path(
        patch_texts,
        "drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c",
    )
    require_tokens(
        hps,
        [
            "MT6797_A72_PHASE_HPS_CPU_UP_BEGIN",
            "hotplug_ret = cpu_up(cpu)",
            "MT6797_A72_PHASE_HPS_CPU_UP_END",
            "MT6797_A72_PHASE_HPS_CPU_DOWN_BEGIN",
            "hotplug_ret = cpu_down(cpu)",
            "MT6797_A72_PHASE_HPS_CPU_DOWN_END",
            "if (hotplug_ret)",
        ],
        "HPS lifecycle",
    )

    docs = (root / "README.md").read_text() + "\n" + (root / "DESIGN.md").read_text()
    require_tokens(
        docs,
        [
            "59e00a9144d782e148332009a835b99c43382467",
            "Buildbox",
            "20170618T000000Z",
            "6.3.0-18cross1",
            "6.3.0 20170516",
            "GNU ld `2.28`",
            "Do not fall back to a native VM build",
            "source build",
            "compiler",
            "separate safety gate",
            "CONFIG_ANBOX",
        ],
        "experiment documentation",
    )
    for digest in ACTIVE_HASHES:
        require(digest in docs, "documentation missing active digest {}".format(digest))
    forbidden_candidate_label = "Candidate " + "AL"
    require(
        forbidden_candidate_label not in docs,
        "vendor observer was given the reserved AL candidate label",
    )
    superseded_dtb_prefix = "da" + "df"
    require(
        superseded_dtb_prefix not in docs.lower(),
        "documentation contains superseded DTB hash",
    )

    return [
        "{}  {}".format(hashlib.sha256(path.read_bytes()).hexdigest(), path.name)
        for path in patch_paths
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    try:
        digests = validate(args.experiment_root.resolve())
    except (OSError, ValidationError) as exc:
        print("FAIL: {}".format(exc), file=sys.stderr)
        return 1
    print("PASS: fixed owner-observer patch invariants")
    for digest in digests:
        print(digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
