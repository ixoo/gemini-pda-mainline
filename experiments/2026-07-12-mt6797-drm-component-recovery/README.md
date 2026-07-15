# Experiment: MT6797 DRM component recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-mt6797-drm-component-recovery` |
| Status | `inconclusive` for mainline runtime; source, live, and disabled-path contracts recovered |
| Subsystem | MT6797 primary display components and DSI host |
| Device variant | Gemini PDA running Gemian |
| Date | 2026-07-12 through 2026-07-14 |
| Investigator | Repository maintainer with Codex assistance |

## Question

Which Linux 7.1 MediaTek DRM component generations accurately describe the
Gemini's retained primary display path, and which MT6797-specific differences
must be represented before any component is enabled?

## Provenance and safety

The source comparison uses exact Gemian kernel commit
`d388d350cb2dda8f23b99be6fa5db9628896e87f`, the independently retained Planet
tree at `c5b0be85017ad0c599725e8273842efdbecdd88a`, and the repository's
checksum-verified Linux 7.1.3 tree. The live target is the same named Gemini PDA
used by the baseline inventory.

The collector is read-only. It reads `/proc`, sysfs, debugfs clock attributes,
and an opt-in, source-audited `/sys/kernel/debug/mtkfb` history callback. The
complete callback output remains private because it can contain kernel and DMA
addresses. No direct MMIO, display state change, clock change, or panel command
is performed.

The private capture is
`artifacts/device-inventory/20260712-drm-components/live-components.txt`,
SHA-256
`06a984b5f1837fbe643c5567b3bb55a63d94b982000539a09bcb055724541903`.
Its sanitized facts are in
[`results/runtime-summary.txt`](results/runtime-summary.txt).

## Associated code

- [`scripts/collect-live-drm-components.sh`](scripts/collect-live-drm-components.sh)
  collects the active clock, interrupt, platform-resource, and filtered retained
  register view.
- [`scripts/check-component-contract.py`](scripts/check-component-contract.py)
  checks the sanitized capture for all active clocks, registered interrupts,
  component dumps, UFOE bypass, and DSI lane/mode evidence.
- [`scripts/check-fixed-function-contract.py`](scripts/check-fixed-function-contract.py)
  compares eleven decisive vendor register definitions with the Linux
  platform data, relay guards, OD behavior, component matches, and all seven
  binding compatibles.
- [`scripts/check-dsi-phy-contract.py`](scripts/check-dsi-phy-contract.py)
  checks the DSI host offsets, MT6797-native PLL field layout, rate-divider
  policy, calibration preservation, PCW latch, and binding compatibles.
- [`scripts/analyze-mt6797-drm-contract.sh`](scripts/analyze-mt6797-drm-contract.sh)
  records vendor/Linux source hashes, bounded display-register anchors, and
  runs the fixed-function and DSI/PHY contract checks.

The source-backed reuse/new-data boundary is recorded in
[`results/mt6797-drm-mainline-design.md`](results/mt6797-drm-mainline-design.md).

The current package revalidation is recorded in
[`results/mainline-display-current-71-validation-20260714.txt`](results/mainline-display-current-71-validation-20260714.txt).
The normalized source audit is
[`results/mainline-drm-source-audit-20260714.txt`](results/mainline-drm-source-audit-20260714.txt);
its analyzer and both mechanical checkers reproduce byte-for-byte in the VM.
It confirms that the DRM, DSI PHY, and panel implementations are packaged as
modules, while all MT6797 DSI/component nodes remain disabled. The mutex node
is implicitly enabled, but its probe only maps the register window and obtains
its clock; it does not perform initial display writes. No panel consumer is
present in the Gemini DTB.

## Observations

The retained primary path is:

```text
OVL0 -> OVL0-2L -> OVL1-2L -> COLOR0 -> CCORR -> AAL -> GAMMA ->
OD -> DITHER -> RDMA0 -> UFOE -> DSI0
```

The vendor route connector skips `OVL0`, while the mutex and live component
state include it; `OVL0 virtual` and `PATH0` are routing pseudo-components and
are omitted above. `UFOE` belongs to the physical path but its live
`UFOE_START=0x4` selects bypass.

All eleven multimedia component gates and both DSI gates remain prepared.
Every rate-bearing multimedia gate is 325 MHz. At the latest screen-sleep
snapshot, the three OVL gates remained enabled while the downstream gates were
disabled; the retained boot dump establishes the complete active path. The DSI
interface gate reports rate zero, which is normal for this downstream gate.
Registered IRQs establish OVL0, both OVL-2L blocks, RDMA0, AAL, and DSI0;
several fixed functions have DT interrupt resources but their retained drivers
do not register handlers.

The OVL register generation matches Linux's MT8173 address window and layer
stride. Its live `0x010020ff` layer-format value is Linux DRM `ABGR8888`: the
MT8173 ARGB encoding plus byte swap and alpha enable. The two OVL-2L instances
use the same register generation with two layers rather than four. MT6797 also
requires the `LAYER_SMI_ID_EN` data-path bit, matching Linux's MT8167 behavior.

RDMA0 likewise matches the MT8173 register generation, including its memory
address at `0xf00`. The live FIFO register encodes 512 16-byte units, proving an
8 KiB FIFO. Vendor threshold policy differs from upstream and is performance
tuning rather than a register-layout difference.

COLOR uses the MT8173 `0xc00` start/size window. CCORR, AAL, GAMMA, OD, DITHER,
and UFOE use the older fixed-function register family. The retained GPL trees
declare AAL, CCORR, and GAMMA driver objects but omit their implementations, so
live registers establish behavior that unavailable source cannot explain.

One concrete incompatibility blocks blind reuse: Linux 7.1 unconditionally
writes AAL output size at `0x4d8`, while the complete retained MT6797 AAL
register definition has no such register. MT6797 data must suppress that write.
Its AAL-integrated gamma capability is also not evidenced. The live proprietary
PQ state (`AAL_CFG=0x16`) must not be treated as a safe upstream default; first
light should preserve or explicitly select relay behavior until PQ programming
is independently recovered.

CCORR coefficients occupy 12-bit fields. Linux's `matrix_bits=10` is therefore
the correct 2.10 fixed-point representation rather than an inference from a
newer SoC. Its retained active configuration is raw value `1`, consistent with
relay. The safe MT6797 model keeps CCORR in relay when no DRM CTM exists,
programs the coefficients first when a CTM is supplied, and only then selects
the engine. Removing the CTM returns the block to relay.

The separate GAMMA aperture has one exact 2 KiB LUT window from `0x700` through
`0xeff`, establishing 512 entries. Each register contains three 10-bit fields.
It therefore uses a 512-entry 10-bit LUT without the MT8173 integrated-dither
behavior. OD has the same internal dither register offsets as the generic
driver, but the retained Gemini uses a separate DITHER block and leaves OD in
relay. Enabling OD's internal dither would contradict that state. DITHER itself
matches the generic offsets and engine-enable bit exactly. UFOE bypass is bit
2 in both the retained header and Linux and was observed live as value `4`.

DSI0 is an MT8173-generation host: command queue at `0x200`, VM command control
and data at `0x130`/`0x134`, four lanes, burst video mode, and no newer shadow or
size-control registers. The MIPI TX uses the same aperture offsets as MT8173,
but it is not register-compatible. MT6797 places pre-divider at bits 3:2,
post-divider at 6:4, and S2Q divider at 13:12; MT8173 instead describes two TX
dividers and a post-divider across bits 9:1. Their bandgap selector fields also
differ. Reusing the MT8173 PHY operations would therefore write valid offsets
with the wrong masks. The retained sequence preserves four-bit lane trim and
bandgap voltage selectors, uses divider ratios 1/2/4/8/16 from 50 MHz through
1.25 GHz, and pulses the PCW-change latch after enabling the PLL.

A dedicated MT6797 host record can reuse the common DSI logic, while the PHY
requires native clock operations inside the existing common MediaTek PHY
framework. The panel node remains disabled until the exact panel suffix,
command program, reset, bias, and backlight contract can be represented
together.

## Interim conclusion

The register evidence supports dedicated MT6797 platform data built from the
MT8173 OVL/RDMA/COLOR/DSI generations, MT8167's OVL SMI-ID behavior, two-layer
OVL variants, an MT6797 AAL guard, and native MIPI-TX PLL fields. It does not
support copying the retained PQ configuration or enabling a generic panel.
The complete disabled-first display path is now encoded, mechanically checked,
and focused-built; runtime support remains unproven until a panel and its
power/M4U/GCE dependencies are tested on hardware.

## First implementation result

Patches 33–34 add dedicated MT6797 OVL, OVL-2L, and RDMA binding compatibles,
then add the four-layer and two-layer OVL platform data, the required SMI-ID
behavior, the eight-bit GMC fields, the retained format table, and the 8 KiB
RDMA FIFO. They also register all three compatibles with the DRM component
matcher. No DT consumer is added or enabled.

Both patches pass strict `checkpatch.pl` with zero warnings. Each of the OVL,
OVL-2L, and RDMA schemas passes an individual `dt_binding_check`; the OVL,
RDMA, and DRM core objects build with `W=1`. The full 34-patch series
reconstructs cleanly and packages as
`linux-7.1.3-gemini-4f66a24c5de9`, with patch-set SHA-256
`4f66a24c5de96ef86c21cd8cbff23c64617ddc71f7704ec251313c41d8e1dc53`.
Every exported package manifest entry verifies at
`artifacts/20260712T124311Z/gemini-pda/linux-7.1.3-gemini-4f66a24c5de9`.
The Image and DTB are intentionally byte-identical to patch 32 because the DRM
driver remains modular and no display consumer node has been attached.

An initial combined schema invocation passed three space-separated paths in a
single `DT_SCHEMA_FILES` value; the kernel make rule handed an empty input to
`yamllint`. That command was invalid rather than a schema failure. Repeating
the three checks individually produced the successful results reported above.

## Fixed-function implementation result

Patches 35–36 add the seven fixed-function binding compatibles and implement
the recovered MT6797 behavior. COLOR uses the `0xc00` MT8173 window. CCORR
uses 2.10 coefficients, starts in relay, enables its engine only after a CTM
has been programmed, and returns to relay when the CTM is removed. AAL skips
the nonexistent `0x4d8` write, advertises no integrated gamma, and starts in
relay. GAMMA exposes one 512-entry 10-bit LUT and starts in relay until a LUT
is installed. OD remains in relay rather than enabling its internal dither;
the separate DITHER and UFOE bypass paths use the generic exact-match logic.

The static checker reports:

```text
PASS vendor-registers=11 aal-output-size=absent ccorr=2.10 gamma=512x10 defaults=relay od-dither=separate compatibles=7
```

Both patches pass strict `checkpatch.pl` with zero warnings. All seven binding
schemas pass individual checks, and every changed DRM object builds with
`W=1`. The complete 36-patch series reconstructs and builds as
`linux-7.1.3-gemini-dbe7c5051964`, patch-set SHA-256
`dbe7c505196402e7ed2cdd237da93b2b850d4de6df2dbb39a4a14a8fc3359a97`.
All exported manifest entries verify at
`artifacts/20260712T130347Z/gemini-pda/linux-7.1.3-gemini-dbe7c5051964`.
The Image is
`bcfb473f96f58ea7a77eef783fd4bce4927374f0b715dcdffa78d2760dade33c`
and the Gemini DTB is
`2b2e2904f8d3fcbc45842245315be0749ea0b43aa3a542848fcf3a2a234e4c44`.
They remain byte-identical because DRM is modular and no consumer node is
attached; this result is compile and contract validation, not hardware support.

## DSI host and MIPI-TX implementation result

Patches 37–39 add native MT6797 DSI and MIPI-TX compatibles. The DSI host uses
the shared MediaTek implementation with a dedicated record for the proven
`0x200` command queue and `0x130` VM-command generation. The PHY remains inside
the shared provider framework but has MT6797-specific clock operations because
its PLL and bandgap fields are not MT8173-compatible. It preserves retained
lane trim and voltage-selector calibration, programs the native divider fields,
and implements the PCW-change latch and power order.

The mechanical checker reports:

```text
PASS host=0x200/0x130 phy-fields=mt6797-native rate=50M..1.25G calibration=preserved pcw-latch=pulsed compatibles=2 nodes=disabled
```

The PHY directory builds with `W=1`. Strict checkpatch reports zero findings;
the generic new-file warning is suppressed only after `get_maintainer.pl`
confirmed that the existing `drivers/phy/mediatek/phy-mtk-mipi*` and generic
MediaTek PHY wildcards cover the new source. No DSI or PHY DT node is attached
in these patches.

Both schemas pass individual `dt_binding_check` runs. The complete 39-patch
series reconstructs and builds as `linux-7.1.3-gemini-3adec95a16dc`, with
patch-set SHA-256
`3adec95a16dcc4882c6092961757dc46fe5167ed2c4a5bf3fc76eca37ab946e8`.
Every package manifest entry verifies at
`artifacts/20260712T133346Z/gemini-pda/linux-7.1.3-gemini-3adec95a16dc`.
The Image remains
`bcfb473f96f58ea7a77eef783fd4bce4927374f0b715dcdffa78d2760dade33c`
and the Gemini DTB remains
`2b2e2904f8d3fcbc45842245315be0749ea0b43aa3a542848fcf3a2a234e4c44`.
They are byte-identical to patch 36 because DRM and the PHY are modular and no
consumer is attached. This remains build and contract validation rather than
a mainline hardware result.

Patch 40 adds the primary `mipi_tx0` provider at `0x10215000` and DSI0 host at
`0x1401c000`, SPI 229, with the MM power domain and exact two multimedia gates.
Both nodes and their empty input/output graph ports remain disabled. The EVB
and X20 DTBs compile, and each new node passes its focused schema check. The
Gemini DTB is validated from the managed reconstructed tree; the disposable
authoring clone has an unrelated pre-existing PMIC-label divergence.

Patch 41 registers `mediatek,mt6797-mmsys` with the DRM master and describes
the 12-component primary path recovered from the vendor
`DDP_SCENARIO_PRIMARY_DISP` table:

```text
OVL0 -> OVL0_2L -> OVL1_2L -> COLOR0 -> CCORR -> AAL -> GAMMA ->
OD -> DITHER -> RDMA0 -> UFOE -> DSI0
```

The vendor-only OVL virtual node and `DISP_PATH0` are routing abstractions
already represented by MMSYS. `PWM0` is a side-band backlight controller, not
a pixel-processing stage, and the Gemini panel uses DSI brightness commands;
it is therefore deliberately absent from the DRM path. This patch adds no new
display algorithm: it composes the MT6797-specific component data added in
earlier patches through the existing MediaTek DRM master.

Patch 42 adds disabled SoC nodes for the eleven pre-DSI components, with exact
IRQs, clock gates, GCE windows, MM-domain references, and the three proven M4U
ports. `ovl-2l0` and `ovl-2l1` aliases are required because the DRM component
mapper otherwise assigns both same-compatible nodes to its first OVL-2L ID.
OD intentionally omits `power-domains`: the current upstream OD binding does
not permit that property, so this patch does not invent an ABI exception.

The expanded checker reports:

```text
PASS host=0x200/0x130 phy-fields=mt6797-native rate=50M..1.25G calibration=preserved pcw-latch=pulsed compatibles=2 pipeline=12-components nodes=12-disabled
```

Patches 41–42 pass strict `checkpatch.pl` with zero findings. The DRM master
object builds with `W=1`; all three canonical MT6797 DTBs compile; and the OVL,
OVL-2L, RDMA, COLOR, CCORR, AAL, GAMMA, OD, DITHER, and UFOE schemas pass
focused checks against the Gemini DTB. This is structural/build validation,
not hardware support: the nodes and DSI path remain disabled.

The complete 42-patch tree packages as
`linux-7.1.3-gemini-71f0b4592d0f`, with patch-set SHA-256
`71f0b4592d0f49e3c0c16e01d8397447306f4f341c9b12858c023070bca2301f`.
Every exported manifest entry verifies at
`artifacts/20260712T141940Z/gemini-pda/linux-7.1.3-gemini-71f0b4592d0f`.
The Image remains
`bcfb473f96f58ea7a77eef783fd4bce4927374f0b715dcdffa78d2760dade33c`;
the Gemini DTB is now
`3a0ca2dbc94b4c6efd1d6e4d178f5766644cbc2f1578b247358f29590d26746a`
because it contains the disabled component nodes.

## Follow-up

Attach only the complete primary path with its SMI/IOMMU, MM power-domain,
MMSYS route, mutex, panel, bias, reset, and backlight dependencies. Keep the
board path disabled until those dependencies are all represented and validate
schemas and focused objects before packaging the series.
