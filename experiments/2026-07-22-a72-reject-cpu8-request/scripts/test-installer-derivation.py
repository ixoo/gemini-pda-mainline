#!/usr/bin/env python3
"""Lineage, safety, mutation, and publication tests for AJ's installer."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from typing import Any


sys.dont_write_bytecode = True


AI_TESTER_SHA256 = (
    "edec475b8e52956cbfb00a90e575cd9f82eec18140c9e34b97177ebcbe7b8832"
)
AJ_INSTALLER_SHA256 = (
    "5cd0d3f59a8a95705f11819ff2cf52c69fd14da04476b132e6000faee1b8c764"
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_deriver(path: pathlib.Path) -> Any:
    spec = importlib.util.spec_from_file_location("candidate_aj_installer_deriver", path)
    if spec is None or spec.loader is None:
        fail("cannot load Candidate AJ installer deriver")
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


def require_rejected(
    action: Callable[[], object], label: str, contains: str | None = None
) -> None:
    try:
        action()
    except (FileExistsError, OSError, RuntimeError, ValueError) as exc:
        if contains is not None and contains not in str(exc):
            fail(
                f"unsafe case failed for the wrong reason: {label}: "
                f"expected {contains!r}, got {exc!r}"
            )
        return
    fail(f"unsafe case was accepted: {label}")


@contextlib.contextmanager
def patched(module: Any, **changes: object) -> Iterator[None]:
    originals = {name: getattr(module, name) for name in changes}
    try:
        for name, value in changes.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shellcheck",
        action="store_true",
        help="also require ShellCheck on AI and both derived AJ installers",
    )
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    deriver_path = script_dir / "derive-installer.py"
    deriver = load_deriver(deriver_path)
    fixture = deriver.Calibration("a" * 64, "8000000", "c" * 64, "b" * 64)
    rejected = 0

    expected_production = (
        "a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8",
        "7380992",
        "143307167adcfe000e7ffc331217248404c1fa45e133600d5e21043d93186ac7",
        "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257",
    )
    production_calibration = deriver.production_calibration()
    actual_production = (
        production_calibration.raw_sha256,
        production_calibration.raw_size,
        production_calibration.artifact_manifest_sha256,
        production_calibration.padded_sha256,
    )
    if actual_production != expected_production:
        fail("Candidate AJ production calibration changed")
    deriver.validate_calibration(production_calibration)
    if deriver.EXPECTED_AI_PADDED_SHA256 != (
        "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
    ):
        fail("Candidate AJ predecessor is not exact installed Candidate AI")
    if deriver.AI_DERIVER_SHA256 != (
        "7f9a912f1a9cc05372ad95b5fb6a9dcc8253eda85635358572556362a504e99e"
    ):
        fail("Candidate AI installer deriver source pin changed")
    if deriver.CANDIDATE_AJ_SOURCE_SHA256 != (
        "77f29772bafc070da6d0dda621136586348d2d1d1cf0c4cecec6b24800eee3c1"
    ):
        fail("Candidate AJ shared identity source pin changed")
    if deriver.AI_INSTALLER_SHA256 != (
        "8d9d0ac258fdb031e840b2042c7abc1fc1fdf01cf6c6893bc24c234b6d9054f6"
    ):
        fail("Candidate AI installer foundation pin changed")
    if deriver.artifact_directory(production_calibration) != (
        "candidate-AJ-a72-reject-cpu8-a3c649b5"
    ):
        fail("Candidate AJ artifact directory changed")
    if deriver.AJ_BOOT_FILENAME != "gemini-a72-reject-cpu8-request.boot.img":
        fail("Candidate AJ boot filename changed")

    with tempfile.TemporaryDirectory(prefix="candidate-aj-installer-test.") as raw:
        work = pathlib.Path(raw)

        # Unresolved or drifted production pins must win before lstat/open of
        # either deliberately nonexistent caller path.
        untouched_source = work / "missing-source-parent" / "source.sh"
        untouched_output = work / "missing-output-parent" / "output.sh"
        with patched(deriver.aj, RAW_SHA256="TO_PIN_TEST_ORDER"):
            require_rejected(
                lambda: deriver.produce(untouched_source, untouched_output),
                "unresolved pin before caller-path I/O",
                "identities remain unpinned",
            )
        if untouched_source.parent.exists() or untouched_output.parent.exists():
            fail("unresolved-pin ordering touched a caller path")
        rejected += 1
        with patched(deriver.aj, AI_PADDED_SHA256="f" * 64):
            require_rejected(
                lambda: deriver.produce(untouched_source, untouched_output),
                "drifted predecessor before caller-path I/O",
                "installed predecessor pin changed",
            )
        if untouched_source.parent.exists() or untouched_output.parent.exists():
            fail("predecessor-pin ordering touched a caller path")
        rejected += 1

        candidate_aj_path = script_dir / "candidate_aj.py"
        fake_candidate_aj = work / "candidate_aj-mutated.py"
        fake_candidate_aj.write_bytes(candidate_aj_path.read_bytes() + b"\n")
        require_rejected(
            lambda: deriver.verify_candidate_aj_source(fake_candidate_aj),
            "mutated Candidate AJ shared identity module",
        )
        rejected += 1
        symlink_candidate_aj = work / "candidate_aj-symlink.py"
        symlink_candidate_aj.symlink_to(candidate_aj_path)
        require_rejected(
            lambda: deriver.verify_candidate_aj_source(symlink_candidate_aj),
            "symlink Candidate AJ shared identity module",
        )
        rejected += 1

        production_output = work / "production-derived-aj.sh"
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
            "validation=candidate-aj-installer-derivation",
            f"foundation_installer_sha256={deriver.AI_INSTALLER_SHA256}",
            f"installer_sha256={AJ_INSTALLER_SHA256}",
            f"candidate_raw_sha256={production_calibration.raw_sha256}",
            f"candidate_raw_size={production_calibration.raw_size}",
            (
                "candidate_artifact_manifest_sha256="
                f"{production_calibration.artifact_manifest_sha256}"
            ),
            f"candidate_padded_sha256={production_calibration.padded_sha256}",
            f"expected_predecessor_sha256={deriver.EXPECTED_AI_PADDED_SHA256}",
            f"artifact_directory={deriver.artifact_directory(production_calibration)}",
            f"boot_filename={deriver.AJ_BOOT_FILENAME}",
            "sole_target_write=one-bounded-16MiB-write",
            "reboot_or_slot_selection=none",
        )
        production_stdout = production.stdout.decode("utf-8")
        if any(line not in production_stdout for line in expected_stdout):
            fail("production derivation output omitted an exact AJ identity")
        if deriver.digest_path(production_output) != AJ_INSTALLER_SHA256:
            fail("production-derived Candidate AJ installer identity changed")
        if stat.S_IMODE(production_output.stat().st_mode) != 0o700:
            fail("production-derived Candidate AJ installer mode is not 0700")
        run(["bash", "-n", os.fspath(production_output)], 0)
        if args.shellcheck:
            run(["shellcheck", "--shell=bash", os.fspath(production_output)], 0)

        override_output = work / "override-must-not-exist.sh"
        run(
            [
                sys.executable,
                os.fspath(deriver_path),
                "--output",
                os.fspath(override_output),
                "--raw-sha256",
                "d" * 64,
            ],
            2,
        )
        if override_output.exists() or override_output.is_symlink():
            fail("rejected production calibration override created output")
        rejected += 1

        # Reconstruct exact AI through its source- and output-pinned deriver.
        ai_path = deriver.reconstruct_ai_installer(repo_root, work)
        ai_data = deriver.read_exact_source(ai_path)
        ai_text = ai_data.decode("utf-8")
        if deriver.digest_path(ai_path) != deriver.AI_INSTALLER_SHA256:
            fail("tracked installer lineage did not reproduce exact Candidate AI")
        if stat.S_IMODE(ai_path.stat().st_mode) != 0o700:
            fail("reconstructed Candidate AI installer mode is not 0700")

        source_output = work / "source-derived-aj.sh"
        run(
            [
                sys.executable,
                os.fspath(deriver_path),
                "--source",
                os.fspath(ai_path),
                "--output",
                os.fspath(source_output),
            ],
            0,
        )
        if source_output.read_bytes() != production_output.read_bytes():
            fail("caller-supplied exact AI and reconstructed lineage differ")

        mutated_ai = work / "mutated-ai.sh"
        mutated_ai.write_bytes(ai_data + b"\n# mutation\n")
        require_rejected(
            lambda: deriver.read_exact_source(mutated_ai),
            "mutated Candidate AI foundation",
        )
        rejected += 1
        symlink_ai = work / "symlink-ai.sh"
        symlink_ai.symlink_to(ai_path)
        require_rejected(
            lambda: deriver.read_exact_source(symlink_ai),
            "symlink Candidate AI foundation",
        )
        rejected += 1

        fake_root = work / "fake-repository"
        fake_deriver = deriver.ai_deriver_path(fake_root)
        fake_deriver.parent.mkdir(parents=True)
        fake_deriver.write_bytes(deriver.ai_deriver_path(repo_root).read_bytes() + b"\n")
        fake_output = work / "fake-output"
        fake_output.mkdir()
        require_rejected(
            lambda: deriver.reconstruct_ai_installer(fake_root, fake_output),
            "mutated Candidate AI deriver lineage",
        )
        rejected += 1
        fake_deriver.unlink()
        fake_deriver.symlink_to(deriver.ai_deriver_path(repo_root))
        symlink_output = work / "symlink-deriver-output"
        symlink_output.mkdir()
        require_rejected(
            lambda: deriver.reconstruct_ai_installer(fake_root, symlink_output),
            "symlink Candidate AI deriver lineage",
        )
        rejected += 1

        invalid_calibrations = (
            deriver.Calibration(
                "TO_PIN_RAW", fixture.raw_size, fixture.artifact_manifest_sha256,
                fixture.padded_sha256,
            ),
            deriver.Calibration(
                fixture.raw_sha256, "TO_PIN_SIZE", fixture.artifact_manifest_sha256,
                fixture.padded_sha256,
            ),
            deriver.Calibration(
                fixture.raw_sha256, fixture.raw_size, "TO_PIN_MANIFEST",
                fixture.padded_sha256,
            ),
            deriver.Calibration(
                fixture.raw_sha256, fixture.raw_size,
                fixture.artifact_manifest_sha256, "TO_PIN_PADDED",
            ),
            deriver.Calibration(
                "z" * 64, fixture.raw_size, fixture.artifact_manifest_sha256,
                fixture.padded_sha256,
            ),
            deriver.Calibration(
                fixture.raw_sha256, fixture.raw_size, "z" * 64,
                fixture.padded_sha256,
            ),
            deriver.Calibration(
                fixture.raw_sha256, fixture.raw_size,
                fixture.artifact_manifest_sha256, "z" * 64,
            ),
            deriver.Calibration(
                fixture.raw_sha256, "not-a-size", fixture.artifact_manifest_sha256,
                fixture.padded_sha256,
            ),
            deriver.Calibration(
                fixture.raw_sha256, "0", fixture.artifact_manifest_sha256,
                fixture.padded_sha256,
            ),
            deriver.Calibration(
                fixture.raw_sha256, str(deriver.BOOT2_SIZE + 1),
                fixture.artifact_manifest_sha256, fixture.padded_sha256,
            ),
            deriver.Calibration(
                deriver.aj.AI_RAW_SHA256, fixture.raw_size,
                fixture.artifact_manifest_sha256, fixture.padded_sha256,
            ),
            deriver.Calibration(
                fixture.raw_sha256, fixture.raw_size,
                deriver.aj.AI_ARTIFACT_MANIFEST_SHA256, fixture.padded_sha256,
            ),
            deriver.Calibration(
                fixture.raw_sha256, fixture.raw_size,
                fixture.artifact_manifest_sha256,
                deriver.EXPECTED_AI_PADDED_SHA256,
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

        derived = deriver.derive_text(ai_data, fixture)
        restored = deriver.restore_ai_contract(derived, fixture)
        if restored != ai_text:
            fail("AJ-to-AI safety-contract round trip changed executable bytes")
        if deriver.digest(restored.encode("utf-8")) != deriver.AI_INSTALLER_SHA256:
            fail("AJ-to-AI round trip did not restore exact AI installer identity")
        if derived != deriver.expected_transform(ai_text, fixture):
            fail("fixture derivation differs from the exact AI-relative transform")
        derived_path = work / "install-candidate-aj-boot2.sh"
        deriver.publish(derived_path, derived)
        if stat.S_IMODE(derived_path.stat().st_mode) != 0o700:
            fail("fixture-derived installer mode is not 0700")
        run(["bash", "-n", os.fspath(derived_path)], 0)
        if args.shellcheck:
            run(["shellcheck", "--shell=bash", os.fspath(derived_path)], 0)

        expected_identity = (
            "usage: install-candidate-aj-boot2.sh",
            deriver.AJ_BOOT_FILENAME,
            f'expected_artifact_name="{deriver.artifact_directory(fixture)}"',
            "candidate-aj-padded-boot2.img",
            "boot2-before-candidate-aj.img",
            "boot2-after-candidate-aj.img",
            "expected_previous_label=AI-installed-readback-verified",
            (
                "readonly AJ_ARTIFACT_MANIFEST_SHA256="
                f"{fixture.artifact_manifest_sha256}"
            ),
            (
                "readonly EXPECTED_CURRENT_AI_PADDED_SHA256="
                f"{deriver.EXPECTED_AI_PADDED_SHA256}"
            ),
            "experiment=2026-07-22-a72-reject-cpu8-request",
        )
        if any(token not in derived for token in expected_identity):
            fail("fixture-derived Candidate AJ identity is incomplete")

        # AI's exact tester transitively executes AH, AG, and AF's complete
        # executable-contract suites. AJ adds focused gates for every named
        # storage invariant plus its new artifact-manifest pin.
        ai_tester = (
            repo_root
            / "experiments/2026-07-22-a72-reject-gate-kernel-split"
            / "scripts/test-installer-derivation.py"
        )
        if deriver.digest_path(ai_tester) != AI_TESTER_SHA256:
            fail("Candidate AI installer mutation suite identity changed")
        ai_command = [sys.executable, os.fspath(ai_tester)]
        if args.shellcheck:
            ai_command.append("--shellcheck")
        ai_result = run(ai_command, 0).stdout.decode("utf-8")
        inherited_markers = (
            "inherited_af_mutations=64-of-64",
            "inherited_ag_mutations=42-of-42",
            "inherited_ah_mutations=58-of-58",
            "ai_mutations_rejected=43-of-43",
            "bounded_target_writes=one",
            "device_contact=none",
            "hardware_write=none",
            "reboot_or_slot_selection=none",
        )
        if any(marker not in ai_result for marker in inherited_markers):
            fail("exact inherited AI/AH/AG/AF suite did not report every gate")

        mutations: tuple[tuple[str, Callable[[str], str]], ...] = (
            (
                "known-good-gemian-kernel-initial",
                lambda text: replace_first_of(
                    text,
                    '[[ "$(uname -r)" == 3.18.41+ ]] || {',
                    '[[ "$(uname -r)" == 3.18.99-mutated ]] || {',
                    1,
                ),
            ),
            (
                "known-good-gemian-kernel-write-gates",
                lambda text: replace_once(
                    text,
                    '[[ "$(uname -r)" == 3.18.41+ ]] || fail '
                    "'remote kernel is not exact known-good Gemian 3.18.41+'",
                    "true # exact recovery kernel gate removed",
                ),
            ),
            (
                "known-good-gemian-root-initial",
                lambda text: replace_once(
                    text,
                    '[[ "$active_root" == /dev/mmcblk0p29 ]] || {',
                    '[[ "$active_root" == /dev/mmcblk0p28 ]] || {',
                ),
            ),
            (
                "known-good-gemian-root-write-gates",
                lambda text: replace_once(
                    text,
                    '[[ "$EXPECTED_ROOT" == /dev/mmcblk0p29 ]] || fail '
                    "'expected root is not exact known-good Gemian /dev/mmcblk0p29'",
                    "true # exact recovery root gate removed",
                ),
            ),
            (
                "capacity",
                lambda text: replace_once(
                    text, "readonly BOOT2_SIZE=16777216", "readonly BOOT2_SIZE=33554432"
                ),
            ),
            (
                "live-gpt-by-partlabel",
                lambda text: replace_once(
                    text,
                    "readlink -f /dev/disk/by-partlabel/boot2",
                    "readlink -f /dev/disk/by-partlabel/boot",
                ),
            ),
            (
                "live-gpt-label-row",
                lambda text: replace_once(
                    text, '$2 == "boot2" { print }', '$2 == "boot" { print }'
                ),
            ),
            (
                "exact-target-size",
                lambda text: replace_once(
                    text,
                    '[[ "$(blockdev --getsize64 "$target")" == "$EXPECTED_SIZE" ]] || \\\n'
                    "\t\tfail 'blockdev size mismatch'",
                    "true # exact target-size gate removed",
                ),
            ),
            (
                "target-writable",
                lambda text: replace_once(
                    text,
                    '[[ -r "$target" && -w "$target" ]] || fail '
                    "'boot2 is not root-readable and writable'",
                    "true # target writable gate removed",
                ),
            ),
            (
                "active-root-identity",
                lambda text: replace_once(
                    text,
                    '[[ "$active_root" == "$EXPECTED_ROOT" ]] || \\\n'
                    '\t\tfail "active root changed: expected=$EXPECTED_ROOT actual=$active_root"',
                    "true # active-root identity gate removed",
                ),
            ),
            (
                "inactive-target",
                lambda text: replace_once(
                    text,
                    '[[ "$active_root" != "$target" ]] || fail '
                    "'boot2 is the active root'",
                    "true # inactive-target gate removed",
                ),
            ),
            (
                "unmounted-target",
                lambda text: replace_once(
                    text,
                    '[[ -z "$mount_matches" ]] || fail \'boot2 is mounted\'',
                    "true # mount gate removed",
                ),
            ),
            (
                "no-swap",
                lambda text: replace_once(
                    text,
                    '[[ "$swap_canonical" != "$target" ]] || fail '
                    "'boot2 is active swap'",
                    "true # swap gate removed",
                ),
            ),
            (
                "no-holders",
                lambda text: replace_once(
                    text,
                    '[[ -z "$holder_entries" ]] || fail \'boot2 has holders\'',
                    "true # holder gate removed",
                ),
            ),
            (
                "power-stability",
                lambda text: replace_once(
                    text,
                    '[[ "$power_second" == "$power_first" ]] || \\\n'
                    '\t\tfail "power changed during stability sample: first=$power_first second=$power_second"',
                    "true # power-stability gate removed",
                ),
            ),
            (
                "external-power",
                lambda text: replace_once(
                    text,
                    '[[ "$ac_online" == 1 || "$usb_online" == 1 ]] || \\\n'
                    '\t\tfail "neither AC nor USB external power is online: $power_first"',
                    "true # external-power gate removed",
                ),
            ),
            (
                "battery-health",
                lambda text: replace_once(
                    text,
                    '[[ "$battery_present" == 1 && "$battery_status" == Full && \\\n'
                    '\t\t"$battery_capacity" == 100 && "$battery_health" == Good ]] || \\\n'
                    '\t\tfail "battery is not present, full, and healthy: $power_first"',
                    "true # battery-health gate removed",
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
                    f"readonly AJ_RAW_SHA256={fixture.raw_sha256}",
                    "readonly AJ_RAW_SHA256=" + "d" * 64,
                ),
            ),
            (
                "candidate-size-pin",
                lambda text: replace_once(
                    text,
                    f"readonly AJ_RAW_SIZE={fixture.raw_size}",
                    "readonly AJ_RAW_SIZE=7000000",
                ),
            ),
            (
                "artifact-manifest-pin",
                lambda text: replace_once(
                    text,
                    (
                        "readonly AJ_ARTIFACT_MANIFEST_SHA256="
                        f"{fixture.artifact_manifest_sha256}"
                    ),
                    "readonly AJ_ARTIFACT_MANIFEST_SHA256=" + "d" * 64,
                ),
            ),
            (
                "artifact-manifest-check",
                lambda text: replace_once(
                    text,
                    '[[ "$candidate_manifest_sha256" == '
                    '"$AJ_ARTIFACT_MANIFEST_SHA256" ]] || \\\n'
                    "\tdie 'candidate SHA256SUMS manifest is not the exact reproduced "
                    "Candidate AJ manifest'",
                    "true # exact artifact-manifest check removed",
                ),
            ),
            (
                "candidate-padded-pin",
                lambda text: replace_once(
                    text,
                    f"readonly AJ_PADDED_SHA256={fixture.padded_sha256}",
                    "readonly AJ_PADDED_SHA256=" + "d" * 64,
                ),
            ),
            (
                "predecessor-pin",
                lambda text: replace_once(
                    text,
                    (
                        "readonly EXPECTED_CURRENT_AI_PADDED_SHA256="
                        f"{deriver.EXPECTED_AI_PADDED_SHA256}"
                    ),
                    "readonly EXPECTED_CURRENT_AI_PADDED_SHA256=" + "d" * 64,
                ),
            ),
            (
                "candidate-filename",
                lambda text: replace_once(
                    text,
                    deriver.AJ_BOOT_FILENAME,
                    deriver.AI_BOOT_FILENAME,
                ),
            ),
            (
                "artifact-directory",
                lambda text: replace_once(
                    text,
                    f'expected_artifact_name="{deriver.artifact_directory(fixture)}"',
                    'expected_artifact_name="candidate-AJ-a72-reject-cpu8-wrong"',
                ),
            ),
            (
                "experiment-identity",
                lambda text: replace_first_of(
                    text,
                    "2026-07-22-a72-reject-cpu8-request",
                    "2026-07-22-a72-reject-gate-kernel-split",
                    2,
                ),
            ),
            (
                "candidate-label",
                lambda text: replace_first_of(
                    text, "candidate_label=AJ", "candidate_label=AI", 2
                ),
            ),
            (
                "predecessor-label",
                lambda text: replace_first_of(
                    text,
                    "AI-installed-readback-verified",
                    "AH-installed-readback-verified",
                    4,
                ),
            ),
            (
                "backup-mode",
                lambda text: replace_once(
                    text,
                    'chmod 0600 "$backup_partial"',
                    'chmod 0644 "$backup_partial"',
                ),
            ),
            (
                "backup-checksum",
                lambda text: replace_once(
                    text,
                    '[[ "$backup_sha256" == "$EXPECTED_CURRENT_AI_PADDED_SHA256" ]] || \\\n'
                    '\tdie "boot2 backup checksum mismatch; inspect $backup_partial"',
                    "true # predecessor backup checksum removed",
                ),
            ),
            (
                "padding-prefix",
                lambda text: replace_once(
                    text,
                    'head -c "$AJ_RAW_SIZE" "$padded" | cmp -s "$candidate" - || \\\n'
                    "\tdie 'padded candidate prefix differs from raw candidate'",
                    "true # padded-prefix gate removed",
                ),
            ),
            (
                "padding-tail",
                lambda text: replace_once(
                    text,
                    "\ttail -c \"$tail_size\" \"$padded\" | od -An -v -tu1 | \\\n"
                    "\t\tawk '{ for (field = 1; field <= NF; field++) if ($field != 0) exit 1 }' || \\\n"
                    "\t\tdie 'padded candidate tail is not all zero'",
                    "\ttrue # zero-tail gate removed",
                ),
            ),
            (
                "padding-hash",
                lambda text: replace_once(
                    text,
                    '[[ "$padded_sha256" == "$AJ_PADDED_SHA256" ]] || \\\n'
                    "\tdie 'zero-padded Candidate AJ checksum is not calibrated'",
                    "true # padded hash gate removed",
                ),
            ),
            (
                "root-stage-mode",
                lambda text: replace_once(
                    text,
                    '[[ "$owner" == root && "$mode" == 400 && '
                    '"$root_stage_size" == "$EXPECTED_SIZE" ]] || \\\n'
                    '\t\tfail "root staging identity mismatch: owner=$owner mode=$mode '
                    'size=$root_stage_size"',
                    "true # immutable root-stage gate removed",
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
                "write-fsync",
                lambda text: replace_once(
                    text,
                    "conv=fsync,notrunc status=none",
                    "conv=notrunc status=none",
                ),
            ),
            (
                "flush",
                lambda text: replace_once(
                    text, 'blockdev --flushbufs "$target"', "true # flush removed"
                ),
            ),
            (
                "readback-stream-size",
                lambda text: replace_once(
                    text,
                    '[[ "$readback_stream_bytes" == "$BOOT2_SIZE" ]] || \\\n'
                    '\tdie "full boot2 readback stream length mismatch; inspect '
                    '$readback_stats"',
                    "true # full readback stream-size gate removed",
                ),
            ),
            (
                "readback-hash",
                lambda text: replace_once(
                    text,
                    '[[ "$readback_sha256" == "$AJ_PADDED_SHA256" ]] || \\\n'
                    '\tdie "full boot2 readback checksum mismatch; inspect '
                    '$readback_partial"',
                    "true # full readback hash gate removed",
                ),
            ),
            (
                "readback-bytes",
                lambda text: replace_once(
                    text,
                    'cmp -s "$padded" "$readback_partial" || \\\n'
                    '\tdie "full boot2 readback differs byte-for-byte; inspect '
                    '$readback_partial"',
                    "true # full readback byte comparison removed",
                ),
            ),
            (
                "boot-id",
                lambda text: replace_first_of(
                    text,
                    '[[ "$(cat /proc/sys/kernel/random/boot_id)" == '
                    '"$EXPECTED_BOOT_ID" ]] ||',
                    "true ||",
                    3,
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
                f"AJ safety adapter mutation: {label}",
            )
            rejected += 1

        narrow_mutation = derived + "\n# unrelated derived mutation\n"
        require_rejected(
            lambda: deriver.validate_exact_delta(ai_text, narrow_mutation, fixture),
            "narrow AI-relative delta mutation",
        )
        rejected += 1

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

    expected_rejections = (
        2 + 2 + 1 + 4 + len(invalid_calibrations) + len(mutations) + 5
    )
    if rejected != expected_rejections:
        fail(
            f"AJ mutation count changed: expected {expected_rejections}, got {rejected}"
        )
    print("validation=candidate-aj-installer-static-mutations")
    print("foundation=exact-reconstructed-candidate-ai")
    print("inherited_af_mutations=64-of-64")
    print("inherited_ag_mutations=42-of-42")
    print("inherited_ah_mutations=58-of-58")
    print("inherited_ai_mutations=43-of-43")
    print(f"aj_mutations_rejected={rejected}-of-{expected_rejections}")
    print("production_calibration=pinned-before-input-path-io")
    print("candidate_manifest=whole-manifest-sha256-pinned")
    print("predecessor=exact-installed-candidate-ai")
    print("recovery_os=exact-gemian-3.18.41+-root-mmcblk0p29")
    print("live_gpt_target=boot2-only")
    print("inactive_unmounted_swap_holders=required")
    print("target_size_writable_power=required")
    print("private_full_backup=mode-0600-checksummed")
    print("padding=exact-16MiB-zero-tail")
    print("write=one-bounded-sync-flush")
    print("readback=full-byte-and-hash-verified")
    print("bash_n=passed")
    print(f"shellcheck={'passed' if args.shellcheck else 'not-requested'}")
    print("device_contact=none")
    print("hardware_write=none")
    print("generated_installer_execution=none")
    print("reboot_or_slot_selection=none")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
