#!/usr/bin/env python3
"""Static and mutation contracts for Quasar's package validator."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPOSITORY = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import candidate_quasar as co

SPEC = importlib.util.spec_from_file_location(
    "quasar_package_validator_test",
    SCRIPT_DIR / "validate-package-quasar.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Quasar package validator")
vp = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = vp
SPEC.loader.exec_module(vp)


def synthetic_config() -> bytes:
    return ("\n".join(sorted(vp.REQUIRED_CONFIG)) + "\n").encode("ascii")


def synthetic_system_map() -> bytes:
    return (
        "".join(
            f"ffff00000000{index:04x} T {symbol}\n"
            for index, symbol in enumerate(sorted(vp.REQUIRED_SYMBOLS))
        )
    ).encode("ascii")


class QuasarPackageContracts(unittest.TestCase):
    def test_exact_profile_series_and_patch_identity(self) -> None:
        vp.validate_patch_pins(REPOSITORY)
        series = vp.regular(REPOSITORY / co.SERIES, "Quasar series")
        entries = vp.series_entries(series)
        self.assertEqual(len(entries), 108)
        self.assertEqual(tuple(entries[-6:]), co.QUASAR_PATCHES)
        self.assertEqual(vp.digest(series), co.SERIES_SHA256)
        self.assertEqual(
            vp.digest(
                vp.regular(
                    REPOSITORY / "patches" / co.QUASAR_PATCH,
                    "Quasar patch",
                )
            ),
            co.QUASAR_PATCH_SHA256,
        )

    def test_config_accepts_exact_and_rejects_identity_mutations(self) -> None:
        config = synthetic_config()
        vp.validate_config(config)
        mutations = (
            config.replace(
                b"CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=y\n",
                b"# CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC is not set\n",
                1,
            ),
            config.replace(
                b"# CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC is not set\n",
                b"CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC=y\n",
                1,
            ),
            config.replace(b"maxcpus=8", b"maxcpus=9", 1),
            config.replace(b"GEMINI_QUASAR_20260727", b"GEMINI_WRONG", 1),
            config.replace(
                b"# CONFIG_REGULATOR_DA9211 is not set\n",
                b"CONFIG_REGULATOR_DA9211=y\n",
                1,
            ),
            config.replace(
                b"# CONFIG_MTK_MT6797_A72_POWER is not set\n",
                b"CONFIG_MTK_MT6797_A72_POWER=y\n",
                1,
            ),
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(ValueError):
                    vp.validate_config(mutated)

    def test_system_map_rejects_missing_or_forbidden_symbols(self) -> None:
        system_map = synthetic_system_map()
        vp.validate_system_map(system_map)
        missing = system_map.replace(b" T mtk_i2c_quasar_write\n", b" T changed\n", 1)
        with self.assertRaises(ValueError):
            vp.validate_system_map(missing)
        for forbidden in sorted(vp.FORBIDDEN_SYMBOLS):
            with self.subTest(forbidden=forbidden):
                mutated = system_map + f"ffff000000ffffff T {forbidden}\n".encode()
                with self.assertRaises(ValueError):
                    vp.validate_system_map(mutated)

    def test_image_accepts_exact_markers_and_rejects_orion(self) -> None:
        command = vp.KERNEL_CMDLINE.removeprefix(
            'CONFIG_CMDLINE="'
        ).removesuffix('"').encode("ascii")
        required = (
            b"GEMINI_QUASAR_NATIVE_DIAGNOSTIC state=ready",
            b"GEMINI_QUASAR_DIAGNOSTIC_GATE missing DVFSP handoff",
            b"GEMINI_QUASAR_DIAGNOSTIC_GATE target node unavailable",
            b"GEMINI_QUASAR_DIAGNOSTIC_GATE node identity mismatch",
            b"GEMINI_QUASAR_DIAGNOSTIC_GATE adapter debugfs unavailable",
            b"GEMINI_QUASAR_DIAGNOSTIC_GATE debugfs creation failed",
            b"quasar-run-native",
            b"candidate=Quasar state=%s one_shot=%s",
            b"forced_length_mode=none forced_engine=none reset_pending=0",
            b"CPU%u boot rejected: A72 power sequence inactive",
        )
        image = b"\0".join((command, command, *required))
        vp.validate_image(image)
        for marker in required:
            with self.subTest(missing=marker):
                with self.assertRaises(ValueError):
                    vp.validate_image(image.replace(marker, b"changed", 1))
        for forbidden in (
            b"orion-run-all",
            b"GEMINI_ORION_DIAGNOSTIC state=ready",
            b"modes=packed-fifo,packed-dma,aux-dma",
        ):
            with self.subTest(forbidden=forbidden):
                with self.assertRaises(ValueError):
                    vp.validate_image(image + b"\0" + forbidden)

    def test_package_checksum_manifest_is_canonical_and_exact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="quasar-package-manifest.") as raw:
            root = pathlib.Path(raw)
            member = root / "Image"
            member.write_bytes(b"synthetic Quasar Image")
            wanted = hashlib.sha256(member.read_bytes()).hexdigest()
            manifest = root / "SHA256SUMS"
            manifest.write_text(f"{wanted}  ./Image\n", encoding="ascii")
            vp.validate_package_manifest(root)
            mutations = (
                f"{'0' * 64}  ./Image\n",
                f"{wanted}  ../Image\n",
                f"{wanted} *./Image\n",
                f"{wanted}  ./Image\n{wanted}  ./Image\n",
            )
            for index, text in enumerate(mutations, 1):
                with self.subTest(mutation=index):
                    manifest.write_text(text, encoding="ascii")
                    with self.assertRaises((OSError, ValueError)):
                        vp.validate_package_manifest(root)


if __name__ == "__main__":
    unittest.main()
