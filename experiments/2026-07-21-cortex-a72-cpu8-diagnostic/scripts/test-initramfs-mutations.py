#!/usr/bin/env python3
"""Require focused unsafe Candidate AF initramfs source mutations to fail."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from collections.abc import Callable


def load_validator(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("candidate_af_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AF validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"mutation anchor is absent or duplicated: {old!r}")
    return text.replace(old, new)


def swap_once(text: str, first: str, second: str) -> str:
    placeholder = "__CANDIDATE_AF_MUTATION_PLACEHOLDER__"
    if placeholder in text:
        raise RuntimeError("mutation placeholder collides with source")
    return replace_once(
        replace_once(replace_once(text, first, placeholder), second, first),
        placeholder,
        second,
    )


def main() -> int:
    sys.dont_write_bytecode = True
    script_dir = pathlib.Path(__file__).resolve().parent
    source_dir = script_dir.parent / "initramfs"
    validator = load_validator(script_dir / "validate-initramfs.py")
    init = (source_dir / "init").read_text(encoding="utf-8")
    worker = (source_dir / "af-cpu8").read_text(encoding="utf-8")

    validator.validate_init(init)
    validator.validate_worker(worker)

    provider_gate = "if ! validate_a72_power_provider; then"
    watchdog_open = "if run_cpu8_diagnostic 3>/dev/watchdog0; then"
    mutations: tuple[tuple[str, Callable[[], None]], ...] = (
        (
            "inherited-sysfs-made-writable",
            lambda: validator.validate_init(
                replace_once(
                    init,
                    "mount -t sysfs -o ro,nosuid,nodev,noexec sysfs /sys",
                    "mount -t sysfs -o rw,nosuid,nodev,noexec sysfs /sys",
                )
            ),
        ),
        (
            "cpu8-worker-not-launched",
            lambda: validator.validate_init(
                replace_once(init, "/bin/af-cpu8 &", "# /bin/af-cpu8 withheld")
            ),
        ),
        (
            "generic-psci-restored",
            lambda: validator.validate_worker(
                replace_once(worker, "mediatek,mt6797-psci", "psci")
            ),
        ),
        (
            "provider-path-changed",
            lambda: validator.validate_worker(
                replace_once(
                    worker,
                    '"$SYSFS"/bus/platform/drivers/mt6797-a72-power/*/ready',
                    '"$SYSFS"/bus/platform/drivers/mt6797-a72-power/ready',
                )
            ),
        ),
        (
            "provider-count-gate-weakened",
            lambda: validator.validate_worker(
                replace_once(worker, '[ "$ready_count" != 1 ]', '[ "$ready_count" -lt 1 ]')
            ),
        ),
        (
            "provider-checked-after-watchdog-open",
            lambda: validator.validate_worker(
                swap_once(worker, provider_gate, watchdog_open)
            ),
        ),
        (
            "provider-abi-gate-removed",
            lambda: validator.validate_worker(
                replace_once(
                    worker,
                    '[ "$provider_abi" != "$PROVIDER_ABI_EXPECTED" ]',
                    "false",
                )
            ),
        ),
        (
            "provider-hooks-gate-removed",
            lambda: validator.validate_worker(
                replace_once(
                    worker,
                    '[ "$provider_hooks_armed" != "$PROVIDER_HOOKS_ARMED_EXPECTED" ]',
                    "false",
                )
            ),
        ),
        (
            "second-watchdog-ping",
            lambda: validator.validate_worker(
                replace_once(
                    worker,
                    "if ! printf '.' >&3; then",
                    "printf '.' >&3\n\tif ! printf '.' >&3; then",
                )
            ),
        ),
        (
            "second-cpu8-write",
            lambda: validator.validate_worker(
                replace_once(
                    worker,
                    "if printf '1\\n' >\"$CPU8_ONLINE\"",
                    "printf '1\\n' >\"$CPU8_ONLINE\"\n\tif printf '1\\n' >\"$CPU8_ONLINE\"",
                )
            ),
        ),
        (
            "cpu9-write",
            lambda: validator.validate_worker(
                replace_once(
                    worker,
                    "if printf '1\\n' >\"$CPU8_ONLINE\"",
                    "printf '1\\n' >\"$CPU9_ONLINE\"\n\tif printf '1\\n' >\"$CPU8_ONLINE\"",
                )
            ),
        ),
        (
            "fault-delta-gate-removed",
            lambda: validator.validate_worker(
                replace_once(
                    worker,
                    "if ! validate_no_new_faults; then",
                    "if false; then",
                )
            ),
        ),
        (
            "worker-reboot-command",
            lambda: validator.validate_worker(worker + "\n/bin/busybox reboot -f\n"),
        ),
    )

    rejected = 0
    for label, mutation in mutations:
        try:
            mutation()
        except (KeyError, ValueError):
            print(f"mutation={label} result=rejected")
            rejected += 1
        else:
            print(f"error: mutation accepted: {label}", file=sys.stderr)
            return 2
    print("validation=candidate-af-initramfs-source-mutations")
    print(f"mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
