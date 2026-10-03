# One WMT query session

State: `completed-query-lifetime`; custodian: root integration agent.
[Runtime 1](results/runtime-1.json) records the exact boot, clock-guard refusal,
sealed evidence, passing A53 regression and confirmed changed-boot Gemian return.
No region-19 preparation or query occurred. The first candidate lacks DEBUG_FS
and must not be selected again. The corrected build and offline candidate now pass;
[Deployment 2](results/deployment-2.json) passed live guards, full readback and
clean shutdown. Both capture and preservation/recovery offline preparation passed
against the real receipt. Runtime 2 consumed the query lifetime successfully.

[Candidate](results/candidate.json), [offline validation](results/candidate-validation-2.json),
[tool validation](results/tooling-validation.json) and [runtime protocol](RUNTIME_PROTOCOL.md)
freeze the inputs, admitted effects, prerequisite checks and finite budgets.

## Completed owner action and result

The owner started the corrected boot2 image with the console on. [Runtime 2](results/runtime-2.json)
records one matched 16-byte default WMT response, two IRQ entries and retained
clocks. Region-19 preparation, complete sealed log, A53 regression and reviewed
changed-boot Gemian recovery passed. This lifetime is retired; do not repeat it.
No further physical selection is requested for this image. Full-mode negotiation,
ROM patch transfer, RF calibration and Wi-Fi reception remain unproved.

## Historical custodian execution

Confirm the exact release `7.1.3-gemini-a53-wmt-query` and a mainline boot identity
changed from the Gemian deployment predecessor. Require the local direct USB
route before one authenticated identity/capture connection. Recheck active
UART0 console/driver/runtime state and positive retained AP-DMA clock votes;
missing observations stop before any trigger. Preserve two equal private
512-KiB preimages, perform one admitted region-19 preparation and verify its
clear/suffix/remap/policy result, then issue one default query. No WLAN start,
ROM patch, calibration, PA-rail transition or RF scan is selected.

A unique matched 16-byte response with successful trigger transport, retained
clocks and 1–31 IRQ entries establishes this exchange. A refusal, malformed or
extra response, timeout or 32-entry terminal retires the lifetime without retry.
Preserve the complete log and private evidence, run the existing bounded A53
regression and reviewed native recovery, and verify a changed known-good Gemian
boot. Run preservation/recovery even after a failed capture; a missing required
identity or evidence blocks that recovery action instead of selecting an alternate.

Successful transport permits preparation of common initialization, not an
immediate scan or a working-Wi-Fi claim. Failure directs BTIF/STP diagnosis.
Record the exact runtime and recovery result before another candidate selection.
