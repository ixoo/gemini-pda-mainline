#!/usr/bin/env python3
"""Static and mutation tests for Candidate AE's installer derivation."""

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
    spec = importlib.util.spec_from_file_location("candidate_ae_deriver", path)
    if spec is None or spec.loader is None:
        fail("cannot load Candidate AE installer deriver")
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

    with tempfile.TemporaryDirectory(prefix="candidate-ae-installer-test.") as raw:
        work = pathlib.Path(raw)

        # Before calibration, the production entry point must reject its first
        # TO_PIN value before source reconstruction or output. After all three
        # constants are pinned, this same non-device control must derive an
        # installer successfully. A partial edit is never an accepted state.
        production_output = work / "production-derived-ae.sh"
        production_values = (
            deriver.AE_RAW_SHA256,
            deriver.AE_RAW_SIZE,
            deriver.AE_PADDED_SHA256,
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
                "error: Candidate AE calibration remains unpinned: "
                "AE_RAW_SHA256\n"
            )
            if (
                result.stderr.decode("utf-8") != expected_error
                or production_output.exists()
            ):
                fail("production TO_PIN refusal changed or created output")
            production_state = "refuses-TO_PIN"
        elif any(production_unpinned):
            fail("production Candidate AE calibration is only partially pinned")
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

        ad = deriver.reconstruct_ad_installer(repo_root, work)
        if deriver.digest_path(ad) != deriver.AD_INSTALLER_SHA256:
            fail("tracked installer lineage did not reproduce exact Candidate AD")
        ad_data = deriver.read_exact_source(ad)
        ad_text = ad_data.decode("utf-8")

        # The accepted-source path is independently hash- and type-pinned.
        mutated_ad = work / "mutated-ad.sh"
        mutated_ad.write_bytes(ad_data + b"\n# mutation\n")
        try:
            deriver.read_exact_source(mutated_ad)
        except ValueError:
            rejected += 1
        else:
            fail("mutated Candidate AD foundation was accepted")
        symlink_ad = work / "symlink-ad.sh"
        symlink_ad.symlink_to(ad)
        try:
            deriver.read_exact_source(symlink_ad)
        except ValueError:
            rejected += 1
        else:
            fail("symlink Candidate AD foundation was accepted")

        derived = deriver.derive_text(ad_data, fixture)
        derived_path = work / "install-candidate-ae-boot2.sh"
        deriver.publish(derived_path, derived)
        if stat.S_IMODE(derived_path.stat().st_mode) != 0o700:
            fail("fixture-derived installer mode is not 0700")
        run(["bash", "-n", os.fspath(derived_path)], 0)
        if args.shellcheck:
            run(["shellcheck", "--shell=bash", os.fspath(derived_path)], 0)

        expected_identity = (
            "gemini-a72-observer.boot.img",
            'candidate-AE-a72-observer-${AE_RAW_SHA256:0:8}',
            "candidate-ae-padded-boot2.img",
            "boot2-before-candidate-ae.img",
            "boot2-after-candidate-ae.img",
            "expected_previous_label=AD-hardware-passed",
            f"readonly EXPECTED_CURRENT_AD_PADDED_SHA256={deriver.AD_PADDED_SHA256}",
        )
        if any(token not in derived for token in expected_identity):
            fail("fixture-derived Candidate AE identity is incomplete")

        # These mutations exercise each decision-changing safety family.  The
        # semantic validator runs directly so the exact-delta backstop cannot
        # mask a missing individual rule.
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
                "target-writable",
                lambda text: replace_once(
                    text,
                    "boot2 is not root-readable and writable",
                    "boot2 writable check removed",
                ),
            ),
            (
                "active-root",
                lambda text: replace_once(
                    text, "boot2 is the active root", "active-root check removed"
                ),
            ),
            (
                "mount",
                lambda text: replace_once(text, "boot2 is mounted", "mount check removed"),
            ),
            (
                "swap",
                lambda text: replace_once(
                    text, "boot2 is active swap", "swap check removed"
                ),
            ),
            (
                "holders",
                lambda text: replace_once(text, "boot2 has holders", "holder check removed"),
            ),
            (
                "power-stability",
                lambda text: replace_once(
                    text,
                    "power changed during stability sample",
                    "power stability check removed",
                ),
            ),
            (
                "external-power",
                lambda text: replace_once(
                    text,
                    "neither AC nor USB external power is online",
                    "external power check removed",
                ),
            ),
            (
                "battery",
                lambda text: replace_once(
                    text,
                    "battery is not present, full, and healthy",
                    "battery check removed",
                ),
            ),
            (
                "host-key",
                lambda text: replace_once(
                    text, "StrictHostKeyChecking=yes", "StrictHostKeyChecking=no"
                ),
            ),
            (
                "identity-mode",
                lambda text: replace_once(
                    text, "Gemini identity mode is not 0600", "identity mode ignored"
                ),
            ),
            (
                "skip-exact-match",
                lambda text: text.replace(
                    "result=skipped-already-matching", "result=write-anyway", 1
                ),
            ),
            (
                "padding-prefix",
                lambda text: replace_once(
                    text,
                    "padded candidate prefix differs from raw candidate",
                    "padding prefix check removed",
                ),
            ),
            (
                "padding-zero-tail",
                lambda text: replace_once(
                    text,
                    "padded candidate tail is not all zero",
                    "zero-tail check removed",
                ),
            ),
            (
                "backup-mode",
                lambda text: replace_once(
                    text, 'chmod 0600 "$backup_partial"', 'chmod 0644 "$backup_partial"'
                ),
            ),
            (
                "backup-checksum",
                lambda text: replace_once(
                    text, "boot2 backup checksum mismatch", "backup checksum ignored"
                ),
            ),
            (
                "prewrite-checksum",
                lambda text: replace_once(
                    text,
                    "boot2 changed at the final pre-write checksum",
                    "prewrite checksum ignored",
                ),
            ),
            (
                "target-write",
                lambda text: replace_once(
                    text,
                    'dd if="$root_stage_file" of="$target" bs=4M '
                    "iflag=fullblock count=4",
                    'dd if="$root_stage_file" of=/dev/mmcblk0 bs=4M',
                ),
            ),
            (
                "flush",
                lambda text: replace_once(
                    text, 'blockdev --flushbufs "$target"', "true # flush removed"
                ),
            ),
            (
                "readback-size",
                lambda text: replace_once(
                    text,
                    "full boot2 readback stream length mismatch",
                    "readback length ignored",
                ),
            ),
            (
                "readback-bytes",
                lambda text: replace_once(
                    text,
                    "full boot2 readback differs byte-for-byte",
                    "readback comparison ignored",
                ),
            ),
            ("reboot", lambda text: text + "\nreboot\n"),
            ("sysrq", lambda text: text + "\necho b > /proc/sysrq-trigger\n"),
            ("alternative-slot", lambda text: text + "\n# /dev/disk/by-partlabel/boot3\n"),
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

        # A byte outside the named safety tokens must still fail the exact
        # source-relative delta backstop.
        narrow_mutation = derived + "\n# unrelated derived mutation\n"
        try:
            deriver.validate_exact_delta(ad_text, narrow_mutation, fixture)
        except ValueError:
            rejected += 1
        else:
            fail("narrow source-relative delta mutation was accepted")

        # Output publication is exclusive, so a second derivation cannot
        # silently replace a reviewed installer.
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
    print("validation=candidate-ae-installer-static-mutations")
    print("foundation=exact-reconstructed-candidate-ad")
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
