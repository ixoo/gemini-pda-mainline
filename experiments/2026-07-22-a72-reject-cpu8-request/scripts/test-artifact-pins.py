#!/usr/bin/env python3
"""Offline positive and mutation tests for the AJ single-artifact pin gate."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import os
import pathlib
import shutil
import stat
import sys
import tempfile
from collections.abc import Callable, Iterator

sys.dont_write_bytecode = True


def load_validator() -> object:
    source = pathlib.Path(__file__).resolve().with_name("validate-artifact-pins.py")
    spec = importlib.util.spec_from_file_location(
        "candidate_aj_artifact_pins_under_test", source
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AJ artifact-pin validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_validator()


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rewrite_manifest(root: pathlib.Path, members: set[str]) -> None:
    lines = []
    for member in sorted(members - {validator.MANIFEST_MEMBER}):
        lines.append(f"{digest(root / member)}  ./{member}\n")
    manifest = root / validator.MANIFEST_MEMBER
    manifest.write_text("".join(lines), encoding="ascii")
    manifest.chmod(0o600)


def make_fixture(parent: pathlib.Path, finalizer: object) -> pathlib.Path:
    raw = b"synthetic Candidate AJ boot\n"
    raw_hash = hashlib.sha256(raw).hexdigest()
    root = parent / f"candidate-AJ-a72-reject-cpu8-{raw_hash[:8]}"
    root.mkdir(mode=0o700)
    members = set(finalizer.EXPECTED_MEMBERS)
    for member in sorted(members - {validator.MANIFEST_MEMBER}):
        data = raw if member == validator.aj.BOOT_MEMBER else f"fixture:{member}\n".encode()
        path = root / member
        path.write_bytes(data)
        mode = 0o755 if member in finalizer.EXECUTABLE_MEMBERS else 0o600
        path.chmod(mode)
    rewrite_manifest(root, members)
    return root


def clone_fixture(
    source: pathlib.Path, parent: pathlib.Path, label: str, name: str | None = None
) -> pathlib.Path:
    case = parent / label
    case.mkdir()
    target = case / (name or source.name)
    shutil.copytree(source, target, copy_function=shutil.copy2)
    return target


def snapshot(root: pathlib.Path) -> dict[str, tuple[int, int, str]]:
    result = {}
    for path in sorted(root.iterdir()):
        info = path.lstat()
        result[path.name] = (
            stat.S_IMODE(info.st_mode),
            info.st_size,
            digest(path),
        )
    return result


@contextlib.contextmanager
def selected_fixture_pins(root: pathlib.Path) -> Iterator[None]:
    names = (
        "IMAGE_GZ_SHA256",
        "IMAGE_GZ_SIZE",
        "SYSTEM_MAP_SHA256",
        "GATE_AUDIT_SHA256",
        "CONFIG_SHA256",
        "FINAL_DTB_SHA256",
        "INITRAMFS_SHA256",
        "RAW_SHA256",
        "RAW_SIZE",
        "ARTIFACT_MANIFEST_SHA256",
        "PADDED_SHA256",
    )
    old = {name: getattr(validator.aj, name) for name in names}
    values = {
        "IMAGE_GZ_SHA256": digest(root / "Image.gz"),
        "IMAGE_GZ_SIZE": str((root / "Image.gz").stat().st_size),
        "SYSTEM_MAP_SHA256": digest(root / "System.map"),
        "GATE_AUDIT_SHA256": digest(
            root / "mt6797-psci-cpu-boot-audit.txt"
        ),
        "CONFIG_SHA256": digest(root / "kernel.config"),
        "FINAL_DTB_SHA256": digest(root / validator.aj.DTB_MEMBER),
        "INITRAMFS_SHA256": digest(root / validator.aj.INITRAMFS_MEMBER),
        "RAW_SHA256": digest(root / validator.aj.BOOT_MEMBER),
        "RAW_SIZE": str((root / validator.aj.BOOT_MEMBER).stat().st_size),
        "ARTIFACT_MANIFEST_SHA256": digest(root / validator.MANIFEST_MEMBER),
        "PADDED_SHA256": "f" * 64,
    }
    try:
        for name, value in values.items():
            setattr(validator.aj, name, value)
        yield
    finally:
        for name, value in old.items():
            setattr(validator.aj, name, value)


def expect_rejected(label: str, action: Callable[[], object]) -> int:
    try:
        action()
    except (OSError, RuntimeError, UnicodeError, ValueError):
        return 1
    raise AssertionError(f"mutation was accepted: {label}")


def main() -> int:
    previous_umask = os.umask(0o077)
    try:
        # Prove the unresolved-pin error wins before helper loading or a
        # caller-controlled lstat/open on a deliberately nonexistent path.
        old_raw = validator.aj.RAW_SHA256
        validator.aj.RAW_SHA256 = "TO_PIN_TEST_ORDER"
        try:
            try:
                validator.validate_candidate(
                    pathlib.Path("/candidate-aj-test-path-must-not-be-touched")
                )
            except ValueError as exc:
                if "identities remain unpinned" not in str(exc):
                    raise AssertionError("path failure occurred before artifact-pin gate")
            else:
                raise AssertionError("unresolved artifact pin was accepted")
        finally:
            validator.aj.RAW_SHA256 = old_raw

        with tempfile.TemporaryDirectory(prefix="candidate-aj-pin-test-") as raw:
            test_root = pathlib.Path(raw)
            # Loading the existing finalizer is itself read-only and does not
            # add a reciprocal hash dependency to candidate_aj.py.
            finalizer = validator.load_finalizer()
            fixture = make_fixture(test_root, finalizer)
            accepted = 1  # unresolved-pin-before-path ordering above
            rejected = 1
            with selected_fixture_pins(fixture):
                before = snapshot(fixture)
                members = validator.validate_candidate(fixture)
                if len(members) != 20 or snapshot(fixture) != before:
                    raise AssertionError("positive validation changed the artifact")
                accepted += 1

                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    validator.emit_report(fixture, members)
                report = output.getvalue()
                if (
                    "padded_sha256=" + "f" * 64 not in report
                    or "padded_artifact_construction=not-performed" not in report
                    or snapshot(fixture) != before
                ):
                    raise AssertionError("padded identity report wrote or omitted data")
                accepted += 1

                wrong_name = clone_fixture(
                    fixture,
                    test_root,
                    "wrong-name",
                    "candidate-AJ-a72-reject-cpu8-deadbeef",
                )
                rejected += expect_rejected(
                    "canonical-directory-name",
                    lambda: validator.validate_candidate(wrong_name),
                )

                missing = clone_fixture(fixture, test_root, "missing")
                (missing / "analysis.txt").unlink()
                rejected += expect_rejected(
                    "missing-member", lambda: validator.validate_candidate(missing)
                )

                extra = clone_fixture(fixture, test_root, "extra")
                (extra / "extra.txt").write_bytes(b"extra\n")
                rejected += expect_rejected(
                    "extra-member", lambda: validator.validate_candidate(extra)
                )

                regular_mode = clone_fixture(fixture, test_root, "regular-mode")
                (regular_mode / "analysis.txt").chmod(0o644)
                rejected += expect_rejected(
                    "regular-mode", lambda: validator.validate_candidate(regular_mode)
                )

                executable_mode = clone_fixture(fixture, test_root, "executable-mode")
                (executable_mode / "console-keymap-verify").chmod(0o700)
                rejected += expect_rejected(
                    "executable-mode",
                    lambda: validator.validate_candidate(executable_mode),
                )

                stale = clone_fixture(fixture, test_root, "stale-manifest")
                (stale / "Image.gz").write_bytes(b"changed\n")
                rejected += expect_rejected(
                    "manifest-checksum", lambda: validator.validate_candidate(stale)
                )

                reordered = clone_fixture(fixture, test_root, "manifest-order")
                manifest = reordered / validator.MANIFEST_MEMBER
                lines = manifest.read_bytes().splitlines(keepends=True)
                manifest.write_bytes(b"".join(reversed(lines)))
                rejected += expect_rejected(
                    "exact-manifest-identity",
                    lambda: validator.validate_candidate(reordered),
                )

                duplicate = clone_fixture(fixture, test_root, "manifest-duplicate")
                manifest = duplicate / validator.MANIFEST_MEMBER
                first_line = manifest.read_bytes().splitlines(keepends=True)[0]
                manifest.write_bytes(manifest.read_bytes() + first_line)
                rejected += expect_rejected(
                    "manifest-completeness",
                    lambda: validator.validate_candidate(duplicate),
                )

                symlink_member = clone_fixture(fixture, test_root, "symlink-member")
                image_gz = symlink_member / "Image.gz"
                image_gz.unlink()
                image_gz.symlink_to("System.map")
                rejected += expect_rejected(
                    "symlink-member",
                    lambda: validator.validate_candidate(symlink_member),
                )

                directory_member = clone_fixture(
                    fixture, test_root, "directory-member"
                )
                image_gz = directory_member / "Image.gz"
                image_gz.unlink()
                image_gz.mkdir()
                rejected += expect_rejected(
                    "directory-member",
                    lambda: validator.validate_candidate(directory_member),
                )

                symlink_root = test_root / "symlink-root"
                symlink_root.symlink_to(fixture, target_is_directory=True)
                rejected += expect_rejected(
                    "symlink-root", lambda: validator.validate_candidate(symlink_root)
                )

                original_manifest_pin = validator.aj.ARTIFACT_MANIFEST_SHA256
                validator.aj.ARTIFACT_MANIFEST_SHA256 = "0" * 64
                try:
                    rejected += expect_rejected(
                        "manifest-pin", lambda: validator.validate_candidate(fixture)
                    )
                finally:
                    validator.aj.ARTIFACT_MANIFEST_SHA256 = original_manifest_pin

                original_raw_pin = validator.aj.RAW_SHA256
                zero_name = "candidate-AJ-a72-reject-cpu8-00000000"
                wrong_raw = clone_fixture(
                    fixture, test_root, "raw-pin", zero_name
                )
                validator.aj.RAW_SHA256 = "0" * 64
                try:
                    rejected += expect_rejected(
                        "raw-sha-pin", lambda: validator.validate_candidate(wrong_raw)
                    )
                finally:
                    validator.aj.RAW_SHA256 = original_raw_pin

                original_size_pin = validator.aj.RAW_SIZE
                validator.aj.RAW_SIZE = str(int(original_size_pin) + 1)
                try:
                    rejected += expect_rejected(
                        "raw-size-pin", lambda: validator.validate_candidate(fixture)
                    )
                finally:
                    validator.aj.RAW_SIZE = original_size_pin

                class ShortFinalizer:
                    EXPECTED_MEMBERS = set(finalizer.EXPECTED_MEMBERS)
                    PRE_MANIFEST_MEMBERS = set(finalizer.PRE_MANIFEST_MEMBERS)
                    MANIFEST_MEMBER = validator.MANIFEST_MEMBER

                    @staticmethod
                    def verify(_root: pathlib.Path) -> dict[str, pathlib.Path]:
                        return {
                            name: fixture / name
                            for name in sorted(finalizer.EXPECTED_MEMBERS)
                            if name != "analysis.txt"
                        }

                rejected += expect_rejected(
                    "finalizer-short-inventory",
                    lambda: validator.validate_selected_tree(
                        fixture, ShortFinalizer()
                    ),
                )

            if accepted != 3 or rejected != 16:
                raise AssertionError(
                    f"unexpected counts: accepted={accepted}, rejected={rejected}"
                )
        print("validation=candidate-aj-artifact-pin-mutations")
        print(f"positive_cases={accepted}")
        print(f"mutations_rejected={rejected}")
        print("pin_gate_before_artifact_path_io=yes")
        print("padded_artifact_constructed=no")
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
