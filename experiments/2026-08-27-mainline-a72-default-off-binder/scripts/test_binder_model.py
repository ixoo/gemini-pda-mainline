#!/usr/bin/env python3
"""Exhaust the CPU8 default-off binder model."""

from __future__ import annotations

import errno

from binder_model import (
    Admission,
    BinderModel,
    EREMOTEIO,
    Faults,
    LEDGER_MAX_STAGE,
    Lifecycle,
    OwnerPhase,
    Stage,
    Terminal,
)


def test_success() -> None:
    assert max(Stage) == LEDGER_MAX_STAGE
    model = BinderModel()
    assert model.run() == 0
    result = model.result
    assert result.terminal == Terminal.CPU8_ONLINE_PROOF
    assert result.checkpoints == 20
    assert result.terminal_commits == 1
    assert result.membership_published
    assert result.cpu_requests == 1
    assert result.cpu_off_requests == 0
    assert result.retries == 0
    assert result.retained == {"p27", "provider", "cpu8"}
    assert result.owner_phase == OwnerPhase.IDLE
    assert not result.owner_active
    assert result.owner_members == 1
    assert not result.p32_required
    assert not result.p32_published
    assert model.events[0] == "ledger:begin"
    assert model.events[-4:] == [
        "before:membership",
        "effect:membership",
        "after:membership",
        "terminal:cpu8_online_proof",
    ]


def test_admission() -> None:
    invalid = (
        Admission(armed=False),
        Admission(token_owned=False),
        Admission(cpu=9),
        Admission(target="CPUHP_AP_ONLINE"),
        Admission(tasks_frozen=True),
        Admission(cpu8_online=True),
        Admission(cpu9_online=True),
    )
    for admission in invalid:
        model = BinderModel()
        assert model.run(admission) == -errno.EPERM
        assert not model.result.attempted
        assert not model.events


def test_ledger_begin_failure() -> None:
    model = BinderModel(Faults(ledger_begin=True))
    assert model.run() == -errno.EIO
    assert model.result.attempted
    assert model.result.terminal == Terminal.REJECTED_PRESTATE
    assert model.result.checkpoints == 0
    assert model.result.terminal_commits == 1
    assert model.result.owner_phase == OwnerPhase.REJECTED
    assert not model.result.owner_active
    assert model.events == [
        "ledger:begin",
        "terminal:rejected_prestate",
    ]


def test_effect_failures() -> None:
    for stage in Stage:
        model = BinderModel(Faults(effect=stage))
        assert model.run() == -errno.EIO
        result = model.result
        assert result.terminal_commits == 1
        assert result.cpu_off_requests == 0
        assert result.retries == 0
        if stage == Stage.WATCHDOG:
            assert result.terminal == Terminal.REJECTED_PRESTATE
            assert not result.watchdog_armed
        elif stage in (Stage.P27, Stage.PROVIDER):
            assert result.terminal == Terminal.ROLLED_BACK_PREISO
            assert not result.retained
        else:
            assert result.terminal == Terminal.FAULT_RETAIN_POSTISO
            assert result.owner_phase == OwnerPhase.FAULT
            assert result.p32_published
        if stage == Stage.MEMBERSHIP:
            assert not result.membership_published


def test_regular_checkpoint_failures() -> None:
    checked = 0
    for stage in Stage:
        for phase in ("before", "after"):
            model = BinderModel(Faults(checkpoint=(phase, stage)))
            assert model.run() == -errno.EIO
            result = model.result
            assert result.checkpoint_errno == -errno.EIO
            assert result.terminal_commits == 1
            assert result.cpu_off_requests == 0
            assert result.retries == 0
            preisolation = (
                stage < Stage.ISOLATION
                or (stage == Stage.ISOLATION and phase == "before")
            )
            if preisolation:
                assert result.terminal in (
                    Terminal.REJECTED_PRESTATE,
                    Terminal.ROLLED_BACK_PREISO,
                )
                assert not result.retained
            else:
                assert result.terminal == Terminal.FAULT_RETAIN_POSTISO
                assert result.owner_phase == OwnerPhase.FAULT
                assert result.p32_published
            checked += 1
    assert checked == 20


def test_terminal_failure_after_membership() -> None:
    model = BinderModel(Faults(terminal=True))
    assert model.run() == -errno.ENOSPC
    result = model.result
    assert result.membership_published
    assert result.terminal == Terminal.FAULT_RETAIN_POSTISO
    assert result.checkpoint_errno == -errno.ENOSPC
    assert result.retained == {"p27", "provider", "cpu8"}
    assert result.owner_members == 1
    assert result.owner_phase == OwnerPhase.FAULT
    assert result.p32_published
    assert model.events[-2:] == [
        "terminal:cpu8_online_proof",
        "p32:published",
    ]


def test_terminal_failures_preserve_primary_fault() -> None:
    checked = 0
    for stage in Stage:
        model = BinderModel(Faults(effect=stage, terminal=True))
        assert model.run() == -errno.EIO
        assert model.result.checkpoint_errno == -errno.ENOSPC
        assert model.result.stage_errno == -errno.EIO
        assert model.result.terminal_commits == 1
        assert model.result.cpu_off_requests == 0
        checked += 1
    for stage in Stage:
        for phase in ("before", "after"):
            model = BinderModel(Faults(
                checkpoint=(phase, stage), terminal=True,
            ))
            assert model.run() == -errno.EIO
            assert model.result.checkpoint_errno == -errno.ENOSPC
            assert model.result.stage_errno == -errno.EIO
            assert model.result.terminal_commits == 1
            assert model.result.cpu_off_requests == 0
            checked += 1
    assert checked == 30


def test_malformed_owner_results() -> None:
    model = BinderModel(Faults(malformed=Stage.WATCHDOG))
    assert model.run() == -errno.EPROTO
    assert model.result.terminal == Terminal.REJECTED_PRESTATE
    assert not model.result.watchdog_armed
    assert not model.result.retained

    model = BinderModel(Faults(malformed=Stage.P27))
    assert model.run() == -errno.EPROTO
    assert model.result.terminal == Terminal.ROLLBACK_FAULT_PREISO
    assert model.result.retained == {"p27"}

    model = BinderModel(Faults(malformed=Stage.PROVIDER))
    assert model.run() == -errno.EPROTO
    assert model.result.terminal == Terminal.ROLLBACK_FAULT_PREISO
    assert model.result.retained == {"p27", "provider"}


def test_rollback_failures() -> None:
    model = BinderModel(Faults(effect=Stage.PROVIDER, provider_release=True))
    assert model.run() == -EREMOTEIO
    assert model.result.terminal == Terminal.ROLLBACK_FAULT_PREISO
    assert model.result.retained == {"p27", "provider"}

    model = BinderModel(Faults(effect=Stage.PROVIDER, p27_release=True))
    assert model.run() == -EREMOTEIO
    assert model.result.terminal == Terminal.ROLLBACK_FAULT_PREISO
    assert model.result.rolled_back == ["provider"]
    assert model.result.retained == {"p27"}


def test_split_lifecycle_and_failure() -> None:
    model = BinderModel()
    assert model.complete() == -errno.EALREADY
    assert model.begin() == 0
    assert model.lifecycle == Lifecycle.CPU_ON_ACCEPTED
    assert model.result.checkpoints == 12
    assert model.secondary_complete() == 0
    assert model.lifecycle == Lifecycle.SECONDARY_COMPLETE
    assert model.result.checkpoints == 14
    assert model.complete() == 0
    assert model.lifecycle == Lifecycle.TERMINAL

    model = BinderModel()
    assert model.begin() == 0
    assert model.fail(-errno.ETIMEDOUT) == -errno.ETIMEDOUT
    assert model.result.terminal == Terminal.FAULT_RETAIN_POSTISO
    assert not model.result.cpu8_online
    assert model.result.checkpoints == 13
    assert model.result.owner_phase == OwnerPhase.ON_ISSUED
    assert model.result.p32_required
    assert model.generic_failure(-errno.ETIMEDOUT) == -errno.ETIMEDOUT
    assert model.result.owner_phase == OwnerPhase.FAULT
    assert model.result.p32_published

    model = BinderModel()
    assert model.begin() == 0
    assert model.secondary_complete() == 0
    assert model.fail(-errno.ENOMEM, cpu8_online=True) == -errno.ENOMEM
    assert model.result.terminal == Terminal.FAULT_RETAIN_POSTISO
    assert model.result.cpu8_online
    assert model.generic_failure(-errno.ENOMEM, cpu8_online=True) == -errno.ENOMEM
    assert model.result.owner_phase == OwnerPhase.FAULT


def test_handoff_guards() -> None:
    model = BinderModel()
    assert model.begin() == 0
    assert model.secondary_complete(cpu=9) == -errno.EPROTO
    assert model.result.terminal == Terminal.FAULT_RETAIN_POSTISO

    model = BinderModel()
    assert model.begin() == 0
    assert model.secondary_complete() == 0
    events = list(model.events)
    assert model.secondary_complete() == -errno.EALREADY
    assert model.events == events
    assert model.complete(cpu8_online=False) == -errno.EPROTO


def test_one_shot() -> None:
    model = BinderModel()
    assert model.run() == 0
    events = list(model.events)
    assert model.begin() == -errno.EALREADY
    assert model.events == events
    assert model.result.cpu_requests == 1
    assert model.result.terminal == Terminal.CPU8_ONLINE_PROOF
    assert model.result.checkpoints == 20


def test_membership_owner_handoff() -> None:
    model = BinderModel()
    assert model.begin() == 0
    assert model.result.owner_phase == OwnerPhase.ON_ISSUED
    assert model.result.owner_active
    assert model.secondary_complete() == 0
    model.faults = Faults(terminal=True)
    assert model.complete() == -errno.ENOSPC
    assert model.result.membership_published
    assert model.result.owner_members == 1
    assert model.result.owner_phase == OwnerPhase.VERIFYING
    assert model.result.p32_required
    terminal_index = model.events.index("terminal:cpu8_online_proof")
    assert model.generic_failure(-errno.ENOSPC, cpu8_online=True) == -errno.ENOSPC
    assert model.result.owner_phase == OwnerPhase.FAULT
    assert model.result.p32_published
    assert model.events.index("p32:published") > terminal_index


def main() -> None:
    tests = (
        test_success,
        test_admission,
        test_ledger_begin_failure,
        test_effect_failures,
        test_regular_checkpoint_failures,
        test_terminal_failure_after_membership,
        test_terminal_failures_preserve_primary_fault,
        test_malformed_owner_results,
        test_rollback_failures,
        test_split_lifecycle_and_failure,
        test_handoff_guards,
        test_one_shot,
        test_membership_owner_handoff,
    )
    for test in tests:
        test()
    print("validation=a72-default-off-binder-model")
    print(f"cases={len(tests)}")
    print("effect_failures=10")
    print("regular_checkpoint_failures=20")
    print("terminal_failure_paths=31")
    print("malformed_owner_results=3")
    print("success_checkpoints=20")
    print("retained_ledger_max_stage=10")
    print("membership_owner_phases=5")
    print("success_owner_phase=idle")
    print("postiso_owner_phase=p32-fault")
    print("terminal_commits=1")
    print("cpu_requests=1")
    print("cpu_off_requests=0")
    print("retries=0")
    print("result=pass")


if __name__ == "__main__":
    main()
