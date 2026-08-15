#!/usr/bin/env python3
"""Validate the MT6797 handoff pure-decoder linkage patch."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0277-soc-mediatek-build-MT6797-state-decoders-for-handoff.patch"
SERIES = ROOT / "patches/series"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing {label}: {needle}")


def main() -> None:
    text = PATCH.read_text()
    if not text.startswith("From 0000000000000000000000000000000000000000 "):
        raise SystemExit("patch is not a zero-commit git format-patch")
    if "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>" not in text:
        raise SystemExit("unexpected experiment author identity")
    if "Signed-off-by:" in text:
        raise SystemExit("synthetic experiment patch must not carry a DCO sign-off")

    added = "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for needle, label in (
        ("config MTK_MT6797_DVFSP_STATE_DECODERS", "hidden decoder gate"),
        ("default y if MTK_MT6797_DVFSP_HANDOFF || MTK_MT6797_DVFSP_CLOCK_BACKEND", "dual consumer default"),
        ("obj-$(CONFIG_MTK_MT6797_DVFSP_STATE_DECODERS) += mt6797-dvfsp-clock-state.o", "clock decoder ownership"),
        ("obj-$(CONFIG_MTK_MT6797_DVFSP_STATE_DECODERS) += mt6797-dvfsp-cspm-state.o", "CSPM decoder ownership"),
    ):
        require(added, needle, label)

    for forbidden in (
        "readl(", "writel(", "i2c_transfer", "regulator_", "clk_set_",
        "cpu_up(", "cpu_down(", "arm_smccc", "platform_driver_register",
    ):
        if forbidden in added:
            raise SystemExit(f"unexpected state-changing addition: {forbidden}")

    entries = [
        line.strip() for line in SERIES.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    expected = "v7.1.3/" + PATCH.name
    if entries[-1] != expected or entries.count(expected) != 1:
        raise SystemExit("patch 0277 is not the unique canonical-series tail")

    print("validation=handoff-decoder-link")
    print("format_patch=passed")
    print("synthetic_signoff=absent")
    print("decoder_gate=handoff-or-clock-backend")
    print("hardware_transport=unchanged-default-off")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
