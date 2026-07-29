#!/usr/bin/env python3
"""Offline source/profile contracts for the fixed Quasar native-path canary."""

from __future__ import annotations

import copy
import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
PATCH_REL = (
    "patches/v7.1.3/"
    "0119-i2c-mediatek-add-fixed-Quasar-native-path-canary.patch"
)
PATCH_SERIES_ENTRY = PATCH_REL.removeprefix("patches/")
PATCH = ROOT / PATCH_REL
QUASAR_SERIES = ROOT / "patches/series-quasar-i2c6-native-fifo"
VEGA_SERIES = ROOT / "patches/series-vega-i2c6-idvfs-fifo"
CANONICAL_SERIES = ROOT / "patches/series"
CONFIG = ROOT / "configs/gemini-i2c6-quasar.fragment"
MANIFEST = ROOT / "kernel/manifest.json"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-quasar"
)
VEGA_PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-vega"
)
DRIVER = "drivers/i2c/busses/i2c-mt65xx.c"
KCONFIG = "drivers/i2c/busses/Kconfig"


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def added_by_path(patch: str) -> dict[str, str]:
    """Return added lines, without diff markers, for each patched path."""
    result: dict[str, list[str]] = {}
    current: str | None = None
    for line in patch.splitlines():
        if line.startswith("diff --git a/"):
            match = re.fullmatch(r"diff --git a/(.+) b/(.+)", line)
            if not match or match.group(1) != match.group(2):
                raise ValueError("non-identical diff paths")
            current = match.group(1)
            result.setdefault(current, [])
            continue
        if current and line.startswith("+") and not line.startswith("+++"):
            result[current].append(line[1:])
    return {path: "\n".join(lines) + "\n" for path, lines in result.items()}


def validate_patch_syntax(patch: str) -> None:
    """Reject malformed unified hunks, including missing context prefixes."""
    old_left = 0
    new_left = 0
    active = False
    header = re.compile(
        r"@@ -[0-9]+(?:,([0-9]+))? \+[0-9]+(?:,([0-9]+))? @@"
    )

    for number, line in enumerate(patch.splitlines(), 1):
        if line == "-- ":
            require(
                not active and old_left == 0 and new_left == 0,
                f"format-patch footer reached inside hunk at line {number}",
            )
            continue
        match = header.match(line)
        if match:
            require(
                not active or (old_left == 0 and new_left == 0),
                f"unfinished hunk before line {number}",
            )
            old_left = int(match.group(1) or "1")
            new_left = int(match.group(2) or "1")
            active = True
            continue
        if not active:
            continue
        require(line != "", f"unprefixed empty hunk line {number}")
        prefix = line[0]
        require(
            prefix in (" ", "+", "-", "\\"),
            f"invalid hunk prefix at line {number}",
        )
        if prefix == " ":
            old_left -= 1
            new_left -= 1
        elif prefix == "-":
            old_left -= 1
        elif prefix == "+":
            new_left -= 1
        require(
            old_left >= 0 and new_left >= 0,
            f"hunk count underflow at line {number}",
        )
        if old_left == 0 and new_left == 0:
            active = False

    require(
        not active and old_left == 0 and new_left == 0,
        "unterminated final hunk",
    )


def series_entries(text: str) -> list[str]:
    return [
        line
        for raw in text.splitlines()
        if (line := raw.strip()) and not line.startswith("#")
    ]


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def require_once(text: str, token: str) -> None:
    require(text.count(token) == 1, f"expected exactly one {token!r}")


def require_order(text: str, *tokens: str) -> None:
    cursor = -1
    for token in tokens:
        position = text.find(token, cursor + 1)
        require(position >= 0, f"missing ordered token {token!r}")
        require(position > cursor, f"out-of-order token {token!r}")
        cursor = position


def validate_contract(
    patch_text: str,
    config_text: str,
    quasar_series_text: str,
    vega_series_text: str,
    canonical_series_text: str,
    manifest: dict[str, object],
) -> None:
    validate_patch_syntax(patch_text)
    additions = added_by_path(patch_text)
    require(set(additions) == {KCONFIG, DRIVER}, "0119 patch scope changed")
    driver = additions[DRIVER]
    kconfig = additions[KCONFIG]

    require(
        "Subject: [PATCH 119/119] i2c: mediatek: add fixed Quasar "
        "native-path canary" in patch_text,
        "patch identity changed",
    )
    require(
        "config I2C_MT65XX_QUASAR_DIAGNOSTIC" in kconfig,
        "Quasar Kconfig symbol missing",
    )
    require(
        "depends on !I2C_MT65XX_ORION_DIAGNOSTIC" in kconfig,
        "Quasar no longer excludes Orion",
    )

    require_once(driver, 'debugfs_create_file("quasar-run-native", 0600,')
    require("orion-run-all" not in driver, "0119 adds an Orion run endpoint")
    require_once(driver, 'memcmp(command, "run\\n", sizeof(command))')
    require_once(driver, "ret = __i2c_transfer(&i2c->adap, msgs,")
    require(
        "ret = i2c_transfer(&i2c->adap" not in driver,
        "Quasar recursively locks through i2c_transfer",
    )
    require(
        "mtk_i2c_init_hw" not in driver,
        "Quasar explicitly resets/reinitializes the controller",
    )
    require(
        "WRITE_ONCE(diag->active_sample" not in driver,
        "Quasar active-sample publication is not release/acquire",
    )
    require(
        driver.count("smp_store_release(&diag->active_sample,") == 3,
        "active-sample release stores changed",
    )
    require(
        driver.count("smp_load_acquire(&i2c->quasar.active_sample)") == 5,
        "snapshot acquire loads changed",
    )
    require_once(
        driver, "i2c_lock_bus(&i2c->adap, I2C_LOCK_ROOT_ADAPTER);"
    )
    require_once(
        driver, "i2c_unlock_bus(&i2c->adap, I2C_LOCK_ROOT_ADAPTER);"
    )
    require(
        all(
            token not in driver
            for token in (
                "I2C_DMA_WARM_RST",
                "I2C_DMA_HARD_RST",
                "OFFSET_RST",
                "mtk_i2c_get_wrrd_len_mode",
                "mtk_i2c_should_use_dma",
            )
        ),
        "Quasar adds a reset or native-policy override",
    )

    require(
        re.search(
            r"mtk_i2c_quasar_registers[^=]*=\s*"
            r"\{\s*0x05,\s*0x06,\s*0x47,\s*\};",
            driver,
            re.S,
        )
        is not None,
        "fixed register order changed",
    )
    require(
        re.search(
            r"mtk_i2c_quasar_expected[^=]*=\s*"
            r"\{\s*0xd9,\s*0xd0,\s*0xc0,\s*\};",
            driver,
            re.S,
        )
        is not None,
        "fixed expected tuple changed",
    )
    require(
        re.search(
            r"mtk_i2c_quasar_prefills[^=]*=\s*"
            r"\{\s*\{\s*0xa5,\s*0x5a,\s*0x3c\s*\},\s*"
            r"\{\s*0x96,\s*0x69,\s*0xc3\s*\},\s*\};",
            driver,
            re.S,
        )
        is not None,
        "six distinct receive prefills changed",
    )
    prefills = (0xA5, 0x5A, 0x3C, 0x96, 0x69, 0xC3)
    expected = (0xD9, 0xD0, 0xC0)
    require(len(set(prefills)) == 6, "receive prefills are not distinct")
    require(not set(prefills) & set(expected), "prefill equals expected data")

    require(driver.count("msgs[0].addr = 0x69;") == 1, "write address changed")
    require(driver.count("msgs[1].addr = 0x69;") == 1, "read address changed")
    require_once(driver, "msgs[0].flags = 0;")
    require_once(driver, "msgs[0].len = 1;")
    require_once(driver, "msgs[0].buf = &pointer;")
    require_once(driver, "msgs[1].flags = I2C_M_RD;")
    require_once(driver, "msgs[1].len = 1;")
    require_once(driver, "msgs[1].buf = &value;")
    require("PAGE_CON" not in driver, "Quasar adds PAGE_CON access")

    require_order(
        driver,
        "diag->state = MTK_I2C_QUASAR_RUNNING;",
        "ret = mtk_i2c_quasar_run(i2c);",
        "diag->state = MTK_I2C_QUASAR_DONE;",
    )
    require_order(
        driver,
        "i2c_lock_bus(&i2c->adap, I2C_LOCK_ROOT_ADAPTER);",
        "device_for_each_child(&i2c->adap.dev",
        "mt6797_dvfsp_handoff_require_ready(i2c->dvfsp_handoff)",
        "diag->transfer_attempts_before",
        "i2c->adap.retries = 0;",
        "for (pass = 0; pass < MTK_I2C_QUASAR_PASS_COUNT; pass++)",
        "for (index = 0; index < MTK_I2C_QUASAR_REGISTER_COUNT;",
        "ret = __i2c_transfer(&i2c->adap, msgs,",
        "out_restore_retries:",
        "i2c->adap.retries = diag->retries_before;",
        "smp_store_release(&diag->active_sample, NULL);",
        "i2c_unlock_bus(&i2c->adap, I2C_LOCK_ROOT_ADAPTER);",
    )
    require_order(
        driver,
        "smp_store_release(&diag->active_sample, sample);",
        "ret = __i2c_transfer(&i2c->adap, msgs,",
        "smp_store_release(&diag->active_sample, NULL);",
    )

    required_gate_and_policy = (
        "!sample->programmed",
        "diag->init_attempts_before != 1",
        "diag->init_successes_before != 1",
        "diag->retries_before != 1",
        "i2c->dev_comp->wrrd_len_mode != MTK_I2C_WRRD_LEN_PACKED_8_5",
        "i2c->dev_comp->fifo_size != 8",
        "sample->pre.transfer_len != 0x0101",
        "sample->pre.transfer_len_aux",
        "sample->pre.transac_len != I2C_WRRD_TRANAC_VALUE",
        "sample->pre.control != 0x003a",
        "sample->pre.control & I2C_CONTROL_DMA_EN",
        "sample->irq_stat != I2C_TRANSAC_COMP",
        "sample->irq.intr_stat != I2C_TRANSAC_COMP",
        "sample->fifo_count != 1",
        "sample->fifo_count_drained ||",
        "diag->transfer_attempts_after != ordinal",
        "diag->dma_starts_after",
        "diag->nonzero_starts_after != ordinal",
        "diag->irqs_after != ordinal",
        "sample->value != sample->expected",
        "diag->transport_completed != MTK_I2C_QUASAR_SAMPLE_COUNT",
        "diag->value_validated != MTK_I2C_QUASAR_SAMPLE_COUNT",
        "diag->transfer_attempts_after != MTK_I2C_QUASAR_SAMPLE_COUNT",
        "diag->nonzero_starts_after != MTK_I2C_QUASAR_SAMPLE_COUNT",
        "diag->irqs_after != MTK_I2C_QUASAR_SAMPLE_COUNT",
        "diag->init_attempts_after != diag->init_attempts_before",
        "diag->init_successes_after != diag->init_successes_before",
    )
    for token in required_gate_and_policy:
        require(token in driver, f"missing gate/policy token {token!r}")

    for phase in ("pre", "irq", "post", "drained"):
        for field in (
            "dma_en",
            "dma_con",
            "dma_int_flag",
            "dma_tx_len",
            "dma_rx_len",
        ):
            require(
                f"sample->{phase}.{field}" in driver,
                f"{phase} APDMA {field} zero gate missing",
            )

    for field in (
        "transfer_len",
        "transfer_len_aux",
        "transac_len",
        "control",
        "start",
        "intr_stat",
        "fifo_stat",
        "dma_en",
        "dma_con",
        "dma_int_flag",
        "dma_tx_len",
        "dma_rx_len",
    ):
        require(
            f"snapshot->{field}" in driver,
            f"snapshot field {field} is no longer recorded",
        )
    require_once(driver, "mtk_i2c_quasar_record_programmed(i2c, use_dma);")
    require_once(driver, "mtk_i2c_quasar_record_irq(i2c, intr_stat);")
    require_once(driver, "mtk_i2c_quasar_record_post(i2c);")
    require_once(
        driver, "mtk_i2c_quasar_record_fifo(i2c, fifo_stat, fifo_count);"
    )
    require_once(driver, "mtk_i2c_quasar_record_drained(i2c);")
    for token in (
        '"attempted=%u transport_completed=%u value_validated=%u "',
        "sample->programmed = true;",
        "sample->transport_completed = true;",
        "diag->transport_completed++;",
        "sample->value_validated = true;",
        "diag->value_validated++;",
        '"unobserved"',
        "fifo_count_drained=%u",
    ):
        require(token in driver, f"result attribution lost {token!r}")

    require(
        'of_find_node_by_path("/i2c@1100e000")' in driver
        and "i2c->dev->of_node != target" in driver
        and "of_node_put(target);" in driver,
        "canonical I2C6 OF identity gate changed",
    )
    require(
        "mode=none" in driver
        and "forced_length_mode=none" in driver
        and "forced_engine=none" in driver
        and "reset_pending=0" in driver,
        "native/no-reset status contract missing",
    )

    config_requirements = (
        'CONFIG_LOCALVERSION="-gemini-quasar"',
        "CONFIG_DEBUG_FS=y",
        "# CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC is not set",
        "CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=y",
        "# CONFIG_I2C_CHARDEV is not set",
        "# CONFIG_REGULATOR_DA9211 is not set",
        "# CONFIG_MTK_MT6797_A72_POWER is not set",
        "maxcpus=8",
        "Gemini-L-Quasar",
        "GEMINI_QUASAR_20260727",
    )
    for token in config_requirements:
        require(token in config_text, f"config lost {token!r}")
    require(
        "CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC=y" not in config_text,
        "profile compiles the Orion diagnostic",
    )

    quasar_entries = series_entries(quasar_series_text)
    vega_entries = series_entries(vega_series_text)
    canonical_entries = series_entries(canonical_series_text)
    require(
        quasar_entries == vega_entries + [PATCH_SERIES_ENTRY],
        "Quasar series is not exact Vega plus 0119",
    )
    positions = [canonical_entries.index(entry) for entry in quasar_entries]
    require(
        positions == sorted(positions) and len(set(positions)) == len(positions),
        "Quasar series is not a canonical-order subsequence",
    )
    for entry in quasar_entries:
        require((ROOT / "patches" / entry).is_file(), f"missing patch {entry}")

    profiles = manifest["config"]["profiles"]  # type: ignore[index]
    require(isinstance(profiles, dict), "manifest profiles are not an object")
    profile = profiles.get(PROFILE)
    vega = profiles.get(VEGA_PROFILE)
    require(isinstance(profile, dict), "Quasar profile missing")
    require(isinstance(vega, dict), "Vega profile missing")
    require(profile.get("base") == "defconfig", "Quasar base changed")
    require(
        profile.get("patch_series") == "patches/series-quasar-i2c6-native-fifo",
        "Quasar series pin changed",
    )
    fragments = profile.get("fragments")
    vega_fragments = vega.get("fragments")
    require(isinstance(fragments, list), "Quasar fragments missing")
    require(isinstance(vega_fragments, list), "Vega fragments missing")
    require(
        fragments == vega_fragments[:-1] + ["configs/gemini-i2c6-quasar.fragment"],
        "Quasar fragments are not exact Vega base plus Quasar policy",
    )


class QuasarContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.patch = read_text(PATCH)
        cls.config = read_text(CONFIG)
        cls.quasar_series = read_text(QUASAR_SERIES)
        cls.vega_series = read_text(VEGA_SERIES)
        cls.canonical_series = read_text(CANONICAL_SERIES)
        cls.manifest = json.loads(read_text(MANIFEST))

    def validate(
        self,
        *,
        patch: str | None = None,
        config: str | None = None,
        quasar_series: str | None = None,
        manifest: dict[str, object] | None = None,
    ) -> None:
        validate_contract(
            patch if patch is not None else self.patch,
            config if config is not None else self.config,
            quasar_series if quasar_series is not None else self.quasar_series,
            self.vega_series,
            self.canonical_series,
            manifest if manifest is not None else self.manifest,
        )

    def test_production_contract(self) -> None:
        self.validate()

    def test_rejects_attribution_and_safety_mutations(self) -> None:
        mutations: list[tuple[str, dict[str, object]]] = [
            (
                "corrupt-context-prefix",
                {
                    "patch": self.patch.replace(
                        " \tif (i2c->dvfsp_handoff) {",
                        "\tif (i2c->dvfsp_handoff) {",
                        1,
                    )
                },
            ),
            (
                "recursive-transfer",
                {
                    "patch": self.patch.replace(
                        "ret = __i2c_transfer(&i2c->adap, msgs,",
                        "ret = i2c_transfer(&i2c->adap, msgs,",
                        1,
                    )
                },
            ),
            (
                "explicit-reset",
                {
                    "patch": self.patch.replace(
                        "+\ti2c->adap.retries = 0;",
                        "+\tmtk_i2c_init_hw(i2c);\n"
                        "+\ti2c->adap.retries = 0;",
                        1,
                    )
                },
            ),
            (
                "wrong-address",
                {
                    "patch": self.patch.replace(
                        "+\t\t\tmsgs[0].addr = 0x69;",
                        "+\t\t\tmsgs[0].addr = 0x68;",
                        1,
                    )
                },
            ),
            (
                "wrong-expected-byte",
                {"patch": self.patch.replace("0xd9, 0xd0, 0xc0", "0xd8, 0xd0, 0xc0", 1)},
            ),
            (
                "duplicate-prefill",
                {"patch": self.patch.replace("0x96, 0x69, 0xc3", "0xa5, 0x69, 0xc3", 1)},
            ),
            (
                "unlock-root-before-transfer",
                {
                    "patch": self.patch.replace(
                        "+\ti2c->adap.retries = 0;",
                        "+\ti2c_unlock_bus(&i2c->adap, I2C_LOCK_ROOT_ADAPTER);\n"
                        "+\ti2c->adap.retries = 0;",
                        1,
                    )
                },
            ),
            (
                "weak-control-check",
                {"patch": self.patch.replace("sample->pre.control != 0x003a", "false", 1)},
            ),
            (
                "weak-programmed-check",
                {"patch": self.patch.replace("!sample->programmed", "false", 1)},
            ),
            (
                "weak-drained-check",
                {
                    "patch": self.patch.replace(
                        "    sample->fifo_count_drained ||",
                        "    false ||",
                        1,
                    )
                },
            ),
            (
                "weak-value-check",
                {
                    "patch": self.patch.replace(
                        "sample->value != sample->expected",
                        "false",
                        1,
                    )
                },
            ),
            (
                "world-readable-file",
                {
                    "patch": self.patch.replace(
                        'debugfs_create_file("quasar-run-native", 0600,',
                        'debugfs_create_file("quasar-run-native", 0644,',
                        1,
                    )
                },
            ),
            (
                "collapse-result-counts",
                {
                    "patch": self.patch.replace(
                        "transport_completed=%u value_validated=%u",
                        "completed=%u completed_again=%u",
                        1,
                    )
                },
            ),
            (
                "orion-enabled",
                {
                    "config": self.config.replace(
                        "# CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC is not set",
                        "CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC=y",
                        1,
                    )
                },
            ),
            (
                "i2cdev-enabled",
                {
                    "config": self.config.replace(
                        "# CONFIG_I2C_CHARDEV is not set",
                        "CONFIG_I2C_CHARDEV=y",
                        1,
                    )
                },
            ),
            (
                "provider-enabled",
                {
                    "config": self.config.replace(
                        "# CONFIG_REGULATOR_DA9211 is not set",
                        "CONFIG_REGULATOR_DA9211=y",
                        1,
                    )
                },
            ),
            (
                "a72-enabled",
                {
                    "config": self.config.replace(
                        "# CONFIG_MTK_MT6797_A72_POWER is not set",
                        "CONFIG_MTK_MT6797_A72_POWER=y",
                        1,
                    )
                },
            ),
            (
                "0119-not-selected",
                {
                    "quasar_series": self.quasar_series.replace(
                        PATCH_SERIES_ENTRY + "\n", "", 1
                    )
                },
            ),
        ]

        manifest_mutation = copy.deepcopy(self.manifest)
        manifest_mutation["config"]["profiles"][PROFILE]["patch_series"] = (  # type: ignore[index]
            "patches/series-vega-i2c6-idvfs-fifo"
        )
        mutations.append(("manifest-reselects-vega", {"manifest": manifest_mutation}))

        for name, kwargs in mutations:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.validate(**kwargs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
