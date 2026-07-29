#!/usr/bin/env python3
"""Exercise Hubble artifact reproduction and installer derivation contracts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import pathlib
import stat
import sys
import tempfile
from types import ModuleType

sys.dont_write_bytecode = True
import candidate_hubble as ch


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Hubble artifact validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expect_rejection(callable_object, label: str) -> None:
    try:
        callable_object()
    except ValueError:
        return
    raise ValueError(f"mutation was accepted: {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-a", required=True, type=pathlib.Path)
    parser.add_argument("--artifact-b", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        ch.require_pins(installer=True)
        scripts = pathlib.Path(__file__).resolve().parent
        validator = load_module(
            scripts / "validate-hubble-artifact.py",
            "hubble_contract_validator",
        )
        derive_installer = load_module(
            scripts / "derive-installer.py",
            "hubble_contract_installer",
        )
        builder = load_module(
            scripts / "build-candidate-hubble.py",
            "hubble_contract_builder",
        )
        first = validator.validate(
            args.artifact_a.absolute(), ch.ARTIFACT_DIR
        )
        second = validator.validate(
            args.artifact_b.absolute(), ch.ARTIFACT_DIR
        )
        if set(first) != set(second):
            raise ValueError("independent Hubble inventories differ")
        for name in first:
            if (
                first[name].read_bytes() != second[name].read_bytes()
                or stat.S_IMODE(first[name].lstat().st_mode)
                != stat.S_IMODE(second[name].lstat().st_mode)
            ):
                raise ValueError(f"independent Hubble member differs: {name}")

        manifest = ch.read_regular(
            first[ch.MANIFEST_MEMBER], "Hubble checksum manifest"
        )
        entries = validator.parse_manifest(manifest)
        manifest_mutations = (
            b"g" + manifest[1:],
            manifest.replace(b"  ./Image.gz", b"  ../Image.gz", 1),
            manifest + manifest.splitlines(keepends=True)[0],
        )
        for index, mutated in enumerate(manifest_mutations, 1):
            expect_rejection(
                lambda data=mutated: validator.parse_manifest(data),
                f"manifest-{index}",
            )

        overlap_rejections = 0
        with tempfile.TemporaryDirectory(prefix="hubble-overlap-contract.") as raw:
            temporary = pathlib.Path(raw).resolve(strict=True)
            source = temporary / "source"
            child = source / "child"
            source.mkdir(mode=0o700)
            child.mkdir(mode=0o700)
            for label, output_root in (
                ("source-equals-output", source),
                ("output-inside-source", child),
                ("source-inside-output", temporary),
            ):
                expect_rejection(
                    lambda root=output_root: builder.safe_output_root(root, source),
                    label,
                )
                overlap_rejections += 1

        with tempfile.TemporaryDirectory(prefix="hubble-installer-contract.") as raw:
            photon = derive_installer.reconstruct_photon(
                pathlib.Path(raw)
            )
        hubble = derive_installer.derive_text(photon)
        if hashlib.sha256(hubble.encode()).hexdigest() != ch.INSTALLER_SHA256:
            raise ValueError("derived Hubble installer identity changed")
        required_counts = {
            ch.PHOTON_R2_PADDED_SHA256: 1,
            ch.CASSINI_PADDED_SHA256: 1,
            ch.CASSINI_RAW_SHA256: 1,
            ch.ARTIFACT_DIR: 1,
            ch.BOOT_MEMBER: 1,
            'dd if="$root_stage_file" of="$target"': 1,
        }
        for token, expected in required_counts.items():
            actual = hubble.count(token)
            if actual != expected:
                raise ValueError(
                    f"Hubble installer token count changed for {token!r}: "
                    f"expected {expected}, found {actual}"
                )
        if any(
            token in hubble
            for token in ("reboot ", "shutdown ", "poweroff ", "kexec ", "sysrq")
        ):
            raise ValueError("Hubble installer gained reboot or shutdown behavior")

        print("validation=hubble-reproduction-and-installer-contracts")
        print(f"complete_member_count={len(first)}")
        print("independent_tree_bytes=identical")
        print("independent_tree_modes=identical")
        print("complete_tree_identity=exact-cassini")
        print(f"manifest_entry_count={len(entries)}")
        print(f"manifest_mutations_rejected={len(manifest_mutations)}")
        print(f"source_output_overlap_cases_rejected={overlap_rejections}")
        print(f"raw_sha256={ch.CASSINI_RAW_SHA256}")
        print(f"padded_sha256={ch.CASSINI_PADDED_SHA256}")
        print(f"expected_predecessor_sha256={ch.PHOTON_R2_PADDED_SHA256}")
        print(f"installer_sha256={ch.INSTALLER_SHA256}")
        print("installer_target_writes=1")
        print("installer_reboot_shutdown_slot_selection=none")
        print("hardware_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
