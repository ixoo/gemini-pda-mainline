#!/usr/bin/env python3
"""Focused synthetic tests for the Candidate AO package validators."""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from types import ModuleType
from typing import Any


sys.dont_write_bytecode = True

# Literal outputs of scripts/kernel's source_state_hash/build_state_hash for the
# pinned AO inputs; keep these independent of the validator implementation.
EXPECTED_SOURCE_STATE_SHA256 = (
    "27788c43475aa4563b5dc493f4005173bc7ade5ffb2db633212ce3102f060dd7"
)
EXPECTED_BUILD_STATE_SHA256 = (
    "1d28a9167e515c529b0bd4fa7b9687ee6edab6e54dc912d2f374efd24b8a647b"
)
EXPECTED_PACKAGE_REPORT_KEYS = {
    "validation",
    "package",
    "profile",
    "series_path",
    "patch_count",
    "series_sha256",
    "patchset_sha256",
    "series_entries",
    "patches_0093_0096",
    "config_inputs_sha256",
    "forced_cmdline",
    "handoff_owner_config",
    "handoff_owner_image_markers",
    "handoff_owner_system_map_symbols",
    "predecessor_observer_markers_symbols",
    "active_0093_markers_symbols",
    "compiled_reject_gate",
    "compiled_handoff",
    "package_dtb_i2c6",
    "package_dtb_handoff_owner",
    "package_dtb_handoff_clock",
    "package_dtb_role",
    "calibration_members",
    "calibration_dtbs",
    "calibration_package_manifest_sha256",
    "calibration_normalized_build_sha256",
    "calibration_config_sha256",
    "calibration_image_sha256",
    "calibration_image_size",
    "calibration_image_gz_sha256",
    "calibration_image_gz_size",
    "calibration_system_map_sha256",
    "calibration_compiled_gate_audit_sha256",
    "calibration_compiled_handoff_audit_sha256",
    "calibration_package_dtb_sha256",
    "output_hashes_pinned",
    "artifact_build",
    "device_access",
    "storage_access",
}


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CandidateAoPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scripts = pathlib.Path(__file__).resolve().parent
        cls.repository = cls.scripts.parents[2]
        cls.validator = load_module(
            cls.scripts / "validate-package.py",
            "candidate_ao_test_package_validator",
        )
        cls.reproduction = load_module(
            cls.scripts / "validate-package-reproduction.py",
            "candidate_ao_test_reproduction_validator",
        )
        cls.artifact_reproduction = load_module(
            cls.scripts / "validate-artifact-reproduction.py",
            "candidate_ao_test_artifact_reproduction",
        )
        if shutil.which("dtc") is None:
            raise unittest.SkipTest("dtc is required for the synthetic DT fixture")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="candidate-ao-package-")
        self.root = pathlib.Path(self.temporary.name)
        self.gate_report = b"".join(self.validator.REQUIRED_GATE_AUDIT_SEMANTICS)
        self.handoff_report = b"".join(
            self.validator.REQUIRED_HANDOFF_AUDIT_SEMANTICS
        )
        self.original_gate_validator = self.validator.validate_compiled_gate
        self.original_handoff_validator = (
            self.validator.validate_compiled_handoff
        )
        self.validator.validate_compiled_gate = lambda package: self.gate_report
        self.validator.validate_compiled_handoff = (
            lambda package: self.handoff_report
        )
        self.first = self.make_package(
            self.root / "first", "2026-07-24T11:00:00Z"
        )
        self.second = self.make_package(
            self.root / "second", "2026-07-24T11:01:00Z"
        )
        self.first_source, self.first_build = self.make_live_build(
            self.first, "first"
        )
        self.second_source, self.second_build = self.make_live_build(
            self.second, "second"
        )

    def tearDown(self) -> None:
        self.validator.validate_compiled_gate = self.original_gate_validator
        self.validator.validate_compiled_handoff = (
            self.original_handoff_validator
        )
        self.temporary.cleanup()

    @property
    def package_name(self) -> str:
        return (
            f"linux-7.1.3-gemini-{self.validator.PROFILE}-"
            f"{self.validator.PATCHSET_SHA256[:8]}-"
            f"{self.validator.CONFIG_INPUTS_SHA256[:8]}"
        )

    def make_directory(self, path: pathlib.Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        current = path
        while current != self.root and self.root in current.parents:
            current.chmod(self.validator.PACKAGE_DIRECTORY_MODE)
            current = current.parent

    def write_member(
        self, package: pathlib.Path, relative: str, data: bytes, mode: int
    ) -> None:
        path = package / relative
        self.make_directory(path.parent)
        path.write_bytes(data)
        path.chmod(mode)

    def resolved_config(self) -> bytes:
        fragments = {
            relative: (self.repository / relative).read_bytes()
            for relative in self.validator.FRAGMENTS
        }
        requested = self.validator.fragment_requests(fragments)
        for line in self.validator.REQUIRED_CONFIG:
            if line.startswith("CONFIG_"):
                symbol = line.split("=", 1)[0]
            else:
                symbol = line[2:-11]
            requested[symbol] = line
        return (
            "\n".join(requested[symbol] for symbol in sorted(requested)) + "\n"
        ).encode("utf-8")

    def synthetic_image(self, config: bytes) -> bytes:
        image = bytearray(64)
        for marker in self.validator.REQUIRED_IMAGE_MARKERS:
            image.extend(marker)
            image.extend(b"\0synthetic-separator\0")
        image.extend(self.validator.IKCONFIG_START)
        image.extend(gzip.compress(config, mtime=0))
        image.extend(self.validator.IKCONFIG_END)
        struct.pack_into("<3Q", image, 8, 0, len(image), 0x0A)
        image[56:60] = self.validator.ARM64_MAGIC
        return bytes(image)

    def synthetic_system_map(self) -> bytes:
        symbols = sorted(self.validator.REQUIRED_SYSTEM_MAP_SYMBOLS)
        return "".join(
            f"{0x40200000 + index * 4:016x} t {symbol}\n"
            for index, symbol in enumerate(symbols)
        ).encode("ascii")

    def synthetic_dtb(self, directory: pathlib.Path) -> bytes:
        source = directory / "fixture.dts"
        output = directory / "fixture.dtb"
        source.write_text(
            """/dts-v1/;

/ {
	#address-cells = <2>;
	#size-cells = <2>;

	cpus {
		#address-cells = <1>;
		#size-cells = <0>;
		cpu@200 {
			device_type = "cpu";
			compatible = "arm,cortex-a72";
			reg = <0x200>;
			enable-method = "mediatek,mt6797-psci";
		};
		cpu@201 {
			device_type = "cpu";
			compatible = "arm,cortex-a72";
			reg = <0x201>;
			enable-method = "mediatek,mt6797-psci";
		};
	};

	infrasys: syscon@10001000 {
		compatible = "mediatek,mt6797-infracfg", "syscon";
		reg = <0 0x10001000 0 0x1000>;
		#clock-cells = <1>;
	};

	i2c@1100e000 {
		compatible = "mediatek,mt6797-i2c";
		reg = <0 0x1100e000 0 0x1000>;
		#address-cells = <1>;
		#size-cells = <0>;
		status = "disabled";
		regulator@68 {
			compatible = "dlg,da9214";
			reg = <0x68>;
		};
	};

	a72-power@10222000 {
		compatible = "mediatek,mt6797-a72-power";
		reg = <0 0x10222000 0 0x1000>;
		status = "okay";
	};

	dvfsp-handoff@11015000 {
		compatible = "mediatek,mt6797-dvfsp-handoff";
		reg = <0 0x11015000 0 0x1000>;
		clocks = <&infrasys 0x36>;
		clock-names = "i2c";
		mediatek,infracfg = <&infrasys>;
		status = "okay";
	};
};
""",
            encoding="ascii",
        )
        subprocess.run(
            ["dtc", "-q", "-I", "dts", "-O", "dtb", "-o", output, source],
            check=True,
        )
        data = output.read_bytes()
        source.unlink()
        output.unlink()
        return data

    def rewrite_manifest(self, package: pathlib.Path) -> None:
        lines: list[str] = []
        for path in sorted(package.rglob("*")):
            if not path.is_file() or path.name == "SHA256SUMS":
                continue
            relative = path.relative_to(package).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  ./{relative}\n")
        manifest = package / "SHA256SUMS"
        manifest.write_text("".join(lines), encoding="ascii")
        manifest.chmod(self.validator.PACKAGE_GENERATED_FILE_MODE)

    def make_package(
        self, parent: pathlib.Path, generated_utc: str
    ) -> pathlib.Path:
        package = parent / self.package_name
        self.make_directory(package)

        repository_manifest = (self.repository / "kernel/manifest.json").read_bytes()
        series = (self.repository / self.validator.SERIES_REL).read_bytes()
        entries = self.validator.series_entries(series)
        for relative, data in (
            ("provenance/kernel-manifest.json", repository_manifest),
            ("provenance/series", series),
        ):
            self.write_member(
                package, relative, data, self.validator.PACKAGE_DEFAULT_FILE_MODE
            )
        for entry in entries:
            self.write_member(
                package,
                f"provenance/patches/{entry}",
                (self.repository / "patches" / entry).read_bytes(),
                self.validator.PACKAGE_DEFAULT_FILE_MODE,
            )
        for relative in self.validator.FRAGMENTS:
            self.write_member(
                package,
                f"provenance/configs/{pathlib.PurePosixPath(relative).name}",
                (self.repository / relative).read_bytes(),
                self.validator.PACKAGE_DEFAULT_FILE_MODE,
            )

        config = self.resolved_config()
        image = self.synthetic_image(config)
        system_map = self.synthetic_system_map()
        dtb = self.synthetic_dtb(parent)
        build: dict[str, Any] = {
            "schema": 1,
            "generated_utc": generated_utc,
            "kernel_release": self.validator.KERNEL_RELEASE,
            "build_profile": self.validator.PROFILE,
            "base_config": "defconfig",
            "config_fragments": self.validator.FRAGMENTS,
            "config_inputs_sha256": self.validator.CONFIG_INPUTS_SHA256,
            "source_sha256": self.validator.SOURCE_SHA256,
            "patchset_sha256": self.validator.PATCHSET_SHA256,
            "config_sha256": hashlib.sha256(config).hexdigest(),
            "modules_built": False,
            "compiler": self.validator.COMPILER,
            "linker": self.validator.LINKER,
        }
        for relative, data, mode in (
            ("Image", image, self.validator.PACKAGE_DEFAULT_FILE_MODE),
            (
                "Image.gz",
                gzip.compress(image, mtime=0),
                self.validator.PACKAGE_DEFAULT_FILE_MODE,
            ),
            ("kernel.config", config, self.validator.PACKAGE_DEFAULT_FILE_MODE),
            ("System.map", system_map, self.validator.PACKAGE_DEFAULT_FILE_MODE),
            (
                "provenance/build.json",
                (json.dumps(build, indent=2) + "\n").encode(),
                self.validator.PACKAGE_GENERATED_FILE_MODE,
            ),
            (
                self.validator.GEMINI_DTB,
                dtb,
                self.validator.PACKAGE_GENERATED_FILE_MODE,
            ),
        ):
            self.write_member(package, relative, data, mode)
        for number in range(self.validator.PACKAGE_DTB_COUNT - 1):
            self.write_member(
                package,
                f"dtbs/mediatek/synthetic-{number:03d}.dtb",
                dtb,
                self.validator.PACKAGE_GENERATED_FILE_MODE,
            )
        self.rewrite_manifest(package)
        self.assertEqual(
            len(self.validator.inventory(package)),
            self.validator.PACKAGE_MEMBER_COUNT,
        )
        return package

    def mutant(self, name: str, source: pathlib.Path | None = None) -> pathlib.Path:
        parent = self.root / f"mutant-{name}"
        package = parent / self.package_name
        shutil.copytree(source or self.first, package, copy_function=shutil.copy2)
        for directory in (parent, package):
            directory.chmod(self.validator.PACKAGE_DIRECTORY_MODE)
        return package

    def make_live_build(
        self, package: pathlib.Path, label: str
    ) -> tuple[pathlib.Path, pathlib.Path]:
        source = self.root / f"live-{label}-source"
        build = self.root / f"live-{label}-build"
        source.mkdir()
        build.mkdir()
        (source / ".gemini-source-state").write_text(
            self.reproduction.expected_source_state(self.validator) + "\n",
            encoding="ascii",
        )
        (build / ".gemini-build-state").write_text(
            self.reproduction.expected_build_state(self.validator) + "\n",
            encoding="ascii",
        )
        for member, relative in self.reproduction.LIVE_OUTPUTS.items():
            destination = build / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package / member, destination)
        live_dtbs = build / "arch/arm64/boot/dts/mediatek"
        live_dtbs.mkdir(parents=True, exist_ok=True)
        for path in (package / "dtbs/mediatek").glob("*.dtb"):
            shutil.copy2(path, live_dtbs / path.name)
        return source, build

    def make_link_artifact(
        self,
        package: pathlib.Path,
        calibration: dict[str, str | int],
        label: str,
    ) -> tuple[pathlib.Path, dict[str, tuple[int, str, int]]]:
        root = self.root / f"link-artifact-{label}"
        root.mkdir()
        for member in ("Image.gz", "System.map", "kernel.config"):
            shutil.copy2(package / member, root / member)
        build = self.validator.load_json(
            package / "provenance/build.json", f"{label} package build"
        )
        (root / "source-build.json").write_bytes(
            self.validator.normalized_build_bytes(build, f"{label} package build")
        )
        report = self.artifact_reproduction.expected_package_report(
            package, calibration, self.validator
        )
        self.assertEqual(set(report), EXPECTED_PACKAGE_REPORT_KEYS)
        (root / "package-validation.txt").write_text(
            "".join(f"{key}={value}\n" for key, value in report.items()),
            encoding="ascii",
        )
        members = {
            path.name: (
                path.stat().st_mode & 0o777,
                hashlib.sha256(path.read_bytes()).hexdigest(),
                path.stat().st_size,
            )
            for path in root.iterdir()
        }
        return root, members

    def assert_rejected(self, package: pathlib.Path) -> None:
        with self.assertRaises((OSError, RuntimeError, UnicodeError, ValueError)):
            self.validator.validate_package(self.repository, package)

    def test_positive_package_and_reproduction(self) -> None:
        first = self.validator.validate_package(self.repository, self.first)
        second = self.validator.validate_package(self.repository, self.second)
        members = self.reproduction.compare_packages(
            self.validator, self.first, self.second
        )
        entries = self.validator.series_entries(
            (self.repository / self.validator.SERIES_REL).read_bytes()
        )
        config = (self.first / "kernel.config").read_text(encoding="utf-8")
        symbols = (self.first / "System.map").read_text(encoding="ascii")
        self.assertEqual(len(entries), 97)
        self.assertEqual(self.validator.PACKAGE_MEMBER_COUNT, 236)
        self.assertIn("CONFIG_MTK_MT6797_DVFSP_HANDOFF=y\n", config)
        self.assertNotIn("CONFIG_MTK_MT6797_DVFSP_HANDOFF_OBSERVER", config)
        self.assertIn(" mt6797_dvfsp_handoff_probe\n", symbols)
        self.assertIn(" mt6797_dvfsp_late_work\n", symbols)
        self.assertEqual(first["image_sha256"], second["image_sha256"])
        self.assertEqual(
            first["compiled_handoff_audit_sha256"],
            hashlib.sha256(self.handoff_report).hexdigest(),
        )
        self.assertEqual(len(members), self.validator.PACKAGE_MEMBER_COUNT)

    def test_live_roots_link_exact_package_outputs(self) -> None:
        roots = {
            "first source": self.first_source,
            "first build": self.first_build,
            "first artifacts": self.first.parent,
            "second source": self.second_source,
            "second build": self.second_build,
            "second artifacts": self.second.parent,
        }
        self.reproduction.require_distinct_live_roots(roots)
        nested = self.first_source / "nested-root"
        nested.mkdir()
        overlapping = {**roots, "second source": nested}
        with self.assertRaisesRegex(ValueError, "alias or overlap"):
            self.reproduction.require_distinct_live_roots(overlapping)
        first = self.reproduction.validate_live_build(
            self.validator,
            self.first,
            self.first_source,
            self.first_build,
            self.first.parent,
            "first",
        )
        second = self.reproduction.validate_live_build(
            self.validator,
            self.second,
            self.second_source,
            self.second_build,
            self.second.parent,
            "second",
        )
        self.assertEqual(first, second)
        first_calibration, second_calibration, members, evidence = (
            self.reproduction.validate_reproduction(
                self.validator,
                self.repository,
                self.first,
                self.second,
                roots,
            )
        )
        for key in self.reproduction.REPRODUCED_CALIBRATION_KEYS:
            self.assertEqual(first_calibration[key], second_calibration[key])
        self.assertEqual(len(members), self.validator.PACKAGE_MEMBER_COUNT)
        self.assertEqual(
            evidence["source_state_sha256"], EXPECTED_SOURCE_STATE_SHA256
        )
        self.assertEqual(evidence["build_state_sha256"], EXPECTED_BUILD_STATE_SHA256)

    def test_expected_state_hashes_match_kernel_algorithm(self) -> None:
        self.assertEqual(
            self.reproduction.expected_source_state(self.validator),
            EXPECTED_SOURCE_STATE_SHA256,
        )
        self.assertEqual(
            self.reproduction.expected_build_state(self.validator),
            EXPECTED_BUILD_STATE_SHA256,
        )

    def test_live_roots_reject_state_and_artifact_root_discontinuity(self) -> None:
        source_state = self.first_source / ".gemini-source-state"
        source_state.write_text("0" * 64 + "\n", encoding="ascii")
        with self.assertRaisesRegex(ValueError, "source-state identity"):
            self.reproduction.validate_live_build(
                self.validator,
                self.first,
                self.first_source,
                self.first_build,
                self.first.parent,
                "first",
            )
        source_state.write_text(EXPECTED_SOURCE_STATE_SHA256 + "\n", encoding="ascii")

        build_state = self.first_build / ".gemini-build-state"
        build_state.write_text("0" * 64 + "\n", encoding="ascii")
        with self.assertRaisesRegex(ValueError, "build-state identity"):
            self.reproduction.validate_live_build(
                self.validator,
                self.first,
                self.first_source,
                self.first_build,
                self.first.parent,
                "first",
            )
        build_state.write_text(EXPECTED_BUILD_STATE_SHA256 + "\n", encoding="ascii")

        with self.assertRaisesRegex(ValueError, "exact child"):
            self.reproduction.validate_live_build(
                self.validator,
                self.first,
                self.first_source,
                self.first_build,
                self.second.parent,
                "first",
            )

    def test_live_roots_reject_output_and_dtb_discontinuity(self) -> None:
        (self.first_build / "arch/arm64/boot/Image.gz").write_bytes(
            b"changed-live-image"
        )
        with self.assertRaisesRegex(ValueError, "exact live build output"):
            self.reproduction.validate_live_build(
                self.validator,
                self.first,
                self.first_source,
                self.first_build,
                self.first.parent,
                "first",
            )
        shutil.copy2(
            self.first / "Image.gz",
            self.first_build / "arch/arm64/boot/Image.gz",
        )
        next(
            iter(
                (
                    self.first_build / "arch/arm64/boot/dts/mediatek"
                ).glob("*.dtb")
            )
        ).unlink()
        with self.assertRaisesRegex(ValueError, "DTB inventories differ"):
            self.reproduction.validate_live_build(
                self.validator,
                self.first,
                self.first_source,
                self.first_build,
                self.first.parent,
                "first",
            )

    def test_live_roots_reject_same_inventory_dtb_byte_change(self) -> None:
        live_dtb_root = self.first_build / "arch/arm64/boot/dts/mediatek"
        live_dtb = next(iter(live_dtb_root.glob("*.dtb")))
        live_dtb.write_bytes(live_dtb.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "exact live build output"):
            self.reproduction.validate_live_build(
                self.validator,
                self.first,
                self.first_source,
                self.first_build,
                self.first.parent,
                "first",
            )

    def test_artifact_link_rechecks_package_config_and_audits(self) -> None:
        calibration = self.validator.validate_package(self.repository, self.first)
        artifact, members = self.make_link_artifact(
            self.first, calibration, "positive"
        )
        self.artifact_reproduction.validate_package_link(
            artifact,
            members,
            self.first,
            calibration,
            self.validator,
            "first",
        )

        original = self.validator.validate_compiled_gate
        self.validator.validate_compiled_gate = lambda package: b"changed-gate-audit\n"
        try:
            with self.assertRaisesRegex(ValueError, "compiled_gate_audit_sha256"):
                self.artifact_reproduction.validate_package_link(
                    artifact,
                    members,
                    self.first,
                    calibration,
                    self.validator,
                    "first",
                )
        finally:
            self.validator.validate_compiled_gate = original

    def test_canonical_package_report_matches_validator_output(self) -> None:
        calibration = self.validator.validate_package(self.repository, self.first)
        output = io.StringIO()
        arguments = [
            "validate-package.py",
            "--repository",
            os.fspath(self.repository),
            "--package",
            os.fspath(self.first),
        ]
        original_arguments = sys.argv
        try:
            sys.argv = arguments
            with contextlib.redirect_stdout(output):
                self.assertEqual(self.validator.main(), 0)
        finally:
            sys.argv = original_arguments
        report = {}
        for line in output.getvalue().splitlines():
            key, separator, value = line.partition("=")
            self.assertTrue(separator)
            self.assertNotIn(key, report)
            report[key] = value
        report["calibration_package_manifest_sha256"] = (
            "validated-build-specific-generation-manifest"
        )
        self.assertEqual(
            report,
            self.artifact_reproduction.expected_package_report(
                self.first, calibration, self.validator
            ),
        )

    def test_artifact_link_rejects_normalized_build_discontinuity(self) -> None:
        calibration = self.validator.validate_package(self.repository, self.first)
        artifact, members = self.make_link_artifact(
            self.first, calibration, "build-discontinuity"
        )
        source_build = artifact / "source-build.json"
        source_build.write_bytes(source_build.read_bytes() + b" ")
        members["source-build.json"] = (
            source_build.stat().st_mode & 0o777,
            hashlib.sha256(source_build.read_bytes()).hexdigest(),
            source_build.stat().st_size,
        )
        with self.assertRaisesRegex(ValueError, "normalized build"):
            self.artifact_reproduction.validate_package_link(
                artifact,
                members,
                self.first,
                calibration,
                self.validator,
                "first",
            )

    def test_artifact_link_rejects_package_report_mutations(self) -> None:
        calibration = self.validator.validate_package(self.repository, self.first)
        artifact, members = self.make_link_artifact(
            self.first, calibration, "report-mutations"
        )
        report = self.artifact_reproduction.expected_package_report(
            self.first, calibration, self.validator
        )
        report_path = artifact / "package-validation.txt"

        mutations = {}
        missing = dict(report)
        del missing["series_path"]
        mutations["missing"] = (missing, "inventory changed")
        extra = {**report, "unexpected": "value"}
        mutations["extra"] = (extra, "inventory changed")
        changed = {**report, "package_dtb_i2c6": "enabled"}
        mutations["changed"] = (changed, "not linked: package_dtb_i2c6")

        for name, (mutant, diagnostic) in mutations.items():
            with self.subTest(name=name):
                report_path.write_text(
                    "".join(f"{key}={value}\n" for key, value in mutant.items()),
                    encoding="ascii",
                )
                with self.assertRaisesRegex(ValueError, diagnostic):
                    self.artifact_reproduction.validate_package_link(
                        artifact,
                        members,
                        self.first,
                        calibration,
                        self.validator,
                        "first",
                    )

    def test_rejects_forbidden_series_entry(self) -> None:
        package = self.mutant("series")
        series = package / "provenance/series"
        series.write_bytes(
            series.read_bytes()
            + b"v7.1.3/0093-soc-mediatek-enable-MT6797-A72-power-sequence.patch\n"
        )
        self.rewrite_manifest(package)
        self.assert_rejected(package)

    def test_rejects_i2c6_enablement(self) -> None:
        package = self.mutant("i2c6")
        subprocess.run(
            [
                "fdtput",
                "-t",
                "s",
                os.fspath(package / self.validator.GEMINI_DTB),
                self.validator.I2C6,
                "status",
                "okay",
            ],
            check=True,
        )
        self.rewrite_manifest(package)
        self.assert_rejected(package)

    def test_rejects_missing_handoff_owner_symbol(self) -> None:
        package = self.mutant("handoff-owner-symbol")
        system_map = package / "System.map"
        lines = [
            line
            for line in system_map.read_text(encoding="ascii").splitlines()
            if not line.endswith(" mt6797_dvfsp_handoff_probe")
        ]
        system_map.write_text("\n".join(lines) + "\n", encoding="ascii")
        self.rewrite_manifest(package)
        self.assert_rejected(package)

    def test_rejects_build_json_change_and_duplicate(self) -> None:
        package = self.mutant("build-field")
        build_path = package / "provenance/build.json"
        build = json.loads(build_path.read_text(encoding="utf-8"))
        build["compiler"] = "unexpected"
        build_path.write_text(json.dumps(build, indent=2) + "\n", encoding="utf-8")
        self.rewrite_manifest(package)
        self.assert_rejected(package)

        duplicate = self.mutant("build-duplicate")
        duplicate_path = duplicate / "provenance/build.json"
        original = duplicate_path.read_text(encoding="utf-8")
        duplicate_path.write_text(
            original.replace('"schema": 1,', '"schema": 1,\\n  "schema": 1,', 1),
            encoding="utf-8",
        )
        self.rewrite_manifest(duplicate)
        self.assert_rejected(duplicate)

    def test_rejects_mode_change(self) -> None:
        package = self.mutant("mode")
        (package / "Image").chmod(0o666)
        self.assert_rejected(package)

    def test_reproduction_rejects_substantive_difference(self) -> None:
        package = self.mutant("reproduction", self.second)
        system_map = package / "System.map"
        system_map.write_bytes(
            system_map.read_bytes() + b"0000000040201000 t harmless_extra_symbol\n"
        )
        self.rewrite_manifest(package)
        self.validator.validate_package(self.repository, package)
        with self.assertRaises(ValueError):
            self.reproduction.compare_packages(
                self.validator, self.first, package
            )


if __name__ == "__main__":
    unittest.main()
