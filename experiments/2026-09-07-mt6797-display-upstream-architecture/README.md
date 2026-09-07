# MT6797 display upstream architecture refresh

## Result

**Stop: no subset of patches 0028–0044 is implementation-ready as a first
upstream series.** Current mainline still lacks MT6797 display-mutex, DDP, DSI,
MIPI-TX and display-PWM support, so the recovered SoC data has not been
superseded wholesale. The problem is ordering and attributable use: the
infrastructure-only subsets have no current caller, while every subset that
adds a real output or backlight consumer crosses at least one unresolved
resource contract.

The panel path remains blocked by the named-device NT36672 versus independent
SSD2092 identity contradiction, unknown bias-controller silicon, unproved
equivalence between MMSYS `LCM_RST_B` and GPIO180, and the difference between
the inferred DRM pixel clock, the DSI host's requested lane rate, and the
retained PHY rate. The independent public implementation does not resolve
these points: at its pinned revision it calls its display work compile-only and
its MIPI-TX PLL values verification-blocked, and it uses a different documented
pipeline/panel assumption.

The most bounded route toward a useful first topic is display PWM, not the
panel or the full DRM pipeline. It is not ready today because patch 0044 changes
the common driver and schema from a mandatory `main` plus `mm` clock contract to
an optional second clock solely from the local one-handle observation. The
frozen project evidence itself says that this conflicts with a hardware-working
two-clock mainline consumer and that display-domain sequencing is unvalidated.

One next discriminator is therefore identified for a later separately admitted
acquisition protocol:

> On the named Gemini in its known-good OS, capture one bounded, attributable
> clock-and-power trace around an existing brightness transition and display
> suspend/resume. Identify the display-PWM consumer clocks, their complete
> parent ancestry and rate-source roles, every gate/domain owner that makes the
> block accessible, and the MM power-domain lifetime. Do not write PWM
> registers.

The existing single `INFRA_DISP_PWM` consumer reference does not prove a
one-clock hardware contract: its `MUX_PWM` parent, inherited enables or the MM
domain may supply the dependency represented by upstream's `mm` clock. If the
observation proves two separately owned clocks, patch 0044's common
optional-clock change is rejected and the SoC node must name both resources.
If it proves that MT6797 truly has one independent consumer clock and separately
accounts for the MM-domain lifetime, a later implementation contract may
freeze a small binding + driver data + disabled SoC-node series and pair it
with a reviewed standard `pwm-backlight` consumer/test plan. Unresolved parent,
inherited or rate-source attribution is inconclusive and preserves the current
mandatory `main` + `mm` contract and this stop.

This review does not authorize the trace, brightness transition or
suspend/resume action. The acquisition mechanism, effects, owner interaction,
finite budget and recovery must be frozen and reviewed before use; avoiding a
direct PWM register write is necessary but not sufficient admission.

This is an architecture and source-applicability result only. The Linux 7.1.3
compiles remain historical mechanical evidence, not schema validation against
the pinned current tree and not hardware support.

## Source pin and bounded overlap check

Official mainline was resolved from Torvalds' kernel.org repository at commit
`28924df2a08f440c73991b83028032c901de2ae4`. Individual files were read through
the commit-addressed `torvalds/linux` raw mirror; no Linux tree was cloned or
retained. The exact 34 official file hashes, five overlapping implementation
patch hashes, local patch hashes, input hashes, URLs, caps and absences are in
[`results/source-review.json`](results/source-review.json).

The public overlap is `bsg100/gemini-linux` commit
`e744a43f9d68cd3251dc0c9743ca41aac74853a8`. Five relevant patch files and its
one display status page were inspected. Exact-string searches found no public
mailing-list posting for the MT6797 compatibles in this packet; zero public
message pages were opened. Absence from that bounded search is not proof that no
discussion exists, and a repository publication is not maintainer acceptance.

The review used 39 current source/binding/overlap patch files plus one public
project page, within the 40-file bound, and all 17 permitted local patches. It
used no device, private capture, binary analysis, build, upstream contact, or
shared-file edit.

## Current upstream matrix

| Area | Pinned-current state | Local behavior | Verdict |
| --- | --- | --- | --- |
| MMSYS clock/syscon | `mediatek,mt6797-mmsys` is bound in the schema, DTS and `mtk-mmsys.c`, but its data contains only `clk-mt6797-mm` | patch 0031 adds 29 recovered routes and 64 resets; 0032 exposes reset/GCE cells | Adapt the recovered table to current MMSYS; do not include `LCM_RST_B` at `0x150` among the 64 reset lines |
| Display mutex | No MT6797 compatible in the inspected binding or driver and no current DTS node | 0028–0030 add the distinct 17-bit map, SOF/EOF encoding and provider | Hardware data remains useful; rebase to the current core, but hold the DTS/provider series until an actual DRM consumer is admitted |
| OVL/OVL-2L/RDMA | Current per-block schemas and drivers have no MT6797 match data | 0033–0034 add MT6797 formats, layer counts and FIFO data | Reuse the drivers; split binding/data by component and validate M4U/SMI/GCE resources with the consuming graph |
| Fixed-function DDP | Current schemas/drivers have no MT6797 match data; several generic CMDQ/data mechanisms now exist | 0035–0036 combine seven bindings, generic changes and SoC data | Reuse current AAL/CCORR/COLOR/GAMMA/DDP-component drivers; discard already-present generic portions and split the remaining SoC data |
| DRM pipeline discovery | Current `mtk_drm_drv.c` supports OF-graph path construction, but has no MT6797 MMSYS match | 0041 hard-codes one MT6797 path | The static-path patch is superseded; a future MT6797 integration must use current graph topology and a minimal SoC match record |
| DSI host | Current driver/binding have no MT6797 compatible; the local offsets match the MT8173-shaped host record | 0037–0038 add the compatible and offset data | Reuse the MediaTek DSI host; hold until the exact clock/resource contract and a PHY/output consumer are frozen |
| MIPI-TX PHY | Current common driver has MT2701/MT8173/MT8183 only | 0039 supplies a distinct MT6797 register/power/PLL implementation | Reuse the common PHY shell, but the new MT6797 data/ops are required. Hold for attributable PLL/divider/power sequencing and Astra review |
| SoC display nodes | Current `mt6797.dtsi` contains only the MMSYS clock/syscon among these display blocks | 0040 and 0042 add DSI/PHY and DDP nodes | Split by accepted providers, add current OF endpoints, and keep consumers disabled until dependencies and test ownership are admitted |
| Panel | Current NT36672E driver has one generic `novatek,nt36672e` descriptor, fixed supplies/reset sequencing, and standard `backlight` phandle support | 0043 adds a board-named descriptor and command/power data | Framework reuse is plausible only after direct identity. Hold; never send the NT36672 table to an SSD2092 or claim identity from the software-selected name |
| Bias rails | Panel-common models supplies but the inspected set contains no evidence for a generic controller at I2C `0x3e` | local panel data names `outp`/`outn`; durable evidence says TPS65132-like protocol but unknown silicon | No generic compatible. Identify silicon/electrical contract first, then route a chip-specific regulator binding/driver if no existing exact match exists |
| Display PWM/backlight | Current PWM driver and binding require `main` and `mm`; no MT6797 match. Panel framework already consumes a standard backlight phandle | 0044 makes `mm` optional, adds MT8173-shaped data and a disabled one-clock node | Hold on the clock/domain contradiction. A single consumer handle does not exclude parent, inherited or MM-domain dependencies. Keep PWM provider, standard `pwm-backlight`, and panel/backlight lifetime as separate owners |

No existing compatible may be reused by register similarity alone. The intended
reuse is of subsystem frameworks and APIs; MT6797-specific compatibles remain
appropriate where the recovered register/resource contract is distinct.

## Ownership and dependency graph

```text
MT6797 MM power domain
  +-- SMI common/larb + M4U/IOMMU mappings
  |     `-- OVL / OVL-2L / RDMA DMA clients
  +-- GCE mailbox
  |     +-- optional CMDQ access to MMSYS routes/resets
  |     +-- optional CMDQ access to display mutex
  |     `-- optional CMDQ programming of DDP components
  +-- MMSYS syscon
  |     +-- clock provider (already upstream)
  |     +-- DDP routes + 64 reset-controller lines (0031/0032)
  |     `-- LCM_RST_B at 0x150 (separate, ownership unresolved)
  +-- display mutex (0028-0030)
  `-- DRM component graph
        OVL0 -> OVL0-2L -> OVL1-2L -> COLOR0 -> CCORR -> AAL
          -> GAMMA -> OD -> DITHER -> RDMA0 -> bypassed UFOE -> DSI0
                                                          `-- MIPI-TX PHY
                                                                `-- panel endpoint
                                                                      +-- identified panel driver
                                                                      +-- positive/negative regulators
                                                                      +-- truthful reset consumer
                                                                      `-- standard backlight
                                                                            `-- MT6797 display PWM
```

M4U/SMI owns address translation and larb lifetime; OVL/RDMA merely consume
their `iommus`. GCE owns mailbox threads; display clients own only their
admitted channel and register window. MMSYS owns route writes and the two
32-bit reset banks. Display mutex owns synchronization and its own MM-domain
lifetime. DRM owns component bind/unbind, graph ordering, modeset and suspend.
The DSI host translates the DRM mode and DSI format into a requested lane rate;
the PHY owns only a validated realization of that rate and analog power
sequence. The panel driver owns panel commands and its declared supplies/reset,
not bias-chip identification or an MMSYS-private reset bit. The PWM provider
owns waveform generation; `pwm-backlight` owns brightness policy; panel code
owns only the standard backlight relationship.

Probe deferral and unwind must follow that ownership. A later DRM series must
prove that failure after any component bind releases mutex, CMDQ, IOMMU/SMI,
clocks and the MM domain; remove and suspend must use subsystem callbacks, not
a hand-written reverse of initialization. An uncertain PHY lock, reset state or
power-domain transition is a refusal, not a best-effort continuation.

## Per-patch disposition

| Patch | Disposition | Current-tree reason |
| --- | --- | --- |
| 0028 | retain | The MT6797 mutex compatible remains absent and the dedicated hardware identity is evidenced; revalidate the current schema when implemented. |
| 0029 | adapt | The distinct module/SOF data remains needed, but it must be rebased and reviewed against the current mutex core and lifetime rules. |
| 0030 | hold | A probing provider without the admitted DRM consumer is precisely the dead-scaffolding case; its MM/GCE dependencies also have upstream ordering. |
| 0031 | adapt | Current MMSYS already owns MT6797 clocks; extend that existing record with routes/resets rather than introduce a parallel owner. |
| 0032 | hold | Exposing reset/GCE cells belongs with an accepted routes/reset consumer and must preserve the separate `LCM_RST_B` boundary. |
| 0033 | split | OVL, OVL-2L and RDMA are separately bound components and should travel with their respective driver data/caller. |
| 0034 | split | Separate OVL and RDMA data and current DRM recognition; do not hide IOMMU/SMI requirements in a combined enablement patch. |
| 0035 | split | Seven independent binding additions are not one reviewable hardware identity. Pair each with its driver data and graph consumer. |
| 0036 | split | Generic CMDQ/data plumbing overlaps current code; retain only still-absent MT6797 data, split by block, and do not resurrect superseded hunks. |
| 0037 | split | DSI-host and PHY compatibles have different subsystem ownership and must accompany their exact implementations. |
| 0038 | hold | The host-shaped offsets are plausible reuse, but no admitted PHY/output consumer or verified rate contract exists. |
| 0039 | hold | This is genuinely MT6797-specific PHY behavior; PLL/divider and analog power sequencing remain unproved and require independent Astra review. |
| 0040 | hold | DSI/PHY DTS nodes depend on accepted bindings, clocks, power and PHY implementation; declaration cannot validate those contracts. |
| 0041 | superseded | Current DRM can construct paths from OF graphs. Replace the hard-coded path with graph endpoints plus only the minimal MT6797 match data still required. |
| 0042 | split | Rework into provider-ordered SoC nodes and current OF endpoints; keep inactive UFOE and unresolved consumers out of first enablement. |
| 0043 | hold | Controller/module identity, bias silicon, reset ownership and mode/rate are unresolved; compile success cannot admit panel commands. |
| 0044 | hold | It weakens a common two-clock contract without decisive MT6797 evidence and has no admitted standard backlight consumer/lifetime test. |

Canonical dependencies remain 0028 through 0044; the dispositions do not
authorize reordering the repository series. A future upstream submission split
would be newly generated against its accepted base, with actual authorship and
DCO handled separately.

## Reuse versus new code

- Reuse current MediaTek MMSYS, mutex, DRM component, DSI, MIPI-TX common and
  display-PWM frameworks. Add only MT6797 data/operations after each resource
  contract is frozen.
- Reuse current OF-graph discovery rather than the static path in 0041.
- Reuse the NT36672E panel driver's descriptor structure only if a named-device
  read proves the matching controller/module family. SSD2092 requires its own
  correctly identified panel support; neither identity may borrow the other's
  command table.
- Do not write a generic bias shim. A new regulator driver/binding is justified
  only for an identified chip whose register protocol and electrical contract
  lack an exact upstream match.
- Do not model `LCM_RST_B` as MMSYS reset ID 64. Either prove GPIO180 is the
  same electrical control and use `reset-gpios`, or define a separately reviewed
  owner for the real hardware control.

## Maintainer and tree routes

The pinned `MAINTAINERS` file gives these routes; it does not predetermine which
maintainer will take a cross-tree series.

| Topic | Primary route |
| --- | --- |
| MMSYS, mutex and MT6797 DTS | ARM/MediaTek SoC: Matthias Brugger, AngeloGioacchino Del Regno; `linux-kernel`, `linux-arm-kernel`, `linux-mediatek`; DT binding reviewers for schema changes |
| DRM components and DSI host | DRM Drivers for MediaTek: Chun-Kuang Hu, Philipp Zabel; `dri-devel`, `linux-mediatek`; binding reviewers when compatibles change |
| MIPI-TX PHY | MediaTek DRM route plus Generic PHY Framework: Vinod Koul and reviewers; `linux-phy`; PHY tree for PHY-owned changes |
| Panel | DRM Panel Drivers: Neil Armstrong, Jessica Zhang; `dri-devel`; `drm-misc` tree; DT binding reviewers |
| Display PWM | PWM subsystem: Uwe Kleine-König; `linux-pwm`; PWM tree; ARM/MediaTek and DT reviewers for the SoC node/binding |
| Standard backlight | Backlight class/subsystem: Daniel Thompson, Jingoo Han; `dri-devel`; backlight tree |
| Bias regulator, if identity requires new support | Voltage/current regulator framework: Liam Girdwood, Mark Brown; regulator tree; DT binding reviewers |

Cross-tree ordering should keep bindings with their implementing owner, SoC DTS
after provider acceptance, and board consumers last. Nothing in this review is
submission approval or permission to contact those maintainers.

## Evidence-transfer limits

The frozen project evidence can support MT6797 register offsets, component
maps, observed resource topology, the single-DSI geometry hypothesis, and the
fact that current hardware support is unknown. It cannot certify a current-tree
rebase, schema result, panel identity, bias silicon/voltage, GPIO-reset
equivalence, PHY PLL correctness, DRM pixel clock, DSI lane rate, teardown,
suspend, or runtime support. The public overlap contributes independent design
comparison only; its compile result and different board assumptions are not
transferred as Gemini support.

Review-ready UTC: `2026-09-07T19:35:12Z`.

Independent Astra Medium review rejected the first discriminator wording
because one observed consumer clock handle cannot exclude parent, inherited or
MM-domain dependencies. The repair added complete ancestry/rate/owner
attribution, an inconclusive branch that preserves mandatory `main` + `mm`, and
separate acquisition admission. The repaired design stop was accepted at
`2026-09-07T19:38:50Z`; no implementation or device action was admitted.
