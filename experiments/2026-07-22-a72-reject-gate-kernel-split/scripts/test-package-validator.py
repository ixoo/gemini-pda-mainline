#!/usr/bin/env python3
"""Exercise Candidate AI series and kernel-policy fail-closed boundaries."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import pathlib
import shutil
import struct
import sys
import tempfile

sys.dont_write_bytecode = True


def load_module(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(function: object, *args: object, **kwargs: object) -> None:
    try:
        function(*args, **kwargs)  # type: ignore[operator]
    except ValueError:
        return
    raise ValueError("mutation unexpectedly passed")


def copy_patch_tree(source: pathlib.Path, destination: pathlib.Path, entries: list[str]) -> None:
    for entry in entries:
        target = destination / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / entry, target)
    destination.chmod(0o775)
    for path in destination.rglob("*"):
        if path.is_dir():
            path.chmod(0o775)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[3],
    )
    args = parser.parse_args()
    repository = args.repository.resolve(strict=True)
    script_dir = pathlib.Path(__file__).resolve().parent
    validator = load_module(script_dir / "validate-package.py", "gemini_ai_package")
    series_validator = load_module(
        script_dir / "validate-series-selection.py", "gemini_ai_series"
    )

    current = (repository / "patches/series").read_bytes()
    ad_series = series_validator.derive_ad_series(current)
    ai_series = (repository / validator.AI_SERIES_REL).read_bytes()
    ad_entries = validator.series_entries(ad_series)
    ai_entries = validator.series_entries(ai_series)
    corrected_patch = (repository / "patches" / validator.PATCH_0092).read_bytes()
    rejected = 0

    synthetic_image = bytearray(4096)
    struct.pack_into("<3Q", synthetic_image, 8, 0x00200000, len(synthetic_image), 0x0A)
    synthetic_image[56:60] = b"ARM\x64"
    image_gz = gzip.compress(bytes(synthetic_image), mtime=0)
    if validator.decompress_lk_image_gz(image_gz, "synthetic Image.gz") != bytes(
        synthetic_image
    ):
        raise ValueError("positive single-member gzip fixture changed")
    for mutation in (
        image_gz + gzip.compress(b"second member", mtime=0),
        image_gz + b"trailing bytes",
    ):
        expect_rejected(
            validator.decompress_lk_image_gz,
            mutation,
            "mutated Image.gz",
        )
        rejected += 1
    bad_flags = bytearray(synthetic_image)
    struct.pack_into("<Q", bad_flags, 24, 0)
    for mutation in (
        gzip.compress(bytes(bad_flags), mtime=0),
        gzip.compress(
            b"\0" * (validator.LK_MT6797_DECOMPRESS_LIMIT + 1), mtime=0
        ),
    ):
        expect_rejected(
            validator.decompress_lk_image_gz,
            mutation,
            "mutated LK Image.gz",
        )
        rejected += 1

    manifest = json.loads((repository / "kernel/manifest.json").read_text())
    validator.validate_manifest_contract(
        (json.dumps(manifest) + "\n").encode(), "positive manifest", require_ai=True
    )
    manifest_mutations = []
    for operation in ("missing-path", "global-path", "unsafe-path", "fragment", "top-level"):
        mutation = copy.deepcopy(manifest)
        profile = mutation["config"]["profiles"][validator.PROFILE]
        if operation == "missing-path":
            del profile["patch_series"]
        elif operation == "global-path":
            profile["patch_series"] = validator.AD_SERIES_REL
        elif operation == "unsafe-path":
            profile["patch_series"] = "../series"
        elif operation == "fragment":
            profile["fragments"] = profile["fragments"][:-1]
        else:
            mutation["patch_series"] = validator.AI_SERIES_REL
        manifest_mutations.append((json.dumps(mutation) + "\n").encode())
    for mutation in manifest_mutations:
        expect_rejected(
            validator.validate_manifest_contract,
            mutation,
            "mutated manifest",
            require_ai=True,
        )
        rejected += 1

    with tempfile.TemporaryDirectory(prefix="candidate-ai-package-tests-") as raw:
        work = pathlib.Path(raw)
        mode_root = work / "package-mode-fixture"
        mode_members: dict[str, pathlib.Path] = {}
        for relative in (
            "Image",
            "SHA256SUMS",
            "dtbs/mediatek/mt6797-gemini-pda.dtb",
            "provenance/build.json",
            "provenance/patches/v7.1.3/0092-test.patch",
        ):
            path = mode_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture\n")
            path.chmod(validator.expected_package_file_mode(relative))
            mode_members[relative] = path
        validator.validate_package_file_modes(mode_members, "positive fixture")
        for relative in ("Image", "SHA256SUMS"):
            path = mode_members[relative]
            expected_mode = validator.expected_package_file_mode(relative)
            path.chmod(0o664 if expected_mode == 0o644 else 0o644)
            expect_rejected(
                validator.validate_package_file_modes,
                mode_members,
                f"mutated {relative}",
            )
            rejected += 1
            path.chmod(expected_mode)

        resource_free = {
            "/watchdog@10007000": {},
            "/i2c@1100e000": {"status": b"disabled\0"},
        }
        validator.validate_resource_free_tree(
            resource_free,
            "positive Gemini fixture",
            require_disabled_i2c6=True,
        )
        validator.validate_resource_free_tree(
            {"/watchdog@10007000": {}, "/i2c@1100e000": {"status": b"okay\0"}},
            "positive non-Gemini fixture",
        )
        expect_rejected(
            validator.validate_resource_free_tree,
            {"/watchdog@10007000": {}, "/i2c@1100e000": {"status": b"okay\0"}},
            "mutated Gemini fixture",
            require_disabled_i2c6=True,
        )
        rejected += 1
        expect_rejected(
            validator.validate_resource_free_tree,
            {
                "/watchdog@10007000": {},
                "/i2c@1100e000": {"status": b"disabled\0"},
                "/i2c@1100e000/regulator@68": {"compatible": b"dlg,da9214\0"},
            },
            "mutated resource fixture",
            require_disabled_i2c6=True,
        )
        rejected += 1

        ad_root = work / "ad-patches"
        ai_root = work / "ai-patches"
        copy_patch_tree(repository / "patches", ad_root, ad_entries)
        copy_patch_tree(repository / "patches", ai_root, ai_entries)
        validator.validate_series_contract(
            ad_series, ad_root, ai_series, ai_root, corrected_patch
        )

        series_mutations = [
            ai_series.replace(ad_entries[-1].encode() + b"\n", b"", 1),
            ai_series.replace(
                validator.PATCH_0092.encode() + b"\n",
                b"v7.1.3/0088-forbidden.patch\n" + validator.PATCH_0092.encode() + b"\n",
                1,
            ),
            ai_series.replace(
                ad_entries[0].encode() + b"\n" + ad_entries[1].encode() + b"\n",
                ad_entries[1].encode() + b"\n" + ad_entries[0].encode() + b"\n",
                1,
            ),
            ai_series + validator.PATCH_0092.encode() + b"\n",
            ai_series.replace(validator.PATCH_0092.encode(), b"../unsafe.patch", 1),
        ]
        for mutation in series_mutations:
            expect_rejected(
                validator.validate_series_contract,
                ad_series,
                ad_root,
                mutation,
                ai_root,
                corrected_patch,
            )
            rejected += 1

        inherited_path = ai_root / ad_entries[0]
        inherited_original = inherited_path.read_bytes()
        inherited_path.write_bytes(inherited_original + b"mutation\n")
        expect_rejected(
            validator.validate_series_contract,
            ad_series,
            ad_root,
            ai_series,
            ai_root,
            corrected_patch,
        )
        rejected += 1
        inherited_path.write_bytes(inherited_original)

        patch_path = ai_root / validator.PATCH_0092
        patch_original = patch_path.read_bytes()
        patch_path.write_bytes(patch_original.replace(b"return false;", b"return true;", 1))
        expect_rejected(
            validator.validate_series_contract,
            ad_series,
            ad_root,
            ai_series,
            ai_root,
            corrected_patch,
        )
        rejected += 1
        patch_path.write_bytes(patch_original)

        extra = ai_root / "v7.1.3/0091-forbidden-extra.patch"
        extra.write_bytes(b"forbidden\n")
        expect_rejected(
            validator.validate_series_contract,
            ad_series,
            ad_root,
            ai_series,
            ai_root,
            corrected_patch,
        )
        rejected += 1
        extra.unlink()

        wrong_corrected = corrected_patch.replace(b"return false;", b"return true;", 1)
        expect_rejected(
            validator.validate_series_contract,
            ad_series,
            ad_root,
            ai_series,
            ai_root,
            wrong_corrected,
        )
        rejected += 1

        config = ("\n".join(sorted(validator.REQUIRED_CONFIG)) + "\n").encode()
        image = b"kernel-prefix\0" + b"".join(validator.REQUIRED_KERNEL_MARKERS)
        system_map = (
            "\n".join(
                f"ffff800080000000 t {symbol}"
                for symbol in sorted(validator.REQUIRED_SYSTEM_MAP)
            )
            + "\n"
        ).encode()
        validator.validate_kernel_policy(
            image,
            system_map,
            config,
            expected_config_hash=hashlib.sha256(config).hexdigest(),
        )

        kernel_cases = [
            (image.replace(validator.REQUIRED_KERNEL_MARKERS[0], b"", 1), system_map, config),
            (image + validator.FORBIDDEN_KERNEL_MARKERS[0], system_map, config),
            (image + validator.FORBIDDEN_KERNEL_MARKERS[1], system_map, config),
            (image, system_map.replace(b"mt6797_psci_cpu_boot", b"missing_gate_symbol", 1), config),
            (image, system_map + b"ffff800080000100 t mt6797_a72_power_driver_init\n", config),
            (image, system_map + b"ffff800080000100 t da9211_regulator_driver_init\n", config),
            (image, system_map + b"ffff800080000100 t mt6797_psci_cpu_die\n", config),
            (image, system_map, config.replace(b"maxcpus=8", b"maxcpus=9", 1)),
            (
                image,
                system_map,
                config.replace(
                    b"# CONFIG_REGULATOR_DA9211 is not set",
                    b"CONFIG_REGULATOR_DA9211=y",
                    1,
                ),
            ),
        ]
        for case_image, case_map, case_config in kernel_cases:
            expect_rejected(
                validator.validate_kernel_policy,
                case_image,
                case_map,
                case_config,
                expected_config_hash=hashlib.sha256(case_config).hexdigest(),
            )
            rejected += 1

        expect_rejected(
            validator.validate_kernel_policy,
            image,
            system_map,
            config,
            expected_config_hash="0" * 64,
        )
        rejected += 1

        expected_rejections = 32
    if rejected != expected_rejections:
        raise ValueError(f"expected {expected_rejections} rejections, observed {rejected}")
    print("validation=candidate-ai-package-validator-mutations")
    print("positive_series_fixture=passed")
    print("positive_manifest_profile_fixture=passed")
    print("positive_kernel_policy_fixture=passed")
    print(f"mutations_rejected={rejected}")
    print("final_ai_package_required=no")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
