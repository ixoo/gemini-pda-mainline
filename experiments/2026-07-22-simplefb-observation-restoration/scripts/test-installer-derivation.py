#!/usr/bin/env python3
"""Static, lineage, and mutation tests for Candidate AG's installer."""

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


AF_TESTER_SHA256 = (
    "e19e84da4415dca5f460a9dae066120f111b12f82f955d943055a52351b7c42f"
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_deriver(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("candidate_ag_deriver", path)
    if spec is None or spec.loader is None:
        fail("cannot load Candidate AG installer deriver")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shellcheck",
        action="store_true",
        help="also require ShellCheck on AF and AG derived installers",
    )
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    deriver_path = script_dir / "derive-installer.py"
    deriver = load_deriver(deriver_path)
    fixture = deriver.Calibration("a" * 64, "8000000", "b" * 64)
    rejected = 0

    expected_production = (
        "0552986c885d89fd65d05f3da8513040f756c9cfc84b1b30e1e085ee68238a91",
        "7387136",
        "63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14",
    )
    actual_production = (
        deriver.AG_RAW_SHA256,
        deriver.AG_RAW_SIZE,
        deriver.AG_PADDED_SHA256,
    )
    if actual_production != expected_production:
        fail("Candidate AG production calibration changed")

    with tempfile.TemporaryDirectory(prefix="candidate-ag-installer-test.") as raw:
        work = pathlib.Path(raw)
        production_output = work / "production-derived-ag.sh"
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
            "validation=candidate-ag-installer-derivation",
            f"foundation_installer_sha256={deriver.AF_INSTALLER_SHA256}",
            f"candidate_raw_sha256={deriver.AG_RAW_SHA256}",
            f"candidate_raw_size={deriver.AG_RAW_SIZE}",
            f"candidate_padded_sha256={deriver.AG_PADDED_SHA256}",
            f"expected_predecessor_sha256={deriver.AF_PADDED_SHA256}",
            "sole_target_write=one-bounded-16MiB-write",
            "reboot_or_slot_selection=none",
        )
        production_text_output = production.stdout.decode("utf-8")
        if any(line not in production_text_output for line in expected_stdout):
            fail("production derivation output omitted an exact AG identity")
        if stat.S_IMODE(production_output.stat().st_mode) != 0o700:
            fail("production-derived installer mode is not 0700")
        run(["bash", "-n", os.fspath(production_output)], 0)
        if args.shellcheck:
            run(["shellcheck", "--shell=bash", os.fspath(production_output)], 0)

        # The production executable deliberately has no caller-supplied hash
        # or predecessor override surface.
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
        if override_output.exists():
            fail("rejected production calibration override created output")

        af = deriver.reconstruct_af_installer(repo_root, work)
        af_data = deriver.read_exact_source(af)
        af_text = af_data.decode("utf-8")
        if deriver.digest_path(af) != deriver.AF_INSTALLER_SHA256:
            fail("tracked installer lineage did not reproduce exact Candidate AF")

        source_output = work / "source-derived-ag.sh"
        run(
            [
                sys.executable,
                os.fspath(deriver_path),
                "--source",
                os.fspath(af),
                "--output",
                os.fspath(source_output),
            ],
            0,
        )
        if source_output.read_bytes() != production_output.read_bytes():
            fail("caller-supplied exact AF and reconstructed lineage differ")

        # Caller-supplied AF is independently hash- and type-pinned.
        mutated_af = work / "mutated-af.sh"
        mutated_af.write_bytes(af_data + b"\n# mutation\n")
        try:
            deriver.read_exact_source(mutated_af)
        except ValueError:
            rejected += 1
        else:
            fail("mutated Candidate AF foundation was accepted")
        symlink_af = work / "symlink-af.sh"
        symlink_af.symlink_to(af)
        try:
            deriver.read_exact_source(symlink_af)
        except ValueError:
            rejected += 1
        else:
            fail("symlink Candidate AF foundation was accepted")

        derived = deriver.derive_text(af_data, fixture)
        if deriver.restore_af_contract(derived, fixture) != af_text:
            fail("AG-to-AF safety-contract round trip changed executable bytes")
        derived_path = work / "install-candidate-ag-boot2.sh"
        deriver.publish(derived_path, derived)
        if stat.S_IMODE(derived_path.stat().st_mode) != 0o700:
            fail("fixture-derived installer mode is not 0700")
        run(["bash", "-n", os.fspath(derived_path)], 0)
        if args.shellcheck:
            run(["shellcheck", "--shell=bash", os.fspath(derived_path)], 0)

        expected_identity = (
            "usage: install-candidate-ag-boot2.sh",
            "gemini-simplefb-observation-restoration.boot.img",
            'candidate-AG-simplefb-restoration-${AG_RAW_SHA256:0:8}',
            "candidate-ag-padded-boot2.img",
            "boot2-before-candidate-ag.img",
            "boot2-after-candidate-ag.img",
            "expected_previous_label=AF-installed-readback-verified",
            (
                "readonly EXPECTED_CURRENT_AF_PADDED_SHA256="
                f"{deriver.AF_PADDED_SHA256}"
            ),
            "experiment=2026-07-22-simplefb-observation-restoration",
        )
        if any(token not in derived for token in expected_identity):
            fail("fixture-derived Candidate AG identity is incomplete")

        # First validate the exact inherited AF contract and all of its focused
        # negative cases. AG then tests its reversible adapter independently.
        af_tester = (
            repo_root
            / "experiments/2026-07-22-cortex-a72-observer-initcall-diagnostic"
            / "scripts/test-installer-derivation.py"
        )
        if deriver.digest_path(af_tester) != AF_TESTER_SHA256:
            fail("Candidate AF installer mutation suite identity changed")
        af_command = [sys.executable, os.fspath(af_tester)]
        if args.shellcheck:
            af_command.append("--shellcheck")
        af_result = run(af_command, 0).stdout.decode("utf-8")
        if "mutations_rejected=64-of-64" not in af_result:
            fail("exact inherited AF mutation suite did not reject 64 of 64")

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
                        "readonly EXPECTED_CURRENT_AF_PADDED_SHA256="
                        f"{deriver.AF_PADDED_SHA256}"
                    ),
                    "readonly EXPECTED_CURRENT_AF_PADDED_SHA256=" + "c" * 64,
                ),
            ),
            (
                "predecessor-host-guard-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$already_current" == no && "$probe_sha256" == '
                    '"$EXPECTED_CURRENT_AF_PADDED_SHA256" ]] || \\\n'
                    "\tdie 'initial gate returned an inconsistent "
                    "AF-installed-readback-verified predecessor checksum'",
                    "true\n: 'initial gate returned an inconsistent "
                    "AF-installed-readback-verified predecessor checksum'",
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
                    'head -c "$AG_RAW_SIZE" "$padded" | '
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
                    '[[ "$padded_sha256" == "$AG_PADDED_SHA256" ]] || \\\n'
                    "\tdie 'zero-padded Candidate AG checksum is not calibrated'",
                    "true\n: 'zero-padded Candidate AG checksum is not calibrated'",
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
                    '"$EXPECTED_CURRENT_AF_PADDED_SHA256" ]] || \\\n'
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
                    '[[ "$readback_sha256" == "$AG_PADDED_SHA256" ]] || \\\n'
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
                    '[[ "$post_sha256" == "$AG_PADDED_SHA256" ]] || '
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
                    f"readonly AG_RAW_SHA256={fixture.raw_sha256}",
                    "readonly AG_RAW_SHA256=" + "c" * 64,
                ),
            ),
            (
                "candidate-filename",
                lambda text: replace_once(
                    text,
                    "gemini-simplefb-observation-restoration.boot.img",
                    "gemini-a72-observer-initcall-diagnostic.boot.img",
                ),
            ),
        )
        for label, mutate in mutations:
            mutated = mutate(derived)
            try:
                deriver.validate_safety(mutated, fixture)
            except ValueError:
                rejected += 1
            else:
                fail(f"AG safety adapter accepted mutation: {label}")

        narrow_mutation = derived + "\n# unrelated derived mutation\n"
        try:
            deriver.validate_exact_delta(af_text, narrow_mutation, fixture)
        except ValueError:
            rejected += 1
        else:
            fail("narrow AF-relative delta mutation was accepted")

        try:
            deriver.publish(derived_path, derived)
        except FileExistsError:
            rejected += 1
        else:
            fail("installer publication overwrote an existing file")

    expected_rejections = 2 + len(mutations) + 2
    if rejected != expected_rejections:
        fail(
            f"AG mutation count changed: expected {expected_rejections}, got {rejected}"
        )
    print("validation=candidate-ag-installer-static-mutations")
    print("foundation=exact-reconstructed-candidate-af")
    print("inherited_af_mutations=64-of-64")
    print(f"ag_mutations_rejected={rejected}-of-{expected_rejections}")
    print("production_calibration=pinned-and-derived")
    print("production_override_surface=none")
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
