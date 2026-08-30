#!/usr/bin/env python3
"""Classify the exact hardware-free P27-attribution binder KUnit proof."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


EXPERIMENT = "2026-08-30-mainline-a72-p27-runtime-attribution"
PROFILE = "a72-default-off-binder-kunit"


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
    generic = load(
        "p27_attribution_classifier_base",
        repository
        / "experiments/2026-08-30-mainline-a72-live-a34-predicate-repair"
        / "scripts/classify-kunit.py",
    )
    binder = load(
        "p27_attribution_binder_inventory",
        repository
        / "experiments/2026-08-27-mainline-a72-default-off-binder"
        / "scripts/classify-kunit.py",
    )
    binder_cases = binder.SUITES[2][1][:-1] + (
        "mt6797_binder_p27_diagnostic_test",
        binder.SUITES[2][1][-1],
    )
    generic.PROFILES[PROFILE] = {
        "options": (
            "CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST=y",
            "CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR_KUNIT_TEST=y",
            "CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER_KUNIT_TEST=y",
        ),
        "suites": (
            binder.SUITES[0],
            binder.SUITES[1],
            (binder.SUITES[2][0], binder_cases),
        ),
    }

    output = io.StringIO()
    with redirect_stdout(output):
        generic.main()
    record = output.getvalue().replace(
        "experiment=2026-08-30-mainline-a72-live-a34-predicate-repair",
        f"experiment={EXPERIMENT}",
        1,
    )
    print(record, end="")


if __name__ == "__main__":
    main()
