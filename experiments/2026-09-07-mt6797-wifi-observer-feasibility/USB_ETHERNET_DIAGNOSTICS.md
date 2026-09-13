# Observe the native USB connection decisions

The [corrected physical test](USB_ETHERNET_CONNECT.md#physical-test-result)
reached its TCP listener but did not enumerate USB. Its former readiness-loop
messages did not recur. The first retained kernel timestamp is 1.603362 seconds,
so printing more early messages alone would risk losing the evidence again.

The [diagnostic patch](patches/usb-ethernet-diagnostics/0001-usb-retain-bounded-native-export-connection-decisions.patch)
adds cumulative decision bits and one packed cable sample to the native MU3D
driver. It prints one summary from the existing `musb_shutdown()` entry, before
that function's hardware operations. The ordinary return path reached this
shutdown in the preceding test. The patch does not add a shutdown, work item,
hardware accessor, role/charger override, radio operation or userspace control.
All original statements and decisions remain unchanged. State updates and
output require the existing recovery diagnostic, Ethernet enabled and Android
disabled. Canonical upstream profiles and board configuration are unchanged.

The three touched source files retain their GPL version 2 license headers.
This is assistant-generated native experiment code without DCO certification,
not an upstream submission or a maintained driver interface. The
[source receipt](results/usb-ethernet-diagnostics.json) pins the exact parent
and changed files, format-patch and ordered 49-patch native manifest. The first
48 patches are unchanged. Exact inverse comparison, application against the
prepared parent and strict Linux 7.1.3 Checkpatch pass; sign-off checking is
disabled for this explicitly non-certifying archive. Full compilation and the
linked report inspection now pass at `895ecb5c16326f4e57970caed6ff2404edae2acb`.
All eleven remote and fetched package files verify; configuration is identical
to the preceding corrected candidate. The inherited 69 section mismatches and
native compiler's `-w` limitation remain.

The compiled shutdown's first call is the report. Its 72-byte body tests and
sets bit 15, returns without printing when already set, and otherwise reaches
one printk call. It calls no hardware accessor. The preceding direct callee
sets and non-printk call-site counts remain present. Linear instruction order
and printk site counts changed with compiler block layout/sharing; they are
not runtime order or binary control-flow equivalence checks. The exact source
inverse comparison separately preserves every original statement.

## Observation and bounds

The one possible line is `wifi-usb-v1 paths=hhhh cable=hhhhhhhh`. A single
atomic test-and-set consumes the report bit before printing, including when
multiple callers reach shutdown. No reset or second report exists. Repeated
native work only sets existing bits or replaces the single atomic cable word;
it allocates no memory and produces no per-callback log flood. The diagnostic
does not write the retained capture slot directly. Its normal printk follows
the existing console path.

`paths` is a cumulative bit mask, not an ordered trace or call count:

| Bit | Existing branch reached |
| --- | --- |
| 0 | Connection work entered |
| 1 | Readiness was false; existing delayed retry branch |
| 2 | Readiness was true |
| 3 | Host role branch |
| 4 | Device role path reached cable evaluation |
| 5 | Connection work received cable-connected true |
| 6 | Connection work received cable-connected false |
| 7 / 8 | Immediately before / after the existing `musb_start()` call |
| 9 / 10 | Immediately before / after the existing `musb_stop()` call |
| 11 | Cable result required neither start nor stop |
| 12 | UART mode branch |
| 13 | Existing power-off charging shortcut |
| 14 | Existing forced-cable branch |
| 15 | First report consumed |

The candidate configuration has FPGA bypass and USB compliance disabled, and
the UART switch, xHCI role check and power-off charging branch enabled. Those
identities must remain fixed for this interpretation.

`cable=ffffffff` means no ordinary cable evaluation reached its final sample.
Otherwise bits 0–7 hold the existing charger-type value, bit 8 the existing
VBUS result, bit 9 the resulting connected boolean, and bits 16–23 an ordinary
memory sample of `cable_mode`. Other bits are zero. In this pinned source,
charger types 0/1/2 mean unknown/standard host/charging host, and cable modes
0/1/2 mean charging only/normal/host only. The existing forced-cable path
supplies synthetic host/VBUS values; bit 14 records that branch without
enabling it. The power-off charging early return sets bit 13 and does not
replace the packed word.

Atomic storage prevents a torn cable word. It does not join the word to the
path-mask snapshot, identify the calling context, or freeze other workers.
`usb_cable_connected()` also has callers outside connection work. A concurrent
mode change can make the recorded mode differ from the preceding policy reads.
Both true and false path bits can accumulate. A returned controller start is
not proof of USB enumeration. No physical cable defect follows from a false
software cable result.

## Next physical session

Hypothesis: one of the existing readiness, UART, host-role or cable decisions
prevents the corrected diagnostic from exposing its USB Ethernet function.
The unique new observation is the late summary of decisions already made.
Keep the preceding export runtime, USB fragment, CPU policy and finite budgets:
one immutable snapshot, one 60-second exchange, pre-armed host collection,
normal return, verified changed-boot Gemian and one preserved console read.
New build, session, package and guarded deployment identities must be bound
before the owner selects boot2. This document alone does not select a device
session or authorize a repeat of the consumed candidate.

Require exactly one well-formed summary after this candidate boot and cycle's
return marker and before normal restart. A missing, earlier, malformed or
duplicate summary is inconclusive. A remove/error-path shutdown can consume
the report before normal return; absence cannot be treated as all-zero state.

- Readiness false without true: inspect readiness ownership using this positive
  branch evidence before changing the connection again.
- UART or host branch: inspect its existing selection inputs and ownership;
  do not force a role from the branch label alone.
- Device path with cable false: use the recorded charger/VBUS/mode evidence to
  choose the next discriminator, respecting the independent-snapshot limits.
- Cable true and controller start returned, but no host enumeration: investigate
  the controller/descriptor path; do not keep changing readiness or cable policy.
- Attributed enumeration: run the unchanged bounded receiver. Only a verified
  snapshot, acknowledgement, retained preserved marker and changed-boot return
  complete export.

Preserve negative results and the original private evidence. Do not clear the
capture, add a radio cycle or repeat unchanged inputs on a timeout.

## Selected session

The [candidate receipt](results/usb-ethernet-diagnostics-candidate.json) binds
the complete build, unchanged DT, 723-member filesystem and boot2 container.
Only session metadata changed in the filesystem. Independent reassembly,
seventeen container mutations and six input refusals pass. The runtime and
startup code retain their prior ARM64 validation.

The [session receipt](results/usb-ethernet-diagnostics-session.json) selects
cycle `ba533dcc-3368-4cb6-aff1-fdc31bf9f4b1` from verified returned Gemian boot
`258eff5c-a742-4379-89e7-60e885eaf797`. The primary integration coordinator
holds sole device custody. The installer retains the reviewed device guard
and all live identity, GPT, inactive/non-root, power, size and full-readback
checks. Exactly five identity/destination substitutions distinguish it from
its parent; inverse comparison, Bash syntax and ShellCheck pass. Installation
must confirm the expected Gemian boot and finish with clean shutdown. The
owner then selects boot2 physically after both collectors are armed.

The [deployment receipt](results/usb-ethernet-diagnostics-deployment.json) now
confirms the expected live Gemian boot, inactive GPT-selected boot2, matching
full readback and clean shutdown. The previous boot's console was already
preserved. No physical selection has yet been reported for this diagnostic.
Its runtime result is pending; installation does not establish USB support.

The return collector changes only the preceding boot UUID; its authenticated
changed-boot checks and one console-read budget are unchanged. USB attribution,
receiver and route helpers are byte-identical. Host configuration changes,
radio requests and capture clears remain zero. The snapshot and log remain
private; only validated identities and sanitized observations are publishable.

## First collection window

Both collectors were observed live and armed before the owner handoff, then
completed their 600-second windows. The
[window result](results/usb-ethernet-diagnostics-window-1.json) records no USB
inventory change, attributed gadget, receiver invocation or verified changed-boot
Gemian return. No console or USB decision summary was received. No physical-start
report arrived for this diagnostic image during the window, so silence does not
establish that it booted or failed.

The installation remains verified. Both collectors are stopped; current device
state and physical selection require the owner report before fresh arming or
another device action. Do not change the candidate on this evidence. Hosted
checks for its published deployment record passed.
