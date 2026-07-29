#!/usr/bin/env python3
"""Mutation tests for Gauss's exact-D3 result classifier."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "gauss_result_validator_test",
    SCRIPT_DIR / "validate-gauss-result.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Gauss result validator")
vr = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = vr
SPEC.loader.exec_module(vr)

VALUES = (0xD9, 0xD0, 0xC0, 0x1F, 0x00, 0x46, 0x46) * 2


def success_header() -> dict[str, str]:
    ready = vr.ordered_fields(
        vr.exact_ready_status(),
        vr.HEADER_FIELDS,
        "synthetic Gauss ready header",
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


def render(header: dict[str, str], samples: list[dict[str, str]]) -> bytes:
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


class GaussResultContract(unittest.TestCase):
    def test_exact_tuple_success(self) -> None:
        result = vr.validate_text(success_result())
        self.assertEqual(result.classification, "complete-success")
        self.assertEqual(result.samples[3]["value"], "1f")
        self.assertEqual(result.samples[10]["value"], "1f")
        self.assertIn("required_d3=d3-exact-1f-two-passes", result.summary_lines)
        self.assertIn("observed_d3_exact_validations=2", result.summary_lines)

    def test_exact_d3_not_masked_d3(self) -> None:
        original = success_result()
        first = (
            b"sample=3 pass=0 index=3 address=68 register=d3 "
            b"expected_kind=exact-d3-stable expected=1f prefill=96 value=1f"
        )
        self.assertIn(first, original)
        with self.assertRaises(vr.ResultError):
            vr.validate_text(
                original.replace(first, first[:-2] + b"1e", 1)
            )

    def test_signature_stability_prefill_and_transport_fail_closed(self) -> None:
        original = success_result()
        mutations = (
            (b"value=d9", b"value=d8"),
            (
                b"sample=11 pass=1 index=4 address=68 register=5e "
                b"expected_kind=stable expected=00 prefill=2d value=00",
                b"sample=11 pass=1 index=4 address=68 register=5e "
                b"expected_kind=stable expected=00 prefill=2d value=01",
            ),
            (
                b"sample=4 pass=0 index=4 address=68 register=5e "
                b"expected_kind=stable expected=00 prefill=69 value=00",
                b"sample=4 pass=0 index=4 address=68 register=5e "
                b"expected_kind=stable expected=00 prefill=69 value=69",
            ),
            (b"engine=fifo", b"engine=dma"),
            (b"irq_stat=0001", b"irq_stat=0002"),
            (b"pre_transfer_len=0101", b"pre_transfer_len=0001"),
            (b"pre_dma_en=00000000", b"pre_dma_en=00000001"),
            (b"fifo_count_drained=0", b"fifo_count_drained=1"),
            (b"attempted=14", b"attempted=13"),
            (b"stability_validated=4", b"stability_validated=3"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.assertIn(old, original)
                with self.assertRaises(vr.ResultError):
                    vr.validate_text(original.replace(old, new, 1))

    def test_result_grammar_and_identity_fail_closed(self) -> None:
        original = success_result()
        mutations = (
            original.rstrip(b"\n"),
            original.replace(b"candidate=Gauss ", b"candidate=Fermi ", 1),
            original.replace(b"d3_exact_mask=ff", b"d3_exact_mask=07", 1),
            original.replace(
                b"d3_exact_expected=1f", b"d3_exact_expected=05", 1
            ),
            original.replace(b"sample=0 ", b"sample=1 ", 1),
            original.rsplit(b"\n", 2)[0] + b"\n",
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(vr.ResultError):
                    vr.validate_text(mutated)

    def test_ready_status_retains_fermi_serviceability(self) -> None:
        ready = vr.exact_ready_status()
        self.assertIn("candidate=Gauss state=ready", ready)
        self.assertIn("d3_exact_mask=ff d3_exact_expected=1f", ready)
        self.assertNotIn("topology_mask=", ready)


if __name__ == "__main__":
    unittest.main(verbosity=2)
