#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Validate the offline MT6797 TOPRGU minimal-restart candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
PATCH = ROOT / "patches/v7.1.3/0543-watchdog-mtk-minimal-MT6797-restart.patch"
PARENT_SERIES = ROOT / "patches/series-before-v4-conversion-correction"
EXPERIMENT_SERIES = ROOT / "patches/series-mt6797-toprgu-minimal-restart"
CANONICAL = ROOT / "patches/series"
MANIFEST = ROOT / "kernel/manifest.json"
PROPOSAL = HERE / "proposal.json"
FRAGMENT = ROOT / "configs/gemini-mt6797-toprgu-minimal-restart.fragment"
OLD_BLOB = "e7b26be"

FROZEN = {
    "patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch": (
        "81168e4cc12d9ffad7645f667c0211d8dff73b0dadda3ebd422f63378e411d56",
        ("watchdog_set_restart_priority(&mtk_wdt->wdt_dev, 128);",
         "wdt_data->restart_priority : 128);", ".restart_priority = 255,"),
    ),
    "patches/v7.1.3/0090-watchdog-mtk-expose-MT6797-TOPRGU-resets.patch": (
        "d7699b40087a7b830802d3c868e01f30f76fb92d12c54dc2f58d0ced1fdb245a",
        ("drivers/watchdog/mtk_wdt.c", ".toprgu_sw_rst_num = MT6797_TOPRGU_SW_RST_NUM",
         "#reset-cells = <1>;"),
    ),
    "patches/v7.1.3/0303-watchdog-mtk-capture-raw-boot-status.patch": (
        "29fbdb0190d3dd3931839bbb6f0ea936cf4e0c4219f44b4e183422a343cae97a",
        ("WDT_STATUS", ".has_boot_status = true", "mtk_wdt_boot_status_snapshot"),
    ),
    "patches/v7.1.3/0308-watchdog-mtk-expose-locked-reset-status.patch": (
        "917182820800180aaa45d555c9e73f43847ded4c2e23b0a875e8071613aa5c33",
        ("toprgu_reset_status", ".status = toprgu_reset_status", "data->lock"),
    ),
    "patches/v7.1.3/0386-watchdog-mediatek-add-one-shot-recovery-takeover.patch": (
        "24d270194617f07ac5da36c0437658aee988ffcddcf78bcc1c3b36c4ab748a33",
        ("mtk_wdt_mutation_begin", "recovery_takeover", "WDT_MODE_RECOVERY_MASK",
         "WDT_MODE_AUTO_START"),
    ),
    "patches/v7.1.3/0387-watchdog-mediatek-test-one-shot-recovery-takeover.patch": (
        "40862eeae0a41f7ce228cbfa2e16e9f651b11ee0502b3c4f959cc4f587c7c12f",
        ("CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER_KUNIT_TEST",
         "mtk_wdt_recovery_mode_fault_test", "KUNIT_CASE"),
    ),
    "patches/v7.1.3/0489-watchdog-mediatek-validate-recovery-owner-read-only.patch": (
        "940c2158c04376d856b7a0cc6b7aa69702883b5e88b2959b3d82589cfce18b91",
        ("mtk_wdt_recovery_validate_owner", "mtk_wdt_recovery_validate",
         "state.writes"),
    ),
}
INDEX_CHAIN = {
    "patches/v7.1.3/0303-watchdog-mtk-capture-raw-boot-status.patch": ("c20f921", "450f50e"),
    "patches/v7.1.3/0308-watchdog-mtk-expose-locked-reset-status.patch": ("450f50e", "21c47b9"),
    "patches/v7.1.3/0386-watchdog-mediatek-add-one-shot-recovery-takeover.patch": ("21c47b9", "f275de2"),
    "patches/v7.1.3/0387-watchdog-mediatek-test-one-shot-recovery-takeover.patch": ("f275de2", "693dc5a"),
    "patches/v7.1.3/0489-watchdog-mediatek-validate-recovery-owner-read-only.patch": ("693dc5a", OLD_BLOB),
    "patches/v7.1.3/0543-watchdog-mtk-minimal-MT6797-restart.patch": (OLD_BLOB, "5d11c4a"),
}


class Refusal(Exception):
    """A candidate failed a named guard."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def reject(condition: bool, reason: str) -> None:
    if not condition:
        raise Refusal(reason)


def series_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def changed(patch: str) -> tuple[list[str], list[str], list[str]]:
    paths: list[str] = []
    removed: list[str] = []
    added: list[str] = []
    for line in patch.splitlines():
        if line.startswith("diff --git a/"):
            paths.append(line.split(" b/", 1)[1])
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---") and line != "-- ":
            removed.append(line[1:])
    return paths, removed, added


def mtk_blob_pair(patch: str) -> tuple[str, str] | None:
    blocks = patch.split("diff --git ")
    for block in blocks:
        if block.startswith("a/drivers/watchdog/mtk_wdt.c "):
            match = re.search(r"^index ([0-9a-f]+)\.\.([0-9a-f]+) 100644$",
                              block, re.MULTILINE)
            return (match.group(1), match.group(2)) if match else None
    return None


def validate_frozen(frozen: dict[str, str] | None = None) -> None:
    """Pin historical content, critical behavior, and the mtk_wdt.c blob chain."""
    frozen = frozen or {relative: (ROOT / relative).read_text() for relative in FROZEN}
    for relative, (expected_hash, markers) in FROZEN.items():
        text = frozen[relative]
        reject(hashlib.sha256(text.encode()).hexdigest() == expected_hash,
               f"FROZEN_SHA256:{relative}")
        for marker in markers:
            reject(marker in text, f"FROZEN_BEHAVIOR:{relative}:{marker}")
    for relative, (old, new) in INDEX_CHAIN.items():
        text = PATCH.read_text() if relative.endswith("0543-watchdog-mtk-minimal-MT6797-restart.patch") else frozen[relative]
        reject(mtk_blob_pair(text) == (old, new), f"FROZEN_BLOB_CHAIN:{relative}")
    reject("diff --git a/drivers/watchdog/mtk_wdt.c" in frozen[
        "patches/v7.1.3/0090-watchdog-mtk-expose-MT6797-TOPRGU-resets.patch"],
           "FROZEN_BLOB_CHAIN:0090-mtk_wdt.c-context")


ALLOWED_REMOVED = {
    "\t.restart_priority = 255,", "\tu32 reg;",
    "\treg = readl(wdt_base + WDT_MODE);", "\tif (reg & WDT_MODE_EN) {",
    "\t\tif (mtk_wdt->use_auto_restart) {", "\t\t\tif (wdt_dev->pretimeout)",
    "\t\t\t\treg |= WDT_MODE_IRQ_EN | WDT_MODE_DUAL_EN;", "\t\t\telse",
    "\t\t\t\treg &= ~(WDT_MODE_IRQ_EN | WDT_MODE_DUAL_EN);",
    "\t\t\twritel(reg | WDT_MODE_AUTO_START | WDT_MODE_KEY,",
    "\t\t\t       wdt_base + WDT_MODE);", "\t\t}",
    "\tif (mtk_wdt->use_auto_restart)", "\t\treg |= WDT_MODE_AUTO_START;",
}
ALLOWED_ADDED = {"\t.restart_priority = 130,",
                 "\tif (readl(wdt_base + WDT_MODE) & WDT_MODE_EN) {"}


def semantic_guards(patch: str, parent_patch: str) -> None:
    """Decision-changing policy checks; called before structural-envelope checks."""
    reject(patch.count("+\t.restart_priority = 130,") == 1,
           "SEMANTIC_MT6797_PRIORITY_130")
    reject("+\t.restart_priority = 128," not in patch and
           "+\t.restart_priority = 255," not in patch,
           "SEMANTIC_MT6797_PRIORITY_NOT_128_OR_255")
    reject(parent_patch.count("+\t\treg |= WDT_MODE_AUTO_START;") == 2,
           "SEMANTIC_RESTART_AUTO_START_RETAINED")
    reject("+\t\tif (mtk_wdt->use_auto_restart)" in parent_patch and
           ".use_auto_restart = true," in parent_patch,
           "SEMANTIC_MT6797_MATCH_RETAINED")
    reject(not ("+\tif (mtk_wdt->use_auto_restart)" in patch and
                "+\t\twritel" in patch),
           "SEMANTIC_NO_MT6797_INIT_POLICY_BRANCH")
    reject("+\t\twritel" not in patch and "+\t\tiowrite32" not in patch,
           "SEMANTIC_NO_INIT_WDT_MODE_WRITE")
    reject(not ("+\tif (mtk_wdt->use_auto_restart)" in patch and
                "+\t\treg |= WDT_MODE_AUTO_START;" in patch),
           "SEMANTIC_NO_START_MATCH_AUTO_START")
    reject(patch.count("-\t\t\twritel(reg | WDT_MODE_AUTO_START | WDT_MODE_KEY,") == 1,
           "SEMANTIC_INIT_AUTO_START_MUTATION_REMOVED")
    reject(patch.count("-\tif (mtk_wdt->use_auto_restart)") == 1 and
           patch.count("-\t\treg |= WDT_MODE_AUTO_START;") == 1,
           "SEMANTIC_START_AUTO_START_MUTATION_REMOVED")


def structural_guards(patch: str) -> None:
    """Generic patch envelope and metadata checks, after semantic guards."""
    paths, removed, added = changed(patch)
    reject(paths == ["drivers/watchdog/mtk_wdt.c"], "STRUCTURE_PATH_SCOPE")
    reject("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" in patch,
           "STRUCTURE_AUTHOR_METADATA")
    reject("Signed-off-by:" not in patch, "STRUCTURE_SYNTHETIC_SIGNOFF")
    reject("/Users/" not in patch and "device_action" not in patch,
           "STRUCTURE_PRIVATE_OR_GENERATED_DATA")
    reject(set(removed) <= ALLOWED_REMOVED and set(added) <= ALLOWED_ADDED,
           "STRUCTURE_CHANGE_ALLOWLIST")
    reject(patch.count("-\t.restart_priority = 255,") == 1,
           "STRUCTURE_PRIORITY_PREDECESSOR")
    reject(patch.count("-\tu32 reg;") == 1 and
           patch.count("+\tif (readl(wdt_base + WDT_MODE) & WDT_MODE_EN) {") == 1,
           "STRUCTURE_INIT_SHAPE")
    reject("mt6797_data" in patch and ".use_auto_restart = true," in patch and
           "recovery_takeover" in patch and "has_boot_status" in patch,
           "STRUCTURE_MATCH_DATA_CONTEXT")
    reject("mtk_wdt_init" in patch and "mtk_wdt_start" in patch,
           "STRUCTURE_LIFECYCLE_CONTEXT")
    reject(sum(line.startswith("@@ ") for line in patch.splitlines()) == 3 and
           "@@ -108,11 +108,11" in patch and
           "@@ -589,20 +589,10" in patch and
           "@@ -626,7 +618,5" in patch,
           "STRUCTURE_HUNK_PLACEMENT")


def validate_candidate(patch: str, parent_patch: str,
                       frozen: dict[str, str] | None = None) -> None:
    validate_frozen(frozen)
    semantic_guards(patch, parent_patch)
    structural_guards(patch)


def subsequence(need: list[str], have: list[str]) -> bool:
    cursor = iter(have)
    return all(any(item == candidate for candidate in cursor) for item in need)


def validate_repository() -> dict[str, object]:
    patch_text = PATCH.read_text()
    parent_series = series_lines(PARENT_SERIES)
    experiment_series = series_lines(EXPERIMENT_SERIES)
    canonical = series_lines(CANONICAL)
    reject(experiment_series == parent_series + [
        "v7.1.3/0543-watchdog-mtk-minimal-MT6797-restart.patch"],
           "SERIES_EXPERIMENT_PREFIX")
    reject(subsequence(experiment_series, canonical), "SERIES_CANONICAL_SUBSEQUENCE")
    manifest = json.loads(MANIFEST.read_text())
    proposal = json.loads(PROPOSAL.read_text())
    profiles = manifest["config"]["profiles"]
    for name, profile in profiles.items():
        selected = series_lines(ROOT / profile.get("patch_series", manifest["patch_series"]))
        reject(subsequence(selected, canonical), f"MANIFEST_ORDER:{name}")
    parent = profiles["da921x-current-service-control"]
    reject(proposal["fragments"][:-1] == parent["fragments"], "PROFILE_PARENT_FRAGMENTS")
    reject(proposal["patch_series"] == "patches/series-mt6797-toprgu-minimal-restart",
           "PROFILE_SERIES")
    reject(proposal["fragments"][-1] == "configs/gemini-mt6797-toprgu-minimal-restart.fragment",
           "PROFILE_LOCALVERSION_FRAGMENT")
    fragment_text = FRAGMENT.read_text()
    reject(fragment_text.count("CONFIG_LOCALVERSION=") == 1 and
           fragment_text.count("CONFIG_") == 1, "PROFILE_LOCALVERSION_ONLY")
    validate_candidate(patch_text, (ROOT / "patches/v7.1.3/0081-watchdog-mtk-set-MT6797-auto-restart-mode.patch").read_text())
    return {"patch_sha256": hashlib.sha256(PATCH.read_bytes()).hexdigest(),
            "parent_series_entries": len(parent_series),
            "experiment_series_entries": len(experiment_series),
            "manifest_profiles_audited": len(profiles)}


def run_fixtures() -> list[dict[str, str]]:
    valid = PATCH.read_text()
    parent = (ROOT / "patches/v7.1.3/0081-watchdog-mtk-set-MT6797-auto-restart-mode.patch").read_text()
    frozen = {relative: (ROOT / relative).read_text() for relative in FROZEN}
    cases: dict[str, tuple[str, str, dict[str, str], str]] = {
        "priority-128": (valid.replace("+\t.restart_priority = 130,", "+\t.restart_priority = 128,"), parent, frozen,
                          "SEMANTIC_MT6797_PRIORITY_130"),
        "priority-255": (valid.replace("+\t.restart_priority = 130,", "+\t.restart_priority = 255,"), parent, frozen,
                         "SEMANTIC_MT6797_PRIORITY_130"),
        "lost-restart-auto-start": (valid, parent.replace("+\t\treg |= WDT_MODE_AUTO_START;", "", 1), frozen,
                                     "SEMANTIC_RESTART_AUTO_START_RETAINED"),
        "changed-non-mt6797-priority": (valid, parent, {
            **frozen,
            "patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch":
                (ROOT / "patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch").read_text().replace(
                    "wdt_data->restart_priority : 128);", "wdt_data->restart_priority : 130);", 1),
        }, "FROZEN_SHA256:patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch"),
        "mt6797-init-policy-branch": (valid.replace(
            "+\tif (readl(wdt_base + WDT_MODE) & WDT_MODE_EN) {",
            "+\tif (mtk_wdt->use_auto_restart) {\n"
            "+\t\twritel(WDT_MODE_AUTO_START | WDT_MODE_KEY, wdt_base + WDT_MODE);\n"
            "+\t}\n"
            "+\tif (readl(wdt_base + WDT_MODE) & WDT_MODE_EN) {"), parent, frozen,
            "SEMANTIC_NO_MT6797_INIT_POLICY_BRANCH"),
        "start-match-data-auto-start": (valid.replace(
            "+\tif (readl(wdt_base + WDT_MODE) & WDT_MODE_EN) {",
            "+\tif (mtk_wdt->use_auto_restart)\n"
            "+\t\treg |= WDT_MODE_AUTO_START;\n"
            "+\tif (readl(wdt_base + WDT_MODE) & WDT_MODE_EN) {"), parent, frozen,
            "SEMANTIC_NO_START_MATCH_AUTO_START"),
        "frozen-recovery-chain": (valid, parent, {
            **frozen,
            "patches/v7.1.3/0489-watchdog-mediatek-validate-recovery-owner-read-only.patch":
                frozen["patches/v7.1.3/0489-watchdog-mediatek-validate-recovery-owner-read-only.patch"].replace(
                    "mtk_wdt_recovery_validate_owner", "mtk_wdt_recovery_validate_owner_mutated", 1),
        }, "FROZEN_SHA256:patches/v7.1.3/0489-watchdog-mediatek-validate-recovery-owner-read-only.patch"),
        "frozen-reset-controller-chain": (valid, parent, {
            **frozen,
            "patches/v7.1.3/0090-watchdog-mtk-expose-MT6797-TOPRGU-resets.patch":
                frozen["patches/v7.1.3/0090-watchdog-mtk-expose-MT6797-TOPRGU-resets.patch"].replace(
                    "MT6797_TOPRGU_SW_RST_NUM", "MT6797_TOPRGU_SW_RST_NUM_MUTATED", 1),
        }, "FROZEN_SHA256:patches/v7.1.3/0090-watchdog-mtk-expose-MT6797-TOPRGU-resets.patch"),
        "frozen-recovery-kunit-chain": (valid, parent, {
            **frozen,
            "patches/v7.1.3/0387-watchdog-mediatek-test-one-shot-recovery-takeover.patch":
                frozen["patches/v7.1.3/0387-watchdog-mediatek-test-one-shot-recovery-takeover.patch"].replace(
                    "mtk_wdt_recovery_mode_fault_test", "mtk_wdt_recovery_mode_fault_test_mutated", 1),
        }, "FROZEN_SHA256:patches/v7.1.3/0387-watchdog-mediatek-test-one-shot-recovery-takeover.patch"),
        "structural-envelope": (valid.replace("drivers/watchdog/mtk_wdt.c", "drivers/watchdog/other.c"), parent, frozen,
                                 "STRUCTURE_PATH_SCOPE"),
    }
    results: list[dict[str, str]] = []
    for name, (candidate, candidate_parent, candidate_frozen, expected) in cases.items():
        try:
            validate_candidate(candidate, candidate_parent, candidate_frozen)
        except Refusal as error:
            reject(error.reason == expected, f"FIXTURE_REASON:{name}:{error.reason}")
            results.append({"name": name, "expected": expected, "observed": error.reason,
                            "outcome": "PASS"})
        else:
            raise Refusal(f"FIXTURE_ACCEPTED:{name}")
    return results


def main() -> int:
    try:
        report = validate_repository()
        report["semantic_fixtures"] = run_fixtures()
        report["result"] = "PASS"
    except (OSError, KeyError, json.JSONDecodeError, Refusal) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
