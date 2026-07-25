#!/usr/bin/env python3
"""Lineage, safety, mutation, and publication tests for AI's installer."""

from __future__ import annotations

import argparse
import importlib.util
import os
import pathlib
import stat
import subprocess
import sys
import tempfile


sys.dont_write_bytecode = True


AH_TESTER_SHA256 = (
    "c00ab56313189c543906729ab300309ffb6ffb6883db2fce285ac17e8ad565a1"
)
AI_INSTALLER_SHA256 = (
    "8d9d0ac258fdb031e840b2042c7abc1fc1fdf01cf6c6893bc24c234b6d9054f6"
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_deriver(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("candidate_ai_deriver", path)
    if spec is None or spec.loader is None:
        fail("cannot load Candidate AI installer deriver")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(command: list[str], expected: int) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        env=environment,
        capture_output=True,
        check=False,
    )
    if result.returncode != expected:
        fail(
            f"command returned {result.returncode}, expected {expected}: "
            f"{' '.join(command)}: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return result


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        fail(f"mutation anchor absent or duplicated: {old!r}")
    return text.replace(old, new)


def replace_first_of(text: str, old: str, new: str, expected: int) -> str:
    actual = text.count(old)
    if actual != expected:
        fail(
            f"mutation anchor count changed: {old!r}: "
            f"expected {expected}, found {actual}"
        )
    return text.replace(old, new, 1)


def require_rejected(callable_, label: str) -> None:
    try:
        callable_()
    except (FileExistsError, OSError, ValueError):
        return
    fail(f"unsafe case was accepted: {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shellcheck",
        action="store_true",
        help="also require ShellCheck on AH and both derived AI installers",
    )
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    deriver_path = script_dir / "derive-installer.py"
    deriver = load_deriver(deriver_path)
    fixture = deriver.Calibration("a" * 64, "8000000", "b" * 64)
    rejected = 0

    expected_production = (
        "1ecfc787fec2f5dc11c5b7d30eb4f11d34b0496e57daf42adea567f010282309",
        "7380992",
        "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86",
    )
    actual_production = (
        deriver.AI_RAW_SHA256,
        deriver.AI_RAW_SIZE,
        deriver.AI_PADDED_SHA256,
    )
    if actual_production != expected_production:
        fail("Candidate AI production calibration changed")
    deriver.validate_calibration(deriver.PRODUCTION_CALIBRATION)
    if deriver.AH_PADDED_SHA256 != (
        "f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012"
    ):
        fail("Candidate AI predecessor is not exact installed Candidate AH")
    if deriver.AI_ARTIFACT_DIR != "candidate-AI-a72-reject-gate-1ecfc787":
        fail("Candidate AI artifact directory changed")
    if deriver.AI_BOOT_FILENAME != (
        "gemini-a72-reject-gate-kernel-split.boot.img"
    ):
        fail("Candidate AI boot filename changed")

    with tempfile.TemporaryDirectory(prefix="candidate-ai-installer-test.") as raw:
        work = pathlib.Path(raw)

        production_output = work / "production-derived-ai.sh"
        production = run(
            [
                sys.executable,
                os.fspath(deriver_path),
                "--output",
                os.fspath(production_output),
            ],
            0,
        )
        expected_stdout = (
            "validation=candidate-ai-installer-derivation",
            f"foundation_installer_sha256={deriver.AH_INSTALLER_SHA256}",
            f"installer_sha256={AI_INSTALLER_SHA256}",
            f"candidate_raw_sha256={deriver.AI_RAW_SHA256}",
            f"candidate_raw_size={deriver.AI_RAW_SIZE}",
            f"candidate_padded_sha256={deriver.AI_PADDED_SHA256}",
            f"expected_predecessor_sha256={deriver.AH_PADDED_SHA256}",
            f"artifact_directory={deriver.AI_ARTIFACT_DIR}",
            f"boot_filename={deriver.AI_BOOT_FILENAME}",
            "sole_target_write=one-bounded-16MiB-write",
            "reboot_or_slot_selection=none",
        )
        production_text_output = production.stdout.decode("utf-8")
        if any(line not in production_text_output for line in expected_stdout):
            fail("production derivation output omitted an exact AI identity")
        if deriver.digest_path(production_output) != AI_INSTALLER_SHA256:
            fail("production-derived Candidate AI installer identity changed")
        if stat.S_IMODE(production_output.stat().st_mode) != 0o700:
            fail("production-derived Candidate AI installer mode is not 0700")
        run(["bash", "-n", os.fspath(production_output)], 0)
        if args.shellcheck:
            run(["shellcheck", "--shell=bash", os.fspath(production_output)], 0)

        # Production exposes no caller-supplied calibration surface.
        override_output = work / "override-must-not-exist.sh"
        run(
            [
                sys.executable,
                os.fspath(deriver_path),
                "--output",
                os.fspath(override_output),
                "--raw-sha256",
                "c" * 64,
            ],
            2,
        )
        if override_output.exists() or override_output.is_symlink():
            fail("rejected production calibration override created output")
        rejected += 1

        # Reconstruct the exact AH installer through its byte-pinned deriver.
        ah = deriver.reconstruct_ah_installer(repo_root, work)
        ah_data = deriver.read_exact_source(ah)
        ah_text = ah_data.decode("utf-8")
        if deriver.digest_path(ah) != deriver.AH_INSTALLER_SHA256:
            fail("tracked installer lineage did not reproduce exact Candidate AH")
        if stat.S_IMODE(ah.stat().st_mode) != 0o700:
            fail("reconstructed Candidate AH installer mode is not 0700")

        source_output = work / "source-derived-ai.sh"
        run(
            [
                sys.executable,
                os.fspath(deriver_path),
                "--source",
                os.fspath(ah),
                "--output",
                os.fspath(source_output),
            ],
            0,
        )
        if source_output.read_bytes() != production_output.read_bytes():
            fail("caller-supplied exact AH and reconstructed lineage differ")

        mutated_ah = work / "mutated-ah.sh"
        mutated_ah.write_bytes(ah_data + b"\n# mutation\n")
        require_rejected(
            lambda: deriver.read_exact_source(mutated_ah),
            "mutated Candidate AH foundation",
        )
        rejected += 1
        symlink_ah = work / "symlink-ah.sh"
        symlink_ah.symlink_to(ah)
        require_rejected(
            lambda: deriver.read_exact_source(symlink_ah),
            "symlink Candidate AH foundation",
        )
        rejected += 1

        fake_root = work / "fake-repository"
        fake_deriver = deriver.ah_deriver_path(fake_root)
        fake_deriver.parent.mkdir(parents=True)
        fake_deriver.write_bytes(deriver.ah_deriver_path(repo_root).read_bytes() + b"\n")
        bad_deriver_output = work / "bad-deriver-output"
        bad_deriver_output.mkdir()
        require_rejected(
            lambda: deriver.reconstruct_ah_installer(
                fake_root, bad_deriver_output
            ),
            "mutated Candidate AH deriver lineage",
        )
        rejected += 1
        fake_deriver.unlink()
        fake_deriver.symlink_to(deriver.ah_deriver_path(repo_root))
        symlink_deriver_output = work / "symlink-deriver-output"
        symlink_deriver_output.mkdir()
        require_rejected(
            lambda: deriver.reconstruct_ah_installer(
                fake_root, symlink_deriver_output
            ),
            "symlink Candidate AH deriver lineage",
        )
        rejected += 1

        # Calibration remains a pure in-process test seam.
        invalid_calibrations = (
            deriver.Calibration("TO_PIN_RAW", fixture.raw_size, fixture.padded_sha256),
            deriver.Calibration(fixture.raw_sha256, "TO_PIN_SIZE", fixture.padded_sha256),
            deriver.Calibration(fixture.raw_sha256, fixture.raw_size, "TO_PIN_PADDED"),
            deriver.Calibration("z" * 64, fixture.raw_size, fixture.padded_sha256),
            deriver.Calibration(fixture.raw_sha256, fixture.raw_size, "z" * 64),
            deriver.Calibration(fixture.raw_sha256, "not-a-size", fixture.padded_sha256),
            deriver.Calibration(fixture.raw_sha256, "0", fixture.padded_sha256),
            deriver.Calibration(
                fixture.raw_sha256,
                str(deriver.BOOT2_SIZE + 1),
                fixture.padded_sha256,
            ),
            deriver.Calibration(
                deriver.AH_RAW_SHA256, fixture.raw_size, fixture.padded_sha256
            ),
            deriver.Calibration(
                fixture.raw_sha256, fixture.raw_size, deriver.AH_PADDED_SHA256
            ),
        )
        for index, calibration in enumerate(invalid_calibrations, start=1):
            require_rejected(
                lambda calibration=calibration: deriver.validate_calibration(
                    calibration
                ),
                f"invalid calibration {index}",
            )
            rejected += 1

        derived = deriver.derive_text(ah_data, fixture)
        restored = deriver.restore_ah_contract(derived, fixture)
        if restored != ah_text:
            fail("AI-to-AH safety-contract round trip changed executable bytes")
        if deriver.digest(restored.encode("utf-8")) != deriver.AH_INSTALLER_SHA256:
            fail("AI-to-AH round trip did not restore exact AH installer identity")
        if derived != deriver.expected_transform(ah_text, fixture):
            fail("fixture derivation differs from the exact AH-relative transform")
        derived_path = work / "install-candidate-ai-boot2.sh"
        deriver.publish(derived_path, derived)
        if stat.S_IMODE(derived_path.stat().st_mode) != 0o700:
            fail("fixture-derived installer mode is not 0700")
        run(["bash", "-n", os.fspath(derived_path)], 0)
        if args.shellcheck:
            run(["shellcheck", "--shell=bash", os.fspath(derived_path)], 0)

        expected_identity = (
            "usage: install-candidate-ai-boot2.sh",
            deriver.AI_BOOT_FILENAME,
            f'expected_artifact_name="{deriver.AI_ARTIFACT_DIR}"',
            "candidate-ai-padded-boot2.img",
            "boot2-before-candidate-ai.img",
            "boot2-after-candidate-ai.img",
            "expected_previous_label=AH-installed-readback-verified",
            (
                "readonly EXPECTED_CURRENT_AH_PADDED_SHA256="
                f"{deriver.AH_PADDED_SHA256}"
            ),
            "experiment=2026-07-22-a72-reject-gate-kernel-split",
        )
        if any(token not in derived for token in expected_identity):
            fail("fixture-derived Candidate AI identity is incomplete")

        # AH's exact tester transitively executes the complete AG and AF suites.
        ah_tester = (
            repo_root
            / "experiments/2026-07-22-ad-contract-af-kernel-split"
            / "scripts/test-installer-derivation.py"
        )
        if deriver.digest_path(ah_tester) != AH_TESTER_SHA256:
            fail("Candidate AH installer mutation suite identity changed")
        ah_command = [sys.executable, os.fspath(ah_tester)]
        if args.shellcheck:
            ah_command.append("--shellcheck")
        ah_result = run(ah_command, 0).stdout.decode("utf-8")
        inherited_markers = (
            "inherited_af_mutations=64-of-64",
            "inherited_ag_mutations=42-of-42",
            "ah_mutations_rejected=58-of-58",
            "bounded_target_writes=one",
            "device_contact=none",
            "hardware_write=none",
            "reboot_or_slot_selection=none",
        )
        if any(marker not in ah_result for marker in inherited_markers):
            fail("exact inherited AH/AG/AF suite did not report every gate")

        # These mutations target AI's adapter and the highest-risk inherited
        # storage/remote boundaries. The inherited suite above remains the
        # exhaustive executable-contract test.
        mutations = (
            (
                "capacity",
                lambda text: replace_once(
                    text,
                    "readonly BOOT2_SIZE=16777216",
                    "readonly BOOT2_SIZE=33554432",
                ),
            ),
            (
                "live-gpt",
                lambda text: replace_once(
                    text,
                    "readlink -f /dev/disk/by-partlabel/boot2",
                    "readlink -f /dev/disk/by-partlabel/boot",
                ),
            ),
            (
                "host-key",
                lambda text: replace_once(
                    text, "StrictHostKeyChecking=yes", "StrictHostKeyChecking=no"
                ),
            ),
            (
                "identity-agent",
                lambda text: replace_once(
                    text, "IdentityAgent=none", "IdentityAgent=SSH_AUTH_SOCK"
                ),
            ),
            (
                "candidate-raw-pin",
                lambda text: replace_once(
                    text,
                    f"readonly AI_RAW_SHA256={fixture.raw_sha256}",
                    "readonly AI_RAW_SHA256=" + "c" * 64,
                ),
            ),
            (
                "candidate-size-pin",
                lambda text: replace_once(
                    text,
                    f"readonly AI_RAW_SIZE={fixture.raw_size}",
                    "readonly AI_RAW_SIZE=7000000",
                ),
            ),
            (
                "candidate-padded-pin",
                lambda text: replace_once(
                    text,
                    f"readonly AI_PADDED_SHA256={fixture.padded_sha256}",
                    "readonly AI_PADDED_SHA256=" + "c" * 64,
                ),
            ),
            (
                "predecessor-pin",
                lambda text: replace_once(
                    text,
                    (
                        "readonly EXPECTED_CURRENT_AH_PADDED_SHA256="
                        f"{deriver.AH_PADDED_SHA256}"
                    ),
                    "readonly EXPECTED_CURRENT_AH_PADDED_SHA256=" + "c" * 64,
                ),
            ),
            (
                "candidate-filename",
                lambda text: replace_once(
                    text,
                    deriver.AI_BOOT_FILENAME,
                    "gemini-ad-contract-af-kernel-split.boot.img",
                ),
            ),
            (
                "artifact-directory",
                lambda text: replace_once(
                    text,
                    f'expected_artifact_name="{deriver.AI_ARTIFACT_DIR}"',
                    'expected_artifact_name="candidate-AI-a72-reject-gate-wrong"',
                ),
            ),
            (
                "experiment-identity",
                lambda text: replace_first_of(
                    text,
                    "2026-07-22-a72-reject-gate-kernel-split",
                    "2026-07-22-ad-contract-af-kernel-split",
                    2,
                ),
            ),
            (
                "candidate-label",
                lambda text: replace_first_of(
                    text, "candidate_label=AI", "candidate_label=AH", 2
                ),
            ),
            (
                "predecessor-label",
                lambda text: replace_first_of(
                    text,
                    "AH-installed-readback-verified",
                    "AG-installed-readback-verified",
                    4,
                ),
            ),
            (
                "target-write-whole-disk",
                lambda text: replace_once(
                    text,
                    'dd if="$root_stage_file" of="$target" bs=4M '
                    "iflag=fullblock count=4",
                    'dd if="$root_stage_file" of=/dev/mmcblk0 bs=4M',
                ),
            ),
            (
                "extra-target-dd",
                lambda text: text
                + '\ndd if="$root_stage_file" of="$target" bs=4M '
                + "iflag=fullblock count=4 conv=fsync,notrunc status=none\n",
            ),
            (
                "write-fsync-removed",
                lambda text: replace_once(
                    text,
                    "conv=fsync,notrunc status=none",
                    "conv=notrunc status=none",
                ),
            ),
            (
                "flush-bypass",
                lambda text: replace_once(
                    text, 'blockdev --flushbufs "$target"', "true # flush removed"
                ),
            ),
            (
                "readback-bytes-bypass",
                lambda text: replace_once(
                    text,
                    'cmp -s "$padded" "$readback_partial" || \\\n'
                    '\tdie "full boot2 readback differs byte-for-byte; '
                    'inspect $readback_partial"',
                    "true\n: 'full boot2 readback byte comparison removed'",
                ),
            ),
            ("reboot", lambda text: text + "\n/sbin/reboot\n"),
            (
                "alternative-slot",
                lambda text: text + "\n# /dev/disk/by-partlabel/boot3\n",
            ),
            ("fixed-partition", lambda text: text + "\n# /dev/mmcblk0p30\n"),
            ("password-input", lambda text: text + "\nsudo -S -- true\n"),
            (
                "raw-private-key",
                lambda text: text + "\n# -----BEGIN OPENSSH PRIVATE KEY-----\n",
            ),
        )
        for label, mutate in mutations:
            mutated = mutate(derived)
            require_rejected(
                lambda mutated=mutated: deriver.validate_safety(mutated, fixture),
                f"AI safety adapter mutation: {label}",
            )
            rejected += 1

        narrow_mutation = derived + "\n# unrelated derived mutation\n"
        require_rejected(
            lambda: deriver.validate_exact_delta(
                ah_text, narrow_mutation, fixture
            ),
            "narrow AH-relative delta mutation",
        )
        rejected += 1

        # Publication is exclusive and output parents must be real directories.
        require_rejected(
            lambda: deriver.publish(derived_path, derived),
            "overwrite existing installer",
        )
        rejected += 1
        real_parent = work / "real-parent"
        real_parent.mkdir()
        symlink_parent = work / "symlink-parent"
        symlink_parent.symlink_to(real_parent, target_is_directory=True)
        require_rejected(
            lambda: deriver.validate_output_path(symlink_parent / "installer.sh"),
            "symlink output parent",
        )
        rejected += 1
        regular_parent = work / "regular-parent"
        regular_parent.write_text("not a directory\n", encoding="utf-8")
        require_rejected(
            lambda: deriver.validate_output_path(regular_parent / "installer.sh"),
            "regular-file output parent",
        )
        rejected += 1
        output_symlink = work / "output-symlink.sh"
        output_symlink.symlink_to(derived_path)
        require_rejected(
            lambda: deriver.validate_output_path(output_symlink),
            "symlink output leaf",
        )
        rejected += 1

    expected_rejections = 1 + 4 + len(invalid_calibrations) + len(mutations) + 5
    if rejected != expected_rejections:
        fail(
            f"AI mutation count changed: expected {expected_rejections}, got {rejected}"
        )
    print("validation=candidate-ai-installer-static-mutations")
    print("foundation=exact-reconstructed-candidate-ah")
    print("inherited_af_mutations=64-of-64")
    print("inherited_ag_mutations=42-of-42")
    print("inherited_ah_mutations=58-of-58")
    print(f"ai_mutations_rejected={rejected}-of-{expected_rejections}")
    print("production_calibration=pinned-and-derived")
    print("test_calibration=pure-in-process-only")
    print("production_override_surface=none")
    print("predecessor=exact-installed-candidate-ah")
    print("bash_n=passed")
    print(f"shellcheck={'passed' if args.shellcheck else 'not-requested'}")
    print("bounded_target_writes=one")
    print("device_contact=none")
    print("hardware_write=none")
    print("reboot_or_slot_selection=none")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
