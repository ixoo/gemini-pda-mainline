#!/usr/bin/env python3
"""Validate a complete successful Orion one-shot debugfs transcript."""

from __future__ import annotations

import argparse
import pathlib
import re
import stat
import sys

sys.dont_write_bytecode = True
import candidate_orion as co


HEADER_FIELDS = {
    "candidate",
    "state",
    "one_shot",
    "run_error",
    "attempted",
    "completed",
    "address",
    "transfer_attempts",
    "dma_starts",
    "nonzero_starts",
    "irqs",
    "retries_before",
    "retries_during",
    "retries_after",
    "registers",
    "modes",
}
SAMPLE_FIELDS = {
    "sample",
    "mode",
    "register",
    "pre",
    "post",
    "ret",
    "engine",
    "transfer_len",
    "transfer_len_aux",
    "transac_len",
    "control",
    "irq_stat",
    "fifo_count",
    "dma_en_pre",
    "dma_con_pre",
    "dma_int_flag_pre",
    "dma_tx_len_pre",
    "dma_rx_len_pre",
    "dma_en_irq",
    "dma_int_flag_irq",
    "dma_en_post",
    "dma_con_post",
    "dma_int_flag_post",
    "dma_tx_len_post",
    "dma_rx_len_post",
}
HEX = re.compile(r"^[0-9a-f]+$")
DECIMAL = re.compile(r"^-?[0-9]+$")
I2C_CONTROL_DMA_EN = 1 << 2
I2C_TRANSAC_COMP = 1 << 0


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def fields(line: str, expected: set[str], label: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for token in line.split():
        if token.count("=") != 1:
            raise ValueError(f"{label} contains a malformed token")
        key, value = token.split("=", 1)
        if key in parsed:
            raise ValueError(f"{label} duplicates field {key}")
        parsed[key] = value
    if set(parsed) != expected:
        missing = sorted(expected - set(parsed))
        extra = sorted(set(parsed) - expected)
        raise ValueError(
            f"{label} field inventory changed: missing={missing} extra={extra}"
        )
    return parsed


def decimal(value: str, label: str) -> int:
    if DECIMAL.fullmatch(value) is None:
        raise ValueError(f"{label} is not decimal")
    return int(value, 10)


def hexadecimal(value: str, width: int, label: str) -> int:
    if len(value) != width or HEX.fullmatch(value) is None:
        raise ValueError(f"{label} is not exact {width}-digit lowercase hex")
    return int(value, 16)


def validate_text(data: bytes) -> dict[str, tuple[int, ...]]:
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Orion result is not ASCII") from exc
    lines = text.splitlines()
    if len(lines) != 10 or any(not line for line in lines):
        raise ValueError("Orion result must contain one header and nine samples")

    header = fields(lines[0], HEADER_FIELDS, "Orion header")
    exact_header = {
        "candidate": "Orion",
        "state": "done",
        "one_shot": "consumed",
        "run_error": "0",
        "attempted": "9",
        "completed": "9",
        "address": "0x69",
        "transfer_attempts": "9",
        "dma_starts": "6",
        "nonzero_starts": "9",
        "irqs": "9",
        "retries_before": "1",
        "retries_during": "0",
        "retries_after": "1",
        "registers": "05,06,47",
        "modes": "packed-fifo,packed-dma,aux-dma",
    }
    for key, wanted in exact_header.items():
        if header[key] != wanted:
            raise ValueError(
                f"Orion header {key}={header[key]!r}, expected {wanted!r}"
            )

    tuples: dict[str, list[int]] = {mode: [] for mode in co.MODE_ORDER}
    expected_order = [
        (mode, register, prefill)
        for mode in co.MODE_ORDER
        for register, prefill in zip(co.REGISTERS, co.PREFILLS, strict=True)
    ]
    for index, (line, expected) in enumerate(
        zip(lines[1:], expected_order, strict=True)
    ):
        mode, register, prefill = expected
        sample = fields(line, SAMPLE_FIELDS, f"Orion sample {index}")
        if decimal(sample["sample"], f"sample {index} index") != index:
            raise ValueError(f"Orion sample {index} index changed")
        if sample["mode"] != mode:
            raise ValueError(f"Orion sample {index} mode changed")
        if hexadecimal(sample["register"], 2, "register") != register:
            raise ValueError(f"Orion sample {index} register changed")
        if hexadecimal(sample["pre"], 2, "prefill") != prefill:
            raise ValueError(f"Orion sample {index} prefill changed")
        post = hexadecimal(sample["post"], 2, "post value")
        tuples[mode].append(post)
        if decimal(sample["ret"], "transfer result") != 2:
            raise ValueError(f"Orion sample {index} did not transfer two messages")
        if hexadecimal(sample["transac_len"], 4, "transaction length") != 2:
            raise ValueError(f"Orion sample {index} transaction length changed")
        if hexadecimal(sample["irq_stat"], 4, "IRQ status") != I2C_TRANSAC_COMP:
            raise ValueError(
                f"Orion sample {index} has error, missing, or extra IRQ status"
            )

        control = hexadecimal(sample["control"], 4, "controller control")
        transfer_len = hexadecimal(
            sample["transfer_len"], 4, "transfer length"
        )
        transfer_len_aux = hexadecimal(
            sample["transfer_len_aux"], 4, "auxiliary transfer length"
        )
        if mode == "packed-fifo":
            if sample["engine"] != "fifo":
                raise ValueError(f"Orion sample {index} did not use FIFO")
            if transfer_len != 0x0101:
                raise ValueError(f"Orion sample {index} packed length changed")
            if control & I2C_CONTROL_DMA_EN:
                raise ValueError(
                    f"Orion sample {index} enabled controller DMA in FIFO mode"
                )
            if decimal(sample["fifo_count"], "FIFO count") != 1:
                raise ValueError(f"Orion sample {index} FIFO count is not one")
            for key in ("dma_en_pre", "dma_en_irq", "dma_en_post"):
                if hexadecimal(sample[key], 8, key):
                    raise ValueError(
                        f"Orion sample {index} started I2C6 APDMA in FIFO mode"
                    )
        else:
            if sample["engine"] != "dma":
                raise ValueError(f"Orion sample {index} did not use DMA")
            if not control & I2C_CONTROL_DMA_EN:
                raise ValueError(
                    f"Orion sample {index} lacks controller DMA enable"
                )
            if decimal(sample["fifo_count"], "FIFO sentinel") != 0xFFFF:
                raise ValueError(f"Orion sample {index} DMA FIFO sentinel changed")
            if mode == "packed-dma" and transfer_len != 0x0101:
                raise ValueError(f"Orion sample {index} packed length changed")
            if mode == "aux-dma" and (
                transfer_len != 1 or transfer_len_aux != 1
            ):
                raise ValueError(f"Orion sample {index} auxiliary length changed")

        for key in (
            "dma_en_pre",
            "dma_con_pre",
            "dma_int_flag_pre",
            "dma_tx_len_pre",
            "dma_rx_len_pre",
            "dma_en_irq",
            "dma_int_flag_irq",
            "dma_en_post",
            "dma_con_post",
            "dma_int_flag_post",
            "dma_tx_len_post",
            "dma_rx_len_post",
        ):
            hexadecimal(sample[key], 8, key)

    return {mode: tuple(values) for mode, values in tuples.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = args.result.resolve(strict=True)
        tuples = validate_text(regular(result, "Orion result"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=orion-complete-success-transcript")
    print("physical_transfers=9")
    print("adapter_retries=1,0,1")
    print("irq_count=exactly-one-per-transfer")
    print("fifo_controller_dma_en=clear")
    print("fifo_i2c6_apdma_channel=unstarted")
    print("shared_ap_dma_clock=not-a-gate")
    for mode in co.MODE_ORDER:
        print(f"{mode}_tuple=" + ",".join(f"{value:02x}" for value in tuples[mode]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
