#!/usr/bin/env python3
"""Mutation tests for Vega attempt 3's exact mixed-result classifier."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True


HERE = pathlib.Path(__file__).resolve().parent
CLASSIFIER_PATH = HERE / "classify-vega-mixed-result.py"
ORION_DIR = HERE.parents[1] / "2026-07-27-mt6797-i2c6-orion" / "scripts"
OBSERVED_FINAL_SHA256 = (
    "cd1f790284c23f3f9c0a98941a4f966c3b15ad41362a579cdeaf792267d56fd2"
)


def load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CLASSIFIER = load("vega_mixed_result_classifier", CLASSIFIER_PATH)


OBSERVED_FINAL = b"""candidate=Orion state=done one_shot=consumed run_error=0 attempted=9 completed=9 address=0x69 transfer_attempts=9 dma_starts=6 nonzero_starts=9 irqs=9 retries_before=1 retries_during=0 retries_after=1 registers=05,06,47 modes=packed-fifo,packed-dma,aux-dma
sample=0 mode=packed-fifo register=05 pre=a5 post=d9 ret=2 engine=fifo transfer_len=0101 transfer_len_aux=0000 transac_len=0002 control=003a irq_stat=0001 fifo_count=1 dma_en_pre=00000000 dma_con_pre=00000000 dma_int_flag_pre=00000000 dma_tx_len_pre=00000000 dma_rx_len_pre=00000000 dma_en_irq=00000000 dma_int_flag_irq=00000000 dma_en_post=00000000 dma_con_post=00000000 dma_int_flag_post=00000000 dma_tx_len_post=00000000 dma_rx_len_post=00000000
sample=1 mode=packed-fifo register=06 pre=5a post=d0 ret=2 engine=fifo transfer_len=0101 transfer_len_aux=0000 transac_len=0002 control=003a irq_stat=0001 fifo_count=1 dma_en_pre=00000000 dma_con_pre=00000000 dma_int_flag_pre=00000000 dma_tx_len_pre=00000000 dma_rx_len_pre=00000000 dma_en_irq=00000000 dma_int_flag_irq=00000000 dma_en_post=00000000 dma_con_post=00000000 dma_int_flag_post=00000000 dma_tx_len_post=00000000 dma_rx_len_post=00000000
sample=2 mode=packed-fifo register=47 pre=3c post=c0 ret=2 engine=fifo transfer_len=0101 transfer_len_aux=0000 transac_len=0002 control=003a irq_stat=0001 fifo_count=1 dma_en_pre=00000000 dma_con_pre=00000000 dma_int_flag_pre=00000000 dma_tx_len_pre=00000000 dma_rx_len_pre=00000000 dma_en_irq=00000000 dma_int_flag_irq=00000000 dma_en_post=00000000 dma_con_post=00000000 dma_int_flag_post=00000000 dma_tx_len_post=00000000 dma_rx_len_post=00000000
sample=3 mode=packed-dma register=05 pre=a5 post=d9 ret=2 engine=dma transfer_len=0101 transfer_len_aux=0000 transac_len=0002 control=003e irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 dma_con_pre=00000000 dma_int_flag_pre=00000000 dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 dma_en_irq=00000000 dma_int_flag_irq=00000003 dma_en_post=00000000 dma_con_post=00000001 dma_int_flag_post=00000003 dma_tx_len_post=00000000 dma_rx_len_post=00000000
sample=4 mode=packed-dma register=06 pre=5a post=d0 ret=2 engine=dma transfer_len=0101 transfer_len_aux=0000 transac_len=0002 control=003e irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 dma_con_pre=00000000 dma_int_flag_pre=00000000 dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 dma_en_irq=00000000 dma_int_flag_irq=00000003 dma_en_post=00000000 dma_con_post=00000001 dma_int_flag_post=00000003 dma_tx_len_post=00000000 dma_rx_len_post=00000000
sample=5 mode=packed-dma register=47 pre=3c post=c0 ret=2 engine=dma transfer_len=0101 transfer_len_aux=0000 transac_len=0002 control=003e irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 dma_con_pre=00000000 dma_int_flag_pre=00000000 dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 dma_en_irq=00000000 dma_int_flag_irq=00000003 dma_en_post=00000000 dma_con_post=00000001 dma_int_flag_post=00000003 dma_tx_len_post=00000000 dma_rx_len_post=00000000
sample=6 mode=aux-dma register=05 pre=a5 post=00 ret=2 engine=dma transfer_len=0001 transfer_len_aux=0000 transac_len=0002 control=003e irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 dma_con_pre=00000000 dma_int_flag_pre=00000000 dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 dma_en_irq=00000001 dma_int_flag_irq=00000001 dma_en_post=00000001 dma_con_post=00000001 dma_int_flag_post=00000001 dma_tx_len_post=00000000 dma_rx_len_post=00000001
sample=7 mode=aux-dma register=06 pre=5a post=00 ret=2 engine=dma transfer_len=0001 transfer_len_aux=0000 transac_len=0002 control=003e irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 dma_con_pre=00000000 dma_int_flag_pre=00000001 dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 dma_en_irq=00000001 dma_int_flag_irq=00000001 dma_en_post=00000001 dma_con_post=00000001 dma_int_flag_post=00000001 dma_tx_len_post=00000000 dma_rx_len_post=00000001
sample=8 mode=aux-dma register=47 pre=3c post=00 ret=2 engine=dma transfer_len=0001 transfer_len_aux=0000 transac_len=0002 control=003e irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 dma_con_pre=00000000 dma_int_flag_pre=00000001 dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 dma_en_irq=00000001 dma_int_flag_irq=00000001 dma_en_post=00000001 dma_con_post=00000001 dma_int_flag_post=00000001 dma_tx_len_post=00000000 dma_rx_len_post=00000001
"""


class VegaMixedResultTests(unittest.TestCase):
    def test_fixture_is_exact_extracted_attempt_3_final(self) -> None:
        self.assertEqual(
            hashlib.sha256(OBSERVED_FINAL).hexdigest(),
            OBSERVED_FINAL_SHA256,
        )
        self.assertEqual(len(OBSERVED_FINAL), 4301)

    def test_exact_observed_result_and_deterministic_counts(self) -> None:
        summary = CLASSIFIER.validate_text(OBSERVED_FINAL)
        self.assertEqual(
            CLASSIFIER.summary_lines(summary),
            [
                "validation=vega-attempt-3-exact-mixed-final",
                "classification=complete-attributable-unexpected-mixed-outcome",
                "physical_transfers=9",
                "software_completions=9",
                "validated_receives=6",
                "packed_fifo_successes=3",
                "packed_dma_successes=3",
                "auxiliary_dma_successes=0",
                "auxiliary_controller_complete_apdma_rx_incomplete=3",
                "adapter_retries=1,0,1",
                "packed_fifo_tuple=d9,d0,c0",
                "packed_dma_tuple=d9,d0,c0",
                "aux_dma_cpu_tuple=00,00,00",
                "aux_dma_transfer_len_aux=0000",
            ],
        )

    def test_cli_accepts_only_an_extracted_final_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = pathlib.Path(temporary) / "vega-final.txt"
            result.write_bytes(OBSERVED_FINAL)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "classify-vega-mixed-result.py",
                        "--result",
                        str(result),
                    ],
                ),
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                self.assertEqual(CLASSIFIER.main(), 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(
                stdout.getvalue(),
                "\n".join(
                    CLASSIFIER.summary_lines(
                        CLASSIFIER.validate_text(OBSERVED_FINAL)
                    )
                )
                + "\n",
            )

    def reject(self, old: bytes, new: bytes) -> None:
        self.assertIn(old, OBSERVED_FINAL)
        mutated = OBSERVED_FINAL.replace(old, new, 1)
        self.assertNotEqual(mutated, OBSERVED_FINAL)
        with self.assertRaises(ValueError):
            CLASSIFIER.validate_text(mutated)

    def test_rejects_header_counter_retry_and_order_mutations(self) -> None:
        mutations = (
            (b"attempted=9", b"attempted=8"),
            (b"completed=9", b"completed=8"),
            (b"transfer_attempts=9", b"transfer_attempts=10"),
            (b"dma_starts=6", b"dma_starts=5"),
            (b"nonzero_starts=9", b"nonzero_starts=8"),
            (b"irqs=9", b"irqs=10"),
            (b"retries_before=1", b"retries_before=0"),
            (b"retries_during=0", b"retries_during=1"),
            (b"retries_after=1", b"retries_after=0"),
            (b"registers=05,06,47", b"registers=06,05,47"),
            (
                b"modes=packed-fifo,packed-dma,aux-dma",
                b"modes=packed-dma,packed-fifo,aux-dma",
            ),
            (
                b"candidate=Orion state=done",
                b"state=done candidate=Orion",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                self.reject(old, new)

    def test_rejects_packed_fifo_mutations(self) -> None:
        prefix = b"sample=0 mode=packed-fifo register=05 pre=a5 "
        mutations = (
            (prefix + b"post=d9", prefix + b"post=00"),
            (prefix + b"post=d9 ret=2", prefix + b"post=d9 ret=-5"),
            (
                b"sample=0 mode=packed-fifo",
                b"sample=0 mode=packed-dma",
            ),
            (
                b"sample=0 mode=packed-fifo register=05",
                b"sample=0 mode=packed-fifo register=06",
            ),
            (
                prefix + b"post=d9 ret=2 engine=fifo transfer_len=0101",
                prefix + b"post=d9 ret=2 engine=fifo transfer_len=0001",
            ),
            (
                b"sample=0 mode=packed-fifo register=05 pre=a5 post=d9 "
                b"ret=2 engine=fifo transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003a",
                b"sample=0 mode=packed-fifo register=05 pre=a5 post=d9 "
                b"ret=2 engine=fifo transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e",
            ),
            (
                b"sample=0 mode=packed-fifo register=05 pre=a5 post=d9 "
                b"ret=2 engine=fifo transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003a "
                b"irq_stat=0001",
                b"sample=0 mode=packed-fifo register=05 pre=a5 post=d9 "
                b"ret=2 engine=fifo transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003a "
                b"irq_stat=0003",
            ),
            (
                b"sample=0 mode=packed-fifo register=05 pre=a5 post=d9 "
                b"ret=2 engine=fifo transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003a "
                b"irq_stat=0001 fifo_count=1",
                b"sample=0 mode=packed-fifo register=05 pre=a5 post=d9 "
                b"ret=2 engine=fifo transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003a "
                b"irq_stat=0001 fifo_count=0",
            ),
            (
                prefix
                + b"post=d9 ret=2 engine=fifo transfer_len=0101 "
                + b"transfer_len_aux=0000 transac_len=0002 control=003a "
                + b"irq_stat=0001 fifo_count=1 dma_en_pre=00000000",
                prefix
                + b"post=d9 ret=2 engine=fifo transfer_len=0101 "
                + b"transfer_len_aux=0000 transac_len=0002 control=003a "
                + b"irq_stat=0001 fifo_count=1 dma_en_pre=00000001",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                self.reject(old, new)

    def test_rejects_packed_dma_rx_completion_mutations(self) -> None:
        prefix = b"sample=3 mode=packed-dma register=05 pre=a5 "
        mutations = (
            (prefix + b"post=d9", prefix + b"post=00"),
            (
                prefix + b"post=d9 ret=2 engine=dma transfer_len=0101 "
                b"transfer_len_aux=0000",
                prefix + b"post=d9 ret=2 engine=dma transfer_len=0101 "
                b"transfer_len_aux=0001",
            ),
            (
                b"sample=3 mode=packed-dma register=05 pre=a5 post=d9 "
                b"ret=2 engine=dma transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000000 dma_int_flag_irq=00000003",
                b"sample=3 mode=packed-dma register=05 pre=a5 post=d9 "
                b"ret=2 engine=dma transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000000 dma_int_flag_irq=00000001",
            ),
            (
                b"sample=3 mode=packed-dma register=05 pre=a5 post=d9 "
                b"ret=2 engine=dma transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000000",
                b"sample=3 mode=packed-dma register=05 pre=a5 post=d9 "
                b"ret=2 engine=dma transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000001",
            ),
            (
                b"sample=3 mode=packed-dma register=05 pre=a5 post=d9 "
                b"ret=2 engine=dma transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000000 dma_int_flag_irq=00000003 "
                b"dma_en_post=00000000 dma_con_post=00000001 "
                b"dma_int_flag_post=00000003 dma_tx_len_post=00000000 "
                b"dma_rx_len_post=00000000",
                b"sample=3 mode=packed-dma register=05 pre=a5 post=d9 "
                b"ret=2 engine=dma transfer_len=0101 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000000 dma_int_flag_irq=00000003 "
                b"dma_en_post=00000000 dma_con_post=00000001 "
                b"dma_int_flag_post=00000003 dma_tx_len_post=00000000 "
                b"dma_rx_len_post=00000001",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                self.reject(old, new)

    def test_rejects_aux_dma_mixed_outcome_mutations(self) -> None:
        prefix = b"sample=6 mode=aux-dma register=05 pre=a5 "
        mutations = (
            (prefix + b"post=00", prefix + b"post=d9"),
            (prefix + b"post=00 ret=2", prefix + b"post=00 ret=-5"),
            (
                prefix + b"post=00 ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000",
                prefix + b"post=00 ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0001",
            ),
            (
                prefix + b"post=00 ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001",
                prefix + b"post=00 ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0000",
            ),
            (
                b"sample=6 mode=aux-dma register=05 pre=a5 post=00 "
                b"ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000001 dma_int_flag_irq=00000001",
                b"sample=6 mode=aux-dma register=05 pre=a5 post=00 "
                b"ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000000 dma_int_flag_irq=00000001",
            ),
            (
                b"sample=6 mode=aux-dma register=05 pre=a5 post=00 "
                b"ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000001 dma_int_flag_irq=00000001",
                b"sample=6 mode=aux-dma register=05 pre=a5 post=00 "
                b"ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000001 dma_int_flag_irq=00000003",
            ),
            (
                b"sample=6 mode=aux-dma register=05 pre=a5 post=00 "
                b"ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000001 dma_int_flag_irq=00000001 "
                b"dma_en_post=00000001 dma_con_post=00000001 "
                b"dma_int_flag_post=00000001 dma_tx_len_post=00000000 "
                b"dma_rx_len_post=00000001",
                b"sample=6 mode=aux-dma register=05 pre=a5 post=00 "
                b"ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000 "
                b"dma_tx_len_pre=00000001 dma_rx_len_pre=00000001 "
                b"dma_en_irq=00000001 dma_int_flag_irq=00000001 "
                b"dma_en_post=00000001 dma_con_post=00000001 "
                b"dma_int_flag_post=00000001 dma_tx_len_post=00000000 "
                b"dma_rx_len_post=00000000",
            ),
            (
                b"sample=7 mode=aux-dma register=06 pre=5a post=00 "
                b"ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000001",
                b"sample=7 mode=aux-dma register=06 pre=5a post=00 "
                b"ret=2 engine=dma transfer_len=0001 "
                b"transfer_len_aux=0000 transac_len=0002 control=003e "
                b"irq_stat=0001 fifo_count=65535 dma_en_pre=00000000 "
                b"dma_con_pre=00000000 dma_int_flag_pre=00000000",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                self.reject(old, new)

    def test_rejects_envelope_spacing_and_encoding_mutations(self) -> None:
        with self.assertRaises(ValueError):
            CLASSIFIER.validate_text(
                b"__VEGA_FINAL_BEGIN__\n"
                + OBSERVED_FINAL
                + b"__VEGA_FINAL_END__\n"
            )
        with self.assertRaises(ValueError):
            CLASSIFIER.validate_text(OBSERVED_FINAL.rstrip(b"\n"))
        with self.assertRaises(ValueError):
            CLASSIFIER.validate_text(OBSERVED_FINAL + b"\n")
        with self.assertRaises(ValueError):
            CLASSIFIER.validate_text(OBSERVED_FINAL.replace(b"\n", b"\r\n"))
        with self.assertRaises(ValueError):
            CLASSIFIER.validate_text(OBSERVED_FINAL + b"\xff")
        self.reject(b"candidate=Orion state=done", b"candidate=Orion  state=done")

    def test_orion_full_and_partial_boundaries_still_reject_mixed_result(
        self,
    ) -> None:
        sys.path.insert(0, str(ORION_DIR))
        try:
            full = load(
                "vega_test_orion_full",
                ORION_DIR / "validate-orion-result.py",
            )
            partial = load(
                "vega_test_orion_partial",
                ORION_DIR / "validate-orion-partial.py",
            )
        finally:
            sys.path.pop(0)
        with self.assertRaises(ValueError):
            full.validate_text(OBSERVED_FINAL)
        with self.assertRaises(ValueError):
            partial.validate_partial(OBSERVED_FINAL)

    def test_regular_input_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            result = directory / "result.txt"
            result.write_bytes(OBSERVED_FINAL)
            link = directory / "result-link.txt"
            link.symlink_to(result)
            self.assertEqual(
                CLASSIFIER.validate_text(
                    CLASSIFIER.regular(result, "fixture")
                )["validated_receives"],
                6,
            )
            with self.assertRaises(ValueError):
                CLASSIFIER.regular(link, "fixture link")


if __name__ == "__main__":
    unittest.main()
