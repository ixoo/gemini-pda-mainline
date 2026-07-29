#!/usr/bin/env python3
"""Offline source/profile contracts for Curie's exact board-control gate."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import candidate_curie as co

FERMI_CONTRACT = (
    ROOT
    / "experiments/2026-07-28-da9214-fermi/scripts/test-fermi-contract.py"
)
FERMI_CONTRACT_SHA256 = (
    "98df331641c3c7b39a3f658d7eb56f1285fd8499912be92a416b49638f88b8cc"
)
PATCH = ROOT / "patches" / co.CURIE_PATCH
CURIE_SERIES = ROOT / co.SERIES
FERMI_SERIES = ROOT / "patches/series-fermi-i2c6-topology-fingerprint"
CANONICAL_SERIES = ROOT / "patches/series"
CONFIG = ROOT / co.CONFIG_FRAGMENT
MANIFEST = ROOT / "kernel/manifest.json"
FERMI_PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-fermi"
)
DRIVER = "drivers/i2c/busses/i2c-mt65xx.c"
KCONFIG = "drivers/i2c/busses/Kconfig"


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def load_fermi_contract():
    data = FERMI_CONTRACT.read_bytes()
    if hashlib.sha256(data).hexdigest() != FERMI_CONTRACT_SHA256:
        raise ValueError("source-pinned Fermi contract test changed")
    fermi_dir = FERMI_CONTRACT.parent
    sys.path.insert(0, str(fermi_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "curie_fermi_contract", FERMI_CONTRACT
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load source-pinned Fermi contract")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(fermi_dir))


fc = load_fermi_contract()


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


def validate_fermi_predecessor(manifest: dict[str, object]) -> None:
    fc.validate_contract(
        read_text(fc.PATCH),
        read_text(fc.CONFIG),
        read_text(fc.FERMI_SERIES),
        read_text(fc.QUASAR_SERIES),
        read_text(fc.CANONICAL_SERIES),
        manifest,
    )


def validate_contract(
    patch: str,
    config: str,
    curie_series: str,
    fermi_series: str,
    canonical_series: str,
    manifest: dict[str, object],
) -> None:
    co.require_input_pins()
    fc.qc.validate_patch_syntax(patch)
    additions = fc.qc.added_by_path(patch)
    require(set(additions) == {KCONFIG, DRIVER}, "0121 patch scope changed")
    driver = additions[DRIVER]
    kconfig = additions[KCONFIG]

    require(
        "Subject: [PATCH 121/121] i2c: mediatek: require exact Curie "
        "board control" in patch,
        "Curie patch subject changed",
    )
    require(
        "config I2C_MT65XX_CURIE_DIAGNOSTIC" in kconfig,
        "Curie Kconfig symbol is absent",
    )
    require(
        "I2C_MT65XX_FERMI_DIAGNOSTIC" not in kconfig,
        "Curie Kconfig additions retain Fermi",
    )
    for dependency in (
        "depends on !I2C_MT65XX_ORION_DIAGNOSTIC",
        "depends on !I2C_MT65XX_QUASAR_DIAGNOSTIC",
    ):
        require(dependency in patch, f"Curie lost exclusion {dependency}")

    for alias in ("read", "write", "fops", "init"):
        require_once(
            driver,
            f"#define mtk_i2c_quasar_{alias}\t\tmtk_i2c_curie_{alias}",
        )
    for token in (
        '#define MTK_I2C_QUASAR_CANDIDATE\t"Curie"',
        '#define MTK_I2C_QUASAR_DEBUGFS_FILE\t"curie-run-native"',
        '#define MTK_I2C_QUASAR_GATE\t\t"GEMINI_CURIE_DIAGNOSTIC_GATE"',
        '#define MTK_I2C_QUASAR_READY_MARKER\t"GEMINI_CURIE_NATIVE_DIAGNOSTIC"',
    ):
        require_once(driver, token)

    require_once(
        driver,
        "\t0xd9, 0xd0, 0xc0, 0x1f, 0x00, 0x00, 0x00,",
    )
    required_semantics = (
        "sample->index == 3 && sample->value != sample->expected",
        'return "exact-stable";',
        '"expected_signature=d9,d0,c0 board_control_register=d3 "',
        '"board_control_expected=1f "',
        "CONFIG_I2C_MT65XX_CURIE_DIAGNOSTIC",
    )
    for token in required_semantics:
        require(token in driver, f"Curie lost semantic token {token!r}")
    for stale in (
        "(sample->value & 0x07) != 0x05",
        '"topology_mask=07 topology_expected=05 "',
        'return "topology-stable";',
        "mtk_i2c_fermi_",
        "fermi-run-native",
        "GEMINI_FERMI_NATIVE_DIAGNOSTIC",
    ):
        require(stale not in driver, f"Curie retains stale semantic {stale!r}")

    # The successor is intentionally a semantic-only patch. The complete
    # Fermi predecessor contract below proves the inherited fixed order,
    # prefills, FIFO/APDMA gates, counters, one-shot, and no-reset behavior.
    for forbidden in (
        "mtk_i2c_init_hw",
        "I2C_DMA_WARM_RST",
        "I2C_DMA_HARD_RST",
        "PAGE_CON",
        "debugfs_create_u",
    ):
        require(forbidden not in driver, f"Curie adds unsafe token {forbidden!r}")

    config_requirements = (
        'CONFIG_LOCALVERSION="-gemini-curie"',
        "# CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC is not set",
        "# CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC is not set",
        "CONFIG_I2C_MT65XX_CURIE_DIAGNOSTIC=y",
        "# CONFIG_I2C_CHARDEV is not set",
        "# CONFIG_REGULATOR_DA9211 is not set",
        "# CONFIG_MTK_MT6797_A72_POWER is not set",
        "maxcpus=8",
        "Gemini-L-Curie",
        "GEMINI_CURIE_20260728",
    )
    for token in config_requirements:
        require(token in config, f"Curie config lost {token!r}")
    require(
        "CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y" not in config,
        "Curie config enables Fermi",
    )

    curie_entries = entries(curie_series)
    fermi_entries = entries(fermi_series)
    canonical_entries = entries(canonical_series)
    require(
        curie_entries == fermi_entries + [co.CURIE_PATCH],
        "Curie series is not exact Fermi plus 0121",
    )
    require(len(curie_entries) == 110, "Curie series count changed")
    positions = [canonical_entries.index(entry) for entry in curie_entries]
    require(
        positions == sorted(positions) and len(set(positions)) == len(positions),
        "Curie series is not a canonical-order subsequence",
    )

    profiles = manifest["config"]["profiles"]  # type: ignore[index]
    require(isinstance(profiles, dict), "manifest profiles are not an object")
    curie = profiles.get(co.PROFILE)
    fermi = profiles.get(FERMI_PROFILE)
    require(isinstance(curie, dict), "Curie profile is absent")
    require(isinstance(fermi, dict), "Fermi profile is absent")
    require(curie.get("base") == "defconfig", "Curie base changed")
    require(curie.get("patch_series") == co.SERIES, "Curie series pin changed")
    fragments = curie.get("fragments")
    fermi_fragments = fermi.get("fragments")
    require(isinstance(fragments, list), "Curie fragments are absent")
    require(isinstance(fermi_fragments, list), "Fermi fragments are absent")
    require(
        fragments
        == fermi_fragments[:-1] + ["configs/gemini-i2c6-curie.fragment"],
        "Curie fragments are not exact Fermi base plus Curie policy",
    )
    validate_fermi_predecessor(manifest)


class CurieContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.patch = read_text(PATCH)
        cls.config = read_text(CONFIG)
        cls.curie_series = read_text(CURIE_SERIES)
        cls.fermi_series = read_text(FERMI_SERIES)
        cls.canonical_series = read_text(CANONICAL_SERIES)
        cls.manifest = json.loads(read_text(MANIFEST))

    def validate(
        self,
        *,
        patch: str | None = None,
        config: str | None = None,
        curie_series: str | None = None,
        manifest: dict[str, object] | None = None,
    ) -> None:
        validate_contract(
            patch if patch is not None else self.patch,
            config if config is not None else self.config,
            curie_series if curie_series is not None else self.curie_series,
            self.fermi_series,
            self.canonical_series,
            manifest if manifest is not None else self.manifest,
        )

    def test_production_contract(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.patch.encode()).hexdigest(),
            co.CURIE_PATCH_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(self.config.encode()).hexdigest(),
            co.CONFIG_FRAGMENT_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(self.curie_series.encode()).hexdigest(),
            co.SERIES_SHA256,
        )
        self.validate()

    def test_rejects_semantic_safety_and_attribution_mutations(self) -> None:
        mutations: list[tuple[str, dict[str, object]]] = [
            (
                "wrong-board-control",
                {
                    "patch": self.patch.replace(
                        "0xd9, 0xd0, 0xc0, 0x1f, 0x00, 0x00, 0x00",
                        "0xd9, 0xd0, 0xc0, 0x05, 0x00, 0x00, 0x00",
                        1,
                    )
                },
            ),
            (
                "masked-comparator",
                {
                    "patch": self.patch.replace(
                        "sample->index == 3 && sample->value != sample->expected",
                        "sample->index == 3 && "
                        "(sample->value & 0x07) != 0x05",
                        1,
                    )
                },
            ),
            (
                "stale-result-kind",
                {
                    "patch": self.patch.replace(
                        'return "exact-stable";',
                        'return "topology-stable";',
                        1,
                    )
                },
            ),
            (
                "ambiguous-read-symbol",
                {
                    "patch": self.patch.replace(
                        "#define mtk_i2c_quasar_read\t\tmtk_i2c_curie_read",
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
                "0121-not-selected",
                {
                    "curie_series": self.curie_series.replace(
                        co.CURIE_PATCH + "\n",
                        "",
                        1,
                    )
                },
            ),
        ]
        manifest_mutation = copy.deepcopy(self.manifest)
        manifest_mutation["config"]["profiles"][co.PROFILE]["patch_series"] = (  # type: ignore[index]
            "patches/series-fermi-i2c6-topology-fingerprint"
        )
        mutations.append(("manifest-reselects-fermi", {"manifest": manifest_mutation}))
        for name, kwargs in mutations:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.validate(**kwargs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
