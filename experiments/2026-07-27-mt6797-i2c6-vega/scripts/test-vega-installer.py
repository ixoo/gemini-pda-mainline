#!/usr/bin/env python3
"""Exercise Vega's source-pinned boot2 installer contracts offline."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
from types import ModuleType

sys.dont_write_bytecode = True
import installer_vega as io


def load_deriver(path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("vega_installer_deriver", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Vega installer deriver")
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


def run_checked(command: list[str], label: str) -> None:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"{label} failed: {detail}")


def main() -> int:
    try:
        scripts = pathlib.Path(__file__).resolve().parent
        deriver = load_deriver(scripts / "derive-installer.py")
        fixture = io.ArtifactPins(
            raw_sha256="1" * 64,
            raw_size=7_700_001,
            padded_sha256="2" * 64,
            manifest_sha256="3" * 64,
        )
        io.require_artifact_pins(fixture)

        with tempfile.TemporaryDirectory(
            prefix="vega-installer-contract."
        ) as raw:
            temporary = pathlib.Path(raw)
            source = deriver.reconstruct_orion(temporary)
            if hashlib.sha256(source.encode()).hexdigest() != io.ORION_INSTALLER_SHA256:
                raise ValueError("reconstructed Orion installer identity changed")

            derived = deriver.derive_text(source, fixture)
            deriver.validate_contract(derived, fixture)
            installer = temporary / "install-candidate-vega-boot2.sh"
            installer.write_text(derived, encoding="utf-8")
            installer.chmod(0o700)
            run_checked(["bash", "-n", os.fspath(installer)], "Bash syntax")
            shellcheck = shutil.which("shellcheck")
            if shellcheck:
                run_checked([shellcheck, os.fspath(installer)], "ShellCheck")
                shellcheck_status = "passed"
            else:
                shellcheck_status = "unavailable"

            mutation_count = 0
            for index, token in enumerate(deriver.CRITICAL_TOKEN_COUNTS, 1):
                mutated = derived.replace(token, f"VEGA_MUTATED_GATE_{index}", 1)
                expect_rejection(
                    lambda data=mutated: deriver.validate_contract(data, fixture),
                    f"critical-gate-{index}",
                )
                mutation_count += 1

            count_mutations = (
                derived
                + '\ndd if="$root_stage_file" of="$target" '
                "bs=4M iflag=fullblock count=4\n",
                derived + "\nreboot now\n",
                derived.replace(fixture.raw_sha256, "4" * 64, 1),
                derived.replace(io.ORION_PADDED_SHA256, "5" * 64, 1),
                derived.replace(fixture.artifact_dir, "candidate-Vega-wrong", 1),
                derived.replace(io.BOOT_MEMBER, "wrong.boot.img", 1),
            )
            for index, mutated in enumerate(count_mutations, 1):
                expect_rejection(
                    lambda data=mutated: deriver.validate_contract(data, fixture),
                    f"identity-or-write-{index}",
                )
                mutation_count += 1

            source_mutations = (
                source.replace("readonly ORION_RAW_SHA256=", "readonly ORION_RAW_SHA257=", 1),
                source.replace("Orion", "Changed", 1),
            )
            for index, mutated in enumerate(source_mutations, 1):
                expect_rejection(
                    lambda data=mutated: deriver.derive_text(data, fixture),
                    f"source-foundation-{index}",
                )
                mutation_count += 1

            pin_mutations = (
                replace(fixture, raw_sha256="UNRESOLVED"),
                replace(fixture, raw_size=0),
                replace(fixture, raw_size=io.BOOT2_SIZE + 1),
                replace(fixture, padded_sha256=io.ORION_PADDED_SHA256),
                replace(fixture, manifest_sha256=fixture.raw_sha256),
            )
            for index, mutated in enumerate(pin_mutations, 1):
                expect_rejection(
                    lambda pins=mutated: io.require_artifact_pins(pins),
                    f"artifact-pin-{index}",
                )
                mutation_count += 1

            existing = temporary / "existing-installer"
            existing.write_text("occupied\n", encoding="utf-8")
            expect_rejection(
                lambda: deriver.validate_output(existing),
                "existing-output",
            )
            mutation_count += 1

            real_parent = temporary / "real-parent"
            real_parent.mkdir(mode=0o700)
            linked_parent = temporary / "linked-parent"
            linked_parent.symlink_to(real_parent, target_is_directory=True)
            expect_rejection(
                lambda: deriver.validate_output(linked_parent / "installer"),
                "symlink-output-parent",
            )
            mutation_count += 1

        production = io.production_pins()
        if io.pins_resolved(production):
            io.require_artifact_pins(production)
            with tempfile.TemporaryDirectory(
                prefix="vega-production-installer-contract."
            ) as raw:
                production_dir = pathlib.Path(raw)
                production_source = deriver.reconstruct_orion(production_dir)
                cli_output = production_dir / "install-candidate-vega-boot2.sh"
                cli_result = subprocess.run(
                    [
                        sys.executable,
                        os.fspath(scripts / "derive-installer.py"),
                        "--output",
                        os.fspath(cli_output),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                if cli_result.returncode:
                    detail = (
                        cli_result.stderr.strip()
                        or cli_result.stdout.strip()
                        or "no diagnostic"
                    )
                    raise ValueError(
                        f"resolved production installer CLI failed: {detail}"
                    )
                info = cli_output.lstat()
                if (
                    cli_output.is_symlink()
                    or not stat.S_ISREG(info.st_mode)
                    or stat.S_IMODE(info.st_mode) != 0o700
                ):
                    raise ValueError("production installer CLI output is unsafe")
                cli_digest = io.digest_path(cli_output)
            production_text = deriver.derive_text(production_source, production)
            production_digest = hashlib.sha256(production_text.encode()).hexdigest()
            if cli_digest != production_digest:
                raise ValueError("production installer CLI bytes are not reproducible")
            if (
                io.INSTALLER_SHA256 != "UNRESOLVED"
                and production_digest != io.INSTALLER_SHA256
            ):
                raise ValueError("pinned production Vega installer identity changed")
            production_state = "resolved"
            production_cli = "derived-mode-0700-byte-identical"
        else:
            expect_rejection(
                lambda: io.require_artifact_pins(production),
                "unresolved-production-pins",
            )
            with tempfile.TemporaryDirectory(
                prefix="vega-unresolved-installer-contract."
            ) as raw:
                cli_output = pathlib.Path(raw) / "must-not-exist.sh"
                cli_result = subprocess.run(
                    [
                        sys.executable,
                        os.fspath(scripts / "derive-installer.py"),
                        "--output",
                        os.fspath(cli_output),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                if cli_result.returncode != 2 or cli_output.exists():
                    raise ValueError(
                        "unresolved production installer CLI did not fail closed"
                    )
            production_digest = "unresolved"
            production_state = "fail-closed-unresolved"
            production_cli = "rejected-before-output"
            mutation_count += 1

        print("validation=vega-source-pinned-installer-contracts")
        print(f"orion_deriver_sha256={io.ORION_DERIVER_SHA256}")
        print(f"orion_installer_sha256={io.ORION_INSTALLER_SHA256}")
        print(f"expected_predecessor_sha256={io.ORION_PADDED_SHA256}")
        print(f"critical_gate_count={len(deriver.CRITICAL_TOKEN_COUNTS)}")
        print(f"mutations_rejected={mutation_count}")
        print(f"fixture_installer_sha256={hashlib.sha256(derived.encode()).hexdigest()}")
        print(f"bash_syntax=passed")
        print(f"shellcheck={shellcheck_status}")
        print(f"production_pins={production_state}")
        print(f"production_cli={production_cli}")
        print(f"production_installer_sha256={production_digest}")
        print("installer_target_writes=1")
        print("installer_reboot_shutdown_slot_selection=none")
        print("device_network_partition_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
