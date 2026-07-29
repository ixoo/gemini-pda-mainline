#!/usr/bin/env python3
"""Mutation tests for bounded Orion stop-first partial validation."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, pathlib.Path(__file__).with_name(filename)
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PARTIAL = load("orion_partial_validator", "validate-orion-partial.py")
FIXTURE = load("orion_result_fixture", "test-orion-result.py")


def replace_header(header: str, replacements: dict[str, str]) -> str:
    tokens = header.split()
    values = dict(token.split("=", 1) for token in tokens)
    values.update(replacements)
    return " ".join(f"{key}={values[key]}" for key in values)


def started_dma_timeout() -> bytes:
    lines = FIXTURE.valid_result().decode("ascii").splitlines()
    lines[0] = replace_header(
        lines[0],
        {
            "run_error": "-110",
            "attempted": "4",
            "completed": "3",
            "transfer_attempts": "4",
            "dma_starts": "1",
            "nonzero_starts": "4",
            "irqs": "3",
        },
    )
    lines = lines[:5]
    lines[-1] = lines[-1].replace("ret=2", "ret=-110")
    lines[-1] = lines[-1].replace("irq_stat=0001", "irq_stat=0000")
    return ("\n".join(lines) + "\n").encode("ascii")


def prestart_dma_failure() -> bytes:
    lines = started_dma_timeout().decode("ascii").splitlines()
    lines[0] = replace_header(
        lines[0],
        {
            "run_error": "-12",
            "dma_starts": "0",
            "nonzero_starts": "3",
        },
    )
    line = lines[-1]
    replacements = {
        "ret=-110": "ret=-12",
        "engine=dma": "engine=fifo",
        "transfer_len=0101": "transfer_len=0000",
        "transac_len=0002": "transac_len=0000",
        "control=0004": "control=0000",
        "dma_tx_len_pre=00000001": "dma_tx_len_pre=00000000",
        "dma_rx_len_pre=00000001": "dma_rx_len_pre=00000000",
        "dma_en_irq=00000001": "dma_en_irq=00000000",
        "dma_tx_len_post=00000001": "dma_tx_len_post=00000000",
        "dma_rx_len_post=00000001": "dma_rx_len_post=00000000",
    }
    for old, new in replacements.items():
        line = line.replace(old, new)
    lines[-1] = line
    return ("\n".join(lines) + "\n").encode("ascii")


def fifo_count_failure() -> bytes:
    lines = FIXTURE.valid_result().decode("ascii").splitlines()
    lines[0] = replace_header(
        lines[0],
        {
            "run_error": "-5",
            "attempted": "1",
            "completed": "0",
            "transfer_attempts": "1",
            "dma_starts": "0",
            "nonzero_starts": "1",
            "irqs": "1",
        },
    )
    lines = lines[:2]
    lines[-1] = lines[-1].replace("ret=2", "ret=-5")
    lines[-1] = lines[-1].replace("fifo_count=1", "fifo_count=0")
    return ("\n".join(lines) + "\n").encode("ascii")


class OrionPartialMutations(unittest.TestCase):
    def test_started_dma_timeout(self) -> None:
        summary = PARTIAL.validate_partial(started_dma_timeout())
        self.assertEqual(summary["completed"], 3)
        self.assertEqual(summary["failing_mode"], "packed-dma")
        self.assertEqual(summary["started"], "yes")

    def test_prestart_dma_failure(self) -> None:
        summary = PARTIAL.validate_partial(prestart_dma_failure())
        self.assertEqual(summary["failing_ret"], -12)
        self.assertEqual(summary["started"], "no")

    def test_fifo_count_failure(self) -> None:
        summary = PARTIAL.validate_partial(fifo_count_failure())
        self.assertEqual(summary["failing_mode"], "packed-fifo")

    def reject(self, data: bytes, old: bytes, new: bytes) -> None:
        mutated = data.replace(old, new, 1)
        self.assertNotEqual(mutated, data)
        with self.assertRaises(ValueError):
            PARTIAL.validate_partial(mutated)

    def test_rejects_hidden_transfer_or_retry(self) -> None:
        self.reject(
            started_dma_timeout(),
            b"transfer_attempts=4",
            b"transfer_attempts=5",
        )
        self.reject(
            started_dma_timeout(), b"retries_after=1", b"retries_after=0"
        )

    def test_rejects_wrong_dma_start_correlation(self) -> None:
        self.reject(started_dma_timeout(), b"dma_starts=1", b"dma_starts=0")

    def test_rejects_hidden_irq_correlations(self) -> None:
        self.reject(prestart_dma_failure(), b"irqs=3", b"irqs=4")
        data = started_dma_timeout()
        data = data.replace(b"irq_stat=0000", b"irq_stat=0002", 1)
        with self.assertRaises(ValueError):
            PARTIAL.validate_partial(data)

    def test_rejects_timeout_with_arbitration_loss(self) -> None:
        data = started_dma_timeout()
        data = data.replace(b"irqs=3", b"irqs=4", 1)
        data = data.replace(b"irq_stat=0000", b"irq_stat=0008", 1)
        with self.assertRaises(ValueError):
            PARTIAL.validate_partial(data)

    def test_rejects_invalid_eio_sources(self) -> None:
        data = fifo_count_failure()
        data = data.replace(b"irqs=1", b"irqs=0", 1)
        data = data.replace(b"irq_stat=0001", b"irq_stat=0000", 1)
        with self.assertRaises(ValueError):
            PARTIAL.validate_partial(data)
        data = fifo_count_failure()
        data = data.replace(b"irqs=1", b"irqs=2", 1)
        data = data.replace(b"irq_stat=0001", b"irq_stat=0003", 1)
        with self.assertRaises(ValueError):
            PARTIAL.validate_partial(data)

    def test_rejects_invalid_fifo_failure_count(self) -> None:
        data = fifo_count_failure().replace(b"fifo_count=0", b"fifo_count=16")
        with self.assertRaises(ValueError):
            PARTIAL.validate_partial(data)
        data = fifo_count_failure()
        data = data.replace(b"run_error=-5", b"run_error=-110", 1)
        data = data.replace(b"ret=-5", b"ret=-110", 1)
        data = data.replace(b"irqs=1", b"irqs=0", 1)
        data = data.replace(b"irq_stat=0001", b"irq_stat=0000", 1)
        with self.assertRaises(ValueError):
            PARTIAL.validate_partial(data)

    def test_rejects_later_sample(self) -> None:
        data = started_dma_timeout()
        extra = FIXTURE.valid_result().splitlines()[5] + b"\n"
        with self.assertRaises(ValueError):
            PARTIAL.validate_partial(data + extra)


if __name__ == "__main__":
    unittest.main()
