# One WMT query session

State: `waiting-owner-boot`; custodian: root integration agent. One physical
selection, one region-19 preparation and one query lifetime are selected.
[Deployment](results/deployment-1.json) records the completed full readback and
clean shutdown. Tooling is published at `5cbe2110`; kernel inputs are `127166e4`.
[Candidate](results/candidate.json), [offline validation](results/candidate-validation.json),
[tool validation](results/tooling-validation.json) and [runtime protocol](RUNTIME_PROTOCOL.md)
freeze the inputs, admitted effects, prerequisite checks and finite budgets.

## Owner action

Keep the established USB cable attached. Power on and physically select boot2
using the established silver-button method during LK selection. Report when the
console is on. Expect the existing console and authenticated USB gadget; no
network credentials, scan command or keyboard test is needed. Do not repeat
boot selection if the expected console/USB does not appear; report the observed
screen so the custodian can preserve evidence and check the recovery path.
Stop on unexpected heat or power behavior under the project safety rules.

## Custodian execution

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
