#!/usr/bin/env python3
"""Exercise Candidate AJ's storage-inert profile and derivation boundaries."""

from __future__ import annotations

import argparse
import copy
import gzip
import importlib.util
import json
import pathlib
import sys
from contextlib import contextmanager
from types import ModuleType
from typing import Any, Iterator

sys.dont_write_bytecode = True

import candidate_aj as aj


EXPECTED_PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-"
    "smp8-a72-reject-gate-cpu8-request"
)
EXPECTED_FRAGMENTS = [
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
    "configs/gemini-smp8.fragment",
    "configs/gemini-a72-reject-cpu8-request.fragment",
]
EXPECTED_IDENTITIES = {
    "fragment": "fbbc03dec4021f2e23e51e2aaad5f7bc8942d011470db90552a10d4467631ba3",
    "config_inputs": "9fa44c817649a81a633b0c2443e2d7bf73008af613431577b1cddc525121f409",
    "ai_config": "32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46",
    "config": "64f1c3d1b9a506aad5b0ee0549188abac2fbcff12e9e8aacbda015cf4ee7b8cb",
}
EXPECTED_PACKAGE_IDENTITIES = {
    "IMAGE_SHA256": "3312c868aaafd0dd383b0d99ffc2f815fb124ff731dc11b92f1322f1f320405a",
    "IMAGE_SIZE": "13293576",
    "IMAGE_GZ_SHA256": "6014c00b3ed32c529f3ab66e8fe39f2c86b6bda3bfef5e0c603d6fb505a6de93",
    "IMAGE_GZ_SIZE": "5531650",
    "SYSTEM_MAP_SHA256": "b8408b1c07924f5ffaa7cf8173d887f4a97f89b38e9d01bd31398d7c9c713b2e",
    "PACKAGE_DTB_SHA256": "510669e70cd39df3c0e1a1b4c806c0eeaa8e0b0fe02e037ee1bf405d39498af8",
    "GATE_AUDIT_SHA256": "2ee5ebc7ed4f4784a957d537009d60e82b2e2254d5be33b8744b429aa1f32785",
    "PACKAGE_MANIFEST_SHA256S": (
        "dae3846f367e9465b1996dfc894879dad754bd0a26fffe13b5f45df5a0df8d9e",
        "1cfe77e54d0151dd104099c50363d9d83307f33632a50b7706d940407cf84906",
    ),
}
EXPECTED_ARTIFACT_IDENTITIES = {
    "RAW_SHA256": "a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8",
    "RAW_SIZE": "7380992",
    "ARTIFACT_MANIFEST_SHA256": "143307167adcfe000e7ffc331217248404c1fa45e133600d5e21043d93186ac7",
    "PADDED_SHA256": "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257",
}
EXPECTED_AI_SCRIPT_HASHES = {
    "validate-series-selection.py": "35ac2e525907745259d85c96f1e51b60e7fa00b0d92d7f9eeb70e465b4044346",
    "validate-package.py": "8c2f105e5cdc89ef4be747a895aeaa78619eafdf0113903a6ec9b3bfae194eda",
    "audit-mt6797-psci-cpu-boot.py": "90aa983f66261e18f192b14a535ccf9520b6e9079d45a8ce9234e30de8e90bde",
    "validate-lineage.py": "7f87eca5d6e89e02f5cb711bfbbf0fe64356775c5fe7735c723ee87e703adb19",
    "validate-boot.py": "4dff83a54875ed96bfd69dd0f67d22e5560c6761970f95f028e255ba3c1200da",
    "finalize-artifact.py": "ffb36348561972aefc0b25fa195d4defe12aa427b190d9f011ad18f0affef718",
    "derive-installer.py": "7f9a912f1a9cc05372ad95b5fb6a9dcc8253eda85635358572556362a504e99e",
}
def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@contextmanager
def patched(module: ModuleType, **replacements: Any) -> Iterator[None]:
    originals = {name: getattr(module, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


def expect_rejected(function: Any, *args: Any, contains: str | None = None, **kwargs: Any) -> None:
    try:
        function(*args, **kwargs)
    except ValueError as exc:
        if contains is not None and contains not in str(exc):
            raise ValueError(
                f"mutation failed for the wrong reason: expected {contains!r}, got {exc!r}"
            ) from exc
        return
    raise ValueError("mutation unexpectedly passed")


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label} identity changed")


def encode_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")


def test_profile_and_config_inputs(
    repository: pathlib.Path, profile_validator: ModuleType
) -> int:
    rejected = 0
    require_equal(aj.PROFILE, EXPECTED_PROFILE, "Candidate AJ profile name")
    require_equal(aj.FRAGMENTS, EXPECTED_FRAGMENTS, "Candidate AJ fragment order")
    require_equal(aj.FRAGMENT_SHA256, EXPECTED_IDENTITIES["fragment"], "fragment pin")
    require_equal(
        aj.CONFIG_INPUTS_SHA256,
        EXPECTED_IDENTITIES["config_inputs"],
        "configuration-input pin",
    )
    require_equal(aj.AI_CONFIG_SHA256, EXPECTED_IDENTITIES["ai_config"], "AI config pin")
    require_equal(aj.CONFIG_SHA256, EXPECTED_IDENTITIES["config"], "AJ config pin")
    require_equal(hasattr(aj, "derive_image"), False, "fixed-offset Image oracle removal")

    fragment_path = repository / aj.FRAGMENT_REL
    fragment = aj.read_regular(fragment_path, "Candidate AJ fragment")
    require_equal(fragment, aj.EXPECTED_FRAGMENT, "Candidate AJ fragment bytes")
    require_equal(aj.digest_bytes(fragment), aj.FRAGMENT_SHA256, "Candidate AJ fragment")

    manifest_data = aj.read_regular(repository / "kernel/manifest.json", "kernel manifest")
    manifest = aj.validate_manifest_profile(manifest_data, "repository manifest")
    profile_validator.validate(repository)

    mutations: list[dict[str, Any]] = []
    missing_aj = copy.deepcopy(manifest)
    del missing_aj["config"]["profiles"][aj.PROFILE]
    mutations.append(missing_aj)
    reordered = copy.deepcopy(manifest)
    reordered["config"]["profiles"][aj.PROFILE]["fragments"][-2:] = reversed(
        reordered["config"]["profiles"][aj.PROFILE]["fragments"][-2:]
    )
    mutations.append(reordered)
    changed_ai = copy.deepcopy(manifest)
    changed_ai["config"]["profiles"][aj.AI_PROFILE]["fragments"] = [
        *aj.AI_FRAGMENTS,
        aj.FRAGMENT_REL,
    ]
    mutations.append(changed_ai)
    for mutation in mutations:
        expect_rejected(
            aj.validate_manifest_profile,
            encode_json(mutation),
            "mutated manifest",
        )
        rejected += 1

    fragments = {
        relative: aj.read_regular(repository / relative, f"fragment {relative}")
        for relative in aj.FRAGMENTS
    }
    require_equal(
        aj.config_inputs_digest(fragments),
        aj.CONFIG_INPUTS_SHA256,
        "Candidate AJ configuration inputs",
    )
    mutated_fragments = dict(fragments)
    inherited = aj.AI_FRAGMENTS[0]
    mutated_fragments[inherited] += b"# mutation\n"
    expect_rejected(
        require_equal,
        aj.config_inputs_digest(mutated_fragments),
        aj.CONFIG_INPUTS_SHA256,
        "mutated configuration inputs",
    )
    rejected += 1

    original_read_regular = aj.read_regular

    def read_mutated_fragment(path: pathlib.Path, label: str) -> bytes:
        data = original_read_regular(path, label)
        if path == fragment_path:
            return data.replace(b"maxcpus=9", b"maxcpus=8", 1)
        return data

    with patched(aj, read_regular=read_mutated_fragment):
        expect_rejected(profile_validator.validate, repository)
    rejected += 1
    return rejected


def test_config_derivation() -> int:
    rejected = 0
    old = f'CONFIG_CMDLINE="{aj.AI_CMDLINE}"'.encode("ascii")
    new = f'CONFIG_CMDLINE="{aj.CMDLINE}"'.encode("ascii")
    baseline = b"# synthetic Candidate AI config\n" + old + b"\nCONFIG_SMP=y\n"
    expected = baseline.replace(old, new)
    with patched(
        aj,
        AI_CONFIG_SHA256=aj.digest_bytes(baseline),
        CONFIG_SHA256=aj.digest_bytes(expected),
    ):
        require_equal(aj.derive_config(baseline), expected, "synthetic AJ config")
        expect_rejected(aj.derive_config, baseline + b"# changed\n", contains="not exact")
        rejected += 1

        duplicate = baseline + old + b"\n"
        with patched(aj, AI_CONFIG_SHA256=aj.digest_bytes(duplicate)):
            expect_rejected(aj.derive_config, duplicate, contains="not unique")
        rejected += 1

        ambiguous = baseline + b"# maxcpus=8\n"
        with patched(aj, AI_CONFIG_SHA256=aj.digest_bytes(ambiguous)):
            expect_rejected(aj.derive_config, ambiguous, contains="not unique")
        rejected += 1

        with patched(aj, CONFIG_SHA256="0" * 64):
            expect_rejected(aj.derive_config, baseline, contains="identity changed")
        rejected += 1
    return rejected


def test_manifest_delta(package_validator: ModuleType) -> int:
    rejected = 0
    ai_manifest: dict[str, Any] = {
        "schema": 1,
        "kernel": {"version": "synthetic"},
        "config": {
            "default_profile": "full",
            "profiles": {
                aj.AI_PROFILE: {
                    "base": "defconfig",
                    "patch_series": aj.SERIES_REL,
                    "fragments": aj.AI_FRAGMENTS,
                },
                "unrelated-existing-profile": {
                    "base": "defconfig",
                    "fragments": ["configs/existing.fragment"],
                },
            },
        },
    }
    candidate = copy.deepcopy(ai_manifest)
    candidate["config"]["profiles"][aj.PROFILE] = {
        "base": "defconfig",
        "patch_series": aj.SERIES_REL,
        "fragments": aj.FRAGMENTS,
    }
    ai_bytes = encode_json(ai_manifest)
    candidate_bytes = encode_json(candidate)
    require_equal(
        package_validator.validate_manifest_delta(ai_bytes, candidate_bytes),
        candidate,
        "insertion-only packaged manifest",
    )

    mutations: list[dict[str, Any]] = []
    changed_existing = copy.deepcopy(candidate)
    changed_existing["config"]["profiles"]["unrelated-existing-profile"][
        "base"
    ] = "tinyconfig"
    mutations.append(changed_existing)
    added_unrelated = copy.deepcopy(candidate)
    added_unrelated["config"]["profiles"]["new-unrelated-profile"] = {
        "base": "defconfig",
        "fragments": [],
    }
    mutations.append(added_unrelated)
    changed_global = copy.deepcopy(candidate)
    changed_global["kernel"]["version"] = "drifted"
    mutations.append(changed_global)
    type_coercion = copy.deepcopy(candidate)
    type_coercion["schema"] = True
    mutations.append(type_coercion)
    missing_aj = copy.deepcopy(candidate)
    del missing_aj["config"]["profiles"][aj.PROFILE]
    mutations.append(missing_aj)
    changed_aj = copy.deepcopy(candidate)
    changed_aj["config"]["profiles"][aj.PROFILE]["fragments"] = aj.AI_FRAGMENTS
    mutations.append(changed_aj)
    for mutation in mutations:
        expect_rejected(
            package_validator.validate_manifest_delta,
            ai_bytes,
            encode_json(mutation),
            contains="not exact Candidate AI plus one AJ profile",
        )
        rejected += 1
    expect_rejected(
        package_validator.decode_json_object,
        b'{"schema":1,"schema":2}',
        "duplicate-member fixture",
        contains="duplicate JSON member",
    )
    rejected += 1
    expect_rejected(
        package_validator.decode_json_object,
        b'{"invalid":NaN}',
        "invalid-number fixture",
        contains="invalid JSON number",
    )
    return rejected + 1


def test_ikconfig_bootstrap(package_validator: ModuleType) -> int:
    rejected = 0
    config = (
        b"CONFIG_IKCONFIG=y\nCONFIG_IKCONFIG_PROC=y\n"
        + f'CONFIG_CMDLINE="{aj.CMDLINE}"\n'.encode("ascii")
    )
    compressed = gzip.compress(config, compresslevel=9, mtime=0)
    image = (
        b"synthetic-prefix"
        + package_validator.IKCONFIG_START
        + compressed
        + package_validator.IKCONFIG_END
        + b"synthetic-suffix"
    )
    require_equal(
        package_validator.extract_ikconfig(image), config, "synthetic embedded IKCONFIG"
    )
    for mutation in (
        image.replace(package_validator.IKCONFIG_START, b"", 1),
        image.replace(
            package_validator.IKCONFIG_START,
            package_validator.IKCONFIG_START * 2,
            1,
        ),
        image.replace(compressed, compressed + b"trailing", 1),
        image.replace(compressed, b"not-gzip", 1),
    ):
        expect_rejected(package_validator.extract_ikconfig, mutation)
        rejected += 1

    plaintext = aj.CMDLINE.encode("ascii") + b"\0" + aj.CMDLINE.encode("ascii")
    package_validator.validate_plaintext_cmdline(plaintext)
    for mutation in (
        aj.CMDLINE.encode("ascii"),
        plaintext + b" maxcpus=9",
        plaintext.replace(b"maxcpus=9", b"maxcpus=8", 1),
    ):
        expect_rejected(package_validator.validate_plaintext_cmdline, mutation)
        rejected += 1
    return rejected


def package_pin_values() -> dict[str, Any]:
    return dict(EXPECTED_PACKAGE_IDENTITIES)


def artifact_pin_values() -> dict[str, Any]:
    return dict(EXPECTED_ARTIFACT_IDENTITIES)


def test_package_and_artifact_pins() -> int:
    rejected = 0
    package_values = package_pin_values()
    actual_package_values = {
        name: getattr(aj, name) for name in EXPECTED_PACKAGE_IDENTITIES
    }
    require_equal(
        actual_package_values,
        package_values,
        "Candidate AJ reproduced package pins",
    )
    aj.require_package_pins()
    package_mutations: tuple[tuple[str, Any], ...] = (
        ("IMAGE_SHA256", "g" * 64),
        ("IMAGE_SIZE", "0"),
        ("IMAGE_GZ_SHA256", "2" * 63),
        ("IMAGE_GZ_SIZE", "0"),
        ("IMAGE_GZ_SIZE", str(16 * 1024 * 1024 + 1)),
        ("SYSTEM_MAP_SHA256", "TO_PIN_AFTER_TWO_PACKAGE_BUILDS"),
        ("PACKAGE_DTB_SHA256", "4" * 63),
        ("GATE_AUDIT_SHA256", "z" * 64),
        ("PACKAGE_MANIFEST_SHA256S", ("6" * 64,)),
        ("PACKAGE_MANIFEST_SHA256S", ("6" * 64, "x" * 64)),
    )
    for name, mutation in package_mutations:
        with patched(aj, **{name: mutation}):
            expect_rejected(aj.require_package_pins)
        rejected += 1
    with patched(
        aj,
        PACKAGE_MANIFEST_SHA256S=("6" * 64, "6" * 64),
    ):
        expect_rejected(
            aj.require_package_pins,
            contains="not two distinct builds",
        )
    rejected += 1

    artifact_values = artifact_pin_values()
    actual_artifact_values = {
        name: getattr(aj, name) for name in EXPECTED_ARTIFACT_IDENTITIES
    }
    require_equal(
        actual_artifact_values,
        artifact_values,
        "Candidate AJ reproduced artifact pins",
    )
    aj.require_artifact_pins()
    for name, mutation in (
        ("RAW_SHA256", "g" * 64),
        ("ARTIFACT_MANIFEST_SHA256", "2" * 63),
        ("PADDED_SHA256", "TO_PIN_AFTER_TWO_PADDING_CHECKS"),
        ("RAW_SIZE", "0"),
        ("RAW_SIZE", str(16 * 1024 * 1024 + 1)),
        ("RAW_SIZE", "not-a-size"),
    ):
        with patched(aj, **{name: mutation}):
            expect_rejected(aj.require_artifact_pins)
        rejected += 1

    for name in ("RAW_SHA256", "ARTIFACT_MANIFEST_SHA256", "PADDED_SHA256"):
        with patched(aj, **{name: "0" * 64}):
            mutated = {
                key: getattr(aj, key) for key in EXPECTED_ARTIFACT_IDENTITIES
            }
            expect_rejected(
                require_equal,
                mutated,
                artifact_values,
                f"wrong but well-formed Candidate AJ {name}",
            )
        rejected += 1
    return rejected


def test_ai_source_pins(repository: pathlib.Path) -> tuple[int, dict[str, bytes]]:
    rejected = 0
    require_equal(
        aj.AI_SCRIPT_HASHES,
        EXPECTED_AI_SCRIPT_HASHES,
        "Candidate AI script pin table",
    )
    snapshots: dict[str, bytes] = {}
    for index, (name, expected_hash) in enumerate(EXPECTED_AI_SCRIPT_HASHES.items()):
        path = aj.ai_script(name)
        expected_path = (
            repository / "experiments" / aj.AI_EXPERIMENT / "scripts" / name
        ).resolve(strict=True)
        require_equal(path.resolve(strict=True), expected_path, f"Candidate AI {name} path")
        data = aj.read_regular(path, f"Candidate AI {name}")
        snapshots[name] = data
        require_equal(aj.digest_bytes(data), expected_hash, f"Candidate AI {name}")
        aj.load_ai_module(name, f"candidate_aj_static_ai_{index}")

    target = "validate-package.py"
    target_path = aj.ai_script(target)
    original_read_regular = aj.read_regular

    def read_mutated_source(path: pathlib.Path, label: str) -> bytes:
        data = original_read_regular(path, label)
        if path == target_path:
            return data + b"# in-memory mutation\n"
        return data

    with patched(aj, read_regular=read_mutated_source):
        expect_rejected(
            aj.load_ai_module,
            target,
            "candidate_aj_static_mutated_ai",
            contains="source-pinned",
        )
    rejected += 1
    return rejected, snapshots


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[3],
    )
    args = parser.parse_args()
    try:
        repository = args.repository.resolve(strict=True)
        require_equal(repository, aj.repository_root(), "Candidate AJ repository root")
        profile_validator = load_module(
            pathlib.Path(__file__).resolve().with_name("validate-profile.py"),
            "candidate_aj_static_profile_validator",
        )
        package_validator = load_module(
            pathlib.Path(__file__).resolve().with_name("validate-package.py"),
            "candidate_aj_static_package_validator",
        )

        rejected, ai_snapshots = test_ai_source_pins(repository)
        try:
            rejected += test_profile_and_config_inputs(repository, profile_validator)
            rejected += test_config_derivation()
            rejected += test_manifest_delta(package_validator)
            rejected += test_ikconfig_bootstrap(package_validator)
            rejected += test_package_and_artifact_pins()
        finally:
            for name, before in ai_snapshots.items():
                after = aj.read_regular(aj.ai_script(name), f"Candidate AI {name}")
                require_equal(after, before, f"Candidate AI {name} remained untouched")

        print("validation=candidate-aj-static-mutations")
        print(f"profile={aj.PROFILE}")
        print(f"fragment_sha256={aj.FRAGMENT_SHA256}")
        print(f"config_inputs_sha256={aj.CONFIG_INPUTS_SHA256}")
        print(f"mutations_rejected={rejected}")
        for name, expected_hash in EXPECTED_AI_SCRIPT_HASHES.items():
            print(f"candidate_ai_script_sha256[{name}]={expected_hash}")
        print("candidate_ai_files_untouched=yes")
        print("fixed_offset_image_oracle=absent")
        print("package_pins=exact-two-build-reproduction")
        print("artifact_pins=exact-two-build-and-padding-reproduction")
        print("build_access=none")
        print("vm_access=none")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
