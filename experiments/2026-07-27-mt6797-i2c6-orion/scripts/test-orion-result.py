#!/usr/bin/env python3
"""Mutation tests for the strict Orion runtime-result validator."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True


SCRIPT = pathlib.Path(__file__).with_name("validate-orion-result.py")
SPEC = importlib.util.spec_from_file_location("orion_result_validator", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Orion result validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def sample(
    index: int,
    mode: str,
    register: int,
    prefill: int,
    post: int,
) -> str:
    fifo = mode == "packed-fifo"
    fields = {
        "sample": str(index),
        "mode": mode,
        "register": f"{register:02x}",
        "pre": f"{prefill:02x}",
        "post": f"{post:02x}",
        "ret": "2",
        "engine": "fifo" if fifo else "dma",
        "transfer_len": "0101" if mode != "aux-dma" else "0001",
        "transfer_len_aux": "0000" if mode != "aux-dma" else "0001",
        "transac_len": "0002",
        "control": "0000" if fifo else "0004",
        "irq_stat": "0001",
        "fifo_count": "1" if fifo else "65535",
        "dma_en_pre": "00000000",
        "dma_con_pre": "00000000",
        "dma_int_flag_pre": "00000000",
        "dma_tx_len_pre": "00000000" if fifo else "00000001",
        "dma_rx_len_pre": "00000000" if fifo else "00000001",
        "dma_en_irq": "00000000" if fifo else "00000001",
        "dma_int_flag_irq": "00000000",
        "dma_en_post": "00000000",
        "dma_con_post": "00000000",
        "dma_int_flag_post": "00000000",
        "dma_tx_len_post": "00000000" if fifo else "00000001",
        "dma_rx_len_post": "00000000" if fifo else "00000001",
    }
    return " ".join(f"{key}={value}" for key, value in fields.items())


def valid_result() -> bytes:
    lines = [
        "candidate=Orion state=done one_shot=consumed run_error=0 "
        "attempted=9 completed=9 address=0x69 transfer_attempts=9 "
        "dma_starts=6 nonzero_starts=9 irqs=9 retries_before=1 "
        "retries_during=0 retries_after=1 registers=05,06,47 "
        "modes=packed-fifo,packed-dma,aux-dma"
    ]
    index = 0
    values = (0xD9, 0xD0, 0xC0)
    for mode in ("packed-fifo", "packed-dma", "aux-dma"):
        for register, prefill, post in zip(
            (0x05, 0x06, 0x47),
            (0xA5, 0x5A, 0x3C),
            values,
            strict=True,
        ):
            lines.append(sample(index, mode, register, prefill, post))
            index += 1
    return ("\n".join(lines) + "\n").encode("ascii")


class OrionResultMutations(unittest.TestCase):
    def test_valid_result(self) -> None:
        self.assertEqual(
            VALIDATOR.validate_text(valid_result())["packed-fifo"],
            (0xD9, 0xD0, 0xC0),
        )

    def reject(self, old: bytes, new: bytes) -> None:
        mutated = valid_result().replace(old, new, 1)
        self.assertNotEqual(mutated, valid_result())
        with self.assertRaises(ValueError):
            VALIDATOR.validate_text(mutated)

    def test_rejects_extra_irq_count(self) -> None:
        self.reject(b"irqs=9", b"irqs=10")

    def test_rejects_error_irq_bits(self) -> None:
        self.reject(b"irq_stat=0001", b"irq_stat=0003")

    def test_rejects_retry_or_failed_restoration(self) -> None:
        self.reject(b"retries_during=0", b"retries_during=1")
        self.reject(b"retries_after=1", b"retries_after=0")

    def test_rejects_fifo_controller_dma(self) -> None:
        self.reject(b"control=0000", b"control=0004")

    def test_rejects_fifo_i2c6_apdma_start(self) -> None:
        self.reject(b"dma_en_irq=00000000", b"dma_en_irq=00000001")

    def test_rejects_wrong_mode_order(self) -> None:
        self.reject(b"mode=packed-fifo", b"mode=packed-dma")


if __name__ == "__main__":
    unittest.main()
