#!/usr/bin/env python3
"""Validate the exact source-only P24 closed-owner milestone."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = ROOT / "experiments/2026-08-05-a72-p24-closed-owner"
MANIFEST = ROOT / "kernel/manifest.json"
CANONICAL_SERIES = Path("patches/series")
PARENT_SERIES = Path(
    "patches/series-a72-reject-gate-a41-kernel-identity-p30-protocol"
)
PROFILE_SERIES = Path(
    "patches/series-a72-reject-gate-a41-kernel-identity-p30-protocol-"
    "p24-closed-owner"
)
PATCH = Path(
    "patches/v7.1.3/0159-arm64-add-closed-A72-transaction-owner-model.patch"
)
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-kernel-identity-p30-protocol-p24-closed-owner"
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
]

PATCH_COMMIT = "f1cd16bf7bdd62d86cfb6a9f1553ada3f231d39c"
PATCH_SHA256 = "39cd3a9e158f2d7ed3e95856002f450709f5886f11e66c9920bb62952394e515"
PATCH_ID = "fd8812286327768700ca7bfae4b548a836b04f1d"
PATCH_SERIES_SHA256 = (
    "29e998313748bcb8c7cabaa25123556d200bd70d589ea147af7c5c99248049db"
)
SOURCE_STATE_SHA256 = (
    "035390e2350cfff576de28083db6904fbdddcc061c4231683942aa13b5c19452"
)
CONFIG_SHA256 = (
    "0fe5961a34c6f2ae14b12d36a30f9f9d7a852f6d628f9344f51297942de0cb58"
)
ORACLE_SHA256 = (
    "68db7877bae6c45cc47b2ae3c3cd3de52b6006ec3e2eb4dd2dd5480d31be6c79"
)
MUTATIONS_SHA256 = (
    "143b2b23c983a31a8e3d2a3b094a02581b3605b8d011264c03e52d32d8094cc1"
)
REVIEWED_FILES = {
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "767713137cdfe2f40c3b5a1ca09d3eda08bd4888efb1f8b5b4c9455d7a68c5c8",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "dbfe6368934e8142a17dd68ba6aa8eda28cad4dc65452a851a4dfea9b4d68051",
    "arch/arm64/kernel/mt6797_a72_membership_test.c":
        "ca40277c8af58de4d307b8bca07bdd1a589412c98dcd5794a2f51db691b1d108",
}
PATCH_PATHS = {
    "arch/arm64/Kconfig",
    "arch/arm64/Kconfig.platforms",
    "arch/arm64/kernel/Makefile",
    *REVIEWED_FILES,
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


def is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    position = 0
    for entry in haystack:
        if position < len(needle) and entry == needle[position]:
            position += 1
    return position == len(needle)


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


def reconstructed_added_file(section: str) -> bytes:
    text = "".join(
        line[1:]
        for line in section.splitlines(keepends=True)
        if line.startswith("+") and not line.startswith("+++")
    )
    return text.encode()


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    for token in tokens:
        require(token in text, f"{label} lost required token: {token}")


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
    require("Subject: [PATCH 159/159] arm64: add closed A72 transaction owner model"
            in text, "patch subject changed")
    require("Signed-off-by:" not in text, "synthetic author gained a sign-off")
    require("not submission-ready" in text,
            "submission-readiness warning missing")

    sections = patch_sections(text)
    require(set(sections) == PATCH_PATHS, "patch source-path set changed")
    for path, expected in REVIEWED_FILES.items():
        actual = sha256_bytes(reconstructed_added_file(sections[path]))
        require(actual == expected, f"reviewed source content changed: {path}")

    header = reconstructed_added_file(
        sections["arch/arm64/include/asm/mt6797_a72_membership.h"]
    ).decode()
    model = reconstructed_added_file(
        sections["arch/arm64/kernel/mt6797_a72_membership.c"]
    ).decode()
    tests = reconstructed_added_file(
        sections["arch/arm64/kernel/mt6797_a72_membership_test.c"]
    ).decode()
    require_tokens(header, (
        "not a P17/P18/P24 token ABI",
        "MT6797_A72_PHASE_UNINITIALIZED",
        "struct mt6797_a72_transaction",
        "struct mt6797_a72_owner_snapshot",
        "mt6797_a72_membership_begin_up",
        "mt6797_a72_membership_owns_up_token",
        "mt6797_a72_membership_copy_up_token",
    ), "owner header")
    require_tokens(model, (
        "deliberately has no production caller or opener",
        "meta/lifecycle boundary before P31/A38",
        ".health = MT6797_A72_OWNER_CLOSED",
        ".phase = MT6797_A72_PHASE_UNINITIALIZED",
        "return -EAGAIN;",
        "ret = -EOPNOTSUPP;",
        "mt6797_a72_membership_snapshot",
        "mt6797_a72_membership_test_reset",
    ), "owner model")
    require("arm64_late_cpu_startup_publish" not in model,
            "owner model gained a P30 publisher")
    require("arm64_late_cpu_startup_consume" not in model,
            "owner model gained a P30 consumer")
    require("psci_ops" not in model and "invoke_psci_fn" not in model,
            "owner model gained a PSCI call")
    require("cpu_on(" not in model.lower(), "owner model gained a CPU_ON call")
    require(tests.count("KUNIT_CASE(") == 8, "KUnit case count changed")
    require_tokens(tests, (
        "mt6797_a72_owner_initial_closed",
        "mt6797_a72_owner_cpu8_denied",
        "mt6797_a72_owner_cpu9_denied",
        "mt6797_a72_owner_repeat_is_diagnostic",
        "mt6797_a72_owner_forged_token_rejected",
        "mt6797_a72_owner_no_live_token",
        "arm64_late_cpu_startup_snapshot",
        "expect_unchanged(test, &before, &after)",
    ), "KUnit source")

    kconfig = sections["arch/arm64/Kconfig"]
    platforms = sections["arch/arm64/Kconfig.platforms"]
    makefile = sections["arch/arm64/kernel/Makefile"]
    require_tokens(kconfig, (
        "config ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST",
        "+\tdepends on KUNIT=y",
        "+\tselect ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL",
    ), "KUnit Kconfig")
    require_tokens(platforms, (
        "config ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL",
        "+\tdepends on ARM64_MT6797_A72_P30_PROTOCOL_MODEL",
        "no production caller or opener",
        "cannot issue CPU_ON",
    ), "platform Kconfig")
    require_tokens(makefile, (
        "CONFIG_ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL",
        "CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST",
    ), "arm64 Makefile")
    require("select HOTPLUG_CPU" not in text,
            "patch selects HOTPLUG_CPU")


def validate_manifest_and_series(manifest: dict) -> tuple[str, str]:
    require(manifest["schema"] == 1, "manifest schema changed")
    require(manifest["architecture"] == "arm64",
            "manifest architecture changed")
    require(manifest["patch_series"] == str(CANONICAL_SERIES),
            "manifest canonical series changed")
    require(manifest["config"]["default_profile"] == "full",
            "default profile changed")
    profiles = manifest["config"]["profiles"]
    require(profiles["full"] == {
        "base": "defconfig",
        "fragments": ["configs/gemini.fragment"],
    }, "default full profile inputs changed")
    require(PROFILE in profiles, "P24 closed-owner profile missing")
    profile = profiles[PROFILE]
    require(profile == {
        "base": "defconfig",
        "patch_series": str(PROFILE_SERIES),
        "fragments": FRAGMENTS,
    }, "P24 closed-owner profile inputs changed")
    fragment_users = [
        name for name, candidate in profiles.items()
        if FRAGMENTS[-1] in candidate.get("fragments", [])
    ]
    require(PROFILE in fragment_users, "P24 fragment user missing")

    parent = series_entries(PARENT_SERIES)
    child = series_entries(PROFILE_SERIES)
    patch_entry = str(PATCH.relative_to("patches"))
    require(child == parent + [patch_entry],
            "P24 profile is not the exact P30 parent plus patch 0159")
    canonical = series_entries(CANONICAL_SERIES)
    positions = [canonical.index(entry) for entry in child]
    require(positions == sorted(positions) and len(set(positions)) == len(positions),
            "P24 series is not a canonical-order subsequence")
    for name in fragment_users:
        candidate = profiles[name]
        selected_series = Path(
            candidate.get("patch_series") or manifest["patch_series"]
        )
        require(
            is_subsequence(child, series_entries(selected_series)),
            f"P24 fragment user does not retain the closed-owner series: {name}",
        )

    series_hash = patch_series_hash(PROFILE_SERIES)
    require(series_hash == PATCH_SERIES_SHA256, "patch-series identity changed")
    state_hash = source_state_hash(manifest, series_hash)
    require(state_hash == SOURCE_STATE_SHA256, "source-state identity changed")
    cfg_hash = config_hash(profile)
    require(cfg_hash == CONFIG_SHA256, "configuration-input identity changed")

    fragment = (ROOT / FRAGMENTS[-1]).read_text()
    require_tokens(fragment, (
        "CONFIG_ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL=y",
        "# CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST is not set",
        'CONFIG_LOCALVERSION="-gemini-p24-owner-closed"',
        "no production caller",
        "issue CPU_ON",
    ), "P24 fragment")

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
        "PARTIAL_P24_CLOSED_OWNER_MODEL",
        "named_prerequisite_subsets=8192",
        "exact_admission_probes=32768",
        "exact_denials=32768",
        "malformed_rejections=12",
        "reachable_owner_states=1",
        "authorized_outcomes=0",
        "violations=0",
        "PASS immutable CLOSED/UNINITIALIZED denial contract",
    ), "oracle output")
    require_tokens(mutation_output, (
        "caller-readiness-authorizes: CALLER_READINESS_NOT_AUTHORITY",
        "cpu-on-issued: CPU_ON_NOT_ISSUED",
        "reset-opens-owner: RESET_NOT_AUTHORITY",
        "mutations_rejected=25/25",
        "PASS intended-check CLOSED-owner mutation suite",
    ), "mutation output")

    readme = (EXPERIMENT / "README.md").read_text()
    design = (EXPERIMENT / "DESIGN.md").read_text()
    review = (
        EXPERIMENT / "results/kernel-static-review-20260805.txt"
    ).read_text()
    require_tokens(readme, (
        "PARTIAL_P24_CLOSED_OWNER_MODEL",
        PATCH_COMMIT,
        SOURCE_STATE_SHA256,
        CONFIG_SHA256,
        "recovery chronology only",
        "the retained original 64-profile series check",
        "No kernel build",
    ), "experiment README")
    require_tokens(design, (
        "Reviewed dormant C mapping",
        "There is no\nproduction `CLOSED -> AVAILABLE` writer",
        "returns `-EAGAIN` before taking the transition mutex",
        "not a P17/P18/P24 token ABI",
        "No production P24 caller",
    ), "experiment design")
    require_tokens(review, (
        "independent_contract_review=GO",
        "independent_boundary_review=GO",
        "independent_p30_review=GO",
        "reviewers=3-GO",
        "production_callers=0",
        "p30_mutator_calls_added=0",
        "cpu_on_calls_added=0",
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
        invariant = run_checked(
            [str(ROOT / "scripts/validate-manifest-series")], ROOT
        )
        require_tokens(invariant, (
            "validation=manifest-series-invariant",
            "profiles_checked=67",
            "canonical_series=patches/series",
        ), "manifest-series audit")
    except (OSError, ValueError, ValidationError) as error:
        print(f"validation_error={error}", file=sys.stderr)
        return 1

    print("validation=p24-closed-owner")
    print("claim=PARTIAL_P24_CLOSED_OWNER_MODEL")
    print(f"patch_sha256={PATCH_SHA256}")
    print(f"patch_id_stable={PATCH_ID}")
    print(f"source_state_sha256={state_hash}")
    print(f"config_inputs_sha256={cfg_hash}")
    print("named_prerequisite_subsets=8192")
    print("exact_admission_probes=32768")
    print("exact_denials=32768")
    print("mutations_rejected=25/25")
    print("reviewers=3-GO")
    print("kunit=8-cases-not-built-or-run")
    print("production_callers=0")
    print("profiles_checked=67")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
