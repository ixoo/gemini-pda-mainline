#!/usr/bin/env python3
"""Mutation tests for Quasar's exact native-path result classifier."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "quasar_result_validator_test",
    SCRIPT_DIR / "validate-quasar-result.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Quasar result validator")
vr = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = vr
SPEC.loader.exec_module(vr)


def success_header() -> dict[str, str]:
    return {
        "candidate": "Quasar",
        "state": "done",
        "one_shot": "consumed",
        "run_error": "0",
        "attempted": "6",
        "transport_completed": "6",
        "value_validated": "6",
        "address": "0x69",
        "passes": "2",
        "registers": "05,06,47",
        "expected": "d9,d0,c0",
        "prefills": "a5,5a,3c,96,69,c3",
        "mode": "none",
        "forced_length_mode": "none",
        "forced_engine": "none",
        "reset_pending": "0",
        "mismatch": "0",
        "failure_pass": "2",
        "failure_index": "3",
        "retries_before": "1",
        "retries_during": "0",
        "retries_after": "1",
        "init_attempts_before": "1",
        "init_attempts_after": "1",
        "init_successes_before": "1",
        "init_successes_after": "1",
        "transfer_attempts_before": "0",
        "transfer_attempts_after": "6",
        "dma_starts_before": "0",
        "dma_starts_after": "0",
        "nonzero_starts_before": "0",
        "nonzero_starts_after": "6",
        "irqs_before": "0",
        "irqs_after": "6",
        "success_counter_contract": "6,0,6,6",
    }


def success_sample(ordinal: int) -> dict[str, str]:
    pass_index, register_index = divmod(ordinal, 3)
    sample = {
        "sample": str(ordinal),
        "pass": str(pass_index),
        "index": str(register_index),
        "register": f"{vr.REGISTERS[ordinal]:02x}",
        "expected": f"{vr.EXPECTED[ordinal]:02x}",
        "prefill": f"{vr.PREFILLS[ordinal]:02x}",
        "value": f"{vr.EXPECTED[ordinal]:02x}",
        "ret": "2",
        "validation_error": "0",
        "programmed": "1",
        "transport_completed": "1",
        "value_validated": "1",
        "engine": "fifo",
        "irq_stat": "0001",
    }
    for snapshot in vr.SNAPSHOTS:
        sample.update(
            {
                f"{snapshot}_transfer_len": "0101",
                f"{snapshot}_transfer_len_aux": "0000",
                f"{snapshot}_transac_len": "0002",
                f"{snapshot}_control": "003a",
                f"{snapshot}_start": "0000",
                f"{snapshot}_intr_stat": (
                    "0001" if snapshot in {"irq", "post"} else "0000"
                ),
                f"{snapshot}_fifo_stat": (
                    "0001" if snapshot in {"irq", "post"} else "0000"
                ),
                f"{snapshot}_dma_en": "00000000",
                f"{snapshot}_dma_con": "00000000",
                f"{snapshot}_dma_int_flag": "00000000",
                f"{snapshot}_dma_tx_len": "00000000",
                f"{snapshot}_dma_rx_len": "00000000",
            }
        )
    sample.update(
        {
            "fifo_stat": "0001",
            "fifo_count": "1",
            "fifo_count_drained": "0",
        }
    )
    return sample


def render(
    header: dict[str, str],
    samples: list[dict[str, str]],
) -> bytes:
    lines = [
        " ".join(f"{key}={header[key]}" for key in vr.HEADER_FIELDS),
        *(
            " ".join(f"{key}={sample[key]}" for key in vr.SAMPLE_FIELDS)
            for sample in samples
        ),
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


def success_result() -> bytes:
    return render(success_header(), [success_sample(index) for index in range(6)])


def bounded_failure() -> bytes:
    header = success_header()
    header.update(
        {
            "run_error": "-110",
            "attempted": "1",
            "transport_completed": "0",
            "value_validated": "0",
            "failure_pass": "0",
            "failure_index": "0",
            "init_attempts_after": "2",
            "init_successes_after": "2",
            "transfer_attempts_after": "1",
            "nonzero_starts_after": "0",
            "irqs_after": "0",
        }
    )
    sample = success_sample(0)
    sample.update(
        {
            "value": "a5",
            "ret": "-110",
            "validation_error": "-110",
            "programmed": "0",
            "transport_completed": "0",
            "value_validated": "0",
            "engine": "unobserved",
            "irq_stat": "0000",
            "fifo_stat": "0000",
            "fifo_count": "65535",
            "fifo_count_drained": "65535",
        }
    )
    for snapshot in vr.SNAPSHOTS:
        for suffix in vr.SNAPSHOT_SUFFIXES:
            width = 8 if suffix.startswith("dma_") else 4
            sample[f"{snapshot}_{suffix}"] = "0" * width
    return render(header, [sample])


class QuasarResultContracts(unittest.TestCase):
    def test_exact_success_and_failure_classify(self) -> None:
        success = vr.validate_text(success_result())
        self.assertEqual(success.classification, "complete-success")
        self.assertEqual(
            [sample["value"] for sample in success.samples],
            ["d9", "d0", "c0", "d9", "d0", "c0"],
        )
        failure = vr.validate_text(bounded_failure())
        self.assertEqual(
            failure.classification,
            "bounded-stop-first-failure",
        )
        self.assertEqual(failure.header["failure_pass"], "0")
        self.assertEqual(failure.header["failure_index"], "0")

    def test_success_mutations_fail_closed(self) -> None:
        mutations = (
            ("run_error=0", "run_error=-71"),
            ("attempted=6", "attempted=5"),
            ("transport_completed=6", "transport_completed=5"),
            ("value_validated=6", "value_validated=5"),
            ("forced_length_mode=none", "forced_length_mode=aux"),
            ("forced_engine=none", "forced_engine=fifo"),
            ("reset_pending=0", "reset_pending=1"),
            ("retries_during=0", "retries_during=1"),
            ("init_attempts_after=1", "init_attempts_after=2"),
            ("transfer_attempts_after=6", "transfer_attempts_after=5"),
            ("dma_starts_after=0", "dma_starts_after=1"),
            ("nonzero_starts_after=6", "nonzero_starts_after=5"),
            ("irqs_after=6", "irqs_after=5"),
            ("value=d9", "value=a5"),
            ("programmed=1", "programmed=0"),
            ("engine=fifo", "engine=dma"),
            ("irq_stat=0001", "irq_stat=0002"),
            ("pre_transfer_len=0101", "pre_transfer_len=0001"),
            ("pre_transfer_len_aux=0000", "pre_transfer_len_aux=0001"),
            ("pre_transac_len=0002", "pre_transac_len=0001"),
            ("pre_control=003a", "pre_control=003b"),
            ("irq_intr_stat=0001", "irq_intr_stat=0003"),
            ("pre_dma_en=00000000", "pre_dma_en=00000001"),
            ("irq_dma_rx_len=00000000", "irq_dma_rx_len=00000001"),
            ("post_dma_int_flag=00000000", "post_dma_int_flag=00000001"),
            ("drained_dma_con=00000000", "drained_dma_con=00000001"),
            ("fifo_count=1", "fifo_count=0"),
            ("fifo_count_drained=0", "fifo_count_drained=1"),
        )
        original = success_result()
        for old, new in mutations:
            with self.subTest(old=old):
                mutated = original.replace(
                    old.encode(),
                    new.encode(),
                    1,
                )
                with self.assertRaises(vr.ResultError):
                    vr.validate_text(mutated)

    def test_grammar_and_stop_first_mutations_fail_closed(self) -> None:
        success = success_result()
        failure = bounded_failure()
        mutations = (
            success.rstrip(b"\n"),
            b"\n" + success,
            success.replace(b"candidate=Quasar ", b"candidate=Quasar  ", 1),
            success.replace(b"sample=0 ", b"sample=1 ", 1),
            success.replace(b"register=05 ", b"register=5 ", 1),
            failure.replace(b"failure_index=0", b"failure_index=1", 1),
            failure.replace(b"run_error=-110", b"run_error=0", 1),
            failure.replace(b"validation_error=-110", b"validation_error=0", 1),
            failure + failure.splitlines(keepends=True)[1],
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(vr.ResultError):
                    vr.validate_text(mutated)

    def test_ready_status_is_exact_and_has_no_sample(self) -> None:
        ready = vr.exact_ready_status()
        fields = vr.ordered_fields(ready, vr.HEADER_FIELDS, "ready status")
        self.assertEqual(fields["state"], "ready")
        self.assertEqual(fields["one_shot"], "unused")
        self.assertEqual(fields["attempted"], "0")
        self.assertEqual(fields["retries_during"], "1")


if __name__ == "__main__":
    unittest.main()
