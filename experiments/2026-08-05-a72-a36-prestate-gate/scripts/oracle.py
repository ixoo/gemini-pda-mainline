#!/usr/bin/env python3
"""Independent bounded model for the dormant A36 prestate gate."""

from dataclasses import dataclass, replace


CPU8 = 1
CPU9 = 2
ENTRY = 0x1000


@dataclass(frozen=True)
class Prestate:
    abi: int = 1
    operation: int = CPU8
    observer_window: int = 1
    call_shape: int = 1
    cpu8_online: int = 0
    cpu9_online: int = 0
    page: int = 0x80
    buckb_enabled: int = 0
    vsel: int = 0x46
    spm_218: int = 0x00010132
    spm_290: int = 0x2
    pwrap_reset: int = 0
    mp2_dcm: int = 0
    sentinels: int = 1
    clock_valid: int = 1
    pstore: int = 1
    watchdog: int = 1
    cluster_dcm: int = 0
    shared_writes: int = 0
    target_mpidr: int = 0x200
    entry_pa: int = ENTRY
    generation: int = 1
    cookie: int = 0xA7200001


def valid(prestate: Prestate) -> bool:
    target = 0x200 if prestate.operation == CPU8 else 0x201
    if (prestate.abi != 1 or prestate.operation not in (CPU8, CPU9) or
            prestate.observer_window != 1 or prestate.call_shape != 1 or
            prestate.target_mpidr != target or prestate.entry_pa != ENTRY or
            prestate.generation != 1 or prestate.cookie != 0xA7200001):
        return False
    if prestate.operation == CPU8:
        return (prestate.cpu8_online == 0 and prestate.cpu9_online == 0 and
                prestate.page == 0x80 and prestate.buckb_enabled == 0 and
                prestate.vsel == 0x46 and prestate.spm_218 == 0x00010132 and
                prestate.spm_290 == 0x2 and prestate.pwrap_reset == 0 and
                prestate.mp2_dcm == 0 and prestate.sentinels == 1 and
                prestate.clock_valid == 1 and prestate.pstore == 1 and
                prestate.watchdog == 1 and prestate.cluster_dcm == 0 and
                prestate.shared_writes == 0)
    return (prestate.cpu8_online == 1 and prestate.cpu9_online == 0 and
            prestate.page == 0 and prestate.buckb_enabled == 0 and
            prestate.vsel == 0 and prestate.spm_218 == 0 and
            prestate.spm_290 == 0 and prestate.pwrap_reset == 0 and
            prestate.mp2_dcm == 0 and prestate.sentinels == 0 and
            prestate.clock_valid == 0 and prestate.pstore == 0 and
            prestate.watchdog == 1 and prestate.cluster_dcm == 1 and
            prestate.shared_writes == 0)


def main() -> None:
    cpu8 = Prestate()
    cpu9 = replace(
        cpu8, operation=CPU9, cpu8_online=1, cluster_dcm=1,
        target_mpidr=0x201, page=0, vsel=0, spm_218=0, spm_290=0,
        sentinels=0, clock_valid=0, pstore=0)
    probes = [cpu8, cpu9]
    print("claim=PARTIAL_A36_PRESTATE_GATE")
    print(f"probes={len(probes)}")
    print(f"cpu8_valid={int(valid(cpu8))}")
    print(f"cpu9_valid={int(valid(cpu9))}")
    print("entry_pa_bound=1")
    print("generation_cookie_bound=1")
    print("hardware_access=0")
    print("cpu_on_calls=0")
    print("status=PASS" if all(map(valid, probes)) else "status=FAIL")


if __name__ == "__main__":
    main()
