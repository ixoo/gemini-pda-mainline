#!/usr/bin/env python3
"""Exhaust the first CPU8 active-transition model boundaries."""

from transition_model import (
    CPU8,
    CPU9,
    CPU_ON_WAIT_MS,
    RECOVERY_TIMEOUT_MS,
    Stage,
    run,
)


success = run(cpu=CPU8)
assert success.terminal == "cpu8-online-proof"
assert success.cpu8_online and not success.cpu9_online
assert success.cpu_requests == 1 and success.cpu_off_requests == 0
assert success.retries == 0 and success.watchdog_armed
assert success.isolation_crossed
assert len(success.checkpoints) == len(Stage) * 2
assert RECOVERY_TIMEOUT_MS > CPU_ON_WAIT_MS

for stage in Stage:
    outcome = run(cpu=CPU8, fail=stage)
    assert outcome.cpu_requests <= 1
    assert outcome.cpu_off_requests == 0 and outcome.retries == 0
    assert outcome.cpu9_online is False
    assert outcome.checkpoints[-1] == f"before:{stage.value}"
    if stage is Stage.WATCHDOG:
        assert outcome.terminal == "rejected-prestate"
        assert not outcome.watchdog_armed
        assert not outcome.p27_owned and not outcome.provider_owned
        assert not outcome.rollback and not outcome.retained_power
    elif stage in (Stage.P27, Stage.PROVIDER):
        assert outcome.terminal == "rolled-back-preiso"
        assert not outcome.p27_owned and not outcome.provider_owned
        assert not outcome.retained_power
    else:
        assert outcome.terminal == "fault-retain-postiso"
        assert "p27" in outcome.retained_power
        assert "provider" in outcome.retained_power

for rejected in (
    run(cpu=CPU9),
    run(cpu=CPU8, prefix_complete=False),
    run(cpu=CPU8, repeat=True),
):
    assert rejected.terminal == "rejected-prestate"
    assert not rejected.attempted and rejected.cpu_requests == 0
    assert not rejected.checkpoints

print(f"success_checkpoints={len(success.checkpoints)}")
print(f"injected_stage_failures={len(Stage)}")
print("watchdog_arm_failures_rejected=1")
print("preisolation_failures_rolled_back=2")
print("postisolation_failures_retained=6")
print("cpu9_prefix_repeat_rejections=3")
print("cpu_requests_maximum=1")
print("cpu_off_requests=0")
print("retries=0")
print("device_action=none")
print("result=pass")
