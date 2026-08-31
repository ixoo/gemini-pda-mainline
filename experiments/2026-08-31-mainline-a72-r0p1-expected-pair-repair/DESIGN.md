# Design: exact r0p1 expected-pair repair

## Selected evidence

The predecessor's sole physical CPU8 trigger retained P30E reason 8 with
mismatch bitmap `0x2`. Bit 1 is MIDR. Its first-value pair was:

- expected: `0x410fd080`;
- observed: `0x410fd081`.

Every other late-target register comparison passed. Earlier independent
target-local capsules also recorded `0x410fd081` on both CPU8 and CPU9.

## Repair boundary

Canonical patch `0459` changes only the immutable prior-cycle expected-pair
initializer in `arch/arm64/kernel/mt6797_psci.c`:

```c
.midr = MIDR_CORTEX_A72 | MIDR_CPU_VAR_REV(0, 1),
```

The `MIDR_CORTEX_A72` model checks used by capability classification remain
revision-neutral. Expected/observed evidence arrays, every other expected-pair
field, source identities, power operations, CPU requests, P30E, CPU_OFF, retry,
storage, and reboot paths remain unchanged.

## Validation contract

- Pin the exact post-`0458` source file and prepared-tree identities.
- Generate one normal format-patch with one removed and one added source line.
- Replay the patch and re-run the exact source assertions.
- Reject changes to revision-neutral model checks or any action-call inventory.
- Run manifest-wide series invariants and strict style review.
- Compile the focused KUnit and production profiles on Buildbox.
- Run the existing no-network 51-test four-vCPU suite.
- Construct and independently validate one production container.

The physical successor retains one CPU8 request maximum. CPU9, CPU_OFF, retry,
and automatic reboot remain forbidden.
