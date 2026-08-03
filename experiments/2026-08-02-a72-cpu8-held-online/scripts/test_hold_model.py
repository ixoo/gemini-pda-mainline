#!/usr/bin/env python3
"""Exercise positive and fail-closed CPU8 hold-model boundaries."""

from hold_model import HoldState, clamp_hps, cpu_down_entry, ipi_sample


def main() -> int:
    state = HoldState()
    assert clamp_hps(state) == 1
    assert cpu_down_entry(state, 8) == -1
    assert state.notifier_calls == state.platform_off_calls == 0
    assert ipi_sample(state, 8)
    assert state.ipi_hits == 1 and state.terminal == "pending"
    assert ipi_sample(state, 8)
    assert state.ipi_hits == 2 and state.terminal == "pass"

    for mutation in (
        HoldState(cpu8_online=False),
        HoldState(cpu9_online=True),
    ):
        assert not ipi_sample(mutation, 8)
        assert mutation.terminal == "fault"
    wrong_cpu = HoldState()
    assert not ipi_sample(wrong_cpu, 7)
    failed_call = HoldState()
    assert not ipi_sample(failed_call, 8, -5)

    cpu0 = HoldState()
    assert cpu_down_entry(cpu0, 0) == 0
    assert cpu0.notifier_calls == cpu0.platform_off_calls == 1
    cpu9 = HoldState()
    assert cpu_down_entry(cpu9, 9) == -1
    assert cpu9.notifier_calls == cpu9.platform_off_calls == 0

    print("validation=cpu8-held-online-model")
    print("positive_samples=2")
    print("fail_closed_cases=4")
    print("cpu8_cpu9_pre_notifier_veto=pass")
    print("cpu0_7_unchanged_model=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
