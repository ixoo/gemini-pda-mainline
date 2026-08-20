#!/usr/bin/env python3
"""Validate the source-pinned Gate-7 CPU8 admission audit."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]

HASHES = {
    "kernel/manifest.json": "3423e7ffc1740f62d4a4575499de069d446afbb4336617e94e92f966e7172375",
    "patches/series": "c3623c3fabd29b851977a80f451e728d663a8f6cea578f388d6372d92260e87c",
    "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch": "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5",
    "patches/v7.1.3/0169-arm64-model-dormant-A72-postprovider-preparation.patch": "2361e3e308bb1cd19079fb5de8699acd544d269bcf93ec986f24a2780d3f7c92",
    "patches/v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch": "becd82625a362af8bf46e91cfb6bfe439fc72b6fec612fcbd3c2eaf9d7b1ce87",
    "patches/v7.1.3/0173-arm64-add-provider-release-refusal-boundary.patch": "39d499200d82cd7debbd0ad2e9591f0a4f98005b7844cee0531e10ef823a7647",
    "experiments/2026-08-20-mainline-da921x-same-value-dt-contract-repair/results/runtime-attempt-2-success-20260820.txt": "d73f98a383a2442f66a5d604f855ba1a6aab88b25fb7b8f924352ffe81a8bd1c",
    "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt": "1295291982ae539681fc817cebc894a6f7abb13484f000500e542caa861adaa4",
    "experiments/2026-08-02-a72-one-way-cpu8-boundary/results/runtime-attempt-1-cpu8-online-20260802.txt": "481d85375ff9a2bdd14f0704c5e4ac33eb557114239d11b97eee1202f3055f95",
    "experiments/2026-08-03-a72-cpu8-late-hold/results/runtime-attempt-2-repeatability-pass-20260803.txt": "aebdff16e9c98086114796b9b091d46e05261bf0fcdd01536be7499c57fd536f",
    "experiments/2026-08-05-a72-safe-off-ownership-contract/results/safe-off-contract.tsv": "8451fbc2910a0d4776efe2d51b84f0bcb3e95ac77310ff425c506bbb59d6af26",
    "experiments/2026-08-05-a72-membership-admission-contract/results/admission-lock-contract.tsv": "d3c10bf62bb89df8301fb2c06145b06ebbdbe8be29437a555a27c33a8ffd0ae5",
    "experiments/2026-08-05-a72-cpu-up-source-closure/results/capability-admission.tsv": "d1dbfe5873deb9f5f4df1bb235593f9fcaf025debfb3cbc4c4711b352dac8008",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(relative: str) -> str:
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"unsafe input: {relative}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    require(digest == HASHES[relative], f"identity changed: {relative}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    sources = {relative: read(relative) for relative in HASHES}
    contract = json.loads((EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
    require(contract["schema"] == "gemini-mainline-cpu8-gate7-admission-audit-v1",
            "contract schema changed")
    require(contract["status"] == "completed-not-ready-for-cpu8",
            "contract status changed")
    require(contract["decision"]["current_mainline_cpu8_ready"] is False,
            "CPU8 was made ready by the audit")
    require(contract["decision"]["first_missing_implementation"] ==
            "default-off-positive-da921x-buckb-provider-acquire-release",
            "first implementation boundary changed")
    require(contract["safety"]["a26_boot_veto"] == "required" and
            contract["safety"]["a14_disable_veto"] == "required",
            "CPU veto changed")

    manifest = json.loads(sources["kernel/manifest.json"])
    profiles = manifest["config"]["profiles"]
    same = profiles["da921x-same-value-write"]["fragments"]
    refusal = profiles["a72-p24-provider-owner-refusal"]["fragments"]
    require("configs/gemini-da921x-same-value-write.fragment" in same,
            "same-value fragment missing")
    require("configs/gemini-da921x-provider-owner-refusal.fragment" not in same,
            "same-value profile gained provider owner")
    require("configs/gemini-a72-p24-closed-hooks.fragment" not in same,
            "same-value profile gained CPU admission hooks")
    for fragment in (
        "configs/gemini-a72-p24-closed-owner.fragment",
        "configs/gemini-a72-p24-closed-hooks.fragment",
        "configs/gemini-da921x-provider-owner-refusal.fragment",
    ):
        require(fragment in refusal, f"refusal profile missing {fragment}")

    acquire = sources[
        "patches/v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch"
    ]
    release = sources[
        "patches/v7.1.3/0173-arm64-add-provider-release-refusal-boundary.patch"
    ]
    veto = sources[
        "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"
    ]
    require("return -EOPNOTSUPP;" in acquire and
            "vote_requested" in acquire and "rail_mutated" in acquire,
            "acquire is no longer structured refusal")
    require("provider-owner release refused: no rollback owner" in release and
            "return -EOPNOTSUPP;" in release,
            "release is no longer structured refusal")
    require("return -EAGAIN;" in veto and "cpu_can_disable" in veto,
            "CPU boot/disable veto changed")

    runtime = sources[
        "experiments/2026-08-20-mainline-da921x-same-value-dt-contract-repair/results/runtime-attempt-2-success-20260820.txt"
    ]
    for marker in (
        "runtime_classification=success-same-value-write",
        "write_entry_payload=da,46",
        "trigger_retries=0",
        "CPU8_CPU9_admission=closed",
        "result=pass",
    ):
        require(marker in runtime, f"mainline runtime marker missing: {marker}")

    rollback = sources[
        "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt"
    ]
    require("state=rolled-back" in rollback and
            "formal_disposition=accepted-pre-isolation-rollback" in rollback,
            "rollback evidence changed")
    online = sources[
        "experiments/2026-08-02-a72-one-way-cpu8-boundary/results/runtime-attempt-1-cpu8-online-20260802.txt"
    ]
    require("cpu8-online-held" in online and
            "CPU8 reached the attributable online checkpoint once" in online,
            "CPU8 startup evidence changed")
    execution = sources[
        "experiments/2026-08-03-a72-cpu8-late-hold/results/runtime-attempt-2-repeatability-pass-20260803.txt"
    ]
    require("repeatability" in execution.lower() and "CPU8" in execution,
            "CPU8 execution evidence changed")

    with (EXPERIMENT / "results/admission-matrix.tsv").open(
            encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    require([row["id"] for row in rows] == [f"G{i:02d}" for i in range(1, 13)],
            "matrix rows changed")
    indexed = {row["id"]: row for row in rows}
    require(indexed["G04"]["current_state"] ==
            "not-implemented-current-mainline", "positive provider gap changed")
    require(indexed["G08"]["gate7_consequence"] == "cpu-on-veto-required",
            "CPU_ON boundary changed")
    require(indexed["G12"]["gate7_consequence"] == "a14-veto-required",
            "CPU_OFF boundary changed")

    forbidden = set(contract["next_implementation"]["forbidden"])
    require({"device-action", "cpu-on", "cpu-off", "page-con-access"} <= forbidden,
            "next implementation opened a forbidden action")
    require(contract["next_implementation"]["hardware_free"] is True,
            "next implementation became hardware-active")

    print("validation=mainline-cpu8-gate7-admission-audit")
    print("source_and_evidence_hashes=13-of-13")
    print("admission_matrix=12-of-12")
    print("gate6_same_value_write=passed")
    print("historical_cpu8_startup=confirmed")
    print("current_positive_provider=missing")
    print("a26_boot_veto=required")
    print("a14_disable_veto=required")
    print("next=hardware-free-positive-provider-acquire-release")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
