#!/usr/bin/env python3
"""Strictly classify Quasar's fixed native-path debugfs result."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import pathlib
import re
import sys

sys.dont_write_bytecode = True


HEADER_FIELDS = (
    "candidate",
    "state",
    "one_shot",
    "run_error",
    "attempted",
    "transport_completed",
    "value_validated",
    "address",
    "passes",
    "registers",
    "expected",
    "prefills",
    "mode",
    "forced_length_mode",
    "forced_engine",
    "reset_pending",
    "mismatch",
    "failure_pass",
    "failure_index",
    "retries_before",
    "retries_during",
    "retries_after",
    "init_attempts_before",
    "init_attempts_after",
    "init_successes_before",
    "init_successes_after",
    "transfer_attempts_before",
    "transfer_attempts_after",
    "dma_starts_before",
    "dma_starts_after",
    "nonzero_starts_before",
    "nonzero_starts_after",
    "irqs_before",
    "irqs_after",
    "success_counter_contract",
)
SAMPLE_PREFIX_FIELDS = (
    "sample",
    "pass",
    "index",
    "register",
    "expected",
    "prefill",
    "value",
    "ret",
    "validation_error",
    "programmed",
    "transport_completed",
    "value_validated",
    "engine",
    "irq_stat",
)
SNAPSHOT_SUFFIXES = (
    "transfer_len",
    "transfer_len_aux",
    "transac_len",
    "control",
    "start",
    "intr_stat",
    "fifo_stat",
    "dma_en",
    "dma_con",
    "dma_int_flag",
    "dma_tx_len",
    "dma_rx_len",
)
SNAPSHOTS = ("pre", "irq", "post", "drained")
SAMPLE_FIELDS = (
    *SAMPLE_PREFIX_FIELDS,
    *(
        f"{snapshot}_{suffix}"
        for snapshot in SNAPSHOTS
        for suffix in SNAPSHOT_SUFFIXES
    ),
    "fifo_stat",
    "fifo_count",
    "fifo_count_drained",
)
REGISTERS = (0x05, 0x06, 0x47, 0x05, 0x06, 0x47)
EXPECTED = (0xD9, 0xD0, 0xC0, 0xD9, 0xD0, 0xC0)
PREFILLS = (0xA5, 0x5A, 0x3C, 0x96, 0x69, 0xC3)
HEX2 = re.compile(r"^[0-9a-f]{2}$")
HEX4 = re.compile(r"^[0-9a-f]{4}$")
HEX8 = re.compile(r"^[0-9a-f]{8}$")
SIGNED = re.compile(r"^-?(?:0|[1-9][0-9]{0,9})$")
UNSIGNED = re.compile(r"^(?:0|[1-9][0-9]{0,9})$")


class ResultError(ValueError):
    """The Quasar result is not exact or not a bounded first failure."""


@dataclass(frozen=True)
class Result:
    classification: str
    header: dict[str, str]
    samples: tuple[dict[str, str], ...]

    @property
    def summary_lines(self) -> tuple[str, ...]:
        values = ",".join(sample["value"] for sample in self.samples)
        return (
            "validation=quasar-native-result",
            f"classification={self.classification}",
            f"run_error={self.header['run_error']}",
            f"attempted={self.header['attempted']}",
            f"transport_completed={self.header['transport_completed']}",
            f"value_validated={self.header['value_validated']}",
            f"failure_pass={self.header['failure_pass']}",
            f"failure_index={self.header['failure_index']}",
            f"values={values or 'none'}",
            "forced_length_mode=none",
            "forced_engine=none",
            "explicit_reset=none",
        )


def ordered_fields(line: str, order: tuple[str, ...], label: str) -> dict[str, str]:
    tokens = line.split(" ")
    if len(tokens) != len(order) or any(not token for token in tokens):
        raise ResultError(f"{label} field count or spacing changed")
    result: dict[str, str] = {}
    for key, token in zip(order, tokens, strict=True):
        if token.count("=") != 1:
            raise ResultError(f"{label} token grammar changed")
        actual, value = token.split("=", 1)
        if actual != key or not value:
            raise ResultError(f"{label} field order changed at {key}")
        result[key] = value
    return result


def unsigned(value: str, label: str, maximum: int = 1_000_000) -> int:
    if UNSIGNED.fullmatch(value) is None:
        raise ResultError(f"{label} is not canonical unsigned decimal")
    number = int(value, 10)
    if number > maximum:
        raise ResultError(f"{label} is out of bounds")
    return number


def signed(value: str, label: str) -> int:
    if SIGNED.fullmatch(value) is None:
        raise ResultError(f"{label} is not canonical signed decimal")
    number = int(value, 10)
    if not -(2**31) <= number < 2**31:
        raise ResultError(f"{label} is out of bounds")
    return number


def exact_ready_status() -> str:
    return (
        "candidate=Quasar state=ready one_shot=unused run_error=0 "
        "attempted=0 transport_completed=0 value_validated=0 address=0x69 "
        "passes=2 registers=05,06,47 expected=d9,d0,c0 "
        "prefills=a5,5a,3c,96,69,c3 mode=none "
        "forced_length_mode=none forced_engine=none reset_pending=0 "
        "mismatch=0 failure_pass=2 failure_index=3 "
        "retries_before=1 retries_during=1 retries_after=1 "
        "init_attempts_before=1 init_attempts_after=1 "
        "init_successes_before=1 init_successes_after=1 "
        "transfer_attempts_before=0 transfer_attempts_after=0 "
        "dma_starts_before=0 dma_starts_after=0 "
        "nonzero_starts_before=0 nonzero_starts_after=0 "
        "irqs_before=0 irqs_after=0 success_counter_contract=6,0,6,6"
    )


def validate_header(header: dict[str, str]) -> tuple[int, int, int, int]:
    fixed = {
        "candidate": "Quasar",
        "state": "done",
        "one_shot": "consumed",
        "address": "0x69",
        "passes": "2",
        "registers": "05,06,47",
        "expected": "d9,d0,c0",
        "prefills": "a5,5a,3c,96,69,c3",
        "mode": "none",
        "forced_length_mode": "none",
        "forced_engine": "none",
        "reset_pending": "0",
        "retries_before": "1",
        "retries_after": "1",
        "init_attempts_before": "1",
        "init_successes_before": "1",
        "transfer_attempts_before": "0",
        "dma_starts_before": "0",
        "nonzero_starts_before": "0",
        "irqs_before": "0",
        "success_counter_contract": "6,0,6,6",
    }
    for key, wanted in fixed.items():
        if header[key] != wanted:
            raise ResultError(f"Quasar header changed: {key}")

    run_error = signed(header["run_error"], "run_error")
    attempted = unsigned(header["attempted"], "attempted", 6)
    completed = unsigned(
        header["transport_completed"], "transport_completed", 6
    )
    validated = unsigned(header["value_validated"], "value_validated", 6)
    if not validated <= completed <= attempted:
        raise ResultError("Quasar result counters are not monotonic")
    if unsigned(header["mismatch"], "mismatch", 1) not in {0, 1}:
        raise ResultError("mismatch is not boolean")
    retries_during = unsigned(header["retries_during"], "retries_during", 1)
    if retries_during not in {0, 1}:
        raise ResultError("retries_during changed")

    counters = (
        "init_attempts_after",
        "init_successes_after",
        "transfer_attempts_after",
        "dma_starts_after",
        "nonzero_starts_after",
        "irqs_after",
    )
    parsed = {key: unsigned(header[key], key) for key in counters}
    if parsed["init_successes_after"] > parsed["init_attempts_after"]:
        raise ResultError("init success count exceeds attempts")
    if parsed["transfer_attempts_after"] != attempted:
        raise ResultError("transfer counter does not equal attempted samples")
    for key in ("dma_starts_after", "nonzero_starts_after", "irqs_after"):
        if parsed[key] > attempted:
            raise ResultError(f"{key} exceeds attempted samples")
    return run_error, attempted, completed, validated


def validate_sample(
    sample: dict[str, str],
    ordinal: int,
    completed_count: int,
    validated_count: int,
) -> None:
    pass_index, register_index = divmod(ordinal, 3)
    fixed_hex = {
        "register": REGISTERS[ordinal],
        "expected": EXPECTED[ordinal],
        "prefill": PREFILLS[ordinal],
    }
    if unsigned(sample["sample"], "sample ordinal", 5) != ordinal:
        raise ResultError("sample ordinal changed")
    if unsigned(sample["pass"], "sample pass", 1) != pass_index:
        raise ResultError("sample pass changed")
    if unsigned(sample["index"], "sample index", 2) != register_index:
        raise ResultError("sample register index changed")
    for key, wanted in fixed_hex.items():
        if HEX2.fullmatch(sample[key]) is None or int(sample[key], 16) != wanted:
            raise ResultError(f"sample {ordinal} {key} changed")
    if HEX2.fullmatch(sample["value"]) is None:
        raise ResultError(f"sample {ordinal} value is not lowercase hex")

    ret = signed(sample["ret"], f"sample {ordinal} ret")
    validation_error = signed(
        sample["validation_error"],
        f"sample {ordinal} validation_error",
    )
    programmed = unsigned(sample["programmed"], "programmed", 1)
    transport = unsigned(sample["transport_completed"], "transport_completed", 1)
    validated = unsigned(sample["value_validated"], "value_validated", 1)
    if transport != int(ordinal < completed_count):
        raise ResultError("sample transport flags are not a contiguous prefix")
    if validated != int(ordinal < validated_count):
        raise ResultError("sample validation flags are not a contiguous prefix")
    if validated and not transport:
        raise ResultError("validated sample lacks transport completion")
    if transport and ret != 2:
        raise ResultError("transport-complete sample return is not two")
    if not transport and ret == 2:
        raise ResultError("transport-incomplete sample returned two")
    if validated:
        if validation_error or int(sample["value"], 16) != EXPECTED[ordinal]:
            raise ResultError("validated sample value or status changed")
    elif validation_error >= 0:
        raise ResultError("failed sample lacks a negative validation error")
    if programmed:
        if sample["engine"] not in {"fifo", "dma"}:
            raise ResultError("programmed sample engine changed")
    elif sample["engine"] != "unobserved":
        raise ResultError("unprogrammed sample inferred an engine")

    if HEX4.fullmatch(sample["irq_stat"]) is None:
        raise ResultError("sample IRQ aggregate is not lowercase 16-bit hex")
    for snapshot in SNAPSHOTS:
        for suffix in SNAPSHOT_SUFFIXES:
            key = f"{snapshot}_{suffix}"
            matcher = HEX8 if suffix.startswith("dma_") else HEX4
            if matcher.fullmatch(sample[key]) is None:
                raise ResultError(f"sample snapshot grammar changed: {key}")
    if HEX4.fullmatch(sample["fifo_stat"]) is None:
        raise ResultError("sample FIFO status is not lowercase 16-bit hex")
    unsigned(sample["fifo_count"], "sample fifo_count", 65535)
    unsigned(sample["fifo_count_drained"], "sample fifo_count_drained", 65535)


def validate_success(header: dict[str, str], samples: tuple[dict[str, str], ...]) -> None:
    exact = {
        "run_error": "0",
        "attempted": "6",
        "transport_completed": "6",
        "value_validated": "6",
        "mismatch": "0",
        "failure_pass": "2",
        "failure_index": "3",
        "retries_during": "0",
        "init_attempts_after": "1",
        "init_successes_after": "1",
        "transfer_attempts_after": "6",
        "dma_starts_after": "0",
        "nonzero_starts_after": "6",
        "irqs_after": "6",
    }
    for key, wanted in exact.items():
        if header[key] != wanted:
            raise ResultError(f"successful Quasar header changed: {key}")
    for ordinal, sample in enumerate(samples):
        required = {
            "value": f"{EXPECTED[ordinal]:02x}",
            "ret": "2",
            "validation_error": "0",
            "programmed": "1",
            "transport_completed": "1",
            "value_validated": "1",
            "engine": "fifo",
            "irq_stat": "0001",
            "pre_transfer_len": "0101",
            "pre_transfer_len_aux": "0000",
            "pre_transac_len": "0002",
            "pre_control": "003a",
            "irq_intr_stat": "0001",
            "fifo_count": "1",
            "fifo_count_drained": "0",
        }
        for key, wanted in required.items():
            if sample[key] != wanted:
                raise ResultError(f"successful sample {ordinal} changed: {key}")
        for snapshot in SNAPSHOTS:
            for suffix in (
                "dma_en",
                "dma_con",
                "dma_int_flag",
                "dma_tx_len",
                "dma_rx_len",
            ):
                key = f"{snapshot}_{suffix}"
                if sample[key] != "00000000":
                    raise ResultError(
                        f"successful sample {ordinal} APDMA changed: {key}"
                    )


def validate_failure(
    header: dict[str, str],
    samples: tuple[dict[str, str], ...],
) -> None:
    attempted = int(header["attempted"], 10)
    completed = int(header["transport_completed"], 10)
    validated = int(header["value_validated"], 10)
    mismatch = int(header["mismatch"], 10)
    if int(header["run_error"], 10) >= 0:
        raise ResultError("bounded failure lacks a negative run error")
    if attempted == 0:
        if (header["failure_pass"], header["failure_index"]) != ("2", "3"):
            raise ResultError("pre-transfer failure sentinel changed")
        if completed or validated or mismatch:
            raise ResultError("pre-transfer failure claims sample progress")
        if header["retries_during"] != "1":
            raise ResultError("pre-transfer failure changed retries")
    elif validated < attempted:
        expected_pass, expected_index = divmod(attempted - 1, 3)
        if (
            header["failure_pass"],
            header["failure_index"],
        ) != (str(expected_pass), str(expected_index)):
            raise ResultError("stop-first failure location changed")
        if validated != attempted - 1 or completed not in {
            attempted - 1,
            attempted,
        }:
            raise ResultError("failure does not stop at the first sample")
        if header["retries_during"] != "0":
            raise ResultError("attempted failure did not use zero retries")
        last = samples[-1]
        observed_mismatch = int(
            last["transport_completed"] == "1"
            and last["value"] != last["expected"]
        )
        if mismatch != observed_mismatch:
            raise ResultError("failure mismatch attribution changed")
    else:
        if (header["failure_pass"], header["failure_index"]) != ("2", "3"):
            raise ResultError("post-run counter failure sentinel changed")
        if mismatch or header["retries_during"] != "0":
            raise ResultError("post-run counter failure attribution changed")
        success_counters = (
            header["init_attempts_after"],
            header["init_successes_after"],
            header["transfer_attempts_after"],
            header["dma_starts_after"],
            header["nonzero_starts_after"],
            header["irqs_after"],
        )
        if success_counters == ("1", "1", "6", "0", "6", "6"):
            raise ResultError(
                "post-run failure has no attributable counter mismatch"
            )
    if len(samples) != attempted:
        raise ResultError("failure sample inventory changed")
    for sample in samples:
        if sample["programmed"] != "0":
            continue
        if (
            sample["irq_stat"] != "0000"
            or sample["fifo_stat"] != "0000"
            or sample["fifo_count"] != "65535"
            or sample["fifo_count_drained"] != "65535"
        ):
            raise ResultError("unprogrammed sample contains observed activity")
        for snapshot in SNAPSHOTS:
            for suffix in SNAPSHOT_SUFFIXES:
                width = 8 if suffix.startswith("dma_") else 4
                if sample[f"{snapshot}_{suffix}"] != "0" * width:
                    raise ResultError(
                        "unprogrammed sample snapshot is not zero"
                    )


def validate_text(data: bytes) -> Result:
    if not data or len(data) > 32 * 1024 or b"\0" in data:
        raise ResultError("Quasar result is empty, oversized, or binary")
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise ResultError("Quasar result is not ASCII") from exc
    if not text.endswith("\n") or text.startswith("\n") or "\r" in text:
        raise ResultError("Quasar result framing changed")
    lines = text.splitlines()
    header = ordered_fields(lines[0], HEADER_FIELDS, "Quasar header")
    run_error, attempted, completed, validated = validate_header(header)
    if len(lines) != attempted + 1:
        raise ResultError("Quasar sample line count changed")
    samples = tuple(
        ordered_fields(line, SAMPLE_FIELDS, f"Quasar sample {ordinal}")
        for ordinal, line in enumerate(lines[1:])
    )
    for ordinal, sample in enumerate(samples):
        validate_sample(sample, ordinal, completed, validated)
    if run_error == 0:
        validate_success(header, samples)
        classification = "complete-success"
    else:
        validate_failure(header, samples)
        classification = "bounded-stop-first-failure"
    return Result(classification, header, samples)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = validate_text(args.result.read_bytes())
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("\n".join(result.summary_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
