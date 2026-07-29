#!/usr/bin/env python3
"""Offline source/profile contracts for the fixed Fermi fingerprint."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import re
import sys
import unittest

sys.dont_write_bytecode = True

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import candidate_fermi as co

QUASAR_CONTRACT = (
    ROOT
    / "experiments/2026-07-27-mt6797-i2c6-quasar/"
    "scripts/test-quasar-contract.py"
)
QUASAR_CONTRACT_SHA256 = (
    "33e48925d0a888f58ea19df243a3b3819199f784011d5f5fa08026c8910a3f53"
)
PATCH = ROOT / "patches" / co.FERMI_PATCH
FERMI_SERIES = ROOT / co.SERIES
QUASAR_SERIES = ROOT / "patches/series-quasar-i2c6-native-fifo"
CANONICAL_SERIES = ROOT / "patches/series"
CONFIG = ROOT / co.CONFIG_FRAGMENT
MANIFEST = ROOT / "kernel/manifest.json"
QUASAR_PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-quasar"
)
DRIVER = "drivers/i2c/busses/i2c-mt65xx.c"
KCONFIG = "drivers/i2c/busses/Kconfig"


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def load_quasar_contract():
    data = QUASAR_CONTRACT.read_bytes()
    if hashlib.sha256(data).hexdigest() != QUASAR_CONTRACT_SHA256:
        raise ValueError("source-pinned Quasar contract test changed")
    spec = importlib.util.spec_from_file_location("fermi_quasar_contract", QUASAR_CONTRACT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Quasar contract")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


qc = load_quasar_contract()


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def require_once(text: str, token: str) -> None:
    require(text.count(token) == 1, f"expected exactly one {token!r}")


def entries(text: str) -> list[str]:
    return [
        line
        for raw in text.splitlines()
        if (line := raw.strip()) and not line.startswith("#")
    ]


def validate_quasar_predecessor(manifest: dict[str, object]) -> None:
    qc.validate_contract(
        read_text(qc.PATCH),
        read_text(qc.CONFIG),
        read_text(qc.QUASAR_SERIES),
        read_text(qc.VEGA_SERIES),
        read_text(qc.CANONICAL_SERIES),
        manifest,
    )


def validate_contract(
    patch: str,
    config: str,
    fermi_series: str,
    quasar_series: str,
    canonical_series: str,
    manifest: dict[str, object],
) -> None:
    co.require_input_pins()
    qc.validate_patch_syntax(patch)
    additions = qc.added_by_path(patch)
    require(set(additions) == {KCONFIG, DRIVER}, "0120 patch scope changed")
    driver = additions[DRIVER]
    kconfig = additions[KCONFIG]

    require(
        "Subject: [PATCH 120/120] i2c: mediatek: add fixed Fermi "
        "topology fingerprint" in patch,
        "Fermi patch subject changed",
    )
    require(
        "config I2C_MT65XX_FERMI_DIAGNOSTIC" in kconfig,
        "Fermi Kconfig symbol is absent",
    )
    for dependency in (
        "depends on !I2C_MT65XX_ORION_DIAGNOSTIC",
        "depends on !I2C_MT65XX_QUASAR_DIAGNOSTIC",
    ):
        require(dependency in kconfig, f"Fermi lost exclusion {dependency}")

    for alias in ("read", "write", "fops", "init"):
        require_once(
            driver,
            f"#define mtk_i2c_quasar_{alias}\t\tmtk_i2c_fermi_{alias}",
        )
    require_once(driver, "#define MTK_I2C_QUASAR_RESULT_SIZE\t32768")
    require_once(
        driver,
        '#define MTK_I2C_QUASAR_DEBUGFS_FILE\t"fermi-run-native"',
    )
    require_once(
        driver,
        '#define MTK_I2C_QUASAR_READY_MARKER\t"GEMINI_FERMI_NATIVE_DIAGNOSTIC"',
    )
    require_once(
        driver,
        '#define MTK_I2C_QUASAR_GATE\t\t"GEMINI_FERMI_DIAGNOSTIC_GATE"',
    )
    require_once(
        driver,
        '#define MTK_I2C_QUASAR_COUNTER_CONTRACT\t"14,0,14,14"',
    )

    require(
        re.search(
            r"mtk_i2c_quasar_addresses[^=]*=\s*\{\s*"
            r"0x69,\s*0x69,\s*0x69,\s*0x68,\s*0x68,\s*0x68,\s*0x68,\s*\};",
            driver,
            re.S,
        )
        is not None,
        "Fermi fixed address order changed",
    )
    require(
        re.search(
            r"mtk_i2c_quasar_registers[^=]*=\s*\{\s*"
            r"0x05,\s*0x06,\s*0x47,\s*0xd3,\s*0x5e,\s*0xd9,\s*0xda,\s*\};",
            driver,
            re.S,
        )
        is not None,
        "Fermi fixed register order changed",
    )
    require(
        re.search(
            r"mtk_i2c_quasar_expected[^=]*=\s*\{\s*"
            r"0xd9,\s*0xd0,\s*0xc0,\s*0x05,\s*0x00,\s*0x00,\s*0x00,\s*\};",
            driver,
            re.S,
        )
        is not None,
        "Fermi expected-field array changed",
    )
    require(
        re.search(
            r"mtk_i2c_quasar_prefills[^=]*=\s*\{\s*"
            r"\{\s*0xa5,\s*0x5a,\s*0x3c,\s*0x96,\s*0x69,\s*0xc3,\s*0x87\s*\},\s*"
            r"\{\s*0x78,\s*0xb4,\s*0x4b,\s*0xd2,\s*0x2d,\s*0xe1,\s*0x1e\s*\},\s*\};",
            driver,
            re.S,
        )
        is not None,
        "Fermi receive-prefill matrix changed",
    )
    flattened = tuple(value for row in co.PREFILLS for value in row)
    require(len(set(flattened)) == 14, "Fermi prefills are not all distinct")

    required_semantics = (
        "sample->value == sample->prefill",
        "sample->index < 3",
        "sample->value != sample->expected",
        "sample->index == 3 && (sample->value & 0x07) != 0x05",
        "sample->pass == 1",
        "diag->samples[sample->index].value",
        "diag->stability_validated++",
        "diag->stability_validated != 4",
        "sample->addr = mtk_i2c_quasar_addresses[index]",
        "msgs[0].addr = sample->addr",
        "msgs[1].addr = sample->addr",
        '"addresses=0x69,0x68 passes=2 "',
        '"topology_mask=07 topology_expected=05 "',
        '"stability_registers=d3,5e,d9,da stability_validated=%u "',
        '"sample=%u pass=%u index=%u address=%02x "',
        '"register=%02x expected_kind=%s expected=%02x "',
        'return "exact";',
        'return "topology-stable";',
        'return "stable";',
    )
    for token in required_semantics:
        require(token in driver, f"Fermi lost semantic token {token!r}")
    require("mtk_i2c_init_hw" not in driver, "Fermi adds explicit reinitialization")
    require("i2c_transfer(&i2c->adap" not in driver, "Fermi adds recursive transfer")
    require(
        all(
            token not in driver
            for token in (
                "I2C_DMA_WARM_RST",
                "I2C_DMA_HARD_RST",
                "OFFSET_RST",
                "PAGE_CON",
                "debugfs_create_u",
            )
        ),
        "Fermi adds reset, page, or configurable debugfs input",
    )
    require(
        driver.count("msgs[0].len = 1;") == 0
        and driver.count("msgs[1].len = 1;") == 0,
        "0120 unexpectedly rewrites inherited transfer lengths",
    )

    config_requirements = (
        'CONFIG_LOCALVERSION="-gemini-fermi"',
        "# CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC is not set",
        "# CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC is not set",
        "CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y",
        "# CONFIG_I2C_CHARDEV is not set",
        "# CONFIG_REGULATOR_DA9211 is not set",
        "# CONFIG_MTK_MT6797_A72_POWER is not set",
        "maxcpus=8",
        "Gemini-L-Fermi",
        "GEMINI_FERMI_20260728",
    )
    for token in config_requirements:
        require(token in config, f"Fermi config lost {token!r}")

    fermi_entries = entries(fermi_series)
    quasar_entries = entries(quasar_series)
    canonical_entries = entries(canonical_series)
    require(
        fermi_entries == quasar_entries + [co.FERMI_PATCH],
        "Fermi series is not exact Quasar plus 0120",
    )
    positions = [canonical_entries.index(entry) for entry in fermi_entries]
    require(
        positions == sorted(positions) and len(set(positions)) == len(positions),
        "Fermi series is not a canonical-order subsequence",
    )

    profiles = manifest["config"]["profiles"]  # type: ignore[index]
    require(isinstance(profiles, dict), "manifest profiles are not an object")
    fermi = profiles.get(co.PROFILE)
    quasar = profiles.get(QUASAR_PROFILE)
    require(isinstance(fermi, dict), "Fermi profile is absent")
    require(isinstance(quasar, dict), "Quasar profile is absent")
    require(fermi.get("base") == "defconfig", "Fermi base changed")
    require(fermi.get("patch_series") == co.SERIES, "Fermi series pin changed")
    fragments = fermi.get("fragments")
    quasar_fragments = quasar.get("fragments")
    require(isinstance(fragments, list), "Fermi fragments are absent")
    require(isinstance(quasar_fragments, list), "Quasar fragments are absent")
    require(
        fragments
        == quasar_fragments[:-1] + ["configs/gemini-i2c6-fermi.fragment"],
        "Fermi fragments are not exact Quasar base plus Fermi policy",
    )
    validate_quasar_predecessor(manifest)


class FermiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.patch = read_text(PATCH)
        cls.config = read_text(CONFIG)
        cls.fermi_series = read_text(FERMI_SERIES)
        cls.quasar_series = read_text(QUASAR_SERIES)
        cls.canonical_series = read_text(CANONICAL_SERIES)
        cls.manifest = json.loads(read_text(MANIFEST))

    def validate(
        self,
        *,
        patch: str | None = None,
        config: str | None = None,
        fermi_series: str | None = None,
        manifest: dict[str, object] | None = None,
    ) -> None:
        validate_contract(
            patch if patch is not None else self.patch,
            config if config is not None else self.config,
            fermi_series if fermi_series is not None else self.fermi_series,
            self.quasar_series,
            self.canonical_series,
            manifest if manifest is not None else self.manifest,
        )

    def test_production_contract(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.patch.encode()).hexdigest(),
            co.FERMI_PATCH_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(self.config.encode()).hexdigest(),
            co.CONFIG_FRAGMENT_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(self.fermi_series.encode()).hexdigest(),
            co.SERIES_SHA256,
        )
        self.validate()

    def test_rejects_safety_and_attribution_mutations(self) -> None:
        mutations: list[tuple[str, dict[str, object]]] = [
            (
                "bad-topology-mask",
                {"patch": self.patch.replace("sample->value & 0x07", "sample->value & 0x03", 1)},
            ),
            (
                "remove-own-prefill-gate",
                {"patch": self.patch.replace("sample->value == sample->prefill", "false", 1)},
            ),
            (
                "weaken-stability",
                {
                    "patch": self.patch.replace(
                        "diag->samples[sample->index].value",
                        "sample->value",
                        1,
                    )
                },
            ),
            (
                "wrong-primary-address",
                {
                    "patch": self.patch.replace(
                        "0x69, 0x69, 0x69, 0x68, 0x68, 0x68, 0x68",
                        "0x69, 0x69, 0x69, 0x69, 0x68, 0x68, 0x68",
                        1,
                    )
                },
            ),
            (
                "duplicate-prefill",
                {
                    "patch": self.patch.replace(
                        "0x78, 0xb4, 0x4b, 0xd2, 0x2d, 0xe1, 0x1e",
                        "0xa5, 0xb4, 0x4b, 0xd2, 0x2d, 0xe1, 0x1e",
                        1,
                    )
                },
            ),
            (
                "truncate-buffer",
                {"patch": self.patch.replace("RESULT_SIZE\t32768", "RESULT_SIZE\t16384", 1)},
            ),
            (
                "ambiguous-read-symbol",
                {
                    "patch": self.patch.replace(
                        "#define mtk_i2c_quasar_read\t\tmtk_i2c_fermi_read",
                        "#define mtk_i2c_quasar_read\t\tmtk_i2c_quasar_read",
                        1,
                    )
                },
            ),
            (
                "quasar-enabled",
                {
                    "config": self.config.replace(
                        "# CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC is not set",
                        "CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=y",
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
                "0120-not-selected",
                {
                    "fermi_series": self.fermi_series.replace(
                        co.FERMI_PATCH + "\n",
                        "",
                        1,
                    )
                },
            ),
        ]
        manifest_mutation = copy.deepcopy(self.manifest)
        manifest_mutation["config"]["profiles"][co.PROFILE]["patch_series"] = (  # type: ignore[index]
            "patches/series-quasar-i2c6-native-fifo"
        )
        mutations.append(
            ("manifest-reselects-quasar", {"manifest": manifest_mutation})
        )
        for name, kwargs in mutations:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.validate(**kwargs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
