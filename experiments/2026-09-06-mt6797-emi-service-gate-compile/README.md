# MT6797 EMI service-gate compile proposal

This experiment adds a separately compiled private `emi-service-gate.o`. The
gate copies the accepted descriptive resource layout and an injected callback
descriptor, validates the copied region 18 WLAN interval through the accepted
EMI ABI helper, and enforces one generation-bound attempt for sequential or
externally serialized caller calls; it makes no concurrency claim. It preserves
the raw 64-bit callback result and decoded signed low word. The callback is
only a compile/test seam: there is no SMC instruction, runtime caller, policy,
reservation acquisition, registration, mapping, firmware, DMA, IRQ, power or
reset effect.

The generated local proposal is
[`0011-wifi-mediatek-compile-emi-service-gate.patch`](0011-wifi-mediatek-compile-emi-service-gate.patch).
Run `python3 -B scripts/verify.py` to reproduce the patch, strict host fixture,
linkage and static-boundary evidence. Checkpatch is pending the integrator's
pinned Linux/Buildbox replay; this verifier performs no network access. The fixture covers valid
generation boundaries, all enumerated layout and exact-alias refusals,
selector-CLEAR representability, cleared outputs, source descriptor mutation,
permissions, callback ordering and arguments, exactly-once calls, every
declared and unknown signed result class, raw high words, terminal repeat
refusal, and the preserved active `image_binding_begin()` refusal.

The predecessor series, design evidence and the pinned Checkpatch identity are
recorded in `inputs.json`.
Canonical-series replay, profile/manifest integration and Buildbox compilation
remain integrator-owned. No device or hardware support claim follows from this
compile experiment. The copied layout is descriptive; the real provider must
still establish reservation lifetime, selector stability, external-writer
exclusion, serialization, deployed SMC compatibility, permission policy,
visibility and recovery.
