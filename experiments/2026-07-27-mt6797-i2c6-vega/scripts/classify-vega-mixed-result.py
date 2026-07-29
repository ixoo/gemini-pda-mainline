#!/usr/bin/env python3
"""Classify the exact mixed outcome observed in Vega attempt 3."""

from __future__ import annotations

import argparse
import pathlib
import stat
import sys
from collections.abc import Mapping, Sequence

sys.dont_write_bytecode = True


HEADER_ORDER = (
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
)
SAMPLE_ORDER = (
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
)
HEADER_EXPECTED = {
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
REGISTERS = ("05", "06", "47")
PREFILLS = ("a5", "5a", "3c")
PACKED_VALUES = ("d9", "d0", "c0")
AUX_VALUES = ("00", "00", "00")
MAX_RESULT_BYTES = 16 * 1024


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is missing or unsafe")
    if not 0 < info.st_size <= MAX_RESULT_BYTES:
        raise ValueError(f"{label} size is outside the bounded result size")
    return path.read_bytes()


def ordered_fields(
    line: str,
    order: Sequence[str],
    label: str,
) -> dict[str, str]:
    tokens = line.split(" ")
    if len(tokens) != len(order) or any(not token for token in tokens):
        raise ValueError(f"{label} field count or spacing changed")
    parsed: dict[str, str] = {}
    for expected_key, token in zip(order, tokens, strict=True):
        if token.count("=") != 1:
            raise ValueError(f"{label} contains a malformed token")
        key, value = token.split("=", 1)
        if key != expected_key:
            raise ValueError(
                f"{label} field order changed at {expected_key}: got {key}"
            )
        if not value:
            raise ValueError(f"{label} field {key} is empty")
        parsed[key] = value
    return parsed


def require_exact(
    observed: Mapping[str, str],
    expected: Mapping[str, str],
    label: str,
) -> None:
    if set(observed) != set(expected):
        raise ValueError(f"{label} field inventory changed")
    for key, wanted in expected.items():
        actual = observed[key]
        if actual != wanted:
            raise ValueError(
                f"{label} {key}={actual!r}, expected {wanted!r}"
            )


def expected_sample(index: int) -> dict[str, str]:
    mode_index, register_index = divmod(index, 3)
    mode = ("packed-fifo", "packed-dma", "aux-dma")[mode_index]
    fifo = mode == "packed-fifo"
    aux = mode == "aux-dma"
    expected = {
        "sample": str(index),
        "mode": mode,
        "register": REGISTERS[register_index],
        "pre": PREFILLS[register_index],
        "post": (
            AUX_VALUES[register_index]
            if aux
            else PACKED_VALUES[register_index]
        ),
        "ret": "2",
        "engine": "fifo" if fifo else "dma",
        "transfer_len": "0001" if aux else "0101",
        "transfer_len_aux": "0000",
        "transac_len": "0002",
        "control": "003a" if fifo else "003e",
        "irq_stat": "0001",
        "fifo_count": "1" if fifo else "65535",
        "dma_en_pre": "00000000",
        "dma_con_pre": "00000000",
        "dma_int_flag_pre": (
            "00000001" if aux and register_index > 0 else "00000000"
        ),
        "dma_tx_len_pre": "00000000" if fifo else "00000001",
        "dma_rx_len_pre": "00000000" if fifo else "00000001",
        "dma_en_irq": "00000001" if aux else "00000000",
        "dma_int_flag_irq": (
            "00000000" if fifo else ("00000001" if aux else "00000003")
        ),
        "dma_en_post": "00000001" if aux else "00000000",
        "dma_con_post": "00000000" if fifo else "00000001",
        "dma_int_flag_post": (
            "00000000" if fifo else ("00000001" if aux else "00000003")
        ),
        "dma_tx_len_post": "00000000",
        "dma_rx_len_post": "00000001" if aux else "00000000",
    }
    if tuple(expected) != SAMPLE_ORDER:
        raise RuntimeError("internal Vega sample field order changed")
    return expected


def validate_text(data: bytes) -> dict[str, int | str]:
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Vega mixed result is not ASCII") from exc
    if "\r" in text or not text.endswith("\n") or text.endswith("\n\n"):
        raise ValueError("Vega mixed result must use one final LF and no CR")
    lines = text[:-1].split("\n")
    if len(lines) != 10 or any(not line for line in lines):
        raise ValueError(
            "Vega mixed result must be the extracted header and nine samples"
        )

    header = ordered_fields(lines[0], HEADER_ORDER, "Vega header")
    require_exact(header, HEADER_EXPECTED, "Vega header")

    samples: list[dict[str, str]] = []
    for index, line in enumerate(lines[1:]):
        sample = ordered_fields(
            line, SAMPLE_ORDER, f"Vega sample {index}"
        )
        require_exact(
            sample, expected_sample(index), f"Vega sample {index}"
        )
        samples.append(sample)

    packed_fifo = sum(
        sample["mode"] == "packed-fifo"
        and sample["post"] in PACKED_VALUES
        and sample["dma_en_pre"]
        == sample["dma_en_irq"]
        == sample["dma_en_post"]
        == "00000000"
        for sample in samples
    )
    packed_dma = sum(
        sample["mode"] == "packed-dma"
        and sample["post"] in PACKED_VALUES
        and sample["dma_en_irq"] == "00000000"
        and sample["dma_int_flag_irq"] == "00000003"
        and sample["dma_en_post"] == "00000000"
        and sample["dma_int_flag_post"] == "00000003"
        and sample["dma_rx_len_post"] == "00000000"
        for sample in samples
    )
    aux_incomplete = sum(
        sample["mode"] == "aux-dma"
        and sample["post"] == "00"
        and sample["transfer_len_aux"] == "0000"
        and sample["irq_stat"] == "0001"
        and sample["dma_en_irq"] == "00000001"
        and sample["dma_int_flag_irq"] == "00000001"
        and sample["dma_rx_len_post"] == "00000001"
        for sample in samples
    )
    if (packed_fifo, packed_dma, aux_incomplete) != (3, 3, 3):
        raise RuntimeError("internal Vega classification count changed")

    return {
        "classification": "complete-attributable-unexpected-mixed-outcome",
        "physical_transfers": int(header["transfer_attempts"], 10),
        "software_completions": int(header["completed"], 10),
        "validated_receives": packed_fifo + packed_dma,
        "packed_fifo_successes": packed_fifo,
        "packed_dma_successes": packed_dma,
        "auxiliary_dma_successes": 0,
        "auxiliary_controller_complete_apdma_rx_incomplete": aux_incomplete,
        "adapter_retries": (
            f"{header['retries_before']},"
            f"{header['retries_during']},"
            f"{header['retries_after']}"
        ),
        "packed_fifo_tuple": ",".join(PACKED_VALUES),
        "packed_dma_tuple": ",".join(PACKED_VALUES),
        "aux_dma_cpu_tuple": ",".join(AUX_VALUES),
        "aux_dma_transfer_len_aux": "0000",
    }


SUMMARY_ORDER = (
    "classification",
    "physical_transfers",
    "software_completions",
    "validated_receives",
    "packed_fifo_successes",
    "packed_dma_successes",
    "auxiliary_dma_successes",
    "auxiliary_controller_complete_apdma_rx_incomplete",
    "adapter_retries",
    "packed_fifo_tuple",
    "packed_dma_tuple",
    "aux_dma_cpu_tuple",
    "aux_dma_transfer_len_aux",
)


def summary_lines(summary: Mapping[str, int | str]) -> list[str]:
    if tuple(summary) != SUMMARY_ORDER:
        raise RuntimeError("internal Vega summary order changed")
    return [
        "validation=vega-attempt-3-exact-mixed-final",
        *(f"{key}={summary[key]}" for key in SUMMARY_ORDER),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--result",
        required=True,
        type=pathlib.Path,
        help="path to the extracted 10-line Vega FINAL body",
    )
    args = parser.parse_args()
    try:
        summary = validate_text(regular(args.result, "Vega mixed result"))
        output = summary_lines(summary)
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("\n".join(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
