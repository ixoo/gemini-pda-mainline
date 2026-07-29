#!/usr/bin/env python3
"""Focused source and package-contract mutation tests for Cassini."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
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


def expect_rejection(callable_object, label: str) -> None:
    try:
        callable_object()
    except ValueError:
        return
    raise ValueError(f"mutation was accepted: {label}")


def main() -> int:
    try:
        scripts = pathlib.Path(__file__).resolve().parent
        repository = scripts.parents[2]
        identity = load(scripts / "candidate_cassini.py", "candidate_cassini")
        probe = load(
            scripts / "validate-cassini-probe.py",
            "cassini_probe_mutation_validator",
        )
        package = load(
            scripts / "validate-package-cassini.py",
            "cassini_package_mutation_validator",
        )
        initramfs = load(
            scripts / "validate-cassini-initramfs.py",
            "cassini_initramfs_mutation_validator",
        )
        installer = load(
            scripts / "derive-installer.py",
            "cassini_installer_mutation_validator",
        )

        manifest = json.loads(
            (repository / "kernel/manifest.json").read_text(encoding="utf-8")
        )
        profile = manifest["config"]["profiles"][identity.PROFILE]
        if (
            profile["base"] != "defconfig"
            or profile["patch_series"] != identity.SERIES
            or profile["fragments"] != list(package.FRAGMENTS)
        ):
            raise ValueError("current Cassini manifest profile is not exact")
        series = (repository / identity.SERIES).read_bytes()
        entries = package.series_entries(series)
        if len(entries) != 102 or identity.digest_path(
            repository / identity.SERIES
        ) != identity.SERIES_SHA256:
            raise ValueError("current Cassini series identity is not exact")

        source_path = (
            repository
            / "experiments/2026-07-27-da9214-direct-address-cassini/"
            "initramfs/cassini-probe.c"
        )
        source = source_path.read_bytes()
        probe.audit_source(source)
        source_mutations = (
            (b"#define CASSINI_I2C_ADDR 0x69U",
             b"#define CASSINI_I2C_ADDR 0x68U"),
            (b"#define CASSINI_PASSES 2U", b"#define CASSINI_PASSES 3U"),
            (b"0x05U, 0x06U, 0x47U", b"0x00U, 0x06U, 0x47U"),
            (b"0xd9U, 0xd0U, 0xc0U", b"0xd9U, 0xd0U, 0xc1U"),
            (b".flags = CASSINI_I2C_M_RD", b".flags = 0U"),
            (b"if (argc != 1)", b"if (argc < 1)"),
            (
                b"GEMINI_CASSINI_TRANSACTION_BEGIN",
                b"GEMINI_CASSINI_TRANSACTION_SKIPPED",
            ),
            (b"CASSINI_I2C_RDWR, &request", b"0x0703UL, &request"),
            (
                b"errno = 0;\n\t\tentry = readdir(directory);",
                b"entry = readdir(directory);",
            ),
            (
                b'if (dprintf(kmsg_fd, "<6>%s\\n", line) != length + 4)',
                b'if (printf("%s\\n", line) != length + 4)',
            ),
            (
                b"GEMINI_CASSINI_PROBE_FAIL stage=kmsg-open transactions=0",
                b"GEMINI_CASSINI_PROBE_FAIL stage=kmsg-optional transactions=0",
            ),
        )
        source_rejections = 0
        for old, new in source_mutations:
            if source.count(old) != 1:
                raise ValueError(f"source mutation token count changed: {old!r}")
            mutated = source.replace(old, new, 1)
            expect_rejection(
                lambda data=mutated: probe.audit_source(data),
                old.decode("ascii", errors="replace"),
            )
            source_rejections += 1
        mutated = source.replace(
            b"if (!emit_marker(", b"if (emit_marker(", 1
        )
        expect_rejection(
            lambda data=mutated: probe.audit_source(data),
            "unchecked durable marker",
        )
        source_rejections += 1

        config = ("\n".join(sorted(package.REQUIRED_CONFIG)) + "\n").encode()
        package.validate_config(config)
        config_mutations = (
            (
                b"CONFIG_I2C_CHARDEV=y",
                b"# CONFIG_I2C_CHARDEV is not set",
            ),
            (b"maxcpus=8", b"maxcpus=9"),
            (b"Gemini-L-Cassini", b"Gemini-L-Pioneer"),
            (
                b"initcall_blacklist=mt6797_a72_power_driver_init",
                b"initcall_blacklist=none",
            ),
            (
                b"CONFIG_PSTORE_CONSOLE=y",
                b"# CONFIG_PSTORE_CONSOLE is not set",
            ),
            (
                b"# CONFIG_MMC is not set",
                b"CONFIG_MMC=y",
            ),
            (
                b"# CONFIG_CPU_FREQ is not set",
                b"CONFIG_CPU_FREQ=y",
            ),
            (
                b"CONFIG_IKCONFIG_PROC=y",
                b"# CONFIG_IKCONFIG_PROC is not set",
            ),
            (
                b"CONFIG_MTK_MT6797_DVFSP_HANDOFF=y",
                b"# CONFIG_MTK_MT6797_DVFSP_HANDOFF is not set",
            ),
        )
        config_rejections = 0
        for old, new in config_mutations:
            if config.count(old) != 1:
                raise ValueError(f"config mutation token count changed: {old!r}")
            mutated = config.replace(old, new, 1)
            expect_rejection(
                lambda data=mutated: package.validate_config(data),
                old.decode("ascii"),
            )
            config_rejections += 1

        symbols = sorted(package.REQUIRED_SYMBOLS)
        system_map = "".join(
            f"{index + 1:016x} T {symbol}\n"
            for index, symbol in enumerate(symbols)
        ).encode()
        package.validate_system_map(system_map)
        symbol_rejections = 0
        for symbol in (
            "mt6797_a72_power_retry_cpu8",
            "mt6797_a72_power_prepare_first",
            "da9214_read_legacy_page2_reg",
        ):
            mutated = system_map + f"ffffffffffffffff T {symbol}\n".encode()
            expect_rejection(
                lambda data=mutated: package.validate_system_map(data), symbol
            )
            symbol_rejections += 1

        cmdline = package.KERNEL_CMDLINE.removeprefix(
            'CONFIG_CMDLINE="'
        ).removesuffix('"').encode("ascii")
        image = b"\0".join(
            (
                cmdline,
                cmdline,
                b"CPU%u boot rejected: A72 power sequence inactive",
                *package.REQUIRED_IMAGE_MARKERS,
            )
        )
        package.validate_image(image)
        image_marker_rejections = 0
        for marker in package.REQUIRED_IMAGE_MARKERS:
            expect_rejection(
                lambda value=image.replace(marker, b"", 1): (
                    package.validate_image(value)
                ),
                repr(marker),
            )
            image_marker_rejections += 1

        for unsafe in (
            b"../escape.patch\n",
            b"/absolute.patch\n",
            b"v7.1.3/not a patch.patch\n",
            b"v7.1.3/a.patch\nv7.1.3/a.patch\n",
        ):
            expect_rejection(
                lambda data=unsafe: package.series_entries(data),
                repr(unsafe),
            )

        provenance_rejections = 0
        with tempfile.TemporaryDirectory(prefix="cassini-provenance-test.") as raw:
            temporary = pathlib.Path(raw)
            synthetic_package = temporary / "package"
            packaged_configs = synthetic_package / "provenance/configs"
            packaged_configs.mkdir(parents=True)
            for relative in package.FRAGMENTS:
                (packaged_configs / pathlib.PurePosixPath(relative).name).write_bytes(
                    (repository / relative).read_bytes()
                )
            package.validate_fragment_provenance(
                repository, synthetic_package
            )
            first_fragment = (
                packaged_configs
                / pathlib.PurePosixPath(package.FRAGMENTS[0]).name
            )
            original_fragment = first_fragment.read_bytes()
            first_fragment.write_bytes(original_fragment + b"\nmutation\n")
            expect_rejection(
                lambda: package.validate_fragment_provenance(
                    repository, synthetic_package
                ),
                "changed packaged fragment",
            )
            provenance_rejections += 1
            first_fragment.write_bytes(original_fragment)
            (packaged_configs / "extra.fragment").write_text(
                "CONFIG_EXTRA=y\n", encoding="ascii"
            )
            expect_rejection(
                lambda: package.validate_fragment_provenance(
                    repository, synthetic_package
                ),
                "extra packaged fragment",
            )
            provenance_rejections += 1

            synthetic_patch_package = temporary / "patch-package"
            packaged_patches = (
                synthetic_patch_package / "provenance/patches/v7.1.3"
            )
            packaged_patches.mkdir(parents=True)
            first_entry = entries[0]
            first_patch = packaged_patches / pathlib.PurePosixPath(
                first_entry
            ).name
            original_patch = (repository / "patches" / first_entry).read_bytes()
            first_patch.write_bytes(original_patch)
            package.validate_patch_provenance(
                repository, synthetic_patch_package, [first_entry]
            )
            first_patch.write_bytes(original_patch + b"\nmutation\n")
            expect_rejection(
                lambda: package.validate_patch_provenance(
                    repository, synthetic_patch_package, [first_entry]
                ),
                "changed packaged patch",
            )
            provenance_rejections += 1
            first_patch.unlink()
            first_patch.symlink_to(repository / "patches" / first_entry)
            expect_rejection(
                lambda: package.validate_patch_provenance(
                    repository, synthetic_patch_package, [first_entry]
                ),
                "symlink packaged patch",
            )
            provenance_rejections += 1

        directory = initramfs.Member(
            0o040755, 0, 0, 2, 0, 0, 0, 0, 0, b""
        )
        repacked_directory = initramfs.Member(
            0o040755, 0, 0, 3, 0, 0, 0, 0, 0, b""
        )
        if not initramfs.inherited_member_equal(directory, repacked_directory):
            raise ValueError("directory-only nlink normalization was rejected")
        changed_directory_mode = initramfs.Member(
            0o040777, 0, 0, 3, 0, 0, 0, 0, 0, b""
        )
        if initramfs.inherited_member_equal(directory, changed_directory_mode):
            raise ValueError("directory mode mutation was accepted")
        init_member = initramfs.Member(
            0o100755, 0, 0, 1, 0, 0, 0, 0, 0, b"exact-init"
        )
        changed_init = initramfs.Member(
            0o100755, 0, 0, 1, 0, 0, 0, 0, 0, b"changed-init"
        )
        if initramfs.inherited_member_equal(init_member, changed_init):
            raise ValueError("inherited /init byte mutation was accepted")

        with tempfile.TemporaryDirectory(prefix="cassini-installer-test.") as raw:
            ao_source = installer.reconstruct_ao(
                pathlib.Path(raw)
            ).read_text(encoding="utf-8", errors="strict")
        calibration = installer.Calibration(
            "1" * 64,
            "7389000",
            "2" * 64,
            "3" * 64,
        )
        derived_installer = installer.derive_text(ao_source, calibration)
        installer.audit_power_policy(derived_installer)
        installer_mutations = (
            ("battery_capacity >= 81", "battery_capacity >= 80"),
            ("battery_capacity <= 100", "battery_capacity <= 101"),
            ('[[ "$battery_present" == 1 ]]', '[[ "$battery_present" != 0 ]]'),
            ('[[ "$battery_health" == Good ]]', '[[ -n "$battery_health" ]]'),
            (
                "check_cassini_battery_immediately_before_write\n"
                '\tprewrite_target_sha256="$(sha256sum "$target"',
                '\tprewrite_target_sha256="$(sha256sum "$target"',
            ),
            ("external_power_required=no", "external_power_required=yes"),
        )
        installer_rejections = 0
        for old, new in installer_mutations:
            if derived_installer.count(old) != 1:
                raise ValueError(
                    f"installer mutation token count changed: {old!r}"
                )
            mutated_installer = derived_installer.replace(old, new, 1)
            expect_rejection(
                lambda text=mutated_installer: installer.audit_power_policy(text),
                old,
            )
            installer_rejections += 1

        print("validation=cassini-source-package-contract-mutations")
        print("manifest_profile=exact")
        print("patch_series=exact-102-entry-childless-i2c6")
        print(f"source_mutations_rejected={source_rejections}")
        print(f"config_mutations_rejected={config_rejections}")
        print(f"forbidden_symbol_mutations_rejected={symbol_rejections}")
        print(f"image_marker_mutations_rejected={image_marker_rejections}")
        print(f"installer_power_mutations_rejected={installer_rejections}")
        print("unsafe_series_mutations_rejected=4")
        print(f"provenance_mutations_rejected={provenance_rejections}")
        print("directory_nlink_only_delta=accepted")
        print("directory_mode_mutation=rejected")
        print("inherited_init_byte_mutation=rejected")
        print("page_con_register_0x00_mutation=rejected")
        print("transaction_begin_marker_mutation=rejected")
        return 0
    except (KeyError, OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
