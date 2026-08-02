#!/usr/bin/env python3
"""Test success and fail-closed boundaries in the rollback reference model."""

from __future__ import annotations

from dataclasses import replace

from rollback_model import ENTRY, run


def main() -> int:
    early = run(observer_capturing=False)
    assert early.state == "pre-latch-refused"
    assert early.final == ENTRY
    assert early.actions == ()
    assert not early.attempted

    success_after_early = run(attempted=early.attempted)
    assert success_after_early.state == "rolled-back"
    assert success_after_early.attempted

    success = run()
    assert success.state == "rolled-back"
    assert success.final == ENTRY
    assert success.actions == (
        "spm-reset-release",
        "pwrap-assert",
        "buck-enable",
        "settled-readback",
        "inject-stop",
        "buck-disable",
        "spm-reset-restore",
        "pwrap-deassert",
    )

    entry_mutations = {
        "cpu8-online": replace(ENTRY, cpu8=1),
        "cpu9-online": replace(ENTRY, cpu9=1),
        "page": replace(ENTRY, page=0),
        "buck": replace(ENTRY, buck=1),
        "vsel": replace(ENTRY, vsel=0x45),
        "spm-reset": replace(ENTRY, spm_reset=0x00010133),
        "isolation": replace(ENTRY, isolation=0),
        "pwrap": replace(ENTRY, pwrap_reset=1),
        "secure": replace(ENTRY, secure_zero=False),
        "dcm": replace(ENTRY, dcm=0x0D),
    }
    for label, state in entry_mutations.items():
        result = run(state)
        assert result.state == "rejected-prestate", label
        assert result.actions == (), label
        assert result.attempted, label

    for label, options in {
        "buck-owner": {"buck_owned": False},
        "reset-owner": {"reset_owned": False},
        "pwrap-owner": {"pwrap_owned": False},
        "buck-readback": {"buck_disable_readback": False},
        "reset-readback": {"reset_restore_readback": False},
        "pwrap-readback": {"pwrap_clear_readback": False},
        "forbidden-boundary": {"violate_boundary": True},
    }.items():
        result = run(**options)
        assert result.state == "fault-retain", label
        assert result.final != ENTRY, label

    repeated = run(attempted=True)
    assert repeated.state == "already-attempted"
    assert repeated.actions == ()
    assert repeated.attempted

    print("PASS: pre-isolation rollback model and 19 fail-closed boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
