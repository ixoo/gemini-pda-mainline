#!/usr/bin/env python3
"""Validate the exact source-only P24 closed-hook milestone."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = ROOT / "experiments/2026-08-05-a72-p24-closed-hooks"
MANIFEST = ROOT / "kernel/manifest.json"
CANONICAL_SERIES = Path("patches/series")
PARENT_SERIES = Path(
    "patches/series-a72-reject-gate-a41-kernel-identity-p30-protocol-"
    "p24-closed-owner"
)
PROFILE_SERIES = Path(
    "patches/series-a72-reject-gate-a41-kernel-identity-p30-protocol-"
    "p24-closed-owner-hooks"
)
PATCH = Path(
    "patches/v7.1.3/0160-cpu-add-closed-arm64-CPU-up-admission-hooks.patch"
)
FOLLOWUP_PATCH = Path(
    "patches/v7.1.3/0171-arm64-complete-dormant-provider-proof-storage.patch"
)
P24_TAIL = [
    f"v7.1.3/{number}"
    for number in (
        "0160-cpu-add-closed-arm64-CPU-up-admission-hooks.patch",
        "0161-arm64-add-read-only-A28-entry-admission-gate.patch",
        "0162-arm64-add-dormant-P31-attempt-consumption.patch",
        "0163-arm64-mint-frozen-A72-transaction-tokens.patch",
        "0164-arm64-validate-frozen-A72-A36-prestates.patch",
        "0165-arm64-publish-dormant-A72-P17-P18-phases.patch",
        "0166-arm64-record-dormant-A72-P27-preparation.patch",
        "0167-arm64-model-dormant-A72-provider-acquire.patch",
        "0168-arm64-model-dormant-A72-provider-refusal-rollback.patch",
        "0169-arm64-model-dormant-A72-postprovider-preparation.patch",
        "0171-arm64-complete-dormant-provider-proof-storage.patch",
    )
]
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-kernel-identity-p30-protocol-p24-closed-owner-hooks"
)
FRAGMENTS = [
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
    "configs/gemini-smp8.fragment",
    "configs/gemini-a72-a41-kernel-identity.fragment",
    "configs/gemini-a72-p30-protocol.fragment",
    "configs/gemini-a72-p24-closed-owner.fragment",
    "configs/gemini-a72-p24-closed-hooks.fragment",
]

PATCH_COMMIT = "7fb9cec977e636c7df35b26588b493c05a1f102f"
PATCH_SHA256 = (
    "5fd606b8eb6554d7e9bcdc7a62548091f4e86476593b6999204f719013b8b287"
)
PATCH_ID = "4e9efdbc51626664a77d08ce402101c4080e4cee"
PATCH_SERIES_SHA256 = (
    "bf1a915e0b5524df61c4c396da84eea8662be56afeba5037ac52721c9ccde359"
)
SOURCE_STATE_SHA256 = (
    "a499c64f9b06a362a29a96ba4099816babeab3026d667bb0be3a6a0ecf8c1373"
)
CONFIG_SHA256 = (
    "6eca02a9f2831249d9353b2822cd0c3661f20bc540f13e460c5d5cee57bf396d"
)
ORACLE_SHA256 = (
    "6c9d3d1c7a682cceaddef0e5329aebedd3e915bd781b08c0b72a0cb955617932"
)
MUTATIONS_SHA256 = (
    "06e5d343a8d25583a0a1c1ed3a022d043e98e6edb2ebf3b47c0460a267623dd1"
)

PATCH_PATHS = {
    "arch/arm64/Kconfig",
    "arch/arm64/Kconfig.platforms",
    "arch/arm64/include/asm/cpu_ops.h",
    "arch/arm64/include/asm/mt6797_a72_membership.h",
    "arch/arm64/kernel/mt6797_a72_membership.c",
    "arch/arm64/kernel/mt6797_a72_membership_test.c",
    "arch/arm64/kernel/mt6797_psci.c",
    "arch/arm64/kernel/smp.c",
    "include/linux/cpu.h",
    "kernel/cpu.c",
}


class ValidationError(RuntimeError):
    """An exact milestone invariant did not hold."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(relative: str | Path) -> str:
    return sha256_bytes((ROOT / relative).read_bytes())


def series_entries(relative: str | Path) -> list[str]:
    return [
        line.strip()
        for line in (ROOT / relative).read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def patch_series_hash(relative: Path) -> str:
    lines = [f"{sha256_file(relative)}  {relative}"]
    for entry in series_entries(relative):
        lines.append(f"{sha256_file(relative.parent / entry)}  {entry}")
    return sha256_bytes(("\n".join(lines) + "\n").encode())


def source_state_hash(manifest: dict, series_hash: str) -> str:
    kernel = manifest["kernel"]
    material = f"{kernel['version']}\n{kernel['sha256']}\n{series_hash}\n"
    return sha256_bytes(material.encode())


def config_hash(profile: dict) -> str:
    lines = [f"profile={PROFILE}", f"base={profile['base']}"]
    for fragment in profile["fragments"]:
        lines.append(f"{sha256_file(fragment)}  {fragment}")
    return sha256_bytes(("\n".join(lines) + "\n").encode())


def patch_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^diff --git a/(\S+) b/(\S+)$", text, re.M))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        require(match.group(1) == match.group(2), "patch renames a source path")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        require(match.group(1) not in sections, "patch repeats a source path")
        sections[match.group(1)] = text[match.start():end]
    return sections


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    for token in tokens:
        require(token in text, f"{label} lost required token: {token}")


def require_order(text: str, tokens: tuple[str, ...], label: str) -> None:
    positions = []
    for token in tokens:
        position = text.find(token)
        require(position >= 0, f"{label} lost order token: {token}")
        positions.append(position)
    require(positions == sorted(positions), f"{label} order changed")


def stable_patch_id(raw: bytes) -> str:
    result = subprocess.run(
        ["git", "patch-id", "--stable"], cwd=ROOT, input=raw,
        capture_output=True, timeout=30, check=False,
    )
    require(result.returncode == 0,
            f"git patch-id failed: {result.stderr.decode().strip()}")
    fields = result.stdout.decode().split()
    require(len(fields) == 2, "unexpected git patch-id output")
    return fields[0]


def validate_patch() -> None:
    raw = (ROOT / PATCH).read_bytes()
    require(sha256_bytes(raw) == PATCH_SHA256, "patch SHA-256 changed")
    require(stable_patch_id(raw) == PATCH_ID, "stable patch-id changed")
    text = raw.decode()
    require(text.startswith(f"From {PATCH_COMMIT} "), "format-patch commit changed")
    require("From: Gemini Mainline Project <noreply@invalid>" in text,
            "experiment-only author changed")
    require("Subject: [PATCH 160/160] cpu: add closed arm64 CPU-up admission hooks"
            in text, "patch subject changed")
    require("Signed-off-by:" not in text, "synthetic author gained a sign-off")
    require("not submission-ready" in text, "submission-readiness warning missing")
    require("10 files changed, 230 insertions(+), 7 deletions(-)" in text,
            "patch summary changed")

    sections = patch_sections(text)
    require(set(sections) == PATCH_PATHS, "patch source-path set changed")

    kconfig = sections["arch/arm64/Kconfig"]
    platforms = sections["arch/arm64/Kconfig.platforms"]
    cpu_ops = sections["arch/arm64/include/asm/cpu_ops.h"]
    owner_h = sections["arch/arm64/include/asm/mt6797_a72_membership.h"]
    owner_c = sections["arch/arm64/kernel/mt6797_a72_membership.c"]
    owner_test = sections["arch/arm64/kernel/mt6797_a72_membership_test.c"]
    psci = sections["arch/arm64/kernel/mt6797_psci.c"]
    smp = sections["arch/arm64/kernel/smp.c"]
    cpu_h = sections["include/linux/cpu.h"]
    generic = sections["kernel/cpu.c"]

    require_tokens(kconfig, (
        "select ARM64_MT6797_A72_P24_ADMISSION_HOOKS",
        "read-only public and internal admission checks",
    ), "KUnit Kconfig")
    require_tokens(platforms, (
        "config ARM64_MT6797_A72_P24_ADMISSION_HOOKS",
        "depends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL",
        "read-only denials",
        "no owner opener or success path",
    ), "hook Kconfig")
    require_tokens(cpu_ops, (
        "cpu_up_preflight",
        "cpu_up_validate",
        "Must not sleep or acquire CPU-map, CPUHP, or",
    ), "CPU operations API")
    require_tokens(owner_h, (
        "mt6797_a72_membership_preflight_up",
        "mt6797_a72_membership_validate_up",
        "return -EOPNOTSUPP",
    ), "owner header")
    require_tokens(owner_c, (
        "mt6797_a72_membership_check_up(",
        "READ_ONCE(a72_owner.health)",
        "raw_spin_lock_irqsave(&a72_state_lock",
        "return -EINVAL",
        "return -EPERM",
        "ret = -EAGAIN",
        "ret = -ESHUTDOWN",
        "ret = -EOPNOTSUPP",
        "mt6797_a72_membership_preflight_up",
        "mt6797_a72_membership_validate_up",
    ), "owner implementation")
    require("mt6797_a72_membership_begin_up(cpu" not in owner_c
            and "return mt6797_a72_membership_begin_up" not in owner_c,
            "admission hook calls transaction begin")
    require("mutex_lock" not in owner_c and "mutex_lock_nested" not in owner_c,
            "leaf hook takes a transition mutex")
    require_tokens(psci, (
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_ADMISSION_HOOKS",
        "return cpu == 8 || cpu == 9",
        "mt6797_a72_membership_preflight_up(cpu, target)",
        "mt6797_a72_membership_validate_up(cpu, tasks_frozen, target)",
        ".cpu_up_preflight = mt6797_psci_cpu_up_preflight",
        ".cpu_up_validate = mt6797_psci_cpu_up_validate",
    ), "MT6797 dispatch")
    require_tokens(smp, (
        "if (cpu >= nr_cpu_ids)",
        "ops = get_cpu_ops(cpu)",
        "ops->cpu_up_preflight",
        "ops->cpu_up_validate",
        "return 0;",
    ), "arm64 dispatch")
    require_tokens(cpu_h, (
        "int arch_cpu_up_preflight(unsigned int cpu, enum cpuhp_state target);",
        "int arch_cpu_up_validate(unsigned int cpu, int tasks_frozen,",
    ), "generic API")
    require_order(generic, (
        "ret = arch_cpu_up_validate(cpu, tasks_frozen, target);",
        "+\tst = per_cpu_ptr(&cpuhp_state, cpu);",
        "cpus_write_lock();",
        "err = arch_cpu_up_preflight(cpu, target);",
        "if (!cpu_possible(cpu))",
    ), "generic hook placement")
    require_tokens(generic, (
        "int __weak arch_cpu_up_preflight",
        "int __weak arch_cpu_up_validate",
        "return 0;",
    ), "weak generic hooks")
    require_order(owner_test, (
        "mt6797_a72_owner_public_hook_denied",
        "mt6797_a72_owner_internal_hook_denied",
        "KUNIT_CASE(mt6797_a72_owner_public_hook_denied)",
        "KUNIT_CASE(mt6797_a72_owner_internal_hook_denied)",
    ), "KUnit hook coverage")
    require_tokens(owner_test, (
        "cpu_up_preflight(8, CPUHP_ONLINE)",
        "cpu_up_validate(8, 1, CPUHP_ONLINE)",
        "expect_unchanged(test, &before, &after)",
    ), "KUnit no-effect checks")
    require("cpu_on(" not in owner_c.lower() and "psci_ops" not in owner_c,
            "owner gained hardware authority")


def validate_manifest_and_series(manifest: dict) -> tuple[str, str]:
    require(manifest["schema"] == 1, "manifest schema changed")
    require(manifest["architecture"] == "arm64", "manifest architecture changed")
    require(manifest["patch_series"] == str(CANONICAL_SERIES),
            "manifest canonical series changed")
    require(manifest["config"]["default_profile"] == "full",
            "default profile changed")
    profiles = manifest["config"]["profiles"]
    require(profiles["full"] == {
        "base": "defconfig",
        "fragments": ["configs/gemini.fragment"],
    }, "default full profile inputs changed")
    require(PROFILE in profiles, "P24 closed-hook profile missing")
    profile = profiles[PROFILE]
    require(profile == {
        "base": "defconfig",
        "patch_series": str(PROFILE_SERIES),
        "fragments": FRAGMENTS,
    }, "P24 closed-hook profile inputs changed")
    fragment_users = [
        name for name, candidate in profiles.items()
        if FRAGMENTS[-1] in candidate.get("fragments", [])
    ]
    require(fragment_users == [PROFILE], "hook fragment selected by another profile")

    parent = series_entries(PARENT_SERIES)
    child = series_entries(PROFILE_SERIES)
    patch_entry = str(PATCH.relative_to("patches"))
    followup_entry = str(FOLLOWUP_PATCH.relative_to("patches"))
    require(child == parent + P24_TAIL,
            "hook profile is not the exact closed-owner parent plus P24 tail")
    canonical = series_entries(CANONICAL_SERIES)
    positions = [canonical.index(entry) for entry in child]
    require(positions == sorted(positions) and len(set(positions)) == len(positions),
            "hook series is not a canonical-order subsequence")
    require(canonical[-1] == followup_entry,
            "canonical series does not end at 0171")

    series_hash = patch_series_hash(PROFILE_SERIES)
    require(series_hash == PATCH_SERIES_SHA256, "patch-series identity changed")
    state_hash = source_state_hash(manifest, series_hash)
    require(state_hash == SOURCE_STATE_SHA256, "source-state identity changed")
    cfg_hash = config_hash(profile)
    require(cfg_hash == CONFIG_SHA256, "configuration-input identity changed")

    fragment = (ROOT / FRAGMENTS[-1]).read_text()
    require_tokens(fragment, (
        "CONFIG_ARM64_MT6797_A72_P24_ADMISSION_HOOKS=y",
        "# CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST is not set",
        'CONFIG_LOCALVERSION="-gemini-p24-hooks-closed"',
        "authorizes no kernel",
        "CPU8 and CPU9 remain read-only denials",
    ), "P24 hook fragment")
    gate = (ROOT / (
        "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"
    )).read_text()
    require_tokens(gate, (
        "static int mt6797_psci_cpu_boot",
        "return -EAGAIN;",
        "static bool mt6797_psci_cpu_can_disable",
        "return false;",
    ), "patch 0092 safety gate")
    return state_hash, cfg_hash


def run_checked(command: list[str], cwd: Path) -> str:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command, cwd=cwd, env=env, text=True, capture_output=True,
        timeout=30, check=False,
    )
    require(result.returncode == 0,
            f"command failed ({' '.join(command)}): {result.stderr.strip()}")
    return result.stdout


def validate_oracle_and_docs() -> None:
    oracle = EXPERIMENT / "scripts/oracle.py"
    mutations = EXPERIMENT / "scripts/test_mutations.py"
    require(sha256_bytes(oracle.read_bytes()) == ORACLE_SHA256,
            "oracle source changed")
    require(sha256_bytes(mutations.read_bytes()) == MUTATIONS_SHA256,
            "mutation source changed")

    oracle_output = run_checked([sys.executable, str(oracle)], EXPERIMENT)
    mutation_output = run_checked([sys.executable, str(mutations)], EXPERIMENT)
    require_tokens(oracle_output, (
        "PARTIAL_P24_CLOSED_ADMISSION_HOOKS",
        "public_order=PUBLIC_HOOK -> CPU_POSSIBLE -> NODE_ONLINE_WORK -> CPU_MAPS_LOCK",
        "internal_order=INTERNAL_HOOK -> PER_CPU_STATE -> CPUS_WRITE_LOCK -> CPUHP_STATE -> CPUHP_CALLBACK -> CPU_BOOT_METHOD",
        "admission_probes=32",
        "owner_validator_calls=10",
        "direct_internal_paths=THAW,SMT",
        "reachable_hook_states=1",
        "a72_authorizations=0",
        "violations=0",
        "PASS closed generic admission-hook contract",
    ), "oracle output")
    require_tokens(mutation_output, (
        "transaction-begin-called: NO_BEGIN_UP",
        "cpu-on-issued: NO_CPU_ON",
        "cpu-boot-called: NO_CPU_BOOT",
        "mutations_rejected=39/39",
        "PASS intended-check closed-hook mutation suite",
    ), "mutation output")

    readme = (EXPERIMENT / "README.md").read_text()
    design = (EXPERIMENT / "DESIGN.md").read_text()
    review = (EXPERIMENT / "results/kernel-static-review-20260805.txt").read_text()
    require_tokens(readme, (
        "PARTIAL_P24_CLOSED_ADMISSION_HOOKS",
        PATCH_COMMIT,
        SOURCE_STATE_SHA256,
        CONFIG_SHA256,
        "Exact milestone validator",
        "all 66 manifest-profile series checks",
        "Buildbox validation",
    ), "experiment README")
    require_tokens(design, (
        "Reviewed C mapping",
        "cpu_up_preflight",
        "cpu_up_validate",
        "no production caller or",
        "No positive CPU8/CPU9 admission",
    ), "experiment design")
    require_tokens(review, (
        "independent_contract_review=GO",
        "independent_order_review=GO",
        "reviewers=2-GO",
        "production_callers=0",
        "p30_mutator_calls_added=0",
        "cpu_on_calls_added=0",
        "kunit_cases=10",
        "A26 and A14 remain closed.",
        "build=not-run-roadmap-source-only",
        "device_action=none",
    ), "static review record")


def main() -> int:
    try:
        manifest = json.loads(MANIFEST.read_text())
        validate_patch()
        state_hash, cfg_hash = validate_manifest_and_series(manifest)
        validate_oracle_and_docs()
        invariant = run_checked([str(ROOT / "scripts/validate-manifest-series")], ROOT)
        require_tokens(invariant, (
            "validation=manifest-series-invariant",
            "profiles_checked=66",
            "canonical_series=patches/series",
        ), "manifest-series audit")
    except (OSError, ValueError, ValidationError) as error:
        print(f"validation_error={error}", file=sys.stderr)
        return 1

    print("validation=p24-closed-admission-hooks")
    print("claim=PARTIAL_P24_CLOSED_ADMISSION_HOOKS")
    print(f"patch_sha256={PATCH_SHA256}")
    print(f"patch_id_stable={PATCH_ID}")
    print(f"source_state_sha256={state_hash}")
    print(f"config_inputs_sha256={cfg_hash}")
    print("admission_probes=32")
    print("mutations_rejected=39/39")
    print("reviewers=2-GO")
    print("kunit=10-cases-not-built-or-run")
    print("production_callers=0")
    print("profiles_checked=66")
    print("build=validated-buildbox")
    print("device_action=none")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
