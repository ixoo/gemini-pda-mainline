#!/usr/bin/env python3
"""Validate and classify a bounded Orion stop-first partial result."""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import stat
import sys

sys.dont_write_bytecode = True
import candidate_orion as co


FULL_PATH = pathlib.Path(__file__).with_name("validate-orion-result.py")
SPEC = importlib.util.spec_from_file_location("orion_full_validator", FULL_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Orion full-result validator")
FULL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FULL)

EIO = -5
ENXIO = -6
EAGAIN = -11
ETIMEDOUT = -110
I2C_ARB_LOST = 1 << 3
I2C_HS_NACKERR = 1 << 2
I2C_ACKERR = 1 << 1
I2C_TRANSAC_COMP = 1 << 0
DMA_FIELDS = (
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


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def fixed_order() -> list[tuple[str, int, int]]:
    return [
        (mode, register, prefill)
        for mode in co.MODE_ORDER
        for register, prefill in zip(co.REGISTERS, co.PREFILLS, strict=True)
    ]


def parse_sample(
    line: str,
    index: int,
    expected: tuple[str, int, int],
) -> dict[str, str]:
    mode, register, prefill = expected
    sample = FULL.fields(line, FULL.SAMPLE_FIELDS, f"Orion sample {index}")
    if FULL.decimal(sample["sample"], "sample index") != index:
        raise ValueError(f"Orion sample {index} index changed")
    if sample["mode"] != mode:
        raise ValueError(f"Orion sample {index} mode changed")
    if FULL.hexadecimal(sample["register"], 2, "register") != register:
        raise ValueError(f"Orion sample {index} register changed")
    if FULL.hexadecimal(sample["pre"], 2, "prefill") != prefill:
        raise ValueError(f"Orion sample {index} prefill changed")
    FULL.hexadecimal(sample["post"], 2, "post value")
    for key in DMA_FIELDS:
        FULL.hexadecimal(sample[key], 8, key)
    return sample


def require_programmed_shape(
    sample: dict[str, str],
    mode: str,
    index: int,
    *,
    completed: bool,
) -> None:
    control = FULL.hexadecimal(sample["control"], 4, "controller control")
    transfer_len = FULL.hexadecimal(
        sample["transfer_len"], 4, "transfer length"
    )
    transfer_len_aux = FULL.hexadecimal(
        sample["transfer_len_aux"], 4, "auxiliary transfer length"
    )
    transac_len = FULL.hexadecimal(
        sample["transac_len"], 4, "transaction length"
    )
    if transac_len != 2:
        raise ValueError(f"Orion sample {index} transaction length changed")
    if mode == "packed-fifo":
        if sample["engine"] != "fifo" or transfer_len != 0x0101:
            raise ValueError(f"Orion sample {index} FIFO programming changed")
        if control & FULL.I2C_CONTROL_DMA_EN:
            raise ValueError(f"Orion sample {index} enabled controller DMA")
        for key in ("dma_en_pre", "dma_en_irq", "dma_en_post"):
            if FULL.hexadecimal(sample[key], 8, key):
                raise ValueError(f"Orion sample {index} started I2C6 APDMA")
        if completed and FULL.decimal(sample["fifo_count"], "FIFO count") != 1:
            raise ValueError(f"Orion sample {index} FIFO count is not one")
    else:
        if sample["engine"] != "dma":
            raise ValueError(f"Orion sample {index} did not use DMA")
        if not control & FULL.I2C_CONTROL_DMA_EN:
            raise ValueError(f"Orion sample {index} lacks controller DMA")
        if FULL.decimal(sample["fifo_count"], "FIFO sentinel") != 0xFFFF:
            raise ValueError(f"Orion sample {index} DMA FIFO sentinel changed")
        if mode == "packed-dma" and transfer_len != 0x0101:
            raise ValueError(f"Orion sample {index} packed length changed")
        if mode == "aux-dma" and (
            transfer_len != 1 or transfer_len_aux != 1
        ):
            raise ValueError(f"Orion sample {index} auxiliary length changed")


def require_completed_sample(
    sample: dict[str, str],
    mode: str,
    index: int,
) -> None:
    if FULL.decimal(sample["ret"], "transfer result") != 2:
        raise ValueError(f"Orion completed sample {index} did not return two")
    if (
        FULL.hexadecimal(sample["irq_stat"], 4, "IRQ status")
        != I2C_TRANSAC_COMP
    ):
        raise ValueError(f"Orion completed sample {index} IRQ is not exact")
    require_programmed_shape(sample, mode, index, completed=True)


def require_unprogrammed_failure(
    sample: dict[str, str], index: int
) -> None:
    zero_hex = (
        "transfer_len",
        "transfer_len_aux",
        "transac_len",
        "control",
        "irq_stat",
    )
    if any(FULL.hexadecimal(sample[key], 4, key) for key in zero_hex):
        raise ValueError(f"Orion failure sample {index} claims programmed state")
    if sample["engine"] != "fifo":
        raise ValueError(f"Orion failure sample {index} default engine changed")
    if FULL.decimal(sample["fifo_count"], "FIFO sentinel") != 0xFFFF:
        raise ValueError(f"Orion failure sample {index} FIFO sentinel changed")
    if any(FULL.hexadecimal(sample[key], 8, key) for key in DMA_FIELDS):
        raise ValueError(f"Orion failure sample {index} claims APDMA state")


def validate_failure_mapping(
    sample: dict[str, str],
    run_error: int,
    started: bool,
    mode: str,
) -> None:
    transfer_ret = FULL.decimal(sample["ret"], "failing transfer result")
    if transfer_ret == 2:
        raise ValueError("Orion failing sample unexpectedly returned two")
    expected_run_error = transfer_ret if transfer_ret < 0 else EIO
    if run_error != expected_run_error:
        raise ValueError("Orion run_error does not match the failing transfer")
    irq = FULL.hexadecimal(sample["irq_stat"], 4, "failing IRQ status")
    fifo_count = FULL.decimal(sample["fifo_count"], "failing FIFO count")
    if not started:
        if irq:
            raise ValueError("Orion pre-START failure has an IRQ")
        return
    if transfer_ret == EAGAIN:
        if not irq & I2C_ARB_LOST:
            raise ValueError("Orion -EAGAIN lacks arbitration-loss evidence")
    elif transfer_ret == ENXIO:
        if (
            irq & I2C_ARB_LOST
            or not irq & (I2C_HS_NACKERR | I2C_ACKERR)
            or not irq & I2C_TRANSAC_COMP
        ):
            raise ValueError("Orion -ENXIO lacks ACK/NACK plus completion")
    elif transfer_ret == ETIMEDOUT:
        if irq & (I2C_TRANSAC_COMP | I2C_ARB_LOST):
            raise ValueError("Orion timeout contains completion or arbitration loss")
    elif transfer_ret == EIO:
        fifo_mismatch = (
            mode == "packed-fifo"
            and irq == I2C_TRANSAC_COMP
            and 0 <= fifo_count <= 15
            and fifo_count != 1
        )
        nonexact_completion = (
            irq & I2C_TRANSAC_COMP
            and irq != I2C_TRANSAC_COMP
            and not irq & (I2C_ARB_LOST | I2C_HS_NACKERR | I2C_ACKERR)
        )
        if not fifo_mismatch and not nonexact_completion:
            raise ValueError("Orion -EIO lacks its bounded failure evidence")
    else:
        raise ValueError("Orion started failure has an unexpected errno")
    if mode == "packed-fifo" and not (
        transfer_ret == EIO
        and irq == I2C_TRANSAC_COMP
        and 0 <= fifo_count <= 15
        and fifo_count != 1
    ) and fifo_count != 0xFFFF:
        raise ValueError("Orion pre-drain FIFO failure lost its sentinel")


def validate_partial(data: bytes) -> dict[str, int | str]:
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Orion partial result is not ASCII") from exc
    lines = text.splitlines()
    if len(lines) < 2 or any(not line for line in lines):
        raise ValueError("Orion partial result is empty or malformed")
    header = FULL.fields(lines[0], FULL.HEADER_FIELDS, "Orion header")
    for key, wanted in {
        "candidate": "Orion",
        "state": "done",
        "one_shot": "consumed",
        "address": "0x69",
        "retries_before": "1",
        "retries_during": "0",
        "retries_after": "1",
        "registers": "05,06,47",
        "modes": "packed-fifo,packed-dma,aux-dma",
    }.items():
        if header[key] != wanted:
            raise ValueError(f"Orion partial header {key} changed")

    attempted = FULL.decimal(header["attempted"], "attempted count")
    completed = FULL.decimal(header["completed"], "completed count")
    run_error = FULL.decimal(header["run_error"], "run error")
    if not 1 <= attempted <= 9 or completed != attempted - 1:
        raise ValueError("Orion result is not a bounded stop-first prefix")
    if run_error >= 0 or len(lines) != attempted + 1:
        raise ValueError("Orion partial line count or run error changed")
    if FULL.decimal(header["transfer_attempts"], "transfer attempts") != attempted:
        raise ValueError("Orion partial contains a hidden transfer or retry")

    nonzero_starts = FULL.decimal(header["nonzero_starts"], "START count")
    if nonzero_starts not in (completed, attempted):
        raise ValueError("Orion partial START count is not stop-first bounded")
    started = nonzero_starts == attempted
    irq_count = FULL.decimal(header["irqs"], "IRQ count")
    if not completed <= irq_count <= completed + 2:
        raise ValueError("Orion partial IRQ count is outside the bounded delta")

    order = fixed_order()
    samples = [
        parse_sample(line, index, order[index])
        for index, line in enumerate(lines[1:])
    ]
    for index, sample in enumerate(samples[:-1]):
        require_completed_sample(sample, order[index][0], index)
    failing = samples[-1]
    failing_mode = order[completed][0]

    completed_dma = max(0, completed - 3)
    expected_dma_starts = completed_dma
    if failing_mode != "packed-fifo" and started:
        expected_dma_starts += 1
    dma_starts = FULL.decimal(header["dma_starts"], "DMA-start count")
    if dma_starts != expected_dma_starts:
        raise ValueError("Orion partial DMA-start count changed")

    if started:
        require_programmed_shape(
            failing, failing_mode, completed, completed=False
        )
    else:
        require_unprogrammed_failure(failing, completed)
    validate_failure_mapping(failing, run_error, started, failing_mode)
    failing_irq = FULL.hexadecimal(
        failing["irq_stat"], 4, "failing IRQ status"
    )
    failing_irq_delta = irq_count - completed
    if not started and failing_irq_delta != 0:
        raise ValueError("Orion pre-START failure has a hidden IRQ")
    if started and (
        (not failing_irq and failing_irq_delta != 0)
        or (failing_irq and not 1 <= failing_irq_delta <= 2)
    ):
        raise ValueError("Orion failing IRQ status/count correlation changed")

    return {
        "attempted": attempted,
        "completed": completed,
        "failing_mode": failing_mode,
        "failing_register": order[completed][1],
        "failing_ret": FULL.decimal(failing["ret"], "failing result"),
        "started": "yes" if started else "no",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = args.result.resolve(strict=True)
        summary = validate_partial(regular(result, "Orion partial result"))
    except (OSError, RuntimeError, TypeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=orion-bounded-stop-first-partial")
    for key, value in summary.items():
        if key == "failing_register":
            print(f"{key}={int(value):02x}")
        else:
            print(f"{key}={value}")
    print("adapter_retries=1,0,1")
    print("hidden_transfer=none")
    print("classification=preserved-failure-not-success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
