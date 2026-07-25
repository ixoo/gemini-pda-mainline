#!/usr/bin/env python3
"""Focused mutation tests for Candidate AP package and PM-audit contracts."""

from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import ModuleType


sys.dont_write_bytecode = True


def load(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CandidateApPackageContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scripts = pathlib.Path(__file__).resolve().parent
        cls.repository = cls.scripts.parents[2]
        cls.validator = load(
            cls.scripts / "validate-package.py",
            "candidate_ap_test_package_validator",
        )
        cls.pm = load(
            cls.scripts / "validate-pm-audit-package.py",
            "candidate_ap_test_pm_package_validator",
        )
        cls.identity = load(
            cls.scripts / "candidate_ap.py",
            "candidate_ap_test_identity",
        )
        cls.boot = load(
            cls.scripts / "validate-boot.py",
            "candidate_ap_test_boot_validator",
        )
        cls.auditor = load(
            cls.scripts / "audit-compiled-handoff.py",
            "candidate_ap_test_compiled_handoff_auditor",
        )

    def patch_bytes(self) -> dict[str, bytes]:
        return {
            entry: (self.repository / "patches" / entry).read_bytes()
            for entry in (
                self.validator.PATCH_0099,
                self.validator.PATCH_0100,
                self.validator.PATCH_0101,
                self.validator.PATCH_0102,
            )
        }

    def fragments(self, *, pm: bool = False) -> dict[str, bytes]:
        paths = (
            self.pm.pm_fragments(self.validator)
            if pm
            else self.validator.FRAGMENTS
        )
        return {relative: (self.repository / relative).read_bytes() for relative in paths}

    def resolved_main_config(self) -> bytes:
        fragments = self.fragments()
        requested = self.validator.fragment_requests(fragments)
        for line in self.validator.REQUIRED_CONFIG:
            symbol = (
                line.split("=", 1)[0]
                if line.startswith("CONFIG_")
                else line[2:-11]
            )
            requested[symbol] = line
        for symbol in self.validator.MAIN_UNAVAILABLE_POWER_SYMBOLS:
            requested.pop(symbol, None)
        requested["CONFIG_SWAP"] = "CONFIG_SWAP=y"
        return (
            "\n".join(requested[symbol] for symbol in sorted(requested)) + "\n"
        ).encode()

    def resolved_pm_config(self) -> bytes:
        fragments = self.fragments(pm=True)
        requested = self.pm.fragment_requests(self.validator, fragments)
        required = {
            line
            for line in self.validator.REQUIRED_CONFIG
            if line != "# CONFIG_SUSPEND is not set"
        } | self.pm.REQUIRED_PM_CONFIG
        for line in required:
            symbol = (
                line.split("=", 1)[0]
                if line.startswith("CONFIG_")
                else line[2:-11]
            )
            requested[symbol] = line
        return (
            "\n".join(requested[symbol] for symbol in sorted(requested)) + "\n"
        ).encode()

    def test_series_is_exact_ao_plus_four_ap_patches(self) -> None:
        data = (self.repository / self.validator.SERIES_REL).read_bytes()
        entries = self.validator.series_entries(data)
        prefixes = [
            pathlib.PurePosixPath(entry).name.split("-", 1)[0] for entry in entries
        ]
        self.assertEqual(len(entries), 101)
        self.assertEqual(prefixes, self.validator.expected_patch_prefixes())
        self.assertEqual(
            entries[-4:],
            [
                self.validator.PATCH_0099,
                self.validator.PATCH_0100,
                self.validator.PATCH_0101,
                self.validator.PATCH_0102,
            ],
        )
        self.assertFalse(
            any(
                pathlib.PurePosixPath(entry).name.startswith(("0093-", "0096-"))
                for entry in entries
            )
        )

    def test_series_parser_rejects_duplicate_and_unsafe_entries(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.validator.series_entries(b"v7.1.3/a.patch\nv7.1.3/a.patch\n")
        for value in (
            b"../escape.patch\n",
            b"/absolute.patch\n",
            b"v7.1.3/not a patch.patch\n",
            b"v7.1.3/not-patch.txt\n",
        ):
            with self.assertRaisesRegex(ValueError, "unsafe"):
                self.validator.series_entries(value)

    def test_current_ap_patch_stack_passes_semantic_source_audit(self) -> None:
        self.validator.validate_ap_patch_semantics(self.patch_bytes())

    def test_source_audit_rejects_missing_explicit_device_link(self) -> None:
        patches = self.patch_bytes()
        patches[self.validator.PATCH_0100] = patches[
            self.validator.PATCH_0100
        ].replace(b"device_link_add(consumer, &supplier->dev,", b"removed_link_add(", 1)
        with self.assertRaisesRegex(ValueError, "device_link_add"):
            self.validator.validate_ap_patch_semantics(patches)

    def test_source_audit_rejects_missing_quietness_counter(self) -> None:
        patches = self.patch_bytes()
        patches[self.validator.PATCH_0101] = patches[
            self.validator.PATCH_0101
        ].replace(
            b"atomic_inc(&i2c->dma_start_count);",
            b"atomic_inc(&i2c->removed_counter);",
            1,
        )
        with self.assertRaisesRegex(ValueError, "dma_start_count"):
            self.validator.validate_ap_patch_semantics(patches)

    def test_source_audit_rejects_cleanup_oracle_drift(self) -> None:
        mutations = (
            (
                b"#define INFRACFG_INFRA1_PDN_STA\t\t0x094",
                b"#define INFRACFG_INFRA1_PDN_STA\t\t0x090",
            ),
            (
                b"#define INFRA_AP_DMA_GATED\t\tBIT(18)",
                b"#define INFRA_AP_DMA_GATED\t\tBIT(17)",
            ),
            (
                b"#define MT6797_DVFSP_CONSUMER_POST_COUNT\t32",
                b"#define MT6797_DVFSP_CONSUMER_POST_COUNT\t31",
            ),
            (
                b"#define MT6797_DVFSP_POST_DELAY_MIN_US\t1000",
                b"#define MT6797_DVFSP_POST_DELAY_MIN_US\t999",
            ),
            (
                b"#define MT6797_DVFSP_POST_DELAY_MAX_US\t1250",
                b"#define MT6797_DVFSP_POST_DELAY_MAX_US\t1251",
            ),
            (
                b"handoff->consumer_post_pcm_failures++;",
                b"handoff->consumer_post_pcm_ignored++;",
            ),
            (
                b"handoff->consumer_post_main_failures++;",
                b"handoff->consumer_post_main_ignored++;",
            ),
            (
                b"handoff->consumer_post_dma_invalid++;",
                b"handoff->consumer_post_dma_ignored++;",
            ),
            (
                b"handoff->consumer_post_dma_gated++;",
                b"handoff->consumer_post_dma_seen++;",
            ),
            (
                b"if (i + 1 < MT6797_DVFSP_CONSUMER_POST_COUNT)",
                b"if (i + 1 <= MT6797_DVFSP_CONSUMER_POST_COUNT)",
            ),
            (b"first_dma_gated = i;", b"first_dma_gated = i + 1;"),
            (
                b"!handoff->consumer_post_dma_invalid &&",
                b"handoff->consumer_post_dma_invalid &&",
            ),
        )
        original = self.patch_bytes()
        provider = original[self.validator.PATCH_0100]
        for old, new in mutations:
            with self.subTest(old=old):
                self.assertEqual(provider.count(old), 1)
                patches = dict(original)
                patches[self.validator.PATCH_0100] = provider.replace(
                    old, new, 1
                )
                with self.assertRaises(ValueError):
                    self.validator.validate_ap_patch_semantics(patches)

    def test_main_and_pm_config_input_identities_are_exact(self) -> None:
        main_fragments = self.fragments()
        pm_fragments = self.fragments(pm=True)
        self.assertEqual(
            self.validator.config_inputs_digest(
                self.validator.PROFILE, main_fragments
            ),
            self.validator.CONFIG_INPUTS_SHA256,
        )
        self.assertEqual(
            self.pm.config_inputs_digest(self.validator, pm_fragments),
            self.pm.PM_CONFIG_INPUTS_SHA256,
        )

    def test_main_config_pins_suspend_off_and_fw_devlink_rpm(self) -> None:
        fragments = self.fragments()
        config = self.resolved_main_config()
        self.validator.validate_resolved_config(config, fragments)
        text = config.decode()
        self.assertIn("# CONFIG_SUSPEND is not set\n", text)
        for symbol in self.validator.MAIN_UNAVAILABLE_POWER_SYMBOLS:
            self.assertNotIn(symbol, text)
        self.assertIn("fw_devlink=rpm", text)
        self.assertNotIn("fw_devlink=on", text)
        self.boot.validate_config(config)
        for symbol in sorted(self.validator.MAIN_UNAVAILABLE_POWER_SYMBOLS):
            with self.subTest(symbol=symbol):
                mutated = config + f"{symbol}=y\n".encode()
                with self.assertRaisesRegex(
                    ValueError, "unavailable power|disabled request"
                ):
                    self.validator.validate_resolved_config(mutated, fragments)
                with self.assertRaisesRegex(ValueError, "unavailable power"):
                    self.boot.validate_config(mutated)
        for disabled, enabled in (
            ("# CONFIG_SUSPEND is not set", "CONFIG_SUSPEND=y"),
            ("# CONFIG_CPU_IDLE is not set", "CONFIG_CPU_IDLE=y"),
        ):
            with self.subTest(enabled=enabled):
                mutated = config.replace(
                    f"{disabled}\n".encode(), f"{enabled}\n".encode(), 1
                )
                with self.assertRaises(ValueError):
                    self.validator.validate_resolved_config(mutated, fragments)
                with self.assertRaises(ValueError):
                    self.boot.validate_config(mutated)

    def test_pm_config_enables_only_compile_audit_sleep_policy(self) -> None:
        fragments = self.fragments(pm=True)
        config = self.resolved_pm_config()
        self.pm.validate_resolved_config(self.validator, config, fragments)
        lines = set(config.decode().splitlines())
        self.assertTrue(self.pm.REQUIRED_PM_CONFIG <= lines)
        self.assertFalse(self.pm.FORBIDDEN_PM_CONFIG & lines)
        optional_disabled = b"# CONFIG_ARCH_ARTPEC is not set\n"
        without_unavailable_optional = config.replace(optional_disabled, b"", 1)
        self.assertNotEqual(without_unavailable_optional, config)
        self.pm.validate_resolved_config(
            self.validator, without_unavailable_optional, fragments
        )
        with self.assertRaisesRegex(ValueError, "enabled disabled request"):
            self.pm.validate_resolved_config(
                self.validator,
                config.replace(
                    optional_disabled, b"CONFIG_ARCH_ARTPEC=y\n", 1
                ),
                fragments,
            )
        suspend_on = b"CONFIG_SUSPEND=y\n"
        without_requested_enabled = config.replace(suspend_on, b"", 1)
        self.assertNotEqual(without_requested_enabled, config)
        with self.assertRaisesRegex(ValueError, "lost fragment request"):
            self.pm.validate_resolved_config(
                self.validator, without_requested_enabled, fragments
            )
        hibernation_off = b"# CONFIG_HIBERNATION is not set\n"
        without_hibernation = config.replace(hibernation_off, b"", 1)
        with_hibernation = config.replace(
            hibernation_off, b"CONFIG_HIBERNATION=y\n", 1
        )
        with self.assertRaisesRegex(ValueError, "HIBERNATION"):
            self.pm.validate_resolved_config(
                self.validator, without_hibernation, fragments
            )
        with self.assertRaisesRegex(ValueError, "HIBERNATION"):
            self.pm.validate_resolved_config(
                self.validator, with_hibernation, fragments
            )

    def test_manifest_has_distinct_main_and_pm_profiles(self) -> None:
        data = (self.repository / "kernel/manifest.json").read_bytes()
        self.validator.validate_manifest_contract(data, "test manifest")
        self.pm.validate_manifest_contract(self.validator, data)

    def test_pm_package_is_one_fragment_larger_and_never_installable(self) -> None:
        self.assertEqual(
            self.pm.pm_fragments(self.validator),
            [*self.validator.FRAGMENTS, self.pm.PM_FRAGMENT],
        )
        self.assertEqual(
            self.pm.PM_PACKAGE_MEMBER_COUNT,
            self.validator.PACKAGE_MEMBER_COUNT + 1,
        )
        builder = (self.scripts / "build-candidate-ap.sh").read_text()
        rejection = (
            "PM-audit package is compile/link evidence only and must never be assembled"
        )
        self.assertIn('\\"build_profile\\": \\"$PM_AUDIT_PROFILE\\"', builder)
        self.assertIn(rejection, builder)
        self.assertLess(builder.index(rejection), builder.index("workdir=\"$(mktemp"))

    def test_analyzer_and_compiled_auditor_pins_are_distinct_and_fail_closed(self) -> None:
        analyzer = (
            self.repository
            / "experiments/2026-07-12-boot-contract-recovery/scripts"
            / "analyze-lk-boot-image.py"
        )
        auditor = self.scripts / "audit-compiled-handoff.py"
        actual = (
            self.identity.digest_path(analyzer),
            self.identity.digest_path(auditor),
        )
        pinned = (
            self.identity.ANALYZER_SHA256,
            self.identity.COMPILED_HANDOFF_AUDITOR_SHA256,
        )
        self.assertEqual(actual, pinned)
        self.assertNotEqual(*pinned)
        self.assertNotEqual(actual, tuple(reversed(pinned)))
        for changed in (
            ("0" * 64, pinned[1]),
            (pinned[0], "0" * 64),
        ):
            with self.subTest(changed=changed):
                self.assertNotEqual(actual, changed)
        self.assertEqual(
            self.validator.COMPILED_HANDOFF_AUDITOR_SHA256,
            self.identity.COMPILED_HANDOFF_AUDITOR_SHA256,
        )
        builder = (self.scripts / "build-candidate-ap.sh").read_text()
        self.assertIn(
            'require_source_hash "$analyzer" "$(candidate_value ANALYZER_SHA256)"',
            builder,
        )
        self.assertIn(
            '"$(candidate_value COMPILED_HANDOFF_AUDITOR_SHA256)"',
            builder,
        )

    def test_image_checks_pin_format_strings_not_runtime_values(self) -> None:
        markers = b"\n".join(self.validator.REQUIRED_IMAGE_MARKERS)
        self.assertIn(b"probe_attempts=%d init_attempts=%d", markers)
        self.assertIn(b"suspend_checks=%d suspend_failures=%d", markers)
        self.assertIn(b"runtime_pm_link=%d", markers)
        self.assertNotIn(b"probe_attempts=1 init_attempts=1", markers)

    def test_compiled_auditor_pins_fully_inlined_transfer_geometry(self) -> None:
        transfer = self.auditor.Region(
            self.auditor.Symbol(0x1000, "t", "mtk_i2c_transfer"),
            0x1000 + 542 * 4,
            (0xD503201F,) * 542,
        )
        calls = [
            (10, "i2c_get_dma_safe_msg_buf"),
            (11, "dma_map_single_attrs"),
            (20, "i2c_get_dma_safe_msg_buf"),
            (21, "dma_map_single_attrs"),
            (30, "i2c_get_dma_safe_msg_buf"),
            (31, "dma_map_single_attrs"),
            (40, "i2c_get_dma_safe_msg_buf"),
            (41, "dma_map_single_attrs"),
            *[(50 + index, "mtk_i2c_writew") for index in range(14)],
            (70, "wait_for_completion_timeout"),
            (71, "mtk_i2c_writew"),
            (80, "mtk_i2c_init_hw"),
            (90, "mtk_i2c_init_hw"),
        ]
        self.auditor.audit_inlined_i2c_transfer([], transfer, calls)

        out_of_line = [
            self.auditor.Symbol(0x1000, "t", "mtk_i2c_do_transfer.constprop.0")
        ]
        with self.assertRaisesRegex(ValueError, "fully inlined"):
            self.auditor.audit_inlined_i2c_transfer(
                out_of_line, transfer, calls
            )
        short_transfer = self.auditor.Region(
            transfer.symbol, transfer.end - 4, transfer.words[:-1]
        )
        with self.assertRaisesRegex(ValueError, "region geometry"):
            self.auditor.audit_inlined_i2c_transfer(
                [], short_transfer, calls
            )
        with self.assertRaisesRegex(ValueError, "dma_map_single_attrs"):
            self.auditor.audit_inlined_i2c_transfer(
                [],
                transfer,
                [item for item in calls if item != (41, "dma_map_single_attrs")],
            )
        reordered = [
            (9, name) if index == 11 else (index, name)
            for index, name in calls
        ]
        with self.assertRaisesRegex(ValueError, "call order"):
            self.auditor.audit_inlined_i2c_transfer(
                [], transfer, reordered
            )

    def test_compiled_auditor_follows_cfg_not_linear_call_layout(self) -> None:
        nop = 0xD503201F
        words = [nop] * 11
        words[2] = 0x14000004
        words[7] = 0x17FFFFFC
        words[4] = 0x14000004
        item = self.auditor.Region(
            self.auditor.Symbol(0x1000, "t", "test_region"),
            0x1000 + len(words) * 4,
            tuple(words),
        )
        self.auditor.require_cfg_sequence(item, [1, 6, 3, 8], "test")
        broken = list(words)
        broken[2] = nop
        broken_item = self.auditor.Region(
            item.symbol, item.end, tuple(broken)
        )
        with self.assertRaisesRegex(ValueError, "CFG sequence"):
            self.auditor.require_cfg_sequence(
                broken_item, [1, 6, 3, 8], "test"
            )

    @unittest.skipUnless(shutil.which("dtc"), "dtc is required")
    def test_package_dtb_accepts_unique_non_0x2c_access_phandle(self) -> None:
        dts = """/dts-v1/;
/ {
	#address-cells = <2>;
	#size-cells = <2>;
	cpus {
		#address-cells = <1>;
		#size-cells = <0>;
		cpu@200 {
			device_type = "cpu";
			reg = <0x200>;
			enable-method = "mediatek,mt6797-psci";
		};
		cpu@201 {
			device_type = "cpu";
			reg = <0x201>;
			enable-method = "mediatek,mt6797-psci";
		};
	};
	infrasys: syscon@10001000 {
		compatible = "mediatek,mt6797-infracfg", "syscon";
		reg = <0 0x10001000 0 0x1000>;
		phandle = <0x17>;
		#clock-cells = <1>;
	};
	handoff: dvfsp-handoff@11015000 {
		compatible = "mediatek,mt6797-dvfsp-handoff";
		reg = <0 0x11015000 0 0x1000>;
		clocks = <&infrasys 0x36>;
		clock-names = "i2c";
		mediatek,infracfg = <&infrasys>;
		#access-controller-cells = <0>;
		phandle = <0x31>;
		status = "okay";
	};
	i2c@1100e000 {
		compatible = "mediatek,mt6797-i2c";
		reg = <0 0x1100e000 0 0x1000>;
		#address-cells = <1>;
		#size-cells = <0>;
		access-controllers = <&handoff>;
		status = "okay";
	};
};
"""
        with tempfile.TemporaryDirectory(prefix="candidate-ap-dtb-") as temporary:
            root = pathlib.Path(temporary)
            source = root / "fixture.dts"
            output = root / "fixture.dtb"
            source.write_text(dts, encoding="ascii")
            subprocess.run(
                ["dtc", "-q", "-I", "dts", "-O", "dtb", "-o", output, source],
                check=True,
            )
            self.validator.validate_package_dtb(output)


if __name__ == "__main__":
    unittest.main()
