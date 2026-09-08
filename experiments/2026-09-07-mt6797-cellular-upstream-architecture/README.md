# Experiment: MT6797 cellular current-upstream architecture

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-07-mt6797-cellular-upstream-architecture` |
| Status | accepted exact stop; no implementation admitted |
| Subsystem | MT6797 modem, CCCI, CLDMA, CCIF, WWAN and remoteproc |
| Device variant | Gemini PDA; no device access in this experiment |
| Date | 2026-09-07 |
| Investigator | Sol Medium cross-file source review; Astra Medium acceptance review |

## Decision

Current public Linux has a reusable upper interface in the WWAN core, but no
matching lower MT6797 transport. The current `t7xx` driver is for a PCIe T7xx
modem: its probe, BAR mapping, MSI-X interrupts, address-translation windows,
power management, MHCCIF state machine and CLDMA implementation all depend on
that PCIe device. Its network path uses DPMAIF. Those dependencies do not match
the frozen MT6797 evidence for APB-mapped CLDMA/CCIF, platform clocks,
bootloader-supplied reservations and EMI-MPU/remap ownership.

`rpmsg_wwan_ctrl` is a useful example of adapting an already-working lower
endpoint to a WWAN port. It is not itself an MT6797 transport: it requires a
real RPMsg device and endpoint, neither of which the frozen MT6797 inputs
establish. MediaTek's current SCP remoteproc driver is also not a match. Its
binding and match table cover MT8183, MT8186, MT8188, MT8192 and MT8195 SCPs,
not an MT6797 cellular modem, and current `mt6797.dtsi` has no modem,
remoteproc, CCCI, CLDMA or CCIF node.

The only implementation-independent reuse decision is therefore:

- use the WWAN core's port and netdev registration interfaces above a future
  proved MT6797 transport;
- keep CCCI channel selection, framing validation, queues, DMA, interrupts,
  firmware state and reset/error recovery below that boundary; and
- do not reuse `t7xx`, `rpmsg_wwan_ctrl` or `mtk_scp` as the lower transport by
  changing a compatible, bus wrapper or structure name.

Exact revisions, file hashes, next-tree comparisons and the normalized
decision are in [the source review](results/source-review.json). The bounded
scope is in [the work item](WORK_ITEM.md).

## Transport comparison

| Candidate | What current public source proves | MT6797 comparison | Decision |
| --- | --- | --- | --- |
| WWAN core | A transport can create typed ports, receive packets, apply TX flow control and register a WWAN netdev | Independent of the modem bus and descriptor format | Reuse above a new lower transport |
| `rpmsg_wwan_ctrl` | A real RPMsg endpoint can be adapted to one WWAN control port | No MT6797 modem remoteproc/RPMsg endpoint or service identity is established | Pattern only; not a transport match |
| `t7xx` control ports | Creates WWAN ports over a T7xx port proxy and a 16-byte CCCI-named header | Header width and third-word channel/sequence/assert layout resemble the frozen MT6797 header; first, second and fourth-word semantics and channel identities were not established as compatible | Do not share the framing implementation yet |
| `t7xx` CLDMA | PCI-device-owned DMA rings using a 24-byte GPD with separate 32-bit high and low address words | Frozen MT6797 contract has packed 16-byte TGPD/RGPD/TBD/RBD shapes and 36-bit address high nibbles in metadata | Descriptor and DMA mismatch |
| `t7xx` MHCCIF/FSM | T7xx-specific PCIe modem handshake, PM and port enumeration | MT6797 CCIF state, watchdog, boot and exception sequencing remain separately unproved | State-machine mismatch |
| `t7xx` netdev | WWAN netdev whose data path submits through DPMAIF | Frozen MT6797 path is CLDMA/CCIF and has a private channel/queue table | Reuse the generic WWAN netdev shape only |
| MediaTek SCP remoteproc | Loads and controls supported Cortex-M4 SCP instances and can host RPMsg children | No supported compatible or evidence that the MT6797 modem is this SCP contract | Not a modem owner |

The CCCI resemblance is deliberately narrow. Both reviewed shapes occupy four
32-bit words, and `t7xx` places channel, 15-bit sequence and assert in its third
word. That observation does not prove packet-length/data semantics, endianness
at the MT6797 boundary, channel numbers, handshake messages, exception
behavior, or safe sharing of code. A common framing helper would be useful only
after those items are established from independently redistributable evidence.

## Ownership and dependency map

| Boundary | Required owner | Evidence required before code can own it |
| --- | --- | --- |
| Firmware identity and load | Future MT6797 modem state owner, using the standard firmware loader where applicable | Exact image selection, authentication/placement responsibility, load addresses, boot entry and shutdown contract; firmware redistribution remains a separate rights question |
| Reserved modem and shared memory | Boot/firmware reservation provider plus one kernel modem owner | Source-pinned placement, size, feature-set layout, `no-map` semantics and lifetime; no fixed address inferred from the July offsets |
| EMI MPU and remap | Platform protection/remap provider coordinated with secure and boot firmware | Who may program or preserve each region, 32 MiB remap behavior, error rollback and final release conditions |
| Power, clocks, reset and watchdog | One platform modem state machine over the established providers | Exact clock/reset ordering, watchdog acknowledgement, warm/cold boot distinctions, failure retention and removal/shutdown behavior |
| CCIF | MT6797 transport | Register layout, IRQ ownership, SRAM/runtime exchange, busy-queue flow control, ordering and crash/exception transitions |
| CLDMA descriptors and queues | MT6797 transport using the DMA API | Exact descriptor bit semantics, queue roles, DMA mask/address encoding, cache coherency, barriers, completion/idle witness, unmap and error recovery |
| CCCI framing and channels | MT6797 transport | Word semantics, byte order, negotiated header/layout versions, channel/ACK mapping and maximum lengths |
| User-facing control/data | WWAN core consumers after the lower contract works | Map only independently verified services to standard WWAN port types and netdevs; do not reproduce the private vendor character/ioctl ABI |

These dependencies are one joined state machine. A disabled platform driver or
binding is not yet a useful first patch: naming registers, memory regions,
interrupts, clocks or resets before their ownership and sequencing are proved
would freeze guesses without a safe caller. A generic CCCI helper would likewise
be unused scaffolding while the shared framing subset is unproved.

## Exact stop and discriminator

The follow-up [memory handoff audit](MEMORY_HANDOFF.md) resolves the host-side
branching and corrects the historical CCIF-tail identity. It finds that loader
readiness still permits shared-remap and staged MPU writes; the selected boot,
secure-side acceptance and region-release contract remain unjoined.

The later [Gemian handoff observation](GEMIAN_HANDOFF.md) joins one actual boot
to its v2 loader metadata, image-header report and reservation map. It leaves
the exact loaded-image digest, an extra reserved tail, secure MPU acceptance
and release authority unresolved; the implementation stop remains.

No kernel, binding, configuration or patch topic is admitted by this review.
The smallest safe output at the current boundary is this source-pinned
architecture record.

The eventual implementation gate is an independently redistributable,
source-pinned MT6797 MD1 specification that joins all of the following in one
internally consistent lifecycle:

1. firmware selection, bootloader reservations and image placement;
2. EMI-MPU and remap ownership;
3. power, clocks, reset and watchdog sequencing;
4. CCIF boot, normal, exception and shutdown states;
5. CLDMA descriptor bits, address width, DMA/cache/barrier rules and positive
   idle/completion witnesses; and
6. CCCI framing, channel/queue mapping and orderly/crash teardown.

The single next discriminator is narrower: perform a source-pinned MD1
reservation-and-protection handoff audit. It must join the selected boot
configuration to the exact modem image and shared-memory regions, active
feature layout, AP and modem address views, remap and EMI-MPU programming
authority, and the owner and release condition for each lifetime. Every link
needs attributable source evidence; names or offsets alone are insufficient.

If any attribution is missing or contradictory, retain the exact stop. The
audit admits no mapping, binding or platform driver, and it does not authorize
a probe, firmware load, reset, radio action or device test. CLDMA queues and
DMA completion, CCCI framing and channel mapping, and the full power/CCIF boot,
orderly-shutdown and crash-teardown state machine remain later gates. Once the
later framing gate proves a common 16-byte subset and real callers exist,
reassess a small CCCI helper.

## Upstream route and removal condition

A future real driver would span several review paths: Devicetree and ARM/
MediaTek for a platform binding and resource ownership; remoteproc only if the
proved firmware lifecycle actually fits that framework; netdev/WWAN for
control ports and data devices. `t7xx` maintainers are useful reviewers for
CCCI and CLDMA overlap, not presumed owners of MT6797 platform hardware.

No local kernel patch exists, so there is no patch-removal condition today. If
a temporary local transport is later justified, removal requires an accepted
upstream equivalent covering the same proved hardware identity, transport and
lifetime contract—not merely an upstream driver with CCCI or CLDMA in its
name. No author identity, DCO certification, maintainer agreement or
submission readiness is claimed.

## Validation and limits

This was an offline, read-only source audit at the exact public revisions in
the JSON receipt. Selected WWAN files were byte-identical between mainline and
`net-next`; selected MediaTek SCP files were byte-identical between mainline
and the remoteproc development refs. A bounded lore review confirmed the
public `t7xx` series describes PCIe, MHCCIF and its own modem state machine; no
exact public MT6797 CCCI/CLDMA submission appeared in the bounded subject
queries. That negative search is not an exhaustive proof that no discussion
has ever existed.

No Linux tree was retained. No build, VM, private source or capture, firmware,
device, modem node, shared-memory access, reset, transmission, upstream contact
or hardware-support claim occurred. A build would not resolve the missing
protocol and ownership evidence.

Review-ready UTC: `2026-09-07T20:14:05Z`.

Accepted UTC: `2026-09-07T20:15:58Z`, after one documentation repair that
separated the immediate reservation/protection discriminator from the eventual
full lifecycle gate. The transport-reuse decision was unchanged.
