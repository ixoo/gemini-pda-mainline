#!/usr/bin/env python3
"""Mutation tests for Curie's exact named-board result classifier."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "curie_result_validator_test",
    SCRIPT_DIR / "validate-curie-result.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Curie result validator")
vr = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = vr
SPEC.loader.exec_module(vr)

VALUES = (0xD9, 0xD0, 0xC0, 0x1F, 0x81, 0x22, 0x33) * 2


def success_header() -> dict[str, str]:
    ready = vr.ordered_fields(
        vr.exact_ready_status(),
        vr.HEADER_FIELDS,
        "synthetic ready header",
    )
    ready.update(
        {
            "state": "done",
            "one_shot": "consumed",
            "attempted": "14",
            "transport_completed": "14",
            "value_validated": "14",
            "stability_validated": "4",
            "failure_pass": "2",
            "failure_index": "7",
            "retries_during": "0",
            "transfer_attempts_after": "14",
            "nonzero_starts_after": "14",
            "irqs_after": "14",
        }
    )
    return ready


def success_sample(ordinal: int) -> dict[str, str]:
    pass_index, register_index = divmod(ordinal, 7)
    address, register = vr.TRANSFER_ORDER[ordinal]
    sample = {
        "sample": str(ordinal),
        "pass": str(pass_index),
        "index": str(register_index),
        "address": f"{address:02x}",
        "register": f"{register:02x}",
        "expected_kind": vr.EXPECTED_KINDS[ordinal],
        "expected": f"{vr.EXPECTED_FIELDS[ordinal]:02x}",
        "prefill": f"{vr.PREFILLS[ordinal]:02x}",
        "value": f"{VALUES[ordinal]:02x}",
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
    return render(
        success_header(),
        [success_sample(index) for index in range(14)],
    )


def bounded_transport_failure() -> bytes:
    header = success_header()
    header.update(
        {
            "run_error": "-110",
            "attempted": "1",
            "transport_completed": "0",
            "value_validated": "0",
            "stability_validated": "0",
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


def bounded_d3_failure() -> bytes:
    header = success_header()
    header.update(
        {
            "run_error": "-117",
            "attempted": "4",
            "transport_completed": "4",
            "value_validated": "3",
            "stability_validated": "0",
            "mismatch": "1",
            "failure_pass": "0",
            "failure_index": "3",
            "transfer_attempts_after": "4",
            "nonzero_starts_after": "4",
            "irqs_after": "4",
        }
    )
    samples = [success_sample(index) for index in range(4)]
    samples[3].update(
        {
            # 0x1d would pass Fermi's old (value & 0x07) == 0x05 gate.
            "value": "1d",
            "validation_error": "-117",
            "value_validated": "0",
        }
    )
    return render(header, samples)


class CurieResultContracts(unittest.TestCase):
    def test_success_requires_exact_d3_and_full_stability(self) -> None:
        result = vr.validate_text(success_result())
        self.assertEqual(result.classification, "complete-success")
        self.assertEqual(result.samples[3]["value"], "1f")
        self.assertEqual(result.samples[10]["value"], "1f")
        self.assertNotEqual(result.samples[5]["value"], result.samples[6]["value"])

    def test_bounded_transport_failure_classifies(self) -> None:
        result = vr.validate_text(bounded_transport_failure())
        self.assertEqual(result.classification, "bounded-stop-first-failure")
        self.assertEqual(result.header["failure_index"], "0")

    def test_bounded_summary_separates_observed_from_required(self) -> None:
        result = vr.validate_text(bounded_d3_failure())
        summary = set(result.summary_lines)
        self.assertIn("observed_signature_passes=1", summary)
        self.assertIn("observed_board_control_validations=0", summary)
        self.assertIn("observed_stability_pairs=0", summary)
        self.assertIn("required_signature=d9,d0,c0-two-passes", summary)
        self.assertNotIn("signature=d9,d0,c0-twice", summary)

    def test_board_control_signature_stability_and_prefill_fail_closed(self) -> None:
        original = success_result()
        mutations = (
            (b"value=d9", b"value=d8"),
            (
                b"sample=3 pass=0 index=3 address=68 register=d3 "
                b"expected_kind=exact-stable expected=1f prefill=96 value=1f",
                b"sample=3 pass=0 index=3 address=68 register=d3 "
                b"expected_kind=exact-stable expected=1f prefill=96 value=1d",
            ),
            (
                b"sample=11 pass=1 index=4 address=68 register=5e "
                b"expected_kind=stable expected=00 prefill=2d value=81",
                b"sample=11 pass=1 index=4 address=68 register=5e "
                b"expected_kind=stable expected=00 prefill=2d value=82",
            ),
            (
                b"sample=4 pass=0 index=4 address=68 register=5e "
                b"expected_kind=stable expected=00 prefill=69 value=81",
                b"sample=4 pass=0 index=4 address=68 register=5e "
                b"expected_kind=stable expected=00 prefill=69 value=69",
            ),
            (b"address=69 register=05", b"address=68 register=05"),
            (b"expected_kind=exact-stable", b"expected_kind=stable"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.assertIn(old, original)
                with self.assertRaises(vr.ResultError):
                    vr.validate_text(original.replace(old, new, 1))

    def test_native_transport_and_counter_mutations_fail_closed(self) -> None:
        original = success_result()
        mutations = (
            (b"attempted=14", b"attempted=13"),
            (b"transport_completed=14", b"transport_completed=13"),
            (b"value_validated=14", b"value_validated=13"),
            (b"stability_validated=4", b"stability_validated=3"),
            (b"forced_length_mode=none", b"forced_length_mode=aux"),
            (b"forced_engine=none", b"forced_engine=fifo"),
            (b"reset_pending=0", b"reset_pending=1"),
            (b"init_attempts_after=1", b"init_attempts_after=2"),
            (b"dma_starts_after=0", b"dma_starts_after=1"),
            (b"engine=fifo", b"engine=dma"),
            (b"irq_stat=0001", b"irq_stat=0002"),
            (b"pre_transfer_len=0101", b"pre_transfer_len=0001"),
            (b"pre_transfer_len_aux=0000", b"pre_transfer_len_aux=0001"),
            (b"pre_control=003a", b"pre_control=003b"),
            (b"pre_dma_en=00000000", b"pre_dma_en=00000001"),
            (b"fifo_count=1", b"fifo_count=0"),
            (b"fifo_count_drained=0", b"fifo_count_drained=1"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                with self.assertRaises(vr.ResultError):
                    vr.validate_text(original.replace(old, new, 1))

    def test_grammar_truncation_and_duplicate_sample_fail_closed(self) -> None:
        success = success_result()
        mutations = (
            success.rstrip(b"\n"),
            b"\n" + success,
            success.replace(b"candidate=Curie ", b"candidate=Curie  ", 1),
            success.replace(b"sample=0 ", b"sample=1 ", 1),
            success.replace(b"register=05 ", b"register=5 ", 1),
            success.rsplit(b"\n", 2)[0] + b"\n",
            success + success.splitlines(keepends=True)[1],
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(vr.ResultError):
                    vr.validate_text(mutated)

    def test_ready_status_exact_and_sample_free(self) -> None:
        fields = vr.ordered_fields(
            vr.exact_ready_status(),
            vr.HEADER_FIELDS,
            "ready status",
        )
        self.assertEqual(fields["state"], "ready")
        self.assertEqual(fields["attempted"], "0")
        self.assertEqual(fields["board_control_expected"], "1f")
        self.assertEqual(fields["stability_validated"], "0")
        self.assertEqual(fields["failure_index"], "7")


if __name__ == "__main__":
    unittest.main(verbosity=2)
