#!/usr/bin/env python3
"""Classify exact hardware-free KUnit coverage for the READY repair."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


EXPERIMENT = "2026-08-30-mainline-a72-ready-token-contract-repair"
DERIVED_CASES = (
    "mt6797_a72_derived_success_test",
    "mt6797_a72_derived_source_rejections_test",
    "mt6797_a72_derived_ready_rejection_test",
    "mt6797_a72_derived_observed_target_rejected_test",
    "mt6797_a72_legacy_assertions_rejected_test",
    "mt6797_a72_derived_repeat_rejected_test",
)
PRE_P28_CASES = (
    "da9213_provider_snapshot_success",
    "da9213_provider_snapshot_transport_faults",
    "da9213_provider_snapshot_unstable",
    "da9213_provider_snapshot_registry_guards",
    "da9213_membership_positive_abort_success",
    "da9213_membership_acquire_transport_faults",
    "da9213_membership_acquire_malformed_success",
    "da9213_membership_release_transport_faults",
    "da9213_membership_release_malformed_success",
    "da9213_membership_abort_guards_and_p29",
)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repository = script_dir.parents[2]
    base_path = (
        repository
        / "experiments/2026-08-30-mainline-a72-live-a34-predicate-repair"
        / "scripts/classify-kunit.py"
    )
    spec = spec_from_file_location("ready_contract_classifier_base", base_path)
    if spec is None or spec.loader is None:
        raise SystemExit("error: unable to load pinned KUnit classifier")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    derived = module.PROFILES["a72-derived-admission-kunit"]
    derived["suites"] = (("mt6797-a72-derived-admission", DERIVED_CASES),)
    module.PROFILES["da921x-pre-p28-provider-abort-kunit"] = {
        "options": (
            "CONFIG_REGULATOR_DA9213_LEGACY_MEMBERSHIP_KUNIT_TEST=y",
        ),
        "suites": (("da9213-legacy-membership-provider", PRE_P28_CASES),),
    }

    output = io.StringIO()
    with redirect_stdout(output):
        module.main()
    record = output.getvalue().replace(
        "experiment=2026-08-30-mainline-a72-live-a34-predicate-repair",
        f"experiment={EXPERIMENT}",
        1,
    )
    print(record, end="")


if __name__ == "__main__":
    main()
