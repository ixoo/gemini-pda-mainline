# Admit the first capability query after START readiness

The [stage-trace boot](../2026-09-29-mt6797-capability-trace/results/runtime-1.json)
returned `-EIO` at stage 0 before a WRPLR read or command submission. Source
inspection identifies a deterministic state mismatch: a successful
`mt6797_start_observe_ready()` moves the INIT transaction from `START_READY`
to `INIT_IDLE`, while the capability query still requires `START_READY`.
Patch 0055 changes that sole gate to require `INIT_IDLE`; it retains the
firmware-ready, one-attempt, deadline and transport guards. There is no new
radio, calibration or packet DMA action.

The [focused host test](tests/test-capability.c) exercises the actual patched
HIF source. It first runs the START state transition before each query, then
checks the existing successful exchange, all 69 injected scalar access faults,
stale queue, malformed reply and deadline. It also proves the pre-readiness
phase is refused without HIF access. The previous test had incorrectly set
`START_READY` and `firmware_ready` together, hiding the live mismatch.

The next physical boot will test whether the corrected gate admits the one
bounded command and, if submitted, whether firmware returns a valid capability
event. A failed queue, TX, reply or parser stage remains a terminal observation
for that boot. A successful capability event establishes only a command/reply
exchange; network interface, association, traffic and radio safety need
separate evidence. Preserve the complete log and A53 regression, then return
to changed-boot Gemian through the reviewed path.
