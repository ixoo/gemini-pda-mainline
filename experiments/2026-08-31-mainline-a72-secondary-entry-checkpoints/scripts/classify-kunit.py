#!/usr/bin/env python3
"""Classify the exact hardware-free CPU8 checkpoint KUnit proof."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


EXPERIMENT = "2026-08-31-mainline-a72-secondary-entry-checkpoints"


def load(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"error: unable to load pinned module: {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repository = script_dir.parents[2]
    base = load(
        "checkpoint_p30e_classifier",
        repository
        / "experiments/2026-08-31-mainline-a72-p30e-entry-diagnostic"
        / "scripts/classify-kunit.py",
    )

    output = io.StringIO()
    with redirect_stdout(output):
        base.main()
    record = output.getvalue().replace(
        "experiment=2026-08-31-mainline-a72-p30e-entry-diagnostic",
        f"experiment={EXPERIMENT}",
        1,
    )
    print(record, end="")


if __name__ == "__main__":
    main()
