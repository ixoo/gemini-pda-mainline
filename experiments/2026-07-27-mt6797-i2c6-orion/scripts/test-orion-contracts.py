#!/usr/bin/env python3
"""Static and modeled regression tests for Candidate Orion's fixed scope."""

from __future__ import annotations

import json
import pathlib
import re
import sys
import unittest

sys.dont_write_bytecode = True
import candidate_orion as co


ROOT = pathlib.Path(__file__).resolve().parents[3]
PROFILE_FRAGMENTS = (
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
    "configs/gemini-smp8.fragment",
    "configs/gemini-a72-observer.fragment",
    "configs/gemini-a72-observer-initcall-blacklist.fragment",
    "configs/gemini-dvfsp-handoff-owner.fragment",
    "configs/gemini-dvfsp-i2c6-consumer.fragment",
    co.CONFIG_FRAGMENT,
)


def text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def entries(relative: str) -> list[str]:
    return [
        line
        for line in text(relative).splitlines()
        if line and not line.startswith("#")
    ]


def added_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def packed_wrrd_length(tx_length: int, rx_length: int) -> int:
    if not tx_length or not rx_length or tx_length > 0xFF or rx_length > 0x1F:
        raise ValueError("unrepresentable packed WRRD length")
    return tx_length | (rx_length << 8)


def use_dma(tx_length: int, rx_length: int | None = None) -> bool:
    return tx_length > 8 or (rx_length is not None and rx_length > 8)


class OrionContracts(unittest.TestCase):
    maxDiff = None

    def test_input_pins(self) -> None:
        co.require_input_pins()
        for relative, wanted in zip(
            co.ORION_PATCHES, co.ORION_PATCH_SHA256, strict=True
        ):
            self.assertEqual(
                co.digest_path(ROOT / "patches" / relative),
                wanted,
                relative,
            )
        self.assertEqual(
            co.digest_path(ROOT / co.SERIES), co.SERIES_SHA256
        )
        self.assertEqual(
            co.digest_path(ROOT / co.CONFIG_FRAGMENT),
            co.CONFIG_FRAGMENT_SHA256,
        )

    def test_series_is_exact_baseline_plus_orion(self) -> None:
        baseline = entries(
            "patches/"
            "series-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve"
        )
        orion = entries(co.SERIES)
        self.assertEqual(orion, baseline + list(co.ORION_PATCHES))
        canonical = entries("patches/series")
        positions = [canonical.index(path) for path in co.ORION_PATCHES]
        self.assertEqual(positions, sorted(positions))

    def test_manifest_selects_only_named_orion_profile(self) -> None:
        manifest = json.loads(text("kernel/manifest.json"))
        profile = manifest["config"]["profiles"][co.PROFILE]
        self.assertEqual(
            profile,
            {
                "base": "defconfig",
                "patch_series": co.SERIES,
                "fragments": list(PROFILE_FRAGMENTS),
            },
        )

    def test_profile_is_fail_closed_and_has_no_arbitrary_i2cdev(self) -> None:
        fragment = set(text(co.CONFIG_FRAGMENT).splitlines())
        required = {
            'CONFIG_LOCALVERSION="-gemini-orion"',
            "CONFIG_DEBUG_FS=y",
            "CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC=y",
            "# CONFIG_I2C_CHARDEV is not set",
            "# CONFIG_REGULATOR_DA9211 is not set",
            "# CONFIG_MTK_MT6797_A72_POWER is not set",
        }
        self.assertTrue(required <= fragment)
        cmdline = next(
            line for line in fragment if line.startswith("CONFIG_CMDLINE=")
        )
        self.assertEqual(cmdline.count("maxcpus=8"), 1)
        self.assertNotIn("maxcpus=9", cmdline)
        self.assertIn("GEMINI_ORION_20260727", cmdline)

    def test_special_controller_does_not_change_ordinary_alias(self) -> None:
        patch = text(co.ORION_PATCHES[1].join(("patches/", "")))
        added = added_lines(patch)
        self.assertIn(
            '{ .compatible = "mediatek,mt6797-idvfs-i2c",', added
        )
        self.assertNotIn(
            '{ .compatible = "mediatek,mt6797-i2c", .data =',
            added,
        )
        self.assertIn(
            ".quirks = &mt6797_idvfs_i2c_quirks,", added
        )
        self.assertIn(
            "I2C_AQ_NO_ZERO_LEN | I2C_AQ_COMB_WRITE_THEN_READ", added
        )
        self.assertIn(".fifo_size = 8,", added)
        self.assertIn("I2C_WRRD_LEN_PACKED_8_5", added)
        self.assertIn("i2c->irq_stat & I2C_ARB_LOST", added)
        self.assertIn("i2c->irq_stat != I2C_TRANSAC_COMP", added)
        self.assertIn("writel(msgs->buf[i],", added)
        self.assertIn("rx_msg->buf[i] = (u8)readl(", added)
        self.assertNotIn("wmb();", added)

    def test_binding_uses_no_wrong_contract_fallback(self) -> None:
        patch = text("patches/" + co.ORION_PATCHES[0])
        added = added_lines(patch)
        self.assertIn("- const: mediatek,mt6797-idvfs-i2c", added)
        self.assertNotIn(
            "- const: mediatek,mt6577-i2c\n"
            "      - items:\n"
            "          - const: mediatek,mt6797-idvfs-i2c",
            added,
        )

    def test_packed_length_and_fifo_boundary_model(self) -> None:
        self.assertEqual(packed_wrrd_length(1, 1), 0x0101)
        self.assertEqual(packed_wrrd_length(0xFF, 0x1F), 0x1FFF)
        for lengths in ((0, 1), (1, 0), (0x100, 1), (1, 0x20)):
            with self.assertRaises(ValueError):
                packed_wrrd_length(*lengths)
        for tx_length, rx_length in ((1, 1), (8, 8)):
            self.assertFalse(use_dma(tx_length, rx_length))
        for tx_length, rx_length in ((9, 1), (1, 9), (9, 9)):
            self.assertTrue(use_dma(tx_length, rx_length))

    def test_dts_is_special_and_childless(self) -> None:
        patch = text(co.ORION_PATCHES[2].join(("patches/", "")))
        added = added_lines(patch)
        for compatible in co.I2C6_COMPATIBLE:
            self.assertIn(f'"{compatible}"', added)
        self.assertNotIn('"mediatek,mt6797-i2c"', added)
        self.assertNotIn('"mediatek,mt6577-i2c"', added)
        self.assertNotRegex(added, r"regulator@|da9214@|a72-power@")

    def test_diagnostic_surface_and_order_are_fixed(self) -> None:
        patch = text(co.ORION_PATCHES[3].join(("patches/", "")))
        added = added_lines(patch)
        mode_block = re.search(
            r"mtk_i2c_orion_modes\[.*?\] = \{(.*?)\};",
            added,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(mode_block)
        assert mode_block is not None
        self.assertEqual(
            re.findall(r"MTK_I2C_ORION_MODE_[A-Z_]+", mode_block.group(1)),
            [
                "MTK_I2C_ORION_MODE_PACKED_FIFO",
                "MTK_I2C_ORION_MODE_PACKED_DMA",
                "MTK_I2C_ORION_MODE_AUX_DMA",
            ],
        )
        self.assertIn('memcmp(command, "run\\n", sizeof(command))', added)
        self.assertIn(
            'debugfs_create_file("orion-run-all", 0600,', added
        )
        self.assertIn("msgs[0].addr = 0x69;", added)
        self.assertIn("msgs[1].addr = 0x69;", added)
        self.assertIn("0x05, 0x06, 0x47", added)
        self.assertIn("0xa5, 0x5a, 0x3c", added)
        self.assertIn("msgs[0].len = 1;", added)
        self.assertIn("msgs[1].len = 1;", added)
        self.assertIn("i2c->orion.reset_pending = true;", added)
        self.assertIn("mtk_i2c_init_hw(i2c);", added)
        self.assertIn("transfer_attempts=%d dma_starts=%d", added)
        self.assertIn("nonzero_starts=%d irqs=%d", added)
        self.assertIn("i2c->orion.retries_before = i2c->adap.retries;", added)
        self.assertIn("i2c->adap.retries = 0;", added)
        self.assertIn(
            "i2c->adap.retries = i2c->orion.retries_before;", added
        )
        self.assertIn(
            "retries_before=%u retries_during=%u retries_after=%u", added
        )
        self.assertIn("goto out_unlock;", added)
        self.assertNotIn("OFFSET_TX_MEM_ADDR", added)
        self.assertNotIn("OFFSET_RX_MEM_ADDR", added)

    def test_candidate_proves_two_exact_dt_lineages(self) -> None:
        builder = text(
            "experiments/2026-07-27-mt6797-i2c6-orion/"
            "scripts/build-candidate-orion.sh"
        )
        self.assertEqual(builder.count('python3 "$dtb_lineage_validator"'), 1)
        self.assertIn('--cassini-package "$cassini_package"', builder)
        self.assertIn('--orion-package "$package"', builder)
        self.assertIn('--derived-dtb "$stage/$DTB_MEMBER"', builder)
        self.assertIn(
            "compiled_dtb_delta="
            "exact-cassini-compiled-plus-only-i2c6-compatible",
            builder,
        )
        self.assertIn(
            "boot_dtb_delta=exact-hubble-plus-only-i2c6-compatible", builder
        )
        self.assertIn("cross_lineage_i2c6_resource_contract=exact", builder)
        self.assertIn("dtb-lineage-validation.txt", builder)
        self.assertIn(
            "grep -c '^generated_utc=' "
            '"$stage/standard-package-validation.raw"',
            builder,
        )
        self.assertIn("grep -v '^generated_utc='", builder)


if __name__ == "__main__":
    unittest.main()
