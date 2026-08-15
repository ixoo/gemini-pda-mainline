# MT6797 handoff decoder-link design

## Problem

The handoff state-source and live-source objects are selected by
`MTK_MT6797_DVFSP_HANDOFF`. They unconditionally call four pure helpers from
`mt6797-dvfsp-clock-state.o` and `mt6797-dvfsp-cspm-state.o`. Those objects are
selected only by the independent, optional
`MTK_MT6797_DVFSP_CLOCK_BACKEND`, so a transport-free handoff profile compiles
the callers but fails the final link.

## Contract

Introduce one hidden `MTK_MT6797_DVFSP_STATE_DECODERS` gate. It is enabled when
either the handoff pipeline or protected-clock transport is selected and owns
both pure decoder objects. The MMIO-backed transport remains selected only by
`MTK_MT6797_DVFSP_CLOCK_BACKEND`.

The change must prove both configurations:

1. `HANDOFF=y`, `CLOCK_BACKEND=n` builds both pure decoder objects and links.
2. `HANDOFF=y`, `CLOCK_BACKEND=y` builds each decoder exactly once and links.

## Non-goals

- no MMIO, I2C, regulator, clock, firmware, CPU hotplug, or secure operation;
- no new platform driver, Device Tree enablement, or runtime registration;
- no device boot or boot-partition write;
- no CPU8 or CPU9 admission.
