#!/usr/bin/env python3
"""Review the current A25 callback inventory and P32 rollback contract."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INVENTORY = ROOT / "experiments/2026-08-05-a72-cpu-up-source-closure/results/post-cpu-on-callbacks.tsv"
CLOSURE = ROOT / "experiments/2026-08-05-a72-cpu-up-source-closure/results/p30-p32-closure.tsv"
SERIES = ROOT / "patches/series"
MANIFEST = ROOT / "kernel/manifest.json"
PROFILE = ROOT / "configs/gemini-a72-p32-rollback.fragment"


def load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def ordered(text: str, tokens: tuple[str, ...]) -> bool:
    positions = [text.lower().find(token.lower()) for token in tokens]
    return all(position >= 0 for position in positions) and positions == sorted(positions)


def main() -> int:
    callbacks = load_tsv(INVENTORY)
    closure = load_tsv(CLOSURE)
    callback_by_id = {row["id"]: row for row in callbacks}
    closure_by_id = {row["id"]: row for row in closure}

    expected_callbacks = tuple(f"H{index:02d}" for index in range(1, 16))
    require(tuple(callback_by_id) == expected_callbacks, "callback inventory is not H01-H15 canonical order")
    for identifier in expected_callbacks:
        row = callback_by_id[identifier]
        require(all(row.get(field, "").strip() for field in (
            "order_or_scope", "callback_set", "up_result", "rollback_or_down_result",
            "selected_reachability", "closure_effect",
        )), f"{identifier} has an empty review field")

    require(ordered(callback_by_id["H06"]["callback_set"], ("writeback", "vmstat", "padata")),
            "H06 mandatory dynamic order changed")
    require(ordered(callback_by_id["H07"]["callback_set"], ("arm64 topology", "io-wq", "cpu-capacity")),
            "H07 mandatory dynamic order changed")
    require(ordered(callback_by_id["H08"]["callback_set"], ("arm64 cpuinfo", "percpu-counter", "CPU LED", "printk")),
            "H08 mandatory dynamic order changed")
    for identifier in ("H09", "H10", "H11", "H12"):
        require("conditional" in callback_by_id[identifier]["order_or_scope"].lower(),
                f"{identifier} is missing conditional insertion classification")

    require(tuple(closure_by_id) == ("P32A", "P32D", "P32F", "P32X", "P32R"),
            "P32 closure rows are not canonical")
    for identifier in closure_by_id:
        row = closure_by_id[identifier]
        forbidden = row["forbidden"].lower()
        require("cpu_off" in forbidden and "affinity" in forbidden,
                f"{identifier} does not forbid CPU_OFF and affinity")
        require(row["retained_state"].strip(), f"{identifier} lacks retained-state contract")

    series_lines = [line.strip() for line in SERIES.read_text().splitlines()
                    if line.strip() and not line.startswith("#")]
    require(len(series_lines) == 179, "current series is not the 179-entry review target")
    for suffix in (
        "0182-arm64-add-dormant-P32-rollback-guards.patch",
        "0183-arm64-consume-P32-rollback-side-channel.patch",
        "0184-arm64-retire-consumed-P32-generation.patch",
        "0185-arm64-bind-P32-operation-to-target.patch",
        "0186-arm64-parenthesize-P32-publication-check.patch",
        "0187-arm64-capture-P32A-rollback-prefix.patch",
        "0188-arm64-capture-P32X-effect-prefix.patch",
        "0189-arm64-hand-P32R-into-owner-ledger.patch",
        "0190-arm64-close-P32A-P32X-coverage.patch",
    ):
        require(any(line.endswith(suffix) for line in series_lines), f"missing current P32 patch {suffix}")

    manifest = json.loads(MANIFEST.read_text())
    profile = manifest["config"]["profiles"]["a72-p32-rollback"]
    require(profile["patch_series"] == "patches/series", "P32 profile does not select canonical series")
    require("configs/gemini-a72-p32-rollback.fragment" in profile["fragments"],
            "P32 profile does not select its fragment")
    profile_text = PROFILE.read_text()
    require("CONFIG_ARM64_MT6797_A72_P32_ROLLBACK=y" in profile_text,
            "P32 fragment is not enabled")
    require("CPU_ON/OFF" in profile_text and "no" in profile_text.lower(),
            "P32 fragment does not document the closed hardware boundary")

    callback_sha256 = hashlib.sha256(INVENTORY.read_bytes()).hexdigest()
    closure_sha256 = hashlib.sha256(CLOSURE.read_bytes()).hexdigest()
    series_sha256 = hashlib.sha256(SERIES.read_bytes()).hexdigest()
    patchset_material = [f"{series_sha256}  patches/series"]
    for relative in series_lines:
        patchset_material.append(
            f"{hashlib.sha256((ROOT / "patches" / relative).read_bytes()).hexdigest()}  {relative}"
        )
    patchset_sha256 = hashlib.sha256(("\n".join(patchset_material) + "\n").encode()).hexdigest()

    print("claim=PARTIAL_A25_SOURCE_ROLLBACK_REVIEW")
    print(f"callback_rows={len(callbacks)}/{len(expected_callbacks)}")
    print("mandatory_dynamic_order=3/3")
    print("conditional_insertions=4/4")
    print("p32_closure_rows=5/5")
    print("current_p32_patches=9/9")
    print("same_boot_numeric_identity=OPEN_H13")
    print("cpu_on_cpu_off_device_action=CLOSED")
    print(f"callback_inventory_sha256={callback_sha256}")
    print(f"p32_closure_sha256={closure_sha256}")
    print(f"series_sha256={series_sha256}")
    print(f"patchset_sha256={patchset_sha256}")
    print("status=PASS_PARTIAL_A25")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
