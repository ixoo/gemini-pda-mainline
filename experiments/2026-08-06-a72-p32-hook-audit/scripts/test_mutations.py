#!/usr/bin/env python3
"""Exercise P32 publication, identity, guard-loss, and one-shot mutations."""

from __future__ import annotations

from oracle import (
    BRANCH_R,
    BRANCH_X,
    CPU8,
    STATE_CONSUMED,
    Transaction,
    cpu_die,
    cpu_disable,
    cpu_kill,
    consume,
    fresh,
    publish,
    rollback_trace,
    target_locked,
)


ERROR = -19


def assert_no_forbidden_effects(tx: Transaction) -> None:
    assert "CPU_OFF" not in " ".join(tx.effects)
    assert "affinity" not in " ".join(tx.effects)


def main() -> int:
    probes = 0

    tx = fresh()
    trace = rollback_trace(tx, CPU8, ERROR)
    assert trace.index("p32-published") < trace.index("outer-reset")
    assert trace.index("p32-published") < trace.index("outer-reverse")
    probes += 1

    assert cpu_disable(tx, CPU8) == "-EIO"
    assert cpu_disable(tx, CPU8) == "-EALREADY"
    assert_no_forbidden_effects(tx)
    probes += 1

    assert cpu_die(tx, CPU8)
    assert cpu_kill(tx, CPU8) == "-EIO"
    assert "park-without-CPU_OFF" in tx.effects
    assert "kill-no-affinity" in tx.effects
    probes += 1

    assert consume(tx, CPU8, ERROR) == "0"
    assert tx.record.branch == BRANCH_R
    assert tx.record.state == STATE_CONSUMED
    assert consume(tx, CPU8, ERROR) == "-EAGAIN"
    assert tx.record.branch == BRANCH_R
    assert not target_locked(tx, CPU8)
    probes += 1

    missing_park = fresh()
    assert publish(missing_park, CPU8, 42, ERROR) == "0"
    assert cpu_disable(missing_park, CPU8) == "-EIO"
    assert cpu_kill(missing_park, CPU8) == "-ETIMEDOUT"
    assert consume(missing_park, CPU8, ERROR) == "-EIO"
    assert missing_park.record.branch == BRANCH_X
    probes += 1

    mismatched = fresh()
    assert publish(mismatched, CPU8, 42, ERROR) == "0"
    assert cpu_die(mismatched, CPU8)
    assert consume(mismatched, CPU8, ERROR - 1) == "-EUCLEAN"
    assert mismatched.record.branch == BRANCH_X
    probes += 1

    for mutation in ("cpu", "mpidr", "generation", "cookie", "operation"):
        stale = fresh()
        assert publish(stale, CPU8, 42, ERROR) == "0"
        if mutation == "cpu":
            probe_cpu = 9
        elif mutation == "mpidr":
            stale.p30_mpidr += 1
            probe_cpu = CPU8
        elif mutation == "generation":
            stale.identity_generation += 1
            probe_cpu = CPU8
        elif mutation == "cookie":
            stale.identity_cookie += 1
            probe_cpu = CPU8
        else:
            stale.operation = "CPU9_UP"
            probe_cpu = CPU8
        assert not target_locked(stale, probe_cpu), mutation
        assert cpu_die(stale, probe_cpu) is False, mutation
        assert cpu_kill(stale, probe_cpu) == "0", mutation
        probes += 1

    for name, tx in (("wrong-cpu", fresh(9)), ("zero-error", fresh())):
        if name == "wrong-cpu":
            result = publish(tx, CPU8, 42, ERROR)
        else:
            result = publish(tx, CPU8, 42, 0)
        assert result == "-EAGAIN" if name == "wrong-cpu" else "-EINVAL"
        probes += 1

    print("claim=P32_EXACT_GENERATION_ROLLBACK_ORACLE")
    print(f"probes={probes}")
    print("nested_publication_before_outer_reset=1")
    print("identity_mutations_rejected=5/5")
    print("missing_park_branch_X=1")
    print("mismatched_error_branch_X=1")
    print("consumed_generation_retired=1")
    print("forbidden_cpu_off_affinity=0")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
