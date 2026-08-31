# Design: accept exact A72 revisions in the expected-policy guard

## Selected evidence

Exact candidate `b5328f6a...` booted serviceably but its read-only pretrigger
frame reported READY validation `ret=-22`, plan mask `0x12f7b00`, and evidence
mask zero. Relative to the last READY frame, the target and required capability
sets lost exactly the Spectre v2, Spectre v4, and BHB bits.

Source tracing identifies one shared prerequisite for those three expected
policy classifiers in `arch/arm64/kernel/proton-pack.c`:

```c
expected->midr == MIDR_CORTEX_A72
```

Canonical patch `0459` intentionally made the immutable expected-pair MIDR the
exact named-unit value `MIDR_CORTEX_A72 | MIDR_CPU_VAR_REV(0, 1)`. The literal
equality therefore rejects valid r0p1 input before any CPU request.

## Repair boundary

Change only that guard to compare model bits:

```c
(expected->midr & MIDR_CPU_MODEL_MASK) == MIDR_CORTEX_A72
```

This matches the existing target-evidence model check in the same file. It
accepts Cortex-A72 revisions, rejects a different CPU model, and leaves the
exact r0p1 value intact for the later target-register comparison.

No expected register, mitigation policy, CPU request, CPU9 path, CPU_OFF path,
retry, hardware access, storage access, power sequence, or reboot path changes.

## Validation contract

- Pin the exact post-`0459` Buildbox source state and `proton-pack.c` identity.
- Generate one normal format-patch with one removed and one added source line.
- Prove the mask accepts A72 r0p1 and another A72 revision but rejects A53 r0p1.
- Preserve the existing independent target-evidence model guard and all action
  call inventories.
- Replay the patch and reject source mutations.
- Audit all manifest profiles and build the focused and production profiles on
  Buildbox.
- Run the existing no-network 51-test four-vCPU suite and independently
  validate one exact production container.

One fresh physical boot is eligible for exactly one CPU8 trigger only after the
pretrigger frame proves READY. CPU9 remains vetoed.
