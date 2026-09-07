# Experiment: MT6797 HIF upstream architecture

## Record

| Field | Value |
| --- | --- |
| ID | `2026-09-07-mt6797-hif-upstream-architecture` |
| Status | accepted design stop; implementation refused |
| Subsystem | MediaTek connectivity, wireless HIF and firmware loading |
| Device variant | Existing named Gemini PDA; no device access |
| Date | 2026-09-07 |
| Investigator | Sol Medium cross-file design; accepted after Astra Medium shared-hardware review |

## Verdict

None of proposal patches `0001` through `0012` is ready to become an upstream
series. The compiled parser and private helper concepts do not yet have a safe,
useful kernel caller. Publishing them alone would create unused scaffolding;
activating them would cross unproved CONSYS power/coexistence, HIF AP-DMA
address/idle, reserved-EMI secure-service, firmware-stop and runtime WLAN
contracts.

The exact review boundary is in [the work item](WORK_ITEM.md). Current Linux,
schema and frozen project identities are in
[the source receipt](results/source-review.json). This record changes no kernel
patch, configuration, manifest, series, roadmap or hardware-support claim.

## Driver reuse decision

| Candidate | Identity and transport | Resource/firmware contract | Decision |
| --- | --- | --- | --- |
| `mt76` MT7628/MT7603 platform WMAC | Explicit MT7628/MT7603 identities; direct MMIO and native mt76 DMA rings | Platform MMIO/IRQ and chip-specific firmware | Mismatch. A similar platform shape is not MT6797 compatibility. |
| `mt76` SDIO | Supported chips behind a real `struct sdio_func` | MMC/SDIO host and function lifetime | Mismatch. MT6797 exposes an AHB command aperture with CMD53-like arithmetic, not an enumerated SDIO function. |
| `mt76` MT7981/MT7986 CONNINFRA | Explicit MT7981/MT7986 identity; direct MMIO/WFDMA/RF-SPI | Multiple MMIO/IRQs, reset, clocks and WMCU reservation | Mismatch in identity, register map, DMA, interrupts and firmware. |
| Mainline MediaTek UART APDMA | UART VFF/ring controller with one address plus `ADDR2` | DMAengine provider and per-channel IRQ | Mismatch. Offset similarity does not establish the MT6797 one-shot source/destination, polling or forced-bit contract. |
| New MT6797 WLAN driver | Retained source relationship includes `WCIR 0x0279 -> 0x6797`; attributable mainline HIF behavior remains absent | Shared CONSYS owner, HIF MMIO/IRQ, exact AP-DMA channel, MTKE/WMT firmware boundary | Required unless later runtime MAC evidence proves reuse of a narrower mt76 core. It must not claim an mt76 compatible. |

Current mainline contains no CONSYS/CONNINFRA provider below
`drivers/soc/mediatek`, only `mt76` and `mt7601u` below MediaTek wireless, and
HSDMA, CQDMA and UART APDMA below MediaTek DMA. No public MT6797 HIF submission
was found in the inspected current trees and public search. The kernel mailing
list search endpoint was bot-blocked, so the negative public-overlap search is
not claimed exhaustive.

## Frozen ownership boundary

| Resource | Kernel owner | Consumer boundary and lifetime |
| --- | --- | --- |
| Physical CONSYS power, clocks, regulators and resets | Existing generic providers retain physical authority; a new MediaTek CONSYS coordinator aggregates leases | WLAN/BT/GNSS/WMT receive opaque generation-bound epochs. Activation waits for proved MT6797 sequencing and cross-client exclusion. |
| Shared reset, remap and protection | CONSYS coordinator serializes masked effects | No client gets a reset handle, raw syscon pointer or permission word. Uncertain effects enter provider-owned `FAULT_HELD`. |
| HIF MMIO and SPI 283 host IRQ | New MT6797 WLAN platform driver | Map/request only inside an active epoch; mask, drain and join IRQ work before release. |
| Exact HIF AP-DMA channel register window beginning at `0x11000080`, extent `0x80` | Eventually the WLAN HIF driver, inline; no generic DMAengine provider is inferred | HIF transfers only. No activation or full-block reset until address encoding and positive idle are known. |
| Streaming packet buffers | WLAN HIF, mapped for the actual AP-DMA master | Retain buffer and mapping after uncertain completion. Reserved CONSYS EMI is not a packet pool. |
| Reserved 2 MiB EMI | Generic reserved memory excludes it from normal RAM; CONSYS owns the resolved resource, mapping and subrange leases | WLAN receives typed copy/seal operations, never a base address. Preserve WLAN's first 512 KiB, WMT's second 512 KiB and the unknown remainder separately. |
| WLAN EMI extent | CONSYS owns writable/seal policy; WLAN owns its immutable source and completion ledger | Confined copies are generation-bound; release waits for proof that firmware cannot fetch and final protection is established. |
| Common WMT extent and lifecycle | CONSYS/WMT owner | BT/GNSS/WLAN cannot repurpose it. Preserve coexistence and diagnostics ownership. |
| WLAN firmware and protocol | WLAN owns `request_firmware()` buffer, MTKE plan, HIF protocol and readiness; CONSYS owns common WMT lifecycle | START follows ordinary transfers and provider-confirmed EMI sealing. Readiness is distinct from cfg80211/mac80211 registration. |

A platform driver's `.remove()` cannot fail. Consumer devres therefore cannot
implement the earlier idea of retaining callable WLAN objects after an uncertain
remove. Provider-owned power claims, shared-effect mappings and fault state
would have to outlive the consumer, while every WLAN callback and code path is
quiescent before detach. That division is a requirement, not a solved transfer:
ownership of a retained packet buffer, its DMA mapping device and domain, the
inline channel claim, outstanding operations, provider code lifetime,
provider removal/unbind and final reclamation all remain unresolved. This
supersedes the predecessor proposal's callable-consumer retention model;
moving state into a provider alone does not establish safe release.
Built-in-only or disabled unbind would defer that missing proof, not solve the
upstream lifetime contract.

Probe failure must unwind without publishing a client epoch or releasing any
buffer whose DMA completion is uncertain. Suspend must not power down, remap,
seal or release a shared generation until every client has quiesced and the
channel, firmware and coexistence owners provide positive stop witnesses.
It cannot report success without that quiescence/retention contract.
Provider remove/unbind is refused while any epoch, mapping, effect or
`FAULT_HELD` state survives. No current proposal proves those conditions, so
probe activation, suspend/resume and either provider or consumer removal remain
outside the admitted implementation surface.

| Lifecycle edge | Required positive condition | Unresolved retention/owner |
| --- | --- | --- |
| Failed probe after an effect | Client is unpublished and all work is joined; completion or safe fault retention is positive | Buffer, DMA mapping device/domain, channel claim, operation and provider code lifetime |
| WLAN consumer detach | Callbacks are quiescent before the non-failable remove returns | Every effect-bearing object has a proved provider-held lifetime and final reclamation path |
| CONSYS provider detach | No epoch, mapping, operation, protection effect or `FAULT_HELD` state survives | Provider removal remains refused until that witness exists |
| Suspend | All clients, channel and firmware are positively stopped without violating coexistence | Shared generation and retained mappings/effects must remain held if any witness is absent; success is refused |

## Binding and maintainer route

- Use the generic dynamic reserved-memory schema with `size`, `alignment`,
  `alloc-ranges` and `no-map`; do not use `shared-dma-pool` or a WLAN allocator.
- A future `mediatek,mt6797-consys.yaml` belongs below the MediaTek SoC
  bindings. It may describe only semantically confirmed register windows, the
  BGF/WDT interrupts, clocks/power domain, supplies and one `memory-region`.
  Route the binding through DT and ARM/MediaTek SoC maintainers and the provider
  through the MediaTek SoC tree.
- A distinct future `mediatek,mt6797-wifi.yaml` may describe HIF MMIO, host IRQ
  and a CONSYS phandle. Add a named `pdma` resource only after exclusivity and
  address encoding are proved. Route it through DT, networking,
  `linux-wireless` and ARM/MediaTek; mt76 maintainers are overlap reviewers, not
  presumed owners. A real new-driver maintainer must be nominated.
- Define no DMA binding now. Reopen that decision only if evidence proves a
  reusable controller rather than an inline HIF channel.
- Firmware names belong in compatible data and the standard firmware loader,
  not a vendor lifecycle ioctl.

## Helper disposition

The bounded MTKE structural/CRC parser, immutable generation-bound image plan,
CMD53-like arithmetic, submitted-versus-completed state, first-error retention,
CONFIG acknowledgement, START/readiness separation, masked-remap arithmetic,
resource validation and transfer ledgers are upstream-shaped concepts. They
must become private implementation details of real provider/WLAN callers.

The standalone caller-MMIO HIF allocator and injected scalar-I/O callbacks,
mutable public plan APIs, consumer-owned effect lifetime, custom raw DT parser,
unproved EMI secure-call ABI, externally callable remap/layout APIs, detached
ordinary-transfer batch and generic APDMA façade are experiment-only. They need
replacement rather than promotion.

## Dependency plan, not a submission series

1. Add proved MT6797 CONN domain data and power-off/error unwind.
2. Add the CONSYS binding and a passive provider with real shared ownership.
3. Add the WLAN binding/client; its standard firmware request calls the private
   parser and immutable planner.
4. Add provider activation and a PIO HIF loader with real state-machine callers.
5. Add EMI copy/seal plus ordinary-transfer/START execution in the same epoch.
6. Add the runtime MAC/control/data path and mac80211 registration.
7. Add optional inline HIF AP-DMA acceleration only after address and idle proof.

Steps 1 through 3 alone would still be unused scaffolding. This ordering is a
future dependency map, not authorization to implement or submit any step.

## Next discriminating evidence

With a separately admitted protocol and the single device custodian, capture
one already-successful, non-replayed known-good firmware-load and shutdown cycle
that records:

- the DMA API address for one host buffer and the programmed source,
  destination and `ADDR2` values;
- the HIF endpoint translation plus `EN`/`INT_FLAG` progression;
- a positive channel-idle witness before unmap;
- firmware-stop evidence and the coherent CONSYS OFF sequence.

The runtime WLAN MCU command/event and TX/RX descriptor contract also remains
unresolved, so a loader-only driver still has no cfg80211/mac80211 endpoint.
That limitation is not selected as a concurrent next action by this record.
The single selected normal-cycle capture can discriminate the address, idle and
coherent-off contract; it cannot by itself prove failed-operation retention or
teardown.

## Safety and validation

This was read-only current-source design work. Exact refs and all source,
schema, project-input and proposal hashes were independently recomputed. No
Linux tree was retained. No build was repeated because kernel inputs did not
change. No VM, private capture, firmware/radio action, device access, candidate,
deployment or upstream contact occurred. No implementation, modern
`Tested-by`, author identity, DCO sign-off or maintainer agreement follows.

The first specialist review accepted the design stop but rejected ambiguous
AP-DMA range notation and incomplete late-lifetime ownership. One
documentation-only repair pinned the platform-driver removal contract,
superseded callable-consumer retention and added explicit failed-probe,
consumer-detach, provider-detach and suspend refusal boundaries. Post-repair
review independently verified the two added platform sources and accepted the
packet at `2026-09-07T18:22:39Z`. No technical effect or implementation was
admitted by the repair.
