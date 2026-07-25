#!/usr/bin/env python3
"""Focused synthetic tests for the Candidate AN package validators."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
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


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CandidateAnPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scripts = pathlib.Path(__file__).resolve().parent
        cls.repository = cls.scripts.parents[2]
        cls.validator = load_module(
            cls.scripts / "validate-package.py",
            "candidate_an_test_package_validator",
        )
        cls.reproduction = load_module(
            cls.scripts / "validate-package-reproduction.py",
            "candidate_an_test_reproduction_validator",
        )
        if shutil.which("dtc") is None:
            raise unittest.SkipTest("dtc is required for the synthetic DT fixture")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="candidate-an-package-")
        self.root = pathlib.Path(self.temporary.name)
        self.gate_report = b"".join(self.validator.REQUIRED_GATE_AUDIT_SEMANTICS)
        self.original_gate_validator = self.validator.validate_compiled_gate
        self.validator.validate_compiled_gate = lambda package: self.gate_report
        self.first = self.make_package(
            self.root / "first", "2026-07-24T11:00:00Z"
        )
        self.second = self.make_package(
            self.root / "second", "2026-07-24T11:01:00Z"
        )

    def tearDown(self) -> None:
        self.validator.validate_compiled_gate = self.original_gate_validator
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

	dvfsp-observer@11015000 {
		compatible = "mediatek,mt6797-dvfsp-handoff-observer";
		reg = <0 0x11015000 0 0x1000>;
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

    def assert_rejected(self, package: pathlib.Path) -> None:
        with self.assertRaises((OSError, RuntimeError, UnicodeError, ValueError)):
            self.validator.validate_package(self.repository, package)

    def test_positive_package_and_reproduction(self) -> None:
        first = self.validator.validate_package(self.repository, self.first)
        second = self.validator.validate_package(self.repository, self.second)
        members = self.reproduction.compare_packages(
            self.validator, self.first, self.second
        )
        self.assertEqual(first["image_sha256"], second["image_sha256"])
        self.assertEqual(len(members), self.validator.PACKAGE_MEMBER_COUNT)

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

    def test_rejects_missing_observer_symbol(self) -> None:
        package = self.mutant("symbol")
        system_map = package / "System.map"
        lines = [
            line
            for line in system_map.read_text(encoding="ascii").splitlines()
            if not line.endswith(" mt6797_dvfsp_observer_probe")
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
