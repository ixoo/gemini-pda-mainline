#!/usr/bin/env python3
"""Validate the offline Gate-7 owner/provider integration review."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parents[1]
FILES = {
    "kernel/manifest.json": "c8f22967e6a45856a9f9b98da1a36f245b9667a909ec24c49cf2aa6c41d3bf64",
    "patches/series": "e37c71c94d8af03b55e003b9ff0d0620b43464aaf7b95ef843386a06bca08a7f",
    "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch": "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5",
    "patches/v7.1.3/0157-arm64-bind-late-CPU-profile-to-kernel-identity.patch": "e184e3c9e04bc51a75001d8dfcdde87ff333dfdab235cf7780dc89f491561950",
    "patches/v7.1.3/0158-arm64-add-dormant-late-CPU-startup-arbitration.patch": "7055f48c5257689b19e9ab32c71075d23ea041eb735a66b59482f0c1a7d9957c",
    "patches/v7.1.3/0159-arm64-add-closed-A72-transaction-owner-model.patch": "39cd3a9e158f2d7ed3e95856002f450709f5886f11e66c9920bb62952394e515",
    "patches/v7.1.3/0160-cpu-add-closed-arm64-CPU-up-admission-hooks.patch": "5fd606b8eb6554d7e9bcdc7a62548091f4e86476593b6999204f719013b8b287",
    "patches/v7.1.3/0166-arm64-record-dormant-A72-P27-preparation.patch": "af0b038c21538fe0df14d23f4e6d41c244a6668e5f7db44d3a9767ed7abb82b7",
    "patches/v7.1.3/0167-arm64-model-dormant-A72-provider-acquire.patch": "79cf88744122528cde95304c34f6daa00100b7ed5b6e49ee8cb3df0f30cfe410",
    "patches/v7.1.3/0168-arm64-model-dormant-A72-provider-refusal-rollback.patch": "8de98ffcdfebfc48c662faa40c36f1b59fa6bffb8cfae3a0c8c8383785388780",
    "patches/v7.1.3/0169-arm64-model-dormant-A72-postprovider-preparation.patch": "2361e3e308bb1cd19079fb5de8699acd544d269bcf93ec986f24a2780d3f7c92",
    "patches/v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch": "becd82625a362af8bf46e91cfb6bfe439fc72b6fec612fcbd3c2eaf9d7b1ce87",
    "patches/v7.1.3/0173-arm64-add-provider-release-refusal-boundary.patch": "39d499200d82cd7debbd0ad2e9591f0a4f98005b7844cee0531e10ef823a7647",
    "patches/v7.1.3/0293-regulator-restore-DA921x-provider-release-registration.patch": "3d483bb5551ee25677204a5c08fdd06f19cb1c89326d9eb8b73467bc4e3a5443",
    "patches/v7.1.3/0294-regulator-add-positive-DA921x-Buck-B-provider-transaction.patch": "4dc1bf5d42aaed8b1d63dbfaf6726d4c20d37ac757b74db38f6df1cf1f59462f",
    "patches/v7.1.3/0295-regulator-test-positive-DA921x-Buck-B-provider-transaction.patch": "1b5cdbdb417176b8488a95994db3df1a6ae95f4b5ab1b17c198dd81c7ddb6a39",
    "experiments/2026-08-20-mainline-da921x-positive-provider-transaction/results/kunit-qemu-20260820.txt": "83f0a7204a3885ac30681564ec62a346a410723f133a607da6f15af47d96f0b8",
    "experiments/2026-08-05-a72-membership-admission-contract/DESIGN.md": "81dd80cd598347bd41857e8cc0c0702c489759d866324f0e5aa7db51c555ee6a",
    "experiments/2026-08-05-a72-safe-off-ownership-contract/README.md": "7d52ee67ed285520a5b1a9f36634e0fb66e3d5f7685082d7d9b0a58c5ad74f8f",
    "experiments/2026-08-05-a72-a41-immutable-plan/results/evidence-audit.tsv": "b170c25e68071d62df96e2d150a5687245ec10e697afcaeacee3d4070007aff8",
    "experiments/2026-08-05-a72-cpu-up-source-closure/DESIGN.md": "4d603e333726f98217b321fb0e25643a888893c568e9ec847d77cc50001c947a",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def main() -> None:
    for relative, expected in FILES.items():
        path = REPO / relative
        require(path.is_file() and not path.is_symlink(), f"unsafe input: {relative}")
        require(sha256(path) == expected, f"input identity changed: {relative}")

    contract = json.loads((ROOT / "contract.json").read_text(encoding="utf-8"))
    require(
        contract["status"] == "completed-not-ready-for-p28-or-cpu8",
        "review status changed",
    )
    safety = contract["safety"]
    for field in (
        "device_access",
        "hardware_write",
        "kernel_build",
        "native_vm_build",
        "boot_candidate",
        "physical_provider_call",
        "p28_effect",
        "cpu_on",
        "cpu_off",
    ):
        require(not safety[field], f"unsafe review permission: {field}")
    require(safety["a26_boot_veto"] == "required", "A26 veto changed")
    require(safety["a14_disable_veto"] == "required", "A14 veto changed")

    decision = contract["decision"]
    require(decision["positive_acquire_can_publish_held"], "R02 result lost")
    require(
        decision["returned_positive_acquire_fault_terminal"] == "missing",
        "returned acquire fault gap changed",
    )
    require(
        decision["pre_p28_positive_release_owner"] == "missing",
        "pre-P28 abort gap changed",
    )
    require(
        decision["first_missing_implementation"]
        == "hardware-free-pre-p28-positive-provider-abort-and-fault-terminal",
        "first implementation boundary changed",
    )

    series = [
        line
        for line in (REPO / "patches/series").read_text().splitlines()
        if line and not line.startswith("#")
    ]
    ordered = [
        "v7.1.3/0167-arm64-model-dormant-A72-provider-acquire.patch",
        "v7.1.3/0168-arm64-model-dormant-A72-provider-refusal-rollback.patch",
        "v7.1.3/0169-arm64-model-dormant-A72-postprovider-preparation.patch",
        "v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch",
        "v7.1.3/0173-arm64-add-provider-release-refusal-boundary.patch",
        "v7.1.3/0293-regulator-restore-DA921x-provider-release-registration.patch",
        "v7.1.3/0294-regulator-add-positive-DA921x-Buck-B-provider-transaction.patch",
        "v7.1.3/0295-regulator-test-positive-DA921x-Buck-B-provider-transaction.patch",
    ]
    positions = [series.index(item) for item in ordered]
    require(
        positions == sorted(positions),
        "owner/provider canonical order changed",
    )

    veto = patch("patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch")
    require("return -EAGAIN;" in veto and "return false;" in veto,
            "CPU boot or disable veto changed")

    owner = patch("patches/v7.1.3/0159-arm64-add-closed-A72-transaction-owner-model.patch")
    require("no production CLOSED -> AVAILABLE writer" in owner,
            "closed-owner boundary changed")
    p27 = patch("patches/v7.1.3/0166-arm64-record-dormant-A72-P27-preparation.patch")
    require("attested source-only preparation ledger, not an MMIO API" in p27,
            "P27 ledger boundary changed")
    p28 = patch("patches/v7.1.3/0169-arm64-model-dormant-A72-postprovider-preparation.patch")
    require("P28 is an attested postprovider preparation, not a hardware API" in p28,
            "P28 ledger boundary changed")

    callback = patch("patches/v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch")
    for token in (
        "mt6797_a72_membership_run_provider_acquire(",
        "return mt6797_a72_membership_confirm_provider_acquire",
        "if (ret != -EOPNOTSUPP ||",
        "return ret;",
    ):
        require(token in callback, f"provider callback token missing: {token}")
    require("MT6797_A72_PROVIDER_FAULT_UNKNOWN" not in callback,
            "returned acquire fault terminal unexpectedly exists")

    refusal = patch("patches/v7.1.3/0168-arm64-model-dormant-A72-provider-refusal-rollback.patch")
    for token in (
        "provider_state != MT6797_A72_PROVIDER_NONE",
        "!a72_owner.active.provider_rejection_valid",
        "P29 records exact P27 restoration",
    ):
        require(token in refusal, f"P29 refusal-only token missing: {token}")
    require("positive_abort" not in refusal and "provider_abort" not in refusal,
            "positive abort unexpectedly exists in P29")

    release = patch("patches/v7.1.3/0173-arm64-add-provider-release-refusal-boundary.patch")
    require("int mt6797_a72_provider_release(" in release,
            "provider release registry function missing")
    require("membership_run_provider_release" not in release,
            "membership release owner unexpectedly exists")

    positive = patch("patches/v7.1.3/0294-regulator-add-positive-DA921x-Buck-B-provider-transaction.patch")
    for token in (
        "DA9213_LEGACY_PROVIDER_FAULT_RETAINED",
        "da9213_legacy_provider_transaction_release",
        "da9213_provider_handle_matches",
        "result->state = DA9213_LEGACY_PROVIDER_RELEASED",
    ):
        require(token in positive, f"positive provider token missing: {token}")

    with (ROOT / "results/integration-matrix.tsv").open(
        encoding="utf-8", newline=""
    ) as source:
        rows = list(csv.DictReader(source, delimiter="\t"))
    require(len(rows) == 15, "integration matrix row count changed")
    by_id = {row["id"]: row for row in rows}
    require(len(by_id) == len(rows), "duplicate integration matrix id")
    require(by_id["I05"]["gate7_consequence"] == "first-source-boundary",
            "pre-P28 boundary changed")
    require(by_id["I08"]["gate7_consequence"] == "do-not-enter",
            "P28 closure changed")
    require(by_id["I13"]["gate7_consequence"] == "retain-a26",
            "A26 matrix result changed")
    require(by_id["I14"]["gate7_consequence"] == "retain-a14",
            "A14 matrix result changed")

    next_implementation = contract["next_implementation"]
    require(next_implementation["hardware_free"], "next slice gained hardware")
    require(next_implementation["default_off"], "next slice is not default-off")
    require(not next_implementation["production_reachability"],
            "next slice gained a production caller")
    forbidden = set(next_implementation["forbidden"])
    require({"p28-effect", "cpu-on", "cpu-off", "device-action"} <= forbidden,
            "next slice lost forbidden effects")

    print("validation=mainline-cpu8-gate7-integration-review")
    print("matrix_rows=15")
    print("positive_provider_proof=passed")
    print("direct_p28_integration=rejected")
    print("next=hardware-free-pre-p28-positive-provider-abort-and-fault-terminal")
    print("buildbox_reconstruction_validation=deferred-dns-unavailable")
    print("hardware_action=none")
    print("device_action=none")
    print("cpu8_cpu9_admission=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
