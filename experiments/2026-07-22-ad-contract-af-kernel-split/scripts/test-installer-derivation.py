#!/usr/bin/env python3
"""Static, lineage, storage, and publication tests for AH's installer."""

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


AG_TESTER_SHA256 = (
    "6275b4a8c78ceeea897f79a690d8435b9d84d042c7be0b8b16951a3690e7dcce"
)
AH_INSTALLER_SHA256 = (
    "01768f0decaf621eebfcfbbf02eba64d15f3595207a1ce3c8ea1918f17656c91"
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_deriver(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("candidate_ah_deriver", path)
    if spec is None or spec.loader is None:
        fail("cannot load Candidate AH installer deriver")
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
        help="also require ShellCheck on AG and both derived AH installers",
    )
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    deriver_path = script_dir / "derive-installer.py"
    deriver = load_deriver(deriver_path)
    fixture = deriver.Calibration("a" * 64, "8000000", "b" * 64)
    rejected = 0

    expected_production = (
        "e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197",
        "7385088",
        "f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012",
    )
    actual_production = (
        deriver.AH_RAW_SHA256,
        deriver.AH_RAW_SIZE,
        deriver.AH_PADDED_SHA256,
    )
    if actual_production != expected_production:
        fail("Candidate AH production calibration changed")
    deriver.validate_calibration(deriver.PRODUCTION_CALIBRATION)
    if deriver.AG_PADDED_SHA256 != (
        "63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14"
    ):
        fail("Candidate AH predecessor is not exact installed Candidate AG")

    with tempfile.TemporaryDirectory(prefix="candidate-ah-installer-test.") as raw:
        work = pathlib.Path(raw)

        production_output = work / "production-derived-ah.sh"
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
            "validation=candidate-ah-installer-derivation",
            f"foundation_installer_sha256={deriver.AG_INSTALLER_SHA256}",
            f"installer_sha256={AH_INSTALLER_SHA256}",
            f"candidate_raw_sha256={deriver.AH_RAW_SHA256}",
            f"candidate_raw_size={deriver.AH_RAW_SIZE}",
            f"candidate_padded_sha256={deriver.AH_PADDED_SHA256}",
            f"expected_predecessor_sha256={deriver.AG_PADDED_SHA256}",
            "sole_target_write=one-bounded-16MiB-write",
            "reboot_or_slot_selection=none",
        )
        production_text_output = production.stdout.decode("utf-8")
        if any(line not in production_text_output for line in expected_stdout):
            fail("production derivation output omitted an exact AH identity")
        if deriver.digest_path(production_output) != AH_INSTALLER_SHA256:
            fail("production-derived Candidate AH installer identity changed")
        if stat.S_IMODE(production_output.stat().st_mode) != 0o700:
            fail("production-derived Candidate AH installer mode is not 0700")
        run(["bash", "-n", os.fspath(production_output)], 0)
        if args.shellcheck:
            run(["shellcheck", "--shell=bash", os.fspath(production_output)], 0)

        # There is no executable caller-supplied calibration surface.
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

        # Pin and reproduce AG's complete source lineage before adapting it.
        ag = deriver.reconstruct_ag_installer(repo_root, work)
        ag_data = deriver.read_exact_source(ag)
        ag_text = ag_data.decode("utf-8")
        if deriver.digest_path(ag) != deriver.AG_INSTALLER_SHA256:
            fail("tracked installer lineage did not reproduce exact Candidate AG")
        if stat.S_IMODE(ag.stat().st_mode) != 0o700:
            fail("reconstructed Candidate AG installer mode is not 0700")

        source_output = work / "source-derived-ah.sh"
        run(
            [
                sys.executable,
                os.fspath(deriver_path),
                "--source",
                os.fspath(ag),
                "--output",
                os.fspath(source_output),
            ],
            0,
        )
        if source_output.read_bytes() != production_output.read_bytes():
            fail("caller-supplied exact AG and reconstructed lineage differ")

        mutated_ag = work / "mutated-ag.sh"
        mutated_ag.write_bytes(ag_data + b"\n# mutation\n")
        require_rejected(
            lambda: deriver.read_exact_source(mutated_ag),
            "mutated Candidate AG foundation",
        )
        rejected += 1
        symlink_ag = work / "symlink-ag.sh"
        symlink_ag.symlink_to(ag)
        require_rejected(
            lambda: deriver.read_exact_source(symlink_ag),
            "symlink Candidate AG foundation",
        )
        rejected += 1

        fake_root = work / "fake-repository"
        fake_deriver = deriver.ag_deriver_path(fake_root)
        fake_deriver.parent.mkdir(parents=True)
        fake_deriver.write_bytes(deriver.ag_deriver_path(repo_root).read_bytes() + b"\n")
        bad_deriver_output = work / "bad-deriver-output"
        bad_deriver_output.mkdir()
        require_rejected(
            lambda: deriver.reconstruct_ag_installer(
                fake_root, bad_deriver_output
            ),
            "mutated Candidate AG deriver lineage",
        )
        rejected += 1
        fake_deriver.unlink()
        fake_deriver.symlink_to(deriver.ag_deriver_path(repo_root))
        symlink_deriver_output = work / "symlink-deriver-output"
        symlink_deriver_output.mkdir()
        require_rejected(
            lambda: deriver.reconstruct_ag_installer(
                fake_root, symlink_deriver_output
            ),
            "symlink Candidate AG deriver lineage",
        )
        rejected += 1

        # Calibration is available only as a pure in-process test seam.
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
                deriver.AG_RAW_SHA256, fixture.raw_size, fixture.padded_sha256
            ),
            deriver.Calibration(
                fixture.raw_sha256, fixture.raw_size, deriver.AG_PADDED_SHA256
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

        derived = deriver.derive_text(ag_data, fixture)
        if deriver.restore_ag_contract(derived, fixture) != ag_text:
            fail("AH-to-AG safety-contract round trip changed executable bytes")
        if derived != deriver.expected_transform(ag_text, fixture):
            fail("fixture derivation differs from the exact AG-relative transform")
        derived_path = work / "install-candidate-ah-boot2.sh"
        deriver.publish(derived_path, derived)
        if stat.S_IMODE(derived_path.stat().st_mode) != 0o700:
            fail("fixture-derived installer mode is not 0700")
        run(["bash", "-n", os.fspath(derived_path)], 0)
        if args.shellcheck:
            run(["shellcheck", "--shell=bash", os.fspath(derived_path)], 0)

        expected_identity = (
            "usage: install-candidate-ah-boot2.sh",
            "gemini-ad-contract-af-kernel-split.boot.img",
            "candidate-AH-ad-contract-af-kernel-split-${AH_RAW_SHA256:0:8}",
            "candidate-ah-padded-boot2.img",
            "boot2-before-candidate-ah.img",
            "boot2-after-candidate-ah.img",
            "expected_previous_label=AG-installed-readback-verified",
            (
                "readonly EXPECTED_CURRENT_AG_PADDED_SHA256="
                f"{deriver.AG_PADDED_SHA256}"
            ),
            "experiment=2026-07-22-ad-contract-af-kernel-split",
        )
        if any(token not in derived for token in expected_identity):
            fail("fixture-derived Candidate AH identity is incomplete")

        # Run the byte-pinned inherited AG suite first. It includes AF's exact
        # 64-case suite; AH then tests its reversible adapter independently.
        ag_tester = (
            repo_root
            / "experiments/2026-07-22-simplefb-observation-restoration"
            / "scripts/test-installer-derivation.py"
        )
        if deriver.digest_path(ag_tester) != AG_TESTER_SHA256:
            fail("Candidate AG installer mutation suite identity changed")
        ag_command = [sys.executable, os.fspath(ag_tester)]
        if args.shellcheck:
            ag_command.append("--shellcheck")
        ag_result = run(ag_command, 0).stdout.decode("utf-8")
        if "inherited_af_mutations=64-of-64" not in ag_result:
            fail("exact inherited AF mutation suite did not reject 64 of 64")
        if "ag_mutations_rejected=42-of-42" not in ag_result:
            fail("exact inherited AG mutation suite did not reject 42 of 42")

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
                "target-writable-bypass",
                lambda text: replace_once(
                    text,
                    '[[ -r "$target" && -w "$target" ]] || '
                    "fail 'boot2 is not root-readable and writable'",
                    "true\n\t: 'boot2 is not root-readable and writable'",
                ),
            ),
            (
                "active-root-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$active_root" != "$target" ]] || '
                    "fail 'boot2 is the active root'",
                    "true\n\t: 'boot2 is the active root'",
                ),
            ),
            (
                "mount-bypass",
                lambda text: replace_once(
                    text,
                    '[[ -z "$mount_matches" ]] || fail \'boot2 is mounted\'',
                    "true\n\t: 'boot2 is mounted'",
                ),
            ),
            (
                "swap-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$swap_canonical" != "$target" ]] || '
                    "fail 'boot2 is active swap'",
                    "true\n\t\t: 'boot2 is active swap'",
                ),
            ),
            (
                "holders-bypass",
                lambda text: replace_once(
                    text,
                    '[[ -z "$holder_entries" ]] || fail \'boot2 has holders\'',
                    "true\n\t: 'boot2 has holders'",
                ),
            ),
            (
                "power-stability-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$power_second" == "$power_first" ]] || \\\n'
                    '\t\tfail "power changed during stability sample: '
                    'first=$power_first second=$power_second"',
                    'true\n\t: "power changed during stability sample: '
                    'first=$power_first second=$power_second"',
                ),
            ),
            (
                "external-power-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$ac_online" == 1 || "$usb_online" == 1 ]] || \\\n'
                    '\t\tfail "neither AC nor USB external power is online: '
                    '$power_first"',
                    'true\n\t: "neither AC nor USB external power is online: '
                    '$power_first"',
                ),
            ),
            (
                "battery-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$battery_present" == 1 && "$battery_status" == Full && \\\n'
                    '\t\t"$battery_capacity" == 100 && '
                    '"$battery_health" == Good ]] || \\\n'
                    '\t\tfail "battery is not present, full, and healthy: '
                    '$power_first"',
                    'true\n\t: "battery is not present, full, and healthy: '
                    '$power_first"',
                ),
            ),
            (
                "host-key",
                lambda text: replace_once(
                    text, "StrictHostKeyChecking=yes", "StrictHostKeyChecking=no"
                ),
            ),
            (
                "identity-mode-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$(file_mode "$identity")" == 600 ]] || '
                    "die 'Gemini identity mode is not 0600'",
                    "true\n: 'Gemini identity mode is not 0600'",
                ),
            ),
            (
                "predecessor-pin",
                lambda text: replace_once(
                    text,
                    (
                        "readonly EXPECTED_CURRENT_AG_PADDED_SHA256="
                        f"{deriver.AG_PADDED_SHA256}"
                    ),
                    "readonly EXPECTED_CURRENT_AG_PADDED_SHA256=" + "c" * 64,
                ),
            ),
            (
                "predecessor-host-guard-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$already_current" == no && "$probe_sha256" == '
                    '"$EXPECTED_CURRENT_AG_PADDED_SHA256" ]] || \\\n'
                    "\tdie 'initial gate returned an inconsistent "
                    "AG-installed-readback-verified predecessor checksum'",
                    "true\n: 'initial gate returned an inconsistent "
                    "AG-installed-readback-verified predecessor checksum'",
                ),
            ),
            (
                "prewrite-checksum-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$prewrite_target_sha256" == '
                    '"$EXPECTED_CURRENT_SHA256" ]] || \\\n'
                    '\t\tfail "boot2 changed at the final pre-write '
                    'checksum: $prewrite_target_sha256"',
                    'true\n\t: "boot2 changed at the final pre-write '
                    'checksum: $prewrite_target_sha256"',
                ),
            ),
            (
                "padding-prefix-bypass",
                lambda text: replace_once(
                    text,
                    'head -c "$AH_RAW_SIZE" "$padded" | '
                    'cmp -s "$candidate" - || \\\n'
                    "\tdie 'padded candidate prefix differs from raw candidate'",
                    "true\n: 'padded candidate prefix differs from raw candidate'",
                ),
            ),
            (
                "padding-zero-tail-bypass",
                lambda text: replace_once(
                    text,
                    'tail -c "$tail_size" "$padded" | od -An -v -tu1 | \\\n',
                    'head -c "$tail_size" "$padded" | od -An -v -tu1 | \\\n',
                ),
            ),
            (
                "padding-checksum-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$padded_sha256" == "$AH_PADDED_SHA256" ]] || \\\n'
                    "\tdie 'zero-padded Candidate AH checksum is not calibrated'",
                    "true\n: 'zero-padded Candidate AH checksum is not calibrated'",
                ),
            ),
            (
                "backup-mode",
                lambda text: replace_once(
                    text, 'chmod 0600 "$backup_partial"', 'chmod 0644 "$backup_partial"'
                ),
            ),
            (
                "backup-checksum-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$backup_sha256" == '
                    '"$EXPECTED_CURRENT_AG_PADDED_SHA256" ]] || \\\n'
                    '\tdie "boot2 backup checksum mismatch; inspect '
                    '$backup_partial"',
                    'true\n: "boot2 backup checksum mismatch; inspect '
                    '$backup_partial"',
                ),
            ),
            (
                "backup-durable-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$(checked_sha256_file "$backup")" == '
                    '"$backup_sha256" ]] || \\\n'
                    "\tdie 'durably flushed pre-write backup failed checksum "
                    "revalidation'",
                    "true\n: 'durably flushed pre-write backup failed checksum "
                    "revalidation'",
                ),
            ),
            (
                "boot-id-stability-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$(cat /proc/sys/kernel/random/boot_id)" == '
                    '"$EXPECTED_BOOT_ID" ]] || \\\n'
                    "\t\tfail 'boot ID changed immediately before write'",
                    "true\n\t: 'boot ID changed immediately before write'",
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
                "readback-size-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$readback_stream_bytes" == "$BOOT2_SIZE" ]] || \\\n'
                    '\tdie "full boot2 readback stream length mismatch; '
                    'inspect $readback_stats"',
                    'true\n: "full boot2 readback stream length mismatch; '
                    'inspect $readback_stats"',
                ),
            ),
            (
                "readback-checksum-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$readback_sha256" == "$AH_PADDED_SHA256" ]] || \\\n'
                    '\tdie "full boot2 readback checksum mismatch; '
                    'inspect $readback_partial"',
                    'true\n: "full boot2 readback checksum mismatch; '
                    'inspect $readback_partial"',
                ),
            ),
            (
                "readback-bytes-bypass",
                lambda text: replace_once(
                    text,
                    'cmp -s "$padded" "$readback_partial" || \\\n'
                    '\tdie "full boot2 readback differs byte-for-byte; '
                    'inspect $readback_partial"',
                    'true\n: "full boot2 readback differs byte-for-byte; '
                    'inspect $readback_partial"',
                ),
            ),
            (
                "readback-durable-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$(checked_sha256_file "$readback")" == '
                    '"$readback_sha256" ]] || \\\n'
                    "\tdie 'durably flushed full local readback failed checksum "
                    "revalidation'",
                    "true\n: 'durably flushed full local readback failed checksum "
                    "revalidation'",
                ),
            ),
            (
                "final-target-checksum-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$post_sha256" == "$AH_PADDED_SHA256" ]] || '
                    "die 'final target checksum mismatch'",
                    "true\n: 'final target checksum mismatch'",
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
            (
                "candidate-pin",
                lambda text: replace_once(
                    text,
                    f"readonly AH_RAW_SHA256={fixture.raw_sha256}",
                    "readonly AH_RAW_SHA256=" + "c" * 64,
                ),
            ),
            (
                "candidate-filename",
                lambda text: replace_once(
                    text,
                    "gemini-ad-contract-af-kernel-split.boot.img",
                    "gemini-simplefb-observation-restoration.boot.img",
                ),
            ),
        )
        for label, mutate in mutations:
            mutated = mutate(derived)
            require_rejected(
                lambda mutated=mutated: deriver.validate_safety(mutated, fixture),
                f"AH safety adapter mutation: {label}",
            )
            rejected += 1

        narrow_mutation = derived + "\n# unrelated derived mutation\n"
        require_rejected(
            lambda: deriver.validate_exact_delta(
                ag_text, narrow_mutation, fixture
            ),
            "narrow AG-relative delta mutation",
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
            f"AH mutation count changed: expected {expected_rejections}, got {rejected}"
        )
    print("validation=candidate-ah-installer-static-mutations")
    print("foundation=exact-reconstructed-candidate-ag")
    print("inherited_af_mutations=64-of-64")
    print("inherited_ag_mutations=42-of-42")
    print(f"ah_mutations_rejected={rejected}-of-{expected_rejections}")
    print("production_calibration=pinned-and-derived")
    print("test_calibration=pure-in-process-only")
    print("production_override_surface=none")
    print("predecessor=exact-installed-candidate-ag")
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
