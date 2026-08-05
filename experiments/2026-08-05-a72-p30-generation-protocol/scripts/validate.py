#!/usr/bin/env python3
"""Validate the exact source-only P30 protocol-model milestone."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = ROOT / "experiments/2026-08-05-a72-p30-generation-protocol"
MANIFEST = ROOT / "kernel/manifest.json"
CANONICAL_SERIES = Path("patches/series")
PARENT_SERIES = Path("patches/series-a72-reject-gate-a41-kernel-identity")
PROFILE_SERIES = Path(
    "patches/series-a72-reject-gate-a41-kernel-identity-p30-protocol"
)
PATCH = Path(
    "patches/v7.1.3/0158-arm64-add-dormant-late-CPU-startup-arbitration.patch"
)
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-kernel-identity-p30-protocol"
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
]

PATCH_COMMIT = "1402ad95c4db48dd38140c62aea6bf916853f414"
PATCH_SHA256 = "7055f48c5257689b19e9ab32c71075d23ea041eb735a66b59482f0c1a7d9957c"
PATCH_ID = "422751b76eef2f08ff7d8419651a9193ba9a43cc"
PATCH_SERIES_SHA256 = "bc32ff461c6890c92687d8d209b4b73bcb0b18f9ceabfcf45c44659b49ca52c7"
SOURCE_STATE_SHA256 = "dab76fafaf0c21695cfb242329c442ceb137e835f7ca143272b07ef8e7be47fb"
CONFIG_SHA256 = "699f14786e1d64eb3811f0b6c481c31d9e0e77fc96b64eb4d12ebbbfde3b23b0"
ORACLE_SHA256 = "5fd9f11e2c00e409e370a3888adf28e1791088f3a3187f5e0975c2b0965b6139"
MUTATIONS_SHA256 = "5ab83f6d81190e3e3e99ce104841738f49a5150981552ff5b60814ea7bbde123"
REVIEWED_FILES = {
    "arch/arm64/include/asm/late_cpu_startup.h":
        "8e601ae0e1b406f2afc1afad42692e0cdfaaaf5c0bdf32f8e70ea8e944c53d2b",
    "arch/arm64/kernel/late_cpu_startup.c":
        "240a7fc677f841994f707631633f59b27b05fd3803cf9353fbd1f6e8cfb5fbb8",
    "arch/arm64/kernel/late_cpu_startup_test.c":
        "8d33a5638e3471699a2e37c8ed17e4210bab19efbc4175c36fbc9966dff24ad5",
}
PATCH_PATHS = {
    "arch/arm64/Kconfig",
    "arch/arm64/Kconfig.platforms",
    *REVIEWED_FILES,
    "arch/arm64/kernel/Makefile",
    "arch/arm64/kernel/mt6797_psci.c",
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


def validate_patch() -> None:
    raw = (ROOT / PATCH).read_bytes()
    require(sha256_bytes(raw) == PATCH_SHA256, "patch SHA-256 changed")
    text = raw.decode()
    require(text.startswith(f"From {PATCH_COMMIT} "), "format-patch commit changed")
    require("From: Gemini Mainline Project <noreply@invalid>" in text,
            "experiment-only author changed")
    require("Subject: [PATCH 158/158] arm64: add dormant late-CPU startup arbitration"
            in text, "patch subject changed")
    require("Signed-off-by:" not in text, "synthetic author gained a sign-off")
    require("not submission-ready" in text, "submission-readiness warning missing")

    sections = patch_sections(text)
    require(set(sections) == PATCH_PATHS, "patch source-path set changed")
    for path, expected in REVIEWED_FILES.items():
        actual = sha256_bytes(reconstructed_added_file(sections[path]))
        require(actual == expected, f"reviewed source content changed: {path}")

    header = reconstructed_added_file(
        sections["arch/arm64/include/asm/late_cpu_startup.h"]
    ).decode()
    model = reconstructed_added_file(
        sections["arch/arm64/kernel/late_cpu_startup.c"]
    ).decode()
    tests = reconstructed_added_file(
        sections["arch/arm64/kernel/late_cpu_startup_test.c"]
    ).decode()
    require_tokens(header, (
        "not an assembly wire ABI",
        "ARM64_LATE_CPU_STARTUP_PREPARED",
        "ARM64_LATE_CPU_STARTUP_ABORTED",
        "ARM64_LATE_CPU_STARTUP_PUBLISHING",
        "ARM64_LATE_CPU_STARTUP_PANICKED",
        "struct arm64_late_cpu_startup_target",
        "arm64_late_cpu_startup_arm_before_cpu_on",
        "arm64_late_cpu_startup_retire_published_after_p14_p15",
    ), "header")
    require_tokens(model, (
        "deliberately has no production caller",
        "not an MMU-off wire",
        "state == ARM64_LATE_CPU_STARTUP_ABORTED",
        "ARM64_LATE_CPU_QUARANTINE_ILLEGAL_EDGE",
        "late_startup_target_matches_locked(target)",
        "try_wait_for_completion(&late_startup.published)",
        "late_startup_target_online_locked(token->target_cpu)",
        "claimed == ARM64_LATE_CPU_STARTUP_BRANCH_P",
        "late_startup.stuck_interlock = true",
    ), "C model")
    require(model.index("try_wait_for_completion(&late_startup.published)") <
            model.index("late_startup_target_online_locked(token->target_cpu)"),
            "online state is sampled before exact completion drain")
    require(tests.count("KUNIT_CASE(") == 17, "KUnit case count changed")
    require_tokens(tests, (
        ".generation = 42",
        ".generation = 7",
        "late_cpu_startup_prearmed_target_claim_test",
        "late_cpu_startup_publishing_wrong_target_test",
        "late_cpu_startup_invalid_failure_branch_test",
        "ARM64_LATE_CPU_STARTUP_BRANCH_C",
        "arm64_late_cpu_startup_publish_panicked",
    ), "KUnit source")

    kconfig = sections["arch/arm64/Kconfig"]
    require("+\tdepends on KUNIT=y" in kconfig, "built-in KUnit dependency changed")
    mt6797 = sections["arch/arm64/kernel/mt6797_psci.c"]
    require_tokens(mt6797, (
        "+\t0x699f14786e1d64eb, 0x3811f0b6c481c31d,",
        "+\t0x9e0e77fc96b64eb4, 0xd12ebbbfde3b23b0,",
    ), "MT6797 config identity")
    require("+.cpu_" not in mt6797 and "+\treturn -EAGAIN" not in mt6797,
            "patch changes a production MT6797 CPU operation")


def validate_manifest_and_series(manifest: dict) -> tuple[str, str]:
    profiles = manifest["config"]["profiles"]
    require(PROFILE in profiles, "P30 profile missing")
    profile = profiles[PROFILE]
    require(profile == {
        "base": "defconfig",
        "patch_series": str(PROFILE_SERIES),
        "fragments": FRAGMENTS,
    }, "P30 profile inputs changed")

    parent = series_entries(PARENT_SERIES)
    child = series_entries(PROFILE_SERIES)
    require(child == parent + [str(PATCH.relative_to("patches"))],
            "P30 profile is not the exact ABI-7 parent plus patch 0158")
    canonical = series_entries(CANONICAL_SERIES)
    positions = [canonical.index(entry) for entry in child]
    require(positions == sorted(positions) and len(set(positions)) == len(positions),
            "P30 series is not a canonical-order subsequence")
    require(canonical[-1] == str(PATCH.relative_to("patches")),
            "canonical series does not end at patch 0158")

    series_hash = patch_series_hash(PROFILE_SERIES)
    require(series_hash == PATCH_SERIES_SHA256, "patch-series identity changed")
    state_hash = source_state_hash(manifest, series_hash)
    require(state_hash == SOURCE_STATE_SHA256, "source-state identity changed")
    cfg_hash = config_hash(profile)
    require(cfg_hash == CONFIG_SHA256, "configuration-input identity changed")

    fragment = (ROOT / FRAGMENTS[-1]).read_text()
    require_tokens(fragment, (
        "CONFIG_ARM64_MT6797_A72_P30_PROTOCOL_MODEL=y",
        "# CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST is not set",
        'CONFIG_LOCALVERSION="-gemini-p30-model-blocked"',
    ), "P30 fragment")

    gate = (ROOT / "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch").read_text()
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


def validate_oracle_and_docs() -> tuple[str, str]:
    oracle = EXPERIMENT / "scripts/oracle.py"
    mutations = EXPERIMENT / "scripts/test_mutations.py"
    require(sha256_bytes(oracle.read_bytes()) == ORACLE_SHA256,
            "oracle source changed")
    require(sha256_bytes(mutations.read_bytes()) == MUTATIONS_SHA256,
            "mutation source changed")

    oracle_output = run_checked([sys.executable, str(oracle)], EXPERIMENT)
    mutation_output = run_checked([sys.executable, str(mutations)], EXPERIMENT)
    require_tokens(oracle_output, (
        "PARTIAL_P30_PROTOCOL_MODEL",
        "reachable_states=144",
        "accepted_transitions=240",
        "opaque_generation_witness=CPU8/gen42 -> CPU9/gen7",
        "violations=0",
        "PASS corrected bounded contract",
    ), "oracle output")
    require_tokens(mutation_output, (
        "prearmed-target-claim-dropped: PREARMED_TARGET_CLAIM_FAULT",
        "c-to-k-cross-closure: K_C_P_E_U_TERMINAL_RULES",
        "mutations_rejected=17/17",
        "PASS intended-check mutation suite",
    ), "mutation output")

    readme = (EXPERIMENT / "README.md").read_text()
    design = (EXPERIMENT / "DESIGN.md").read_text()
    review = (EXPERIMENT / "results/kernel-static-review-20260805.txt").read_text()
    require_tokens(readme, (
        "PARTIAL_P30_PROTOCOL_MODEL",
        PATCH_COMMIT,
        SOURCE_STATE_SHA256,
        CONFIG_SHA256,
        "recovery chronology only",
        "No kernel build",
    ), "experiment README")
    require_tokens(design, (
        "A claimed C failure parks as C",
        "K-to-C refinement",
        "not an assembly ABI",
        "effect enforcement is intentionally deferred",
    ), "experiment design")
    require_tokens(review, (
        "independent_code_review=GO",
        "independent_contract_review=GO",
        "production_callers=0",
        "build=not-run-roadmap-source-only",
        "A26 and A14 remain closed",
    ), "static review record")
    return oracle_output, mutation_output


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
            "profiles_checked=63",
            "canonical_series=patches/series",
        ), "manifest-series audit")
    except (OSError, ValueError, ValidationError) as error:
        print(f"validation_error={error}", file=sys.stderr)
        return 1

    print("validation=p30-generation-protocol")
    print("claim=PARTIAL_P30_PROTOCOL_MODEL")
    print(f"patch_sha256={PATCH_SHA256}")
    print(f"patch_id_stable={PATCH_ID}")
    print(f"source_state_sha256={state_hash}")
    print(f"config_inputs_sha256={cfg_hash}")
    print("reachable_states=144")
    print("accepted_transitions=240")
    print("mutations_rejected=17/17")
    print("reviewers=2-GO")
    print("kunit=17-cases-not-built-or-run")
    print("production_callers=0")
    print("profiles_checked=63")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
