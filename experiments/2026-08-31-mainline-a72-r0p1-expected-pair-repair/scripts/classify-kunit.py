#!/usr/bin/env python3
"""Classify the exact hardware-free r0p1 expected-pair KUnit proof."""

from __future__ import annotations

import hashlib
import io
from contextlib import redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


EXPERIMENT = "2026-08-31-mainline-a72-r0p1-expected-pair-repair"
SOURCE_SHA256 = "8e6bdb8064207650365f893bd86ce529d2759f747a6a3a326a9329ccb3968026"


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repository = script_dir.parents[2]
    source = (
        repository
        / "experiments/2026-08-31-mainline-a72-post-capabilities-checkpoints"
        / "scripts/classify-kunit.py"
    )
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise SystemExit("error: source KUnit classifier changed")
    spec = spec_from_file_location("r0p1_kunit_classifier", source)
    if spec is None or spec.loader is None:
        raise SystemExit("error: unable to load pinned KUnit classifier")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    output = io.StringIO()
    with redirect_stdout(output):
        module.main()
    record = output.getvalue().replace(
        "experiment=2026-08-31-mainline-a72-post-capabilities-checkpoints",
        f"experiment={EXPERIMENT}",
        1,
    )
    print(record, end="")


if __name__ == "__main__":
    main()
