# One pre-patch chip-reply capture lifetime

Status: [guarded deployment verified](results/deployment-1.json); owner physical
boot2 selection and runtime capture pending.

## Hypothesis and decision

The installed ROM review found inconsistent inner register-read event lengths
and unchecked ROM-read returns. One mandatory chip-ID request before negotiation
will measure the actual reply encoding needed for a checked common-init owner.
This lifetime accepts no identity and selects no firmware. An attributable raw
reply permits private encoding review and preparation of a strict validator.
No reply, partial TX, overflow or unexpected status requires diagnosis from the
retained evidence; none authorizes another trigger or identical boot.

The [candidate](results/candidate.json) uses kernel inputs `8956fbc1`, release
`7.1.3-gemini-a53-wmt-identity-capture`, padded boot2 SHA-256
`7e7134923871220062c55ff652754aac5f7ae842c57d4aaa6dedce2ced5dcd69`, and
manifest SHA-256 `47bfd8b8e2ba75097e1b5ee676e1b50e3bc484c6aff84df9b3dcd1a1240b9422`.
Two independent constructions are byte-identical across all seven members.
The composed DTB passes the selected schema; the build/schema receipts cover
the compiled source and separate package DTB. Private firmware, calibration and
all RAM-root members except the init release gate are inherited unchanged.

## Admission and inherited effects

Root is the sole device custodian. Require fresh live Gemian identity, the
reviewed guarded boot2 installer and its full readback receipt, then clean
shutdown and owner physical boot2 selection. The installer accepts only the
previous negotiated padded digest
`ed4503ebf70a41a024bda42f4cb4b1244013bec6dcbd8bea1df4a403dc4ef9f2`
or an already matching new candidate. Resolve logical boot2 from live GPT and
apply the reviewed device guard twice; verify inactive, unmounted, non-root,
exact size, writable state and stable power. Use the verified project backup.
No automatic reboot, alternate partition or fresh backup is selected.

Before any runtime trigger, require the exact mainline release and changed
boot identity, direct USB route, UART0 console argument and enabled console,
bound MediaTek UART0 driver, active runtime status and positive AP-DMA CCF
prepare/enable counters. One read-only debugfs mount is admitted during
identification if needed. No console close, unbind, suspend, clock policy
change, clock-summary walk or concurrent diagnostic is admitted through sealing.

Preserve two equal complete 512-KiB region-19 preimages. Execute the sole existing
WMT memory preparation, verifying the 351232-byte zero prefix, unchanged suffix,
exact remap/policy and five records with CONN held off. The capture trigger
rechecks inherited domain/rail/reset/resource gates, consumes the deferred-start
attempt, acquires the shared CONSYS mutex and uses the reviewed fresh power/reset
release and BTIF setup. The [initial setup effects](../2026-10-03-mt6797-wmt-default-query/RUNTIME_PROTOCOL.md#exact-effects-and-budgets)
and [clock admission](../2026-10-03-mt6797-wmt-default-query/results/clock-admission.json)
apply unchanged to setup only, including channel-local DMA_EN observation and
its admitted possible timeout acknowledgement. No packet-DMA start, descriptor,
global status or unrelated channel observation is added.

## Capture limits and failure lifetime

The sole root trigger is
`/sys/bus/platform/devices/10001340.consys/wmt_identity_capture`.
It runs directly after setup; no default query or mode negotiation precedes it.
WLAN is disabled and the query-only continuation guard excludes HIF, EMI-set/copy,
WLAN firmware START and scan. No HW/ROM read, patch, DLM write, MCU-clock sequence,
PA vote, RF calibration or radio operation is admitted.

The [capture leaf](../2026-10-03-mt6797-wifi-audit/IDENTITY_CAPTURE.md) permits one
26-byte mandatory-STP chip read, at most 32 RBR bytes, 64 services including the
initial kick and eight RX bytes per service, clipped by one 500-ms deadline.
It requires empty initial FIFOs, uses normal-bank TX-room/empty accounting and
refuses early RX, stale data, unexpected causes or exceeded budgets. One
exclusive IRQ registration uses NO_AUTOEN, source masking, CPU IRQ retirement,
synchronization and free. Retain power/clocks after every uncertain effect.
No flush, repair, reset, reseed or retry follows. Framework/scheduler latency
is not claimed to have a hard real-time bound.

Ordinary capture expiry returns `-ETIMEDOUT`, including after receiving a reply.
The host makes one attempt with a 30-second observation limit, retains process,
stdout/stderr and raw log, and reports the nonzero sysfs write status. It installs
a restoration trap before remount, verifies read-only restoration and unchanged
boot identity, and separately checks the kernel terminal and exact contiguous
TX/RX dumps. An unexpected write status is preserved for diagnosis. The
classifier accounts for bytes and bounds but accepts no reply status, inner
length, chip identity or ROM applicability. Timeout is never accepted identity.

## Preservation and recovery

After every capture outcome, run `passive-host.py` for complete zero-through-seal
kernel-log preservation, established bounded A53 regression and reviewed native
mainline-to-Gemian recovery. Classification runs after preservation/recovery and
cannot bypass them. Verify live identity and recovery-tool identity first;
preserve unique evidence and confirm a changed known-good Gemian boot afterward.
Missing prerequisites defer recovery; they do not authorize another path.
A host timeout is not permission to repeat a trigger or restart a capture.

Keep raw wire bytes, region captures, firmware, calibration and private RAM root
ignored and restricted. Publish only sanitized counts, decisions, checksums,
regression and recovery receipts. Working Wi-Fi still requires checked common
initialization, management reception, association and traffic.
