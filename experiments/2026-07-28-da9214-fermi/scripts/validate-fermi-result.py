#!/usr/bin/env python3
"""Strictly classify Fermi's fixed legacy-topology debugfs result."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True


QUASAR_VALIDATOR = (
    "experiments/2026-07-27-mt6797-i2c6-quasar/"
    "scripts/validate-quasar-result.py"
)
QUASAR_VALIDATOR_SHA256 = (
    "0a2c532dae2ff19438cdfecc0b12ac8c473b23a4b7a40dfce1c151cd9acc19f5"
)


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_quasar() -> ModuleType:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    source = repository / QUASAR_VALIDATOR
    data = regular(source, "source-pinned Quasar result validator")
    if hashlib.sha256(data).hexdigest() != QUASAR_VALIDATOR_SHA256:
        raise ValueError("source-pinned Quasar result validator changed")
    spec = importlib.util.spec_from_file_location("fermi_quasar_result", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Quasar result validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


_Q = load_quasar()
ResultError = _Q.ResultError
ordered_fields = _Q.ordered_fields
unsigned = _Q.unsigned
signed = _Q.signed
SNAPSHOT_SUFFIXES = _Q.SNAPSHOT_SUFFIXES
SNAPSHOTS = _Q.SNAPSHOTS
HEX2 = _Q.HEX2
HEX4 = _Q.HEX4
HEX8 = _Q.HEX8

HEADER_FIELDS = (
    "candidate",
    "state",
    "one_shot",
    "run_error",
    "attempted",
    "transport_completed",
    "value_validated",
    "addresses",
    "passes",
    "transfer_order",
    "expected_signature",
    "topology_register",
    "topology_mask",
    "topology_expected",
    "stability_registers",
    "stability_validated",
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
    "address",
    "register",
    "expected_kind",
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
TRANSFER_ORDER = (
    (0x69, 0x05),
    (0x69, 0x06),
    (0x69, 0x47),
    (0x68, 0xD3),
    (0x68, 0x5E),
    (0x68, 0xD9),
    (0x68, 0xDA),
) * 2
EXPECTED_FIELDS = (0xD9, 0xD0, 0xC0, 0x05, 0x00, 0x00, 0x00) * 2
EXPECTED_KINDS = (
    "exact",
    "exact",
    "exact",
    "topology-stable",
    "stable",
    "stable",
    "stable",
) * 2
PREFILLS = (
    0xA5,
    0x5A,
    0x3C,
    0x96,
    0x69,
    0xC3,
    0x87,
    0x78,
    0xB4,
    0x4B,
    0xD2,
    0x2D,
    0xE1,
    0x1E,
)
SIGNATURE = (0xD9, 0xD0, 0xC0)
SAMPLE_COUNT = 14


@dataclass(frozen=True)
class Result:
    classification: str
    header: dict[str, str]
    samples: tuple[dict[str, str], ...]

    @property
    def summary_lines(self) -> tuple[str, ...]:
        values = ",".join(
            f"{sample['address']}:{sample['register']}={sample['value']}"
            for sample in self.samples
        )
        return (
            "validation=fermi-topology-result",
            f"classification={self.classification}",
            f"run_error={self.header['run_error']}",
            f"attempted={self.header['attempted']}",
            f"transport_completed={self.header['transport_completed']}",
            f"value_validated={self.header['value_validated']}",
            f"stability_validated={self.header['stability_validated']}",
            f"failure_pass={self.header['failure_pass']}",
            f"failure_index={self.header['failure_index']}",
            f"values={values or 'none'}",
            "signature=d9,d0,c0-twice",
            "topology=(d3&07)==05-twice",
            "stability=d3,5e,d9,da-full-byte-pair-equality",
            "forced_length_mode=none",
            "forced_engine=none",
            "explicit_reset=none",
        )


def exact_ready_status() -> str:
    return (
        "candidate=Fermi state=ready one_shot=unused run_error=0 "
        "attempted=0 transport_completed=0 value_validated=0 "
        "addresses=0x69,0x68 passes=2 "
        "transfer_order=69:05,69:06,69:47,68:d3,68:5e,68:d9,68:da "
        "expected_signature=d9,d0,c0 topology_register=d3 "
        "topology_mask=07 topology_expected=05 "
        "stability_registers=d3,5e,d9,da stability_validated=0 "
        "prefills=a5,5a,3c,96,69,c3,87,78,b4,4b,d2,2d,e1,1e "
        "mode=none forced_length_mode=none forced_engine=none "
        "reset_pending=0 mismatch=0 failure_pass=2 failure_index=7 "
        "retries_before=1 retries_during=1 retries_after=1 "
        "init_attempts_before=1 init_attempts_after=1 "
        "init_successes_before=1 init_successes_after=1 "
        "transfer_attempts_before=0 transfer_attempts_after=0 "
        "dma_starts_before=0 dma_starts_after=0 "
        "nonzero_starts_before=0 nonzero_starts_after=0 "
        "irqs_before=0 irqs_after=0 success_counter_contract=14,0,14,14"
    )


def validate_header(header: dict[str, str]) -> tuple[int, int, int, int]:
    fixed = {
        "candidate": "Fermi",
        "state": "done",
        "one_shot": "consumed",
        "addresses": "0x69,0x68",
        "passes": "2",
        "transfer_order": "69:05,69:06,69:47,68:d3,68:5e,68:d9,68:da",
        "expected_signature": "d9,d0,c0",
        "topology_register": "d3",
        "topology_mask": "07",
        "topology_expected": "05",
        "stability_registers": "d3,5e,d9,da",
        "prefills": "a5,5a,3c,96,69,c3,87,78,b4,4b,d2,2d,e1,1e",
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
        "success_counter_contract": "14,0,14,14",
    }
    for key, wanted in fixed.items():
        if header[key] != wanted:
            raise ResultError(f"Fermi header changed: {key}")
    run_error = signed(header["run_error"], "run_error")
    attempted = unsigned(header["attempted"], "attempted", SAMPLE_COUNT)
    completed = unsigned(
        header["transport_completed"],
        "transport_completed",
        SAMPLE_COUNT,
    )
    validated = unsigned(
        header["value_validated"],
        "value_validated",
        SAMPLE_COUNT,
    )
    if not validated <= completed <= attempted:
        raise ResultError("Fermi result counters are not monotonic")
    mismatch = unsigned(header["mismatch"], "mismatch", 1)
    if mismatch not in {0, 1}:
        raise ResultError("Fermi mismatch is not boolean")
    retries_during = unsigned(header["retries_during"], "retries_during", 1)
    if retries_during not in {0, 1}:
        raise ResultError("Fermi retries_during changed")
    stability = unsigned(
        header["stability_validated"],
        "stability_validated",
        4,
    )
    expected_stability = max(0, min(4, validated - 10))
    if stability != expected_stability:
        raise ResultError("Fermi stability count differs from validated prefix")
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
        raise ResultError("Fermi init success count exceeds attempts")
    if parsed["transfer_attempts_after"] != attempted:
        raise ResultError("Fermi transfer counter differs from attempts")
    for key in ("dma_starts_after", "nonzero_starts_after", "irqs_after"):
        if parsed[key] > attempted:
            raise ResultError(f"Fermi {key} exceeds attempted samples")
    return run_error, attempted, completed, validated


def validate_sample_shape(
    sample: dict[str, str],
    ordinal: int,
    completed_count: int,
    validated_count: int,
) -> None:
    pass_index, register_index = divmod(ordinal, 7)
    address, register = TRANSFER_ORDER[ordinal]
    exact = {
        "pass": str(pass_index),
        "index": str(register_index),
        "address": f"{address:02x}",
        "register": f"{register:02x}",
        "expected_kind": EXPECTED_KINDS[ordinal],
        "expected": f"{EXPECTED_FIELDS[ordinal]:02x}",
        "prefill": f"{PREFILLS[ordinal]:02x}",
    }
    if unsigned(sample["sample"], "sample ordinal", 13) != ordinal:
        raise ResultError("Fermi sample ordinal changed")
    for key, wanted in exact.items():
        if sample[key] != wanted:
            raise ResultError(f"Fermi sample {ordinal} {key} changed")
    if HEX2.fullmatch(sample["value"]) is None:
        raise ResultError(f"Fermi sample {ordinal} value is not lowercase hex")
    ret = signed(sample["ret"], f"sample {ordinal} ret")
    validation_error = signed(
        sample["validation_error"],
        f"sample {ordinal} validation_error",
    )
    programmed = unsigned(sample["programmed"], "programmed", 1)
    transport = unsigned(sample["transport_completed"], "transport_completed", 1)
    validated = unsigned(sample["value_validated"], "value_validated", 1)
    if transport != int(ordinal < completed_count):
        raise ResultError("Fermi transport flags are not a contiguous prefix")
    if validated != int(ordinal < validated_count):
        raise ResultError("Fermi validation flags are not a contiguous prefix")
    if validated and not transport:
        raise ResultError("Fermi validated sample lacks transport completion")
    if transport and ret != 2:
        raise ResultError("Fermi transport-complete sample return is not two")
    if not transport and ret == 2:
        raise ResultError("Fermi transport-incomplete sample returned two")
    if validated and validation_error:
        raise ResultError("Fermi validated sample has a validation error")
    if not validated and validation_error >= 0:
        raise ResultError("Fermi failed sample lacks negative validation error")
    if programmed:
        if sample["engine"] not in {"fifo", "dma"}:
            raise ResultError("Fermi programmed sample engine changed")
    elif sample["engine"] != "unobserved":
        raise ResultError("Fermi unprogrammed sample inferred an engine")
    if HEX4.fullmatch(sample["irq_stat"]) is None:
        raise ResultError("Fermi sample IRQ aggregate is not 16-bit hex")
    for snapshot in SNAPSHOTS:
        for suffix in SNAPSHOT_SUFFIXES:
            key = f"{snapshot}_{suffix}"
            matcher = HEX8 if suffix.startswith("dma_") else HEX4
            if matcher.fullmatch(sample[key]) is None:
                raise ResultError(f"Fermi snapshot grammar changed: {key}")
    if HEX4.fullmatch(sample["fifo_stat"]) is None:
        raise ResultError("Fermi FIFO status is not 16-bit hex")
    unsigned(sample["fifo_count"], "fifo_count", 65535)
    unsigned(sample["fifo_count_drained"], "fifo_count_drained", 65535)


def validate_validated_values(samples: tuple[dict[str, str], ...], count: int) -> None:
    for ordinal, sample in enumerate(samples[:count]):
        value = int(sample["value"], 16)
        if value == PREFILLS[ordinal]:
            raise ResultError(f"Fermi sample {ordinal} retained its receive prefill")
        index = ordinal % 7
        if index < 3 and value != SIGNATURE[index]:
            raise ResultError(f"Fermi sample {ordinal} signature changed")
        if index == 3 and value & 0x07 != 0x05:
            raise ResultError(f"Fermi sample {ordinal} topology changed")
        if ordinal >= 10 and value != int(samples[index]["value"], 16):
            raise ResultError(f"Fermi sample {ordinal} is not byte-stable")


def validate_success(
    header: dict[str, str],
    samples: tuple[dict[str, str], ...],
) -> None:
    exact = {
        "run_error": "0",
        "attempted": "14",
        "transport_completed": "14",
        "value_validated": "14",
        "stability_validated": "4",
        "mismatch": "0",
        "failure_pass": "2",
        "failure_index": "7",
        "retries_during": "0",
        "init_attempts_after": "1",
        "init_successes_after": "1",
        "transfer_attempts_after": "14",
        "dma_starts_after": "0",
        "nonzero_starts_after": "14",
        "irqs_after": "14",
    }
    for key, wanted in exact.items():
        if header[key] != wanted:
            raise ResultError(f"successful Fermi header changed: {key}")
    validate_validated_values(samples, SAMPLE_COUNT)
    for ordinal, sample in enumerate(samples):
        required = {
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
                raise ResultError(f"successful Fermi sample {ordinal} changed: {key}")
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
                        f"successful Fermi sample {ordinal} APDMA changed: {key}"
                    )


def semantic_mismatch(
    samples: tuple[dict[str, str], ...],
    ordinal: int,
) -> bool:
    sample = samples[ordinal]
    if sample["transport_completed"] != "1":
        return False
    value = int(sample["value"], 16)
    if value == PREFILLS[ordinal]:
        return False
    index = ordinal % 7
    if index < 3:
        return value != SIGNATURE[index]
    if index == 3 and value & 0x07 != 0x05:
        return True
    if ordinal >= 10:
        return value != int(samples[index]["value"], 16)
    return False


def validate_failure(
    header: dict[str, str],
    samples: tuple[dict[str, str], ...],
) -> None:
    attempted = int(header["attempted"], 10)
    completed = int(header["transport_completed"], 10)
    validated = int(header["value_validated"], 10)
    mismatch = int(header["mismatch"], 10)
    if int(header["run_error"], 10) >= 0:
        raise ResultError("bounded Fermi failure lacks negative run error")
    validate_validated_values(samples, validated)
    if attempted == 0:
        if (header["failure_pass"], header["failure_index"]) != ("2", "7"):
            raise ResultError("Fermi pre-transfer failure sentinel changed")
        if completed or validated or mismatch or header["stability_validated"] != "0":
            raise ResultError("Fermi pre-transfer failure claims progress")
        if header["retries_during"] != "1":
            raise ResultError("Fermi pre-transfer failure changed retries")
    elif validated < attempted:
        expected_pass, expected_index = divmod(attempted - 1, 7)
        if (
            header["failure_pass"],
            header["failure_index"],
        ) != (str(expected_pass), str(expected_index)):
            raise ResultError("Fermi stop-first failure location changed")
        if validated != attempted - 1 or completed not in {
            attempted - 1,
            attempted,
        }:
            raise ResultError("Fermi failure is not at the first sample")
        if header["retries_during"] != "0":
            raise ResultError("attempted Fermi failure did not use zero retries")
        if mismatch != int(semantic_mismatch(samples, attempted - 1)):
            raise ResultError("Fermi failure mismatch attribution changed")
    else:
        if (header["failure_pass"], header["failure_index"]) != ("2", "7"):
            raise ResultError("Fermi post-run failure sentinel changed")
        if mismatch or header["retries_during"] != "0":
            raise ResultError("Fermi post-run failure attribution changed")
        success_counters = (
            header["init_attempts_after"],
            header["init_successes_after"],
            header["transfer_attempts_after"],
            header["dma_starts_after"],
            header["nonzero_starts_after"],
            header["irqs_after"],
            header["stability_validated"],
        )
        if success_counters == ("1", "1", "14", "0", "14", "14", "4"):
            raise ResultError("Fermi post-run failure has no attributable mismatch")
    if len(samples) != attempted:
        raise ResultError("Fermi failure sample inventory changed")
    for sample in samples:
        if sample["programmed"] != "0":
            continue
        if (
            sample["irq_stat"] != "0000"
            or sample["fifo_stat"] != "0000"
            or sample["fifo_count"] != "65535"
            or sample["fifo_count_drained"] != "65535"
        ):
            raise ResultError("unprogrammed Fermi sample contains activity")
        for snapshot in SNAPSHOTS:
            for suffix in SNAPSHOT_SUFFIXES:
                width = 8 if suffix.startswith("dma_") else 4
                if sample[f"{snapshot}_{suffix}"] != "0" * width:
                    raise ResultError("unprogrammed Fermi snapshot is not zero")


def validate_text(data: bytes) -> Result:
    if not data or len(data) > 32 * 1024 or b"\0" in data:
        raise ResultError("Fermi result is empty, oversized, or binary")
    try:
        text = data.decode("ascii", "strict")
    except UnicodeError as exc:
        raise ResultError("Fermi result is not ASCII") from exc
    if not text.endswith("\n") or text.startswith("\n") or "\r" in text:
        raise ResultError("Fermi result framing changed")
    lines = text.splitlines()
    header = ordered_fields(lines[0], HEADER_FIELDS, "Fermi header")
    run_error, attempted, completed, validated = validate_header(header)
    if len(lines) != attempted + 1:
        raise ResultError("Fermi sample line count changed")
    samples = tuple(
        ordered_fields(line, SAMPLE_FIELDS, f"Fermi sample {ordinal}")
        for ordinal, line in enumerate(lines[1:])
    )
    for ordinal, sample in enumerate(samples):
        validate_sample_shape(sample, ordinal, completed, validated)
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
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("\n".join(result.summary_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
