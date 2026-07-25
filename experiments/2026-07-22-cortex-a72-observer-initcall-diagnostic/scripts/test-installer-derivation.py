#!/usr/bin/env python3
"""Static and mutation tests for Candidate AF's installer derivation."""

from __future__ import annotations

import argparse
import importlib.util
import os
import pathlib
import stat
import subprocess
import sys
import tempfile


def fail(message: str) -> None:
    raise RuntimeError(message)


def load_deriver(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("candidate_af_deriver", path)
    if spec is None or spec.loader is None:
        fail("cannot load Candidate AF installer deriver")
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
        help="also require ShellCheck on the fixture-derived installer",
    )
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    deriver_path = script_dir / "derive-installer.py"
    deriver = load_deriver(deriver_path)
    fixture = deriver.Calibration("a" * 64, "8000000", "b" * 64)
    rejected = 0

    with tempfile.TemporaryDirectory(prefix="candidate-af-installer-test.") as raw:
        work = pathlib.Path(raw)

        # Production must refuse all TO_PIN states before lineage reconstruction,
        # publication, SSH, or any installer behavior. A partially pinned state
        # is invalid; a fully calibrated future state must derive successfully.
        production_output = work / "production-derived-af.sh"
        production_values = (
            deriver.AF_RAW_SHA256,
            deriver.AF_RAW_SIZE,
            deriver.AF_PADDED_SHA256,
        )
        production_unpinned = tuple(
            value.startswith("TO_PIN_") for value in production_values
        )
        if all(production_unpinned):
            result = run(
                [
                    sys.executable,
                    os.fspath(deriver_path),
                    "--output",
                    os.fspath(production_output),
                ],
                2,
            )
            expected_error = (
                "error: Candidate AF calibration remains unpinned: "
                "AF_RAW_SHA256\n"
            )
            if (
                result.stderr.decode("utf-8") != expected_error
                or production_output.exists()
            ):
                fail("production TO_PIN refusal changed or created output")
            production_state = "refuses-TO_PIN"
        elif any(production_unpinned):
            fail("production Candidate AF calibration is only partially pinned")
        else:
            run(
                [
                    sys.executable,
                    os.fspath(deriver_path),
                    "--output",
                    os.fspath(production_output),
                ],
                0,
            )
            run(["bash", "-n", os.fspath(production_output)], 0)
            if args.shellcheck:
                run(
                    ["shellcheck", "--shell=bash", os.fspath(production_output)],
                    0,
                )
            production_state = "pinned-and-derived"

        # There is deliberately no production calibration override surface.
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

        ae = deriver.reconstruct_ae_installer(repo_root, work)
        if deriver.digest_path(ae) != deriver.AE_INSTALLER_SHA256:
            fail("tracked installer lineage did not reproduce exact Candidate AE")
        ae_data = deriver.read_exact_source(ae)
        ae_text = ae_data.decode("utf-8")

        # Caller-supplied source mode is independently hash- and type-pinned.
        mutated_ae = work / "mutated-ae.sh"
        mutated_ae.write_bytes(ae_data + b"\n# mutation\n")
        try:
            deriver.read_exact_source(mutated_ae)
        except ValueError:
            rejected += 1
        else:
            fail("mutated Candidate AE foundation was accepted")
        symlink_ae = work / "symlink-ae.sh"
        symlink_ae.symlink_to(ae)
        try:
            deriver.read_exact_source(symlink_ae)
        except ValueError:
            rejected += 1
        else:
            fail("symlink Candidate AE foundation was accepted")

        derived = deriver.derive_text(ae_data, fixture)
        derived_path = work / "install-candidate-af-boot2.sh"
        deriver.publish(derived_path, derived)
        if stat.S_IMODE(derived_path.stat().st_mode) != 0o700:
            fail("fixture-derived installer mode is not 0700")
        run(["bash", "-n", os.fspath(derived_path)], 0)
        if args.shellcheck:
            run(["shellcheck", "--shell=bash", os.fspath(derived_path)], 0)

        expected_identity = (
            "gemini-a72-observer-initcall-diagnostic.boot.img",
            'candidate-AF-a72-observer-initcall-${AF_RAW_SHA256:0:8}',
            "candidate-af-padded-boot2.img",
            "boot2-before-candidate-af.img",
            "boot2-after-candidate-af.img",
            "expected_previous_label=AE-installed-readback-verified",
            (
                "readonly EXPECTED_CURRENT_AE_PADDED_SHA256="
                f"{deriver.AE_PADDED_SHA256}"
            ),
            "experiment=2026-07-22-cortex-a72-observer-initcall-diagnostic",
        )
        if any(token not in derived for token in expected_identity):
            fail("fixture-derived Candidate AF identity is incomplete")

        # Exercise every decision-changing safety family directly. This keeps
        # the semantic rules independently useful instead of relying only on
        # the exact source-relative delta backstop.
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
                "target-geometry-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$label" == boot2 && "$type" == part && '
                    '"$size" == "$EXPECTED_SIZE" && "$ro" == 0 ]] || \\\n'
                    '\t\tfail "boot2 identity mismatch: label=$label '
                    'type=$type size=$size ro=$ro"',
                    'true\n\t: "boot2 identity mismatch: label=$label '
                    'type=$type size=$size ro=$ro"',
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
                "active-root-confirmed-bypass",
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
                "identities-only",
                lambda text: replace_once(
                    text, "IdentitiesOnly=yes", "IdentitiesOnly=no"
                ),
            ),
            (
                "identity-agent",
                lambda text: replace_once(
                    text, "IdentityAgent=none", "IdentityAgent=SSH_AUTH_SOCK"
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
                        "readonly EXPECTED_CURRENT_AE_PADDED_SHA256="
                        f"{deriver.AE_PADDED_SHA256}"
                    ),
                    "readonly EXPECTED_CURRENT_AE_PADDED_SHA256=" + "c" * 64,
                ),
            ),
            (
                "predecessor-host-guard-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$already_current" == no && "$probe_sha256" == '
                    '"$EXPECTED_CURRENT_AE_PADDED_SHA256" ]] || \\\n'
                    "\tdie 'initial gate returned an inconsistent "
                    "AE-installed-readback-verified predecessor checksum'",
                    "true\n: 'initial gate returned an inconsistent "
                    "AE-installed-readback-verified predecessor checksum'",
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
                "skip-confirmed-remove-exit",
                lambda text: replace_once(
                    text,
                    "\tprintf 'backup_dir=%s\\nreboot=none\\nruntime_result="
                    "not-tested\\n' \"$backup_dir\"\n\texit 0\nfi",
                    "\tprintf 'backup_dir=%s\\nreboot=none\\nruntime_result="
                    "not-tested\\n' \"$backup_dir\"\nfi",
                ),
            ),
            (
                "skip-condition-bypass",
                lambda text: replace_once(
                    text,
                    'if [[ "$already_current" == yes ]]; then',
                    "if true; then",
                ),
            ),
            (
                "padding-prefix-bypass",
                lambda text: replace_once(
                    text,
                    'head -c "$AF_RAW_SIZE" "$padded" | '
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
                    '[[ "$padded_sha256" == "$AF_PADDED_SHA256" ]] || \\\n'
                    "\tdie 'zero-padded Candidate AF checksum is not calibrated'",
                    "true\n: 'zero-padded Candidate AF checksum is not calibrated'",
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
                "backup-checksum-bypass",
                lambda text: replace_once(
                    text,
                    '[[ "$backup_sha256" == '
                    '"$EXPECTED_CURRENT_AE_PADDED_SHA256" ]] || \\\n'
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
                "extra-second-target-dd-confirmed",
                lambda text: text
                + '\ndd if="$root_stage_file" of="$target" bs=4M '
                + "iflag=fullblock count=4 conv=fsync,notrunc status=none\n",
            ),
            (
                "extra-busybox-target-dd",
                lambda text: text
                + '\n/bin/busybox dd if="$root_stage_file" '
                + 'of="${target}" bs=4M\n',
            ),
            (
                "extra-cp-target",
                lambda text: text + '\ncp "$root_stage_file" "$target"\n',
            ),
            (
                "extra-tee-target",
                lambda text: text + '\ntee "$target" < "$root_stage_file"\n',
            ),
            (
                "extra-redirection-target",
                lambda text: text + '\nprintf x > "$target"\n',
            ),
            (
                "extra-blockdev-target-action",
                lambda text: text + '\nblockdev --setro "$target"\n',
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
                    text,
                    'blockdev --flushbufs "$target"',
                    "true # flush removed",
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
                    '[[ "$readback_sha256" == "$AF_PADDED_SHA256" ]] || \\\n'
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
                    '[[ "$post_sha256" == "$AF_PADDED_SHA256" ]] || '
                    "die 'final target checksum mismatch'",
                    "true\n: 'final target checksum mismatch'",
                ),
            ),
            ("reboot-plain", lambda text: text + "\nreboot\n"),
            ("reboot-absolute", lambda text: text + "\n/sbin/reboot\n"),
            (
                "reboot-busybox-confirmed",
                lambda text: text + "\n/bin/busybox reboot\n",
            ),
            (
                "reboot-busybox-path-variant",
                lambda text: text + "\n/usr/bin/busybox reboot\n",
            ),
            ("reboot-toybox", lambda text: text + "\ntoybox reboot\n"),
            (
                "reboot-toybox-path-variant",
                lambda text: text + "\n/bin/toybox reboot\n",
            ),
            (
                "reboot-systemctl-absolute",
                lambda text: text + "\n/usr/bin/systemctl reboot\n",
            ),
            (
                "reboot-systemctl-option",
                lambda text: text + "\nsystemctl --no-wall reboot\n",
            ),
            (
                "reboot-loginctl",
                lambda text: text + "\n/usr/bin/loginctl poweroff\n",
            ),
            (
                "reboot-shutdown-absolute",
                lambda text: text + "\n/usr/sbin/shutdown -r now\n",
            ),
            ("reboot-poweroff", lambda text: text + "\n/sbin/poweroff\n"),
            ("reboot-halt", lambda text: text + "\n/sbin/halt\n"),
            ("reboot-kexec", lambda text: text + "\n/usr/sbin/kexec -e\n"),
            ("reboot-init-six", lambda text: text + "\n/sbin/init 6\n"),
            ("sysrq", lambda text: text + "\necho b > /proc/sysrq-trigger\n"),
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
            try:
                deriver.validate_safety(mutated, fixture)
            except ValueError:
                rejected += 1
            else:
                fail(f"semantic safety validator accepted mutation: {label}")

        narrow_mutation = derived + "\n# unrelated derived mutation\n"
        try:
            deriver.validate_exact_delta(ae_text, narrow_mutation, fixture)
        except ValueError:
            rejected += 1
        else:
            fail("narrow source-relative delta mutation was accepted")

        # Exclusive output publication prevents silent replacement of a
        # reviewed installer.
        try:
            deriver.publish(derived_path, derived)
        except FileExistsError:
            rejected += 1
        else:
            fail("installer publication overwrote an existing file")

    expected_rejections = 2 + len(mutations) + 2
    if rejected != expected_rejections:
        fail(
            f"mutation count changed: expected {expected_rejections}, got {rejected}"
        )
    print("validation=candidate-af-installer-static-mutations")
    print("foundation=exact-reconstructed-candidate-ae")
    print(f"production_calibration={production_state}")
    print("production_override_surface=none")
    print(f"mutations_rejected={rejected}-of-{expected_rejections}")
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
