#!/usr/bin/env python3
"""Offline positive and mutation tests for AJ artifact reproduction helpers."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import stat
import sys
import tempfile
from collections.abc import Callable

sys.dont_write_bytecode = True


def load_validator() -> object:
    source = pathlib.Path(__file__).resolve().with_name(
        "validate-artifact-reproduction.py"
    )
    spec = importlib.util.spec_from_file_location(
        "candidate_aj_artifact_reproduction_under_test", source
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AJ artifact reproduction validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_validator()


def file_digest(path: pathlib.Path) -> str:
    return validator.digest_path(path)


def rewrite_manifest(root: pathlib.Path) -> None:
    lines = []
    for member in sorted(validator.PRE_MANIFEST_MEMBERS):
        lines.append(f"{file_digest(root / member)}  ./{member}\n")
    manifest = root / validator.MANIFEST_MEMBER
    manifest.write_text("".join(lines), encoding="ascii")
    manifest.chmod(0o600)


def make_fixture(parent: pathlib.Path, name: str) -> pathlib.Path:
    root = parent / name
    root.mkdir(mode=0o700)
    for member in sorted(validator.PRE_MANIFEST_MEMBERS):
        path = root / member
        path.write_bytes(f"fixture:{member}\n".encode("ascii"))
        path.chmod(validator.expected_mode(member))
    rewrite_manifest(root)
    return root


def clone_fixture(source: pathlib.Path, parent: pathlib.Path, name: str) -> pathlib.Path:
    target = parent / name
    shutil.copytree(source, target, copy_function=shutil.copy2)
    return target


def expect_rejected(label: str, action: Callable[[], object]) -> int:
    try:
        action()
    except (OSError, RuntimeError, UnicodeError, ValueError):
        return 1
    raise AssertionError(f"mutation was accepted: {label}")


def provenance_bytes(inventory: object) -> bytes:
    values = dict(validator.FIXED_PROVENANCE)
    values.update(
        {
            "candidate_sha256": inventory[validator.aj.BOOT_MEMBER][2],
            "candidate_size": str(inventory[validator.aj.BOOT_MEMBER][1]),
            "candidate_image_gz_sha256": inventory["Image.gz"][2],
            "candidate_system_map_sha256": inventory["System.map"][2],
            "candidate_source_build_sha256": inventory["source-build.json"][2],
            "compiled_gate_audit_sha256": inventory[validator.AUDIT_MEMBER][2],
        }
    )
    return "".join(f"{key}={value}\n" for key, value in values.items()).encode(
        "ascii"
    )


def mutated_provenance(data: bytes, old: bytes, new: bytes) -> bytes:
    if data.count(old) != 1:
        raise AssertionError(f"test precondition failed for {old!r}")
    return data.replace(old, new)


def test_inventory_and_equality(root: pathlib.Path) -> tuple[int, int]:
    accepted = 0
    rejected = 0
    baseline = make_fixture(root, "baseline")
    baseline_inventory = validator.inspect_artifact_tree(baseline)
    if len(baseline_inventory) != 20:
        raise AssertionError("positive fixture did not produce 20 members")
    accepted += 1

    replica = clone_fixture(baseline, root, "replica")
    replica_inventory = validator.inspect_artifact_tree(replica)
    validator.compare_artifact_trees(
        baseline, baseline_inventory, replica, replica_inventory
    )
    accepted += 1

    def mutation(name: str, edit: Callable[[pathlib.Path], None]) -> int:
        candidate = clone_fixture(baseline, root, name)
        edit(candidate)
        return expect_rejected(name, lambda: validator.inspect_artifact_tree(candidate))

    rejected += mutation("missing", lambda tree: (tree / "analysis.txt").unlink())
    rejected += mutation(
        "extra", lambda tree: (tree / "unexpected.txt").write_bytes(b"extra\n")
    )
    rejected += mutation(
        "regular-mode", lambda tree: (tree / "analysis.txt").chmod(0o644)
    )
    rejected += mutation(
        "executable-mode",
        lambda tree: (tree / "console-keymap-verify").chmod(0o700),
    )
    rejected += mutation(
        "stale-checksum", lambda tree: (tree / "Image.gz").write_bytes(b"changed\n")
    )

    def reorder_manifest(tree: pathlib.Path) -> None:
        manifest = tree / validator.MANIFEST_MEMBER
        lines = manifest.read_bytes().splitlines(keepends=True)
        manifest.write_bytes(b"".join(reversed(lines)))

    rejected += mutation("manifest-order", reorder_manifest)

    def duplicate_manifest(tree: pathlib.Path) -> None:
        manifest = tree / validator.MANIFEST_MEMBER
        first = manifest.read_bytes().splitlines(keepends=True)[0]
        manifest.write_bytes(manifest.read_bytes() + first)

    rejected += mutation("manifest-duplicate", duplicate_manifest)

    def unsafe_manifest(tree: pathlib.Path) -> None:
        manifest = tree / validator.MANIFEST_MEMBER
        data = manifest.read_bytes()
        manifest.write_bytes(data.replace(b"./Image.gz", b"../Image.gz", 1))

    rejected += mutation("manifest-unsafe-path", unsafe_manifest)

    def nested_member(tree: pathlib.Path) -> None:
        nested = tree / "nested"
        nested.mkdir()
        (nested / "member").write_bytes(b"nested\n")

    rejected += mutation("nested-member", nested_member)

    def symlink_member(tree: pathlib.Path) -> None:
        member = tree / "Image.gz"
        member.unlink()
        member.symlink_to("System.map")

    rejected += mutation("symlink-member", symlink_member)

    symlink_root = root / "symlink-root"
    symlink_root.symlink_to(baseline, target_is_directory=True)
    rejected += expect_rejected(
        "symlink-root", lambda: validator.inspect_artifact_tree(symlink_root)
    )
    rejected += expect_rejected(
        "same-tree-comparison",
        lambda: validator.compare_artifact_trees(
            baseline, baseline_inventory, baseline, baseline_inventory
        ),
    )
    rejected += expect_rejected(
        "non-exact-manifest-source",
        lambda: validator.canonical_manifest_bytes(
            {key: value for key, value in baseline_inventory.items() if key != "Image.gz"}
        ),
    )

    changed = clone_fixture(baseline, root, "changed-but-self-consistent")
    (changed / "Image.gz").write_bytes(b"changed-and-rehashed\n")
    (changed / "Image.gz").chmod(0o600)
    rewrite_manifest(changed)
    changed_inventory = validator.inspect_artifact_tree(changed)
    rejected += expect_rejected(
        "complete-tree-byte-delta",
        lambda: validator.compare_artifact_trees(
            baseline, baseline_inventory, changed, changed_inventory
        ),
    )

    expected_name = (
        "candidate-AJ-a72-reject-cpu8-"
        f"{baseline_inventory[validator.aj.BOOT_MEMBER][2][:8]}"
    )
    validator.validate_artifact_basename(pathlib.Path(expected_name), baseline_inventory)
    accepted += 1
    rejected += expect_rejected(
        "artifact-basename",
        lambda: validator.validate_artifact_basename(
            pathlib.Path("candidate-AJ-a72-reject-cpu8-deadbeef"),
            baseline_inventory,
        ),
    )
    return accepted, rejected


def test_pair_binding() -> tuple[int, int]:
    accepted = 0
    rejected = 0
    artifact = {
        "Image.gz": b"image-gz",
        "System.map": b"system-map",
        "kernel.config": b"config",
        "source-build.json": b"normalized-build",
        validator.AUDIT_MEMBER: b"audit",
    }
    package = {
        "Image.gz": b"image-gz",
        "System.map": b"system-map",
        "kernel.config": b"config",
    }
    validator.validate_binding_bytes(
        artifact, package, b"normalized-build", b"audit"
    )
    accepted += 1
    for member in validator.BOUND_PACKAGE_MEMBERS:
        changed = dict(package)
        changed[member] = b"changed"
        rejected += expect_rejected(
            f"pair-binding-{member}",
            lambda changed=changed: validator.validate_binding_bytes(
                artifact, changed, b"normalized-build", b"audit"
            ),
        )
    rejected += expect_rejected(
        "pair-binding-normalized-build",
        lambda: validator.validate_binding_bytes(
            artifact, package, b"changed", b"audit"
        ),
    )
    rejected += expect_rejected(
        "pair-binding-compiled-audit",
        lambda: validator.validate_binding_bytes(
            artifact, package, b"normalized-build", b"changed"
        ),
    )
    rejected += expect_rejected(
        "pair-binding-missing-member",
        lambda: validator.validate_binding_bytes(
            {key: value for key, value in artifact.items() if key != "Image.gz"},
            package,
            b"normalized-build",
            b"audit",
        ),
    )
    return accepted, rejected


def test_provenance_and_selected_pins(root: pathlib.Path) -> tuple[int, int]:
    accepted = 0
    rejected = 0
    fixture = make_fixture(root, "provenance")
    inventory = validator.inspect_artifact_tree(fixture)
    data = provenance_bytes(inventory)
    validator.validate_provenance(data, inventory)
    accepted += 1

    rejected += expect_rejected(
        "provenance-duplicate",
        lambda: validator.validate_provenance(
            data + b"candidate_label=AJ\n", inventory
        ),
    )
    rejected += expect_rejected(
        "provenance-fixed-value",
        lambda: validator.validate_provenance(
            mutated_provenance(
                data,
                b"cpu_policy=maxcpus-9-cpu8-request-cpu9-not-requested\n",
                b"cpu_policy=maxcpus-10\n",
            ),
            inventory,
        ),
    )
    rejected += expect_rejected(
        "provenance-raw-hash",
        lambda: validator.validate_provenance(
            mutated_provenance(
                data,
                f"candidate_sha256={inventory[validator.aj.BOOT_MEMBER][2]}\n".encode(),
                b"candidate_sha256=" + b"0" * 64 + b"\n",
            ),
            inventory,
        ),
    )
    rejected += expect_rejected(
        "provenance-size",
        lambda: validator.validate_provenance(
            mutated_provenance(
                data,
                f"candidate_size={inventory[validator.aj.BOOT_MEMBER][1]}\n".encode(),
                b"candidate_size=1\n",
            ),
            inventory,
        ),
    )
    rejected += expect_rejected(
        "provenance-extra",
        lambda: validator.validate_provenance(data + b"extra=value\n", inventory),
    )
    rejected += expect_rejected(
        "provenance-malformed",
        lambda: validator.validate_provenance(data + b"not-an-assignment\n", inventory),
    )

    old_values = (
        validator.aj.RAW_SHA256,
        validator.aj.RAW_SIZE,
        validator.aj.ARTIFACT_MANIFEST_SHA256,
    )
    try:
        validator.aj.RAW_SHA256 = inventory[validator.aj.BOOT_MEMBER][2]
        validator.aj.RAW_SIZE = str(inventory[validator.aj.BOOT_MEMBER][1])
        validator.aj.ARTIFACT_MANIFEST_SHA256 = inventory[validator.MANIFEST_MEMBER][2]
        validator.validate_selected_identities(inventory)
        accepted += 1

        validator.aj.RAW_SHA256 = "0" * 64
        rejected += expect_rejected(
            "selected-raw-hash",
            lambda: validator.validate_selected_identities(inventory),
        )
        validator.aj.RAW_SHA256 = inventory[validator.aj.BOOT_MEMBER][2]
        validator.aj.RAW_SIZE = "1"
        rejected += expect_rejected(
            "selected-raw-size",
            lambda: validator.validate_selected_identities(inventory),
        )
        validator.aj.RAW_SIZE = str(inventory[validator.aj.BOOT_MEMBER][1])
        validator.aj.ARTIFACT_MANIFEST_SHA256 = "0" * 64
        rejected += expect_rejected(
            "selected-manifest-hash",
            lambda: validator.validate_selected_identities(inventory),
        )
    finally:
        (
            validator.aj.RAW_SHA256,
            validator.aj.RAW_SIZE,
            validator.aj.ARTIFACT_MANIFEST_SHA256,
        ) = old_values
    return accepted, rejected


def main() -> int:
    previous_umask = os.umask(0o077)
    try:
        with tempfile.TemporaryDirectory(prefix="candidate-aj-artifact-test-") as raw:
            root = pathlib.Path(raw)
            accepted = 0
            rejected = 0
            for test in (
                test_inventory_and_equality,
                lambda path: test_pair_binding(),
                test_provenance_and_selected_pins,
            ):
                case_accepted, case_rejected = test(root)
                accepted += case_accepted
                rejected += case_rejected
        if accepted != 6 or rejected != 30:
            raise AssertionError(
                f"unexpected test counts: accepted={accepted}, rejected={rejected}"
            )
        print("validation=candidate-aj-artifact-reproduction-mutations")
        print(f"positive_cases={accepted}")
        print(f"mutations_rejected={rejected}")
        print("synthetic_fixtures=yes")
        print("vm_access=none")
        print("device_access=none")
        return 0
    except (AssertionError, OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
