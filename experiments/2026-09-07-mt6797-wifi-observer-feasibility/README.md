# Experiment: known-good Gemian Wi-Fi observer feasibility

## Verdict

The running known-good Gemian kernel cannot provide the dynamic observation
path required by the accepted MT6797 HIF lifetime discriminator. It has
debugfs and event tracing, but its only available tracer is `nop`; kprobes,
kprobe events, function tracing, function-graph tracing and dynamic ftrace are
disabled. The corresponding live probe and function-filter interfaces are
absent even with noninteractive root privilege.

This is a capability stop, not evidence about WLAN teardown. It does not show
that firmware stopped, DMA became idle, mappings were released, programmed
addresses matched DMA API addresses, or CONSYS powered off coherently.

The bounded scope is in [the work item](WORK_ITEM.md), and the complete
sanitized chronology and coherent snapshot are in
[the result](results/observer-feasibility.json).

## Live boundary

At `2026-09-07T19:04:16Z`, the named device was still running exact Gemian
`3.18.41+` on AArch64 from `/dev/mmcblk0p29`. `wlan0` was present and `up`
under `mt-wifi`. The boot ID matched before and after the snapshot. The query
read only identity, sysfs links, mount/configuration metadata and tracer
capability; it did not read a trace buffer or change tracing state.

Five authenticated invocations occurred. The first established the known-good
OS identity. The second stopped early after a shell-quoting error while reading
mount metadata; it had already observed only WLAN presence, state and driver.
The third corrected that read and established the absent interfaces. The fourth
read configuration and privilege capability but emitted one harmless local
shell diagnostic after testing an absent filter path. The fifth coherent
snapshot repeated all decision fields with corrected quoting and stable boot
identity. No retry changed device state or exercised WLAN.

## Consequence

Do not design a live kprobe/ftrace collector for this kernel, and do not treat
static event-tracing support as an equivalent observer. The next HIF lifetime
action requires either:

1. an already retained, independently attributable successful load/shutdown
   record containing the required DMA address/programming, endpoint,
   channel-idle, firmware-stop and coherent-OFF evidence; or
2. a separately admitted non-replayed observation mechanism whose acquisition
   effects, radio action, recovery, ownership and finite budgets are reviewed
   before use.

An instrumented kernel or vendor debug interface is not selected merely because
the current standard tracing path is absent. The owner-closed retained binary
observer line remains closed.

## Safety and limits

The boot ID remained unchanged during the final coherent snapshot. No
invocation issued a probe, tracer, event, module, interface, firmware, radio,
register, power, partition, boot or reboot action. No private capture was
accessed and no sensitive device or network identity is published. This result
changes no support claim and admits no kernel implementation, candidate,
deployment or upstream submission.

Independent Astra Medium review accepted the capability stop at
`2026-09-07T19:11:51Z` after one wording repair narrowed boot-ID continuity to
the final bracketed snapshot. The review introduced no new device access or
technical claim.

## Offline follow-up

The [native source assessment](NATIVE_SOURCE_FEASIBILITY.md) identifies actual
read sites and misleading success paths for a possible compiled observer. It
leaves source/configuration attribution and experiment admission unresolved.

The [cycle-control and recovery assessment](CYCLE_CONTROL.md) records the native
request/teardown limits and a fresh read-only check of active Gemian actors.

The [native DMA hooks](DMA_HOOKS.md#native-producer-implementation) now join
software HIF bindings to DMA addresses, programming, polls and unmap boundaries.
Host access comparisons and focused native compilation pass. The hooks remain
unselected; controller integration, full kernel linking and hardware admission
are still required.

The [native firmware-stop hooks](STOP_HOOKS.md) record evaluated gates, direct
read completions and actual exit branches while preserving native effects.
They do not treat the adapter-stop return as shutdown evidence.

The [firmware file-read hooks](FIRMWARE_READ_HOOKS.md) distinguish the actual
signed read result from the native success return and published unsigned length.
They establish recorded read extents, not firmware-buffer identity or execution.

The unselected [firmware image hooks](FIRMWARE_IMAGE_HOOKS.md) carry the successful
read witness into native buffer hashing and section records; interval immutability
and full cycle admission remain unproven.

The unselected [EMI hooks](EMI_HOOKS.md) capture actual lower protection results
and native mapping/copy boundaries after the image hooks. Shared ownership,
visibility and candidate admission remain separate.

The unselected [provider OFF hooks](PROVIDER_OFF_HOOKS.md) retain actual CONN
state, protection, control and terminal condition observations. Common-owner
attribution and isolation still require their own producers and joins.

The unselected [common OFF hooks](COMMON_OFF_HOOKS.md) now bind that provider
to the synchronous common-power call and actual clock callback. The outer
ioctl/worker join and broader consumer isolation remain separate.

The unselected [operation-ownership correction](OPERATION_OWNERSHIP.md) prevents
reset completion from recycling a still-running operation or being overwritten
by later worker success. It does not establish reset/resource isolation.

The unselected [request hooks](REQUEST_CAPTURE.md) bind one native ioctl pair
to its worker completions and synchronous common OFF scope. Firmware causality,
controller integration and reset/resource isolation remain open.

The [firmware/request join](REQUEST_FIRMWARE.md) requires the recorded read and
image completion to belong to the ON worker, rejecting a successful no-load
shortcut. Submitted-byte identity and resource isolation remain unproven.

The [pre-map payload witness](TX_PAYLOAD.md) now joins the eight actual
coalescing-buffer payload digests to their DMA completions. Buffer stability
after hashing, broader consumer isolation and device admission remain open.
