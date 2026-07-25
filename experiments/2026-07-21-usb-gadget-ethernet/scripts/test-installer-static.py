#!/usr/bin/env python3
"""Exercise Candidate AC's installer chain without contacting hardware."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

from ac_contract import (  # noqa: E402
    AB_BOOT_SHA256,
    AB_BOOT_SIZE,
    BOOT2_CAPACITY,
    digest_path,
    read_regular,
)


AA_R1_INSTALLER_SHA256 = "f081ef03b2dce68d28458eacdcc184a5550c88eeb75579fab61359e936a40f9f"
AB_INNER_INSTALLER_SHA256 = "260c7d907cdd7656b664d71a6564109a6ed03fcb95bf3e5c6da8bcc3bff4050c"
AB_PADDED_SHA256 = "b58c0347d34a3fd9031c74cb03447dd7a6fc630d5b8ea2b7eabc36827e754350"
MATERIALIZER_SHA256 = "4199517680e63b1d793b7ed7e5c61ca82326a06159d5e057cc708761cc0e540c"
AB_DERIVER_SHA256 = "0ca386dca403da51ea700dc3a697e13ddcfccafc257167afa4d37d940f50d7d7"
RAW_FIXTURE_BYTES = b"Candidate AC installer coherent raw fixture\n"
RAW_FIXTURE = hashlib.sha256(RAW_FIXTURE_BYTES).hexdigest()
RAW_SIZE_FIXTURE = len(RAW_FIXTURE_BYTES)


def load_calibrator(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("ac_installer_calibrator", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load Candidate AC installer calibrator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(
    command: list[str],
    expected: int,
    *,
    environment_updates: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if environment_updates:
        environment.update(environment_updates)
    result = subprocess.run(command, capture_output=True, check=False, env=environment)
    if result.returncode != expected:
        raise RuntimeError(
            f"unexpected status {result.returncode}, expected {expected}: {command}\n"
            f"stdout={result.stdout.decode(errors='replace')}\n"
            f"stderr={result.stderr.decode(errors='replace')}"
        )
    return result


def derive_command(
    deriver: pathlib.Path,
    source: pathlib.Path,
    output: pathlib.Path,
    *,
    raw_hash: str,
    raw_size: str,
    padded_hash: str,
) -> list[str]:
    return [
        sys.executable,
        os.fspath(deriver),
        "--source",
        os.fspath(source),
        "--output",
        os.fspath(output),
        "--raw-sha256",
        raw_hash,
        "--raw-size",
        raw_size,
        "--padded-sha256",
        padded_hash,
    ]


def copy_dependency(source: pathlib.Path, target: pathlib.Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    target.chmod(0o755)


def main() -> int:
    script_dir = pathlib.Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    template = script_dir / "install-candidate-ac-boot2.sh.in"
    calibrator_path = script_dir / "calibrate-installer.py"
    ac_deriver = script_dir / "derive-installer.py"
    materializer = (
        repo_root
        / "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/"
        "materialize-aa-r1-installer.py"
    )
    ab_deriver = (
        repo_root
        / "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/"
        "derive-installer.py"
    )
    try:
        if digest_path(materializer) != MATERIALIZER_SHA256:
            raise ValueError("exact AA r1 installer materializer changed")
        if digest_path(ab_deriver) != AB_DERIVER_SHA256:
            raise ValueError("exact Candidate AB installer deriver changed")
        template_data = read_regular(template, "uncalibrated AC wrapper", mode=0o644)
        calibrator = load_calibrator(calibrator_path)
        padded_fixture = calibrator.padded_digest(RAW_FIXTURE_BYTES)
        if padded_fixture == AB_PADDED_SHA256:
            raise ValueError("static AC padded fixture equals exact AB predecessor")

        placeholder = run(
            [
                "bash",
                os.fspath(template),
                "--repo-root",
                os.fspath(repo_root),
                "--help",
            ],
            2,
        )
        if b"calibration placeholder remains" not in placeholder.stderr:
            raise ValueError("uncalibrated wrapper did not fail at its placeholder gate")

        with tempfile.TemporaryDirectory(prefix="candidate-ac-installer-static.") as raw:
            temp = pathlib.Path(raw)
            aa_installer = temp / "install-candidate-aa-r1-boot2.sh"
            run(
                [
                    sys.executable,
                    os.fspath(materializer),
                    "--output",
                    os.fspath(aa_installer),
                ],
                0,
            )
            if digest_path(aa_installer) != AA_R1_INSTALLER_SHA256:
                raise ValueError("reconstructed exact AA r1 installer changed")

            ab_inner = temp / "install-candidate-ab-inner-boot2.sh"
            run(
                derive_command(
                    ab_deriver,
                    aa_installer,
                    ab_inner,
                    raw_hash=AB_BOOT_SHA256,
                    raw_size=str(AB_BOOT_SIZE),
                    padded_hash=AB_PADDED_SHA256,
                ),
                0,
            )
            run(["bash", "-n", os.fspath(ab_inner)], 0)
            if digest_path(ab_inner) != AB_INNER_INSTALLER_SHA256:
                raise ValueError("derived exact Candidate AB installer changed")

            first = temp / "install-candidate-ac-inner.first.sh"
            second = temp / "install-candidate-ac-inner.second.sh"
            first_command = derive_command(
                ac_deriver,
                ab_inner,
                first,
                raw_hash=RAW_FIXTURE,
                raw_size=str(RAW_SIZE_FIXTURE),
                padded_hash=padded_fixture,
            )
            second_command = list(first_command)
            second_command[second_command.index(os.fspath(first))] = os.fspath(second)
            run(first_command, 0)
            run(second_command, 0)
            run(["bash", "-n", os.fspath(first)], 0)
            if first.read_bytes() != second.read_bytes():
                raise ValueError("two Candidate AC inner derivations differ")
            if stat.S_IMODE(first.stat().st_mode) != 0o700:
                raise ValueError("derived Candidate AC inner mode is not 0700")
            inner_sha256 = digest_path(first)
            inner_text = first.read_text(encoding="utf-8")
            exact_inner_counts = {
                f"readonly AC_RAW_SHA256={RAW_FIXTURE}": 1,
                f"readonly AC_RAW_SIZE={RAW_SIZE_FIXTURE}": 1,
                f"readonly AC_PADDED_SHA256={padded_fixture}": 1,
                "readonly EXPECTED_CURRENT_AB_PADDED_SHA256="
                + AB_PADDED_SHA256: 1,
                "gemini-usb-gadget-ethernet.boot.img": 1,
                "candidate-AC-usb-gadget-ethernet-final-${AC_RAW_SHA256:0:8}": 1,
                'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4': 1,
                "expected_previous_label=AB-hardware-passed": 1,
                "candidate_label=AC": 2,
                "reboot_or_shutdown_performed=no": 2,
            }
            for token, count in exact_inner_counts.items():
                if inner_text.count(token) != count:
                    raise ValueError(f"AC inner token count changed: {token!r}")
            if inner_text.count('of="$target"') != 1:
                raise ValueError("Candidate AC inner gained another target write")
            forbidden_inner = (
                "Candidate AB",
                "candidate-ab",
                "readonly AB_RAW",
                "readonly AB_PADDED",
                "EXPECTED_CURRENT_AA_R1",
                "gemini-mt6797-kernel-restart.boot.img",
                "candidate_label=AB",
            )
            if any(token in inner_text for token in forbidden_inner):
                raise ValueError("Candidate AC inner retained AB target identity")
            if "sysrq-trigger" in inner_text or re.search(
                r"(?m)^[ \t]*(?:sudo[ \t]+)?"
                r"(?:reboot|shutdown|poweroff|halt|kexec)(?:[ \t]|$)",
                inner_text,
            ):
                raise ValueError("Candidate AC inner can reboot or power off the device")

            values = {
                "AC_RAW_SHA256": RAW_FIXTURE,
                "AC_RAW_SIZE": str(RAW_SIZE_FIXTURE),
                "AC_PADDED_SHA256": padded_fixture,
                "AC_INNER_INSTALLER_SHA256": inner_sha256,
                "MATERIALIZER_SHA256": digest_path(materializer),
                "AB_DERIVER_SHA256": digest_path(ab_deriver),
                "AC_DERIVER_SHA256": digest_path(ac_deriver),
            }
            wrapper_data = calibrator.render_wrapper(template_data, values)
            if calibrator.render_wrapper(template_data, values) != wrapper_data:
                raise ValueError("two Candidate AC wrapper renderings differ")
            wrapper = temp / "install-candidate-ac-boot2.sh"
            calibrator.publish(wrapper, wrapper_data)
            run(["bash", "-n", os.fspath(wrapper)], 0)
            if stat.S_IMODE(wrapper.stat().st_mode) != 0o700:
                raise ValueError("calibrated Candidate AC wrapper mode is not 0700")
            wrapper_text = wrapper.read_text(encoding="utf-8")
            wrapper_tokens = (
                'export GEMINI_REPO_ROOT="$repo_root"',
                '"$ac_inner" "${installer_args[@]}"',
                f"readonly AC_INNER_INSTALLER_SHA256={inner_sha256}",
                f"readonly MATERIALIZER_SHA256={digest_path(materializer)}",
                f"readonly AB_DERIVER_SHA256={digest_path(ab_deriver)}",
                f"readonly AC_DERIVER_SHA256={digest_path(ac_deriver)}",
                f"readonly AB_INNER_INSTALLER_SHA256={AB_INNER_INSTALLER_SHA256}",
                f"readonly AB_PADDED_SHA256={AB_PADDED_SHA256}",
            )
            if any(wrapper_text.count(token) != 1 for token in wrapper_tokens):
                raise ValueError("Candidate AC wrapper reconstruction contract changed")
            if 'of="$target"' in wrapper_text or "sysrq-trigger" in wrapper_text:
                raise ValueError("Candidate AC wrapper gained a direct hardware write")

            ssh_marker = temp / "ssh-was-called"
            stub_bin = temp / "stub-bin"
            stub_bin.mkdir()
            ssh_stub = stub_bin / "ssh"
            ssh_stub.write_text(
                "#!/usr/bin/env sh\nprintf called >\"$GEMINI_AC_SSH_MARKER\"\nexit 97\n",
                encoding="utf-8",
            )
            ssh_stub.chmod(0o755)
            guarded_environment = {
                "PATH": os.fspath(stub_bin) + os.pathsep + os.environ.get("PATH", ""),
                "GEMINI_AC_SSH_MARKER": os.fspath(ssh_marker),
            }
            run(
                [
                    os.fspath(wrapper),
                    "--repo-root",
                    os.fspath(repo_root),
                    "--help",
                ],
                0,
                environment_updates=guarded_environment,
            )
            if ssh_marker.exists():
                raise ValueError("wrapper help path contacted SSH")
            run([os.fspath(wrapper), "--help"], 2)

            wrong_values = dict(values)
            wrong_values["MATERIALIZER_SHA256"] = "0" * 64
            wrong_wrapper = temp / "install-candidate-ac-wrong-hash.sh"
            calibrator.publish(
                wrong_wrapper, calibrator.render_wrapper(template_data, wrong_values)
            )
            run(
                [
                    os.fspath(wrong_wrapper),
                    "--repo-root",
                    os.fspath(repo_root),
                    "--help",
                ],
                2,
                environment_updates=guarded_environment,
            )
            if ssh_marker.exists():
                raise ValueError("dependency-hash rejection contacted SSH")

            fake_repo = temp / "fake-repo"
            fake_materializer = (
                fake_repo
                / "experiments/2026-07-20-mt6797-kernel-restart-diagnostic/scripts/"
                "materialize-aa-r1-installer.py"
            )
            fake_ab_deriver = fake_materializer.parent / "derive-installer.py"
            fake_ac_deriver = (
                fake_repo
                / "experiments/2026-07-21-usb-gadget-ethernet/scripts/"
                "derive-installer.py"
            )
            copy_dependency(materializer, fake_materializer)
            copy_dependency(ab_deriver, fake_ab_deriver)
            copy_dependency(ac_deriver, fake_ac_deriver)
            fake_materializer.write_bytes(fake_materializer.read_bytes() + b"# mutation\n")
            run(
                [
                    os.fspath(wrapper),
                    "--repo-root",
                    os.fspath(fake_repo),
                    "--help",
                ],
                2,
                environment_updates=guarded_environment,
            )
            if ssh_marker.exists():
                raise ValueError("dependency-content rejection contacted SSH")

            artifact = temp / f"candidate-AC-usb-gadget-ethernet-final-{RAW_FIXTURE[:8]}"
            artifact.mkdir(mode=0o700)
            candidate = artifact / "gemini-usb-gadget-ethernet.boot.img"
            candidate.write_bytes(RAW_FIXTURE_BYTES + b"mutation")
            (artifact / "SHA256SUMS").write_text(
                f"{hashlib.sha256(candidate.read_bytes()).hexdigest()}  ./{candidate.name}\n",
                encoding="ascii",
            )
            run(
                [
                    os.fspath(wrapper),
                    "--repo-root",
                    os.fspath(repo_root),
                    "--target",
                    "invalid@127.0.0.1",
                    "--candidate",
                    os.fspath(candidate),
                    "--backup-dir",
                    "artifacts/device-partitions/candidate-ac-static-never",
                ],
                2,
                environment_updates=guarded_environment,
            )
            if ssh_marker.exists():
                raise ValueError("candidate-mutation rejection contacted SSH")

            run(first_command, 2)
            mutated_ab = temp / "mutated-ab-inner.sh"
            mutated_ab.write_bytes(ab_inner.read_bytes() + b"# mutation\n")
            run(
                derive_command(
                    ac_deriver,
                    mutated_ab,
                    temp / "mutated-ab.out",
                    raw_hash=RAW_FIXTURE,
                    raw_size=str(RAW_SIZE_FIXTURE),
                    padded_hash=padded_fixture,
                ),
                2,
            )
            symlink_ab = temp / "symlink-ab-inner.sh"
            symlink_ab.symlink_to(ab_inner)
            run(
                derive_command(
                    ac_deriver,
                    symlink_ab,
                    temp / "symlink-ab.out",
                    raw_hash=RAW_FIXTURE,
                    raw_size=str(RAW_SIZE_FIXTURE),
                    padded_hash=padded_fixture,
                ),
                2,
            )
            run(
                derive_command(
                    ac_deriver,
                    ab_inner,
                    temp / "predecessor-raw.out",
                    raw_hash=AB_BOOT_SHA256,
                    raw_size=str(RAW_SIZE_FIXTURE),
                    padded_hash=padded_fixture,
                ),
                2,
            )
            run(
                derive_command(
                    ac_deriver,
                    ab_inner,
                    temp / "predecessor-padded.out",
                    raw_hash=RAW_FIXTURE,
                    raw_size=str(RAW_SIZE_FIXTURE),
                    padded_hash=AB_PADDED_SHA256,
                ),
                2,
            )
            run(
                derive_command(
                    ac_deriver,
                    ab_inner,
                    temp / "malformed.out",
                    raw_hash="not-a-sha256",
                    raw_size=str(RAW_SIZE_FIXTURE),
                    padded_hash=padded_fixture,
                ),
                2,
            )
            run(
                derive_command(
                    ac_deriver,
                    ab_inner,
                    temp / "oversized.out",
                    raw_hash=RAW_FIXTURE,
                    raw_size=str(BOOT2_CAPACITY + 1),
                    padded_hash=padded_fixture,
                ),
                2,
            )
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("placeholder_fail_closed=PASS")
    print("exact_aa_r1_reconstruction=PASS")
    print("exact_ab_inner_reconstruction=PASS")
    print("exact_ab_inner_sha256=260c7d907cdd7656b664d71a6564109a6ed03fcb95bf3e5c6da8bcc3bff4050c")
    print("deterministic_ac_inner_derivation=PASS")
    print("sole_bounded_target_write=PASS")
    print("exact_ab_predecessor=PASS")
    print("no_automatic_reboot=PASS")
    print("deterministic_outer_wrapper=PASS")
    print("outer_wrapper_help_no_device=PASS")
    print("dependency_hash_mutation_rejection=PASS")
    print("dependency_content_mutation_rejection=PASS")
    print("candidate_mutation_rejection=PASS")
    print("foundation_mutation_and_symlink_rejection=PASS")
    print("predecessor_identity_rejection=PASS")
    print("malformed_and_size_boundary_rejection=PASS")
    print("device_contact=none")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
