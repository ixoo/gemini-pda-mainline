#!/usr/bin/env python3
"""Fail-closed tests for the one-way CPU8 startup model."""

from dataclasses import replace

from one_way_model import ENTRY, POSTISO_STAGES, PREISO_STAGES, run


def main() -> None:
    success = run()
    assert success.terminal == "cpu8-online-held"
    assert success.cpu8_online and not success.cpu9_online
    assert success.buck and success.isolation == 0
    assert success.spm_reset == 0x00010133
    assert success.sram_verified and success.dcm == 0x0D
    assert success.watchdog_armed

    for stage in PREISO_STAGES:
        result = run(fail_at=stage)
        assert result.terminal == "rolled-back-preiso", stage
        assert not result.cpu8_online and not result.buck
        assert result.spm_reset == ENTRY.spm_reset
        assert result.isolation == ENTRY.isolation
        assert not result.pwrap_reset and result.dcm == 0

    for stage in POSTISO_STAGES:
        result = run(fail_at=stage)
        assert result.terminal.startswith("fault-retain-postiso:"), stage
        assert result.buck, stage
        assert result.watchdog_armed, stage

    ambiguous = run(fail_at="isolation-write")
    assert ambiguous.isolation is None
    assert ambiguous.buck and ambiguous.spm_reset == 0x00010133
    assert run(fail_at="isolation-readback").isolation is None
    assert run(fail_at="pwrap-deassert").pwrap_reset is None
    assert not run(fail_at="sram-readback").sram_verified
    assert run(fail_at="psci").cpu8_online is None
    assert run(fail_at="secondary").cpu8_online is None
    dcm_failure = run(fail_at="dcm")
    assert dcm_failure.cpu8_online and dcm_failure.dcm is None

    for psci_result, affinity, secondary in (
        ("denied", "off", False),
        ("already-on", "off", False),
        ("on-pending", "pending", False),
        ("success", "on", False),
    ):
        result = run(
            psci_result=psci_result,
            affinity=affinity,
            secondary=secondary,
        )
        assert result.terminal.startswith("fault-retain-postiso:")
        assert result.buck and result.isolation == 0

    for psci_result in ("already-on", "on-pending"):
        result = run(psci_result=psci_result, affinity="on", secondary=True)
        assert result.terminal == "cpu8-online-held"

    assert run(target=9).terminal == "rejected-prestate"
    assert run(replace(ENTRY, buck=True)).terminal == "rejected-prestate"
    assert run(replace(ENTRY, isolation=0)).terminal == "rejected-prestate"
    assert run(replace(ENTRY, watchdog_armed=False)).terminal == "rejected-prestate"

    print("PASS: one-way CPU8 model, pre-isolation rollback, and post-isolation fault-retain")


if __name__ == "__main__":
    main()
