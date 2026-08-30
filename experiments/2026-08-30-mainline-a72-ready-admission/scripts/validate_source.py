#!/usr/bin/env python3
"""Validate the post-0434 config-off and candidate-identity contracts."""

from __future__ import annotations

import argparse
from pathlib import Path


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def function(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for offset in range(brace, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[start:offset + 1]
    raise ValidationError(f"unterminated function: {signature}")


def profile_switch(header: str) -> tuple[str, str]:
    start = header.index("#ifdef CONFIG_ARM64_LATE_CPU_PROFILE")
    end = header.index("#endif\n\n#endif /* __ASM_LATE_CPU_PROFILE_H */", start)
    enabled, disabled = header[start:end].split("#else\n", 1)
    return enabled, disabled


def validate_config_off(root: Path) -> list[str]:
    header = (root / "arch/arm64/include/asm/late_cpu_profile.h").read_text()
    enabled, disabled = profile_switch(header)
    scope = header.index("int arm64_late_cpu_validate_boot_caps(void);")
    switch = header.index("#ifdef CONFIG_ARM64_LATE_CPU_PROFILE")
    require(scope < switch, "boot-capability prototype is not always visible")
    require(header.count("int arm64_late_cpu_validate_boot_caps(void);") == 1,
            "boot-capability prototype count changed")
    require(enabled.count(
        "int arm64_validate_late_cpu_preflight(unsigned int cpu);") == 1,
        "enabled preflight declaration count changed")
    require("arm64_late_cpu_validate_boot_caps" not in enabled,
            "boot-capability prototype remains profile-scoped")
    stub = function(disabled, "arm64_validate_late_cpu_preflight(")
    require("return 0;" in stub,
            "configuration-off preflight no longer passes through")
    for forbidden in (
        "return -", "arm64_late_cpu_validate_boot_caps", "cpu_up(",
        "cpu_down(", "cpu_off(", "psci_cpu_on", "psci_cpu_off",
        "ARM64_LATE_CPU_PROFILE_READY",
    ):
        require(forbidden not in stub,
                f"configuration-off stub gained behavior: {forbidden}")
    return [
        "config_off_validation=pass",
        "boot_caps_prototype=always-visible",
        "config_off_preflight=pass-through",
    ]


def validate(root: Path) -> list[str]:
    markers = validate_config_off(root)
    profile = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()
    expected = (
        "\t0x5968c24f1904c055, 0x9dea25480c41fbc7,\n"
        "\t0xdb49e822dc3600d1, 0xbdd7632330853f40,\n"
    )
    fixture = (
        "\t0x7b875e34f11c7c6d, 0x007124aacc3e1e01,\n"
        "\t0x3acc41cc1628913a, 0x94cfddf0be8d7a74,\n"
    )
    require(profile.count(expected) == 1,
            "production candidate configuration identity changed")
    require(profile.count(fixture) == 1,
            "historical fixture configuration identity changed")
    require("0x699f14786e1d64eb" not in profile,
            "obsolete production configuration identity remains")
    require(profile.count(
        "memcmp(evidence->config_input_identity,\n"
        "\t\t   mt6797_a72_config_input_identity,") == 1,
        "runtime evidence is no longer bound to the candidate identity")
    for forbidden in (
        "cpu_up(8", "cpu_up(9", "cpu_down(8", "cpu_down(9",
        "psci_cpu_off", "boot2",
    ):
        require(forbidden not in expected,
                f"identity repair gained forbidden action: {forbidden}")
    markers.extend((
        "identity_validation=pass",
        "candidate_profile=a72-admission-live-trigger-candidate",
        "candidate_config_inputs_sha256="
        "5968c24f1904c0559dea25480c41fbc7db49e822dc3600d1bdd7632330853f40",
        "fixture_identity=unchanged",
        "new_cpu_request_paths=0",
        "cpu9_request_paths=0",
        "cpu_off_paths=0",
        "retry_paths=0",
    ))
    return markers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        print("\n".join(validate(args.source_root.resolve())))
    except (OSError, ValueError, ValidationError) as error:
        print(f"validation_error={error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
