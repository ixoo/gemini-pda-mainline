# Wi-Fi integration handoff

Base: `de48e24af88ef4647f8e94ec69975e5bd00d12ec`.
Topic: `codex/mt6797-wifi-contract`. Exact completion revision is supplied by
the final Git handoff rather than a self-referential commit field.

## Scope and result

Owned paths are this experiment and `docs/hardware/mt6797-wifi.md`.
No manifest, canonical/named series, configuration, kernel patch, roadmap,
existing support matrix, workstream registry or queue edits are included.

The [decision](README.md) selects an integrated gen3 AHB SDIO-like WLAN development path,
rejects unproven driver-ID substitutions, separates GPLv2 host-source rights
from unresolved firmware rights, and identifies shared DMA/CONSYS ownership
and the WLAN protocol/calibration contract as real missing dependencies.
The metadata-only collector and refusal fixtures are concrete preparation for
the [first discriminator](SESSION.md). Exact validations and any later admitted
device observation are recorded in `results/`.

The physical session is now complete and custody released. Native recovery
from the verified consumed V4 session reached Gemian. The first ancestry
collector returned inconclusive; the separately admitted eight-path follow-up
positively observed direct WLAN platform ancestry and localized the missing
metadata to OF exposure. Both classifiers' conservative outcomes and consumed
budgets are preserved in [the session record](results/device-session.md).
The exact retained firmware passed the selected gen3 MTKE structural validator
([receipt](results/firmware-mtke.json)); this does not establish runtime loading.

## Proposed shared deltas for the integrator

- Link the dedicated [hardware contract](../../docs/hardware/mt6797-wifi.md)
  from `docs/hardware/README.md` and the Wi-Fi workstream evidence.
- In `docs/hardware/mt6797-live-resource-map.md`, replace descriptions of a
  "proprietary gen2" host implementation with "vendor gen3 AHB SDIO-like"
  and link the selected-source build audit and
  file-level GPLv2 audit. Preserve firmware-rights uncertainty.
- Correct any claim that HIF-SDIO log initialization or shared vendor ID
  tables establish Gemini WLAN's SDIO parent. AHB source/platform evidence
  and observed live ancestry have distinct attribution.
- Avoid explaining `mt76` incompatibility as integrated versus standalone:
  upstream supports some integrated MediaTek MACs. The missing match is the
  exact MT6797 generation's register, DMA and firmware protocol.
- In `docs/hardware/firmware.md`, qualify HIF-SDIO log activity as vendor
  messaging, not exact WLAN bus or blob load attribution. No firmware file
  license was recovered by this task.
- Keep Wi-Fi a named usability requirement. Proposed queue item
  `wifi-parent-attribution` links to this packet and actual readiness/result;
  it is a Gemian metadata observation, not a new boot2 candidate. Do not label
  radio enablement ready or conditional merely because host tests pass.
  The completed metadata item must be recorded as consumed, with no selected
  candidate and no automatic rerun. The next active radio experiment remains
  planned while technical power/HIF/EMI/firmware/regulatory contracts are open.
- Future mainline Wi-Fi admission depends on one frozen authenticated A53
  serviceability pass and independent recovery, plus the explicit radio
  resource/firmware predicates. It does not depend on A72 or all ten cold boots.

Historical experiments and captures remain unchanged. Corrections here refine
interpretation rather than rewrite old evidence. Shared ordered implementation
steps remain solely in `docs/ROADMAP.md`.

## A53 interface handshake

The serviceability worker confirmed a userspace-only authenticated child of
the historical PWRAP candidate: unchanged kernel/DT, CPU0-7 available and
CPU8/9 offline, static USB device address `10.15.19.82/24`, no DHCP/default
route, pinned key-only Dropbear authentication and separate bounded logs.
Exact candidate validation is still that worker's responsibility. Minimal
initramfs is BusyBox-only; the Python collector remains Gemian-only and does
not impose a new Python dependency on the mainline candidate.

No Wi-Fi kernel switch or resource enablement was requested. Preserve the
CONSYS reservation and AP-DMA state. The source-derived Wi-Fi DMA window
`0x11000080+0x80` needs a reviewed ownership agreement with the existing
AP-DMA/I2C preservation contract before an active kernel implementation.

## Resume point

Continue the selected gen3 WLAN command/firmware-offload audit from the
pinned GPLv2 source, including DMA channel/memory protection and WMT lifecycle
ownership. Existing private firmware/dumps may be inspected in the RE VM under
the owner's authorization without redistributing them. Do not re-extract
large evidence or manufacture an RF calibration default. Prepare an active
kernel topic only when its register, power, firmware and recovery preconditions
can be enforced and tested. Kernel builds then require coordinated, clean,
published inputs and the explicit Buildbox backend.

## Checks and concrete next offline slice

The three focused suites pass 110 synthetic tests (40 ancestry, 15 presence,
55 firmware), with actual Python 3.5 dry runs and completed bounded Gemian
metadata execution. The common repository publication gate and exact source
digests are in [host-validation.txt](results/host-validation.txt). No kernel
input changed, so no build is claimed or needed.

Implement the selected gen3 DOWNLOAD_CONFIG/PDA/ACK length, sequence and
status contract with refusal fixtures, while specifying exclusive ownership
of the two shared-EMI sections, remap/MPU and AP-DMA resources. Use the retained
blob through a standard loader after those technical gates are met. Open
replacement firmware and unresolved redistribution do not block this slice.
No further device slot is needed for that offline implementation.
