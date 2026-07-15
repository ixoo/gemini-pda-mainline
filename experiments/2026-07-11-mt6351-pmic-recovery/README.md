# Experiment: MT6351 PMIC and MT6797 EINT recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-11-mt6351-pmic-recovery` |
| Status | `completed` |
| Subsystem | PMIC wrapper, MT6351, regulators, RTC, power key, and parent EINT |
| Device variant | Gemini PDA running Gemian |
| Date | 2026-07-11 through 2026-07-14 |
| Investigator | Repository maintainer with Codex assistance |

## Question

What PMIC and revision is physically responding behind the MT6797 PMIC
wrapper, which rails and interrupt paths are active, and what is missing from
Linux 7.1.3 before storage, power key, RTC, and safe regulator control can work?

## Evidence and safety

The owner-authorized live probe used the committed
[`collect-live-pmic.sh`](scripts/collect-live-pmic.sh). Its default mode only
reads procfs, sysfs, debugfs, and running-kernel configuration. Private output
is ignored by Git at `artifacts/device-inventory/20260711-live/pmic.txt`; the
normalized facts are committed in
[`results/runtime-summary.txt`](results/runtime-summary.txt).

A second default-mode run on 2026-07-14 is retained privately at
`artifacts/device-inventory/20260714-live/pmic.txt` and summarized in the
[consolidated live snapshot](../2026-07-14-first-boot-probe-audit/results/live-runtime-snapshot-20260714.txt).
It confirms the same `mt-pmic`/`mt-rtc`, PWRAP IRQ, EINT176, and storage-rail
topology. The explicit chip-ID and regulator-control options were not used in
this repeat, so the earlier HWCID/SWCID record remains the authoritative
stateful-read evidence.

A further default-mode capture is retained at
`artifacts/device-inventory/20260714-live/pmic-latest.txt` and summarized in
[`runtime-pmic-repeat-20260714.txt`](results/runtime-pmic-repeat-20260714.txt).
It is topologically stable but shows ordinary-operation deltas in the PMIC EINT
counter, battery interrupt counters, and `vemc_3v3` consumer count. These are
dynamic baseline changes, not evidence of a new control path.

The optional `--read-chip-id` path was used after auditing the exact vendor
`pmic_access` handler. A single token of at most four characters calls
`pwrap_wacs2()` with write-enable zero; an address and value would select the
dangerous write branch. The probe supplied only register addresses `0x200`
(HWCID) and `0x202` (SWCID). It did not write a PMIC register. The full PMIC
register-dump interface was deliberately not used because bulk reads can touch
read-clear status registers.

The live tree was recaptured privately as `device-tree-v5.txt`, then decoded
with [`decode-eint-capture.py`](../2026-07-11-gemian-hardware-inventory/scripts/decode-eint-capture.py).
The normalized EINT result is in [`results/eint-summary.txt`](results/eint-summary.txt).
The source-only Linux probe-safety audit is recorded in
[`results/mt6351-probe-safety-audit-20260714.txt`](results/mt6351-probe-safety-audit-20260714.txt).
The current 72-patch package, live PMIC capture, descriptor extraction, and
probe-safety hashes are consolidated in
[`results/mainline-mt6351-current-72-validation-20260714.txt`](results/mainline-mt6351-current-72-validation-20260714.txt).
The reproducible source-only audit is
[`scripts/audit-mainline-probe-safety.sh`](scripts/audit-mainline-probe-safety.sh).

The current package revalidation applies the complete 72-entry series to
Linux 7.1.3 and produces the corrected `linux-7.1.3-gemini-c2d9eea95daa`. The package,
configuration, DTB, live-capture, descriptor, and first-boot audit hashes are
recorded in
[`mainline-mt6351-current-72-validation-20260714.txt`](results/mainline-mt6351-current-72-validation-20260714.txt).
The package contains 1,570 `.ko` module objects, while the PMIC wrapper,
MFD, regulator, key, RTC, and eMMC probe dependencies are linked into the
first-boot Image. This is build and source-contract evidence only; no mainline
PMIC probe or rail control has run on the device.
The packaged Gemini DTB was also inspected read-only in the dev VM: its
`pwrap`, `pmic`, and `mt6351regulator` nodes are present and enabled by the
implicit Device Tree default (`status` is absent). A first mainline boot will
therefore enter the stateful wrapper and MFD probe paths unless a separate
candidate explicitly disables them. The [first-boot probe dependency audit](../2026-07-14-first-boot-probe-audit/README.md)
records the exact UART → PWRAP → MT6351 → regulator → eMMC ordering and the
source-level writes that make this path stateful.

The authoritative current Image/DTB package is now
`linux-7.1.3-gemini-b7721ab55e41` (77 packaged entries, no module tree). Its
direct PWRAP/MT6351 configuration and generated-DTB audit is recorded in
[`mainline-mt6351-current-77-package-20260714.txt`](results/mainline-mt6351-current-77-package-20260714.txt).
It confirms built-in PWRAP, MT6351 MFD/regulator, PMIC keys, and RTC support;
the PWRAP and PMIC nodes are implicitly enabled, with VEMC boot-on at 3.0–3.3 V
and VIO18 always-on at 1.8 V. The audit is static package evidence only and
does not claim a mainline PMIC probe or rail control.

Interpretation uses the Planet 3.18 GPL source at
[`c5b0be85017ad0c599725e8273842efdbecdd88a`](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/tree/c5b0be85017ad0c599725e8273842efdbecdd88a)
and the partial 4.9 Gemini port at
[`c65b8b5592a462041dce0d3058dc4e5f831704ce`](https://github.com/NotKit/kernel-4.9-geminipda/tree/c65b8b5592a462041dce0d3058dc4e5f831704ce).
Public source is used as implementation evidence, not assumed to be identical
to the running build where live behavior contradicts it.

The running kernel itself is `3.18.41+`, build `#7 SMP PREEMPT Fri Mar 29
10:39:03 GMT 2019`. Read-only hashes prove the `boot`, `boot2`, and `boot3`
partitions are byte-identical. One private copy, the running configuration,
and the separately installed kernel-package payload are preserved below
`artifacts/vendor-kernel/gemian-2019/`; Git ignores that directory and its
contents are owner-only. The sanitized hashes and Android boot-header layout
are recorded in
[`results/vendor-kernel-provenance.txt`](results/vendor-kernel-provenance.txt).

The installed `gemian-modular-kernel` package is not the running image: its
`linux-boot.img` differs from the active partition beginning at the kernel-size
field. This distinction matters when correlating disassembly, configuration,
and source; package files must not be cited as runtime evidence unless their
content is independently matched.

## Physical PMIC identity

The live reads returned:

| Register | Value | Interpretation |
| --- | ---: | --- |
| HWCID `0x200` | `0x5140` | MT6351 hardware-family identifier |
| SWCID `0x202` | `0x5120` | MT6351 E2 revision code in vendor source |

This upgrades the PMIC from a DT-described candidate to a directly read,
confirmed MT6351 E2. The vendor's E1-only alternate VMC selector tables and
efuse-reading workaround do not apply to this device revision.

## PMIC-wrapper contract

| Property | Recovered value |
| --- | --- |
| Wrapper registers | `0x1000d000` + `0x1000` |
| Wrapper interrupt | GIC SPI 178, level high |
| SPI source/mux | `pmicspi_sel`, observed 26 MHz |
| AP wrapper gate | `infra_pmic_ap`, observed 26 MHz |
| Reset | infracfg reset bank 2, bit 0; linear reset ID 64 |
| PMIC bus width | 16-bit registers and values |

Linux 7.1.3 already has `mediatek,mt6797-pwrap` master data and an
`mediatek,mt6351` slave regmap definition. That support is not currently usable
from the upstream MT6797 DTS:

1. `mt6797.dtsi` has no pwrap node.
2. The pwrap binding requires `spi` and `wrap` clocks. The real pair is strongly
   supported as `CLK_TOP_MUX_PMICSPI` and `CLK_INFRA_PMIC_AP`, matching newer
   MediaTek DTS practice and both live 26 MHz rates. The 4.9 port's synthetic
   40 MHz `wrap` clock should not be copied.
3. MT6797 pwrap data has `PWRAP_CAP_RESET`, making its reset mandatory, but
   Linux 7.1.3's MT6797 infracfg driver exposes no reset controller.

The historical 4.9 code establishes three simple read/modify/write reset banks
at offsets `0x120`, `0x124`, and `0x128`. Its reset header assigns pwrap ID 64,
which is bank 2 bit 0. The current clock reset API can represent this as
`MTK_RST_SIMPLE`; the required first patch is therefore an MT6797 infracfg
reset descriptor and binding/header, not a fake clock or removal of the pwrap
reset capability.

That prerequisite is now implemented as the first local Linux 7.1.3 series:

1. [`dt-bindings: reset: mediatek: add MT6797 infracfg resets`](../../patches/v7.1.3/0001-dt-bindings-reset-mediatek-add-MT6797-infracfg-reset.patch)
2. [`clk: mediatek: mt6797: add infracfg reset controller`](../../patches/v7.1.3/0002-clk-mediatek-mt6797-add-infracfg-reset-controller.patch)
3. [`arm64: dts: mediatek: mt6797: expose infracfg resets`](../../patches/v7.1.3/0003-arm64-dts-mediatek-mt6797-expose-infracfg-resets.patch)

The series passed strict `checkpatch.pl` except for its generic new-file
MAINTAINERS reminder; `get_maintainer.pl` confirms the new reset header is
already covered by the reset, Devicetree, and MediaTek entries. It also passed
the targeted infracfg `dt_binding_check`, compiled `clk-mt6797.o`, and compiled
all arm64 DTBs on native AArch64. These are build results, not Gemini runtime
validation; no reset line has been pulsed on the device.

The repository's canonical `./scripts/dev-vm build-kernel` workflow then
applied the three patches to the pinned, checksum-verified Linux 7.1.3 source,
built `Image` and all arm64 DTBs, and produced the checksum-clean package
`linux-7.1.3-gemini-eb7b71df014e` in the guest. Its recorded patchset SHA-256 is
`eb7b71df014e419fa7c20e213f88866c443de3ee5daeb7c08298217e776b5b4c`.

The recovered wrapper contract is implemented by patch 7:

1. [`arm64: dts: mediatek: mt6797: add PMIC wrapper`](../../patches/v7.1.3/0007-arm64-dts-mediatek-mt6797-add-PMIC-wrapper.patch)

It passes strict `checkpatch.pl`, the pwrap binding's `dt_binding_check`, and
schema validation for both upstream MT6797 DTBs. The node and its MT6351 child
also compile. This validates representation and integration only; the wrapper
and PMIC have not been run from a mainline kernel on the Gemini.

The canonical workflow subsequently applied all seven local patches to a
fresh checksum-verified Linux 7.1.3 tree and built `Image` plus every arm64
DTB. The checksum-clean package is
`linux-7.1.3-gemini-4879532d0fb4`; its full patchset SHA-256 is
`4879532d0fb468925c7d10f4e7d0e53c3e231f1b3a2ea50bc9e2fbe33a686b83`.
The packaged `mt6797-evb.dtb` independently confirms pwrap at `0x1000d000`,
SPI178 level high, reset ID64, EINT SPI170 level high, and the MT6351 child on
EINT176 level high. The build workflow now aborts packaging if its source,
patch series, configuration, or toolchain state changes during compilation.

## Parent EINT prerequisite

The PMIC's external interrupt is not wired directly to the GIC. The live path
is:

```text
MT6351 interrupt output -> downstream pseudo-GPIO 262 -> MT6797 EINT 176
                       -> EINT parent GIC SPI 170
```

The PMIC child requests level-high with 1000 microseconds debounce. The EINT
controller is at `0x1000b000`, has 192 channels, ten debounce encodings, and a
172-entry GPIO-to-EINT map. Relevant decoded mappings include:

| GPIO | EINT | Known consumer |
| ---: | ---: | --- |
| 67 | 6 | microSD card detect |
| 85 | 8 | touchscreen |
| 88 | 11 | ambient-light/proximity sensor candidate |
| 262 | 176 | MT6351 external interrupt |

GPIO 262 is a vendor pseudo-line beyond physical GPIO 0–261. It exists only to
associate the dedicated PMIC signal with EINT 176.

Linux 7.1.3's MT6797 pinctrl has no EINT resource or interrupt-controller
properties, no `mtk_eint_hw`, and marks every pin `NO_EINT_SUPPORT`. Restoring
the standard MediaTek EINT block is a platform prerequisite for the PMIC,
keyboard/touch/sensors, card detect, and wake. The ordinary modern EINT resource
request also expects every EINT to map to a GPIO descriptor. The current
MediaTek core already supports virtual GPIO descriptors specifically for
internal PMIF and USB EINT inputs: a null mux function makes resource setup
skip GPIO mode and direction writes. The local implementation uses that model
for pseudo-GPIO262/EINT176 and built-in EINT186, while `gpio-ranges` remains
limited to physical GPIO0–261. Blindly extending the normal register ranges
through either virtual descriptor would be unsafe.

That prerequisite is implemented as patches 4–6 of the local Linux 7.1.3
series:

1. [`dt-bindings: pinctrl: mediatek: update MT6797 schema`](../../patches/v7.1.3/0004-dt-bindings-pinctrl-mediatek-update-MT6797-schema.patch)
2. [`pinctrl: mediatek: add MT6797 EINT support`](../../patches/v7.1.3/0005-pinctrl-mediatek-add-MT6797-EINT-support.patch)
3. [`arm64: dts: mediatek: mt6797: add EINT controller`](../../patches/v7.1.3/0006-arm64-dts-mediatek-mt6797-add-EINT-controller.patch)

The decoder's `--kernel-header` check proves that the authored pin table
matches all 172 captured mappings and represents built-in EINT186. The binding
passes `dt_binding_check`; both upstream MT6797 DTBs pass direct schema
validation; and `pinctrl-mt6797.o` compiles with `CONFIG_EINT_MTK=y`. Strict
`checkpatch.pl` reports no errors or warnings. Its only two checks point at the
two new multiline `MTK_PIN(` invocations, matching the surrounding generated
header style. Runtime interrupt delivery remains untested on the Gemini.

## MT6351 interrupt and MFD model

The PMIC has four 16-bit interrupt status/enable banks, or 64 logical sources.
The first bank begins with separate press and release sources:

| ID | Source | Live count |
| ---: | --- | ---: |
| 0 | power-key press | 10 |
| 1 | home/reset-key press | 0 |
| 2 | power-key release | 10 |
| 3 | home/reset-key release | 0 |
| 9 | RTC | 0 in snapshot |
| 10 | audio | 0 in snapshot |
| 12–14 | ACCDET sources | 0 in snapshot |

The active external IRQ appears as `pmic-eint` on EINT 176. Power key events
are handed to `mtk-kpd` and reported as Linux key code 116 (`KEY_POWER`). The
live balanced press/release counters prove both PMIC sources are used; a
mainline implementation should not synthesize release by polling.

The live keypad node sets debounce 1024, software/hardware power codes 116/8,
and software/hardware reset-key codes 231/17. The public `cust_kpd.dtsi`
instead lists software reset code 115, another reason to prefer the running
flattened tree over a board-family source default. No reset/home-key interrupt
had occurred in the captured session, so its physical presence is unproven.

Linux 7.1.3's `mt6397-core` MFD has no MT6351 chip data, IRQ controller, or
cells. The sound-only driver is not a PMIC core. MT6351 needs:

- register and IRQ headers, including HWCID/SWCID validation;
- an IRQ-domain implementation for its four banks;
- MFD cells for regulator, RTC, keys, and existing sound, with charger/AUXADC
  deferred to later series;
- four named key IRQ resources, because this revision supplies distinct press
  and release interrupts.

The exact GPL vendor implementation confirms four flat 16-bit enable banks at
`0x2c2`, `0x2c8`, `0x2ce`, and `0x2d4`, with set/clear aliases through
`0x2d8`. The four W1C status banks are `0x2e0`–`0x2e6`. It writes a one to each
asserted status bit after dispatch, and uses a direct full-register write to
mask every source during initialization. This is the legacy MT6397-style flat
bank model, not the later MT6358 top-group interrupt architecture.

### MFD child-node binding boundary

The Linux 7.1.3 MFD core does not treat `mfd_cell.of_compatible` as a
registration filter. For an enabled matching child it attaches that child
node to the platform device. If no matching child exists, it still registers
the platform device without an `of_node` and emits a warning. A matching child
whose status is `disabled` is the special case: that cell is skipped and the
call succeeds. The source-only audit and hashes are in
[`results/mfd-child-of-match-audit-20260714.txt`](results/mfd-child-of-match-audit-20260714.txt),
reproduced by
[`scripts/audit-mfd-child-of-match.sh`](scripts/audit-mfd-child-of-match.sh).

This matters for the four MT6351 cells. The regulator has a platform-ID match,
so it can probe without a child node; the RTC and PMIC-key drivers are
OF-match-only, so they do not bind without matching nodes (and the key probe
assumes non-NULL OF match data). The sound driver's platform name matches the
MFD cell, so it can probe even without a sound child, although its component
initialization writes are deferred until a later ALSA component bind. The
current Gemini DTS has regulator and RTC children but deliberately has no
sound or key child. Therefore the absence of a sound node does not suppress
the name-matched codec platform device; keep `CONFIG_SND_SOC_MT6351` and the
machine card disabled until analog wiring is proven. Adding a key node remains
an explicit hardware-policy decision. This is source evidence only; no child
driver was probed on the device.

Local patches 8–10 now implement the binding, regulator function container,
and MFD/IRQ core:

1. [`dt-bindings: mfd: mediatek: add MT6351 PMIC`](../../patches/v7.1.3/0008-dt-bindings-mfd-mediatek-add-MT6351-PMIC.patch)
2. [`arm64: dts: mediatek: mt6797: describe MT6351 regulators`](../../patches/v7.1.3/0009-arm64-dts-mediatek-mt6797-describe-MT6351-regulators.patch)
3. [`mfd: mt6397: add MT6351 core and interrupt support`](../../patches/v7.1.3/0010-mfd-mt6397-add-MT6351-core-and-interrupt-support.patch)

The IRQ helper is generalized by bank count, giving MT6351 a 64-source domain
without forcing its flat registers into the MT6358 grouped model. The MFD uses
SWCID register `0x202` with high-byte chip ID `0x51`, supplies RTC IRQ9 and
four named key resources, and registers regulator, RTC, existing sound, and
key cells. Both modified MFD objects compile with `W=1`; strict checkpatch is
clean except for the generic new-file MAINTAINERS reminder, while existing MFD
and MediaTek entries already select the new headers. Both bindings pass
independent `dt_binding_check`, and both MT6797 DTBs pass schema-aware builds.

The clean canonical workflow independently re-extracted the pinned Linux
7.1.3 archive, applied all ten patches in repository order, and built `Image`
plus every arm64 DTB. All package checksums pass for
`linux-7.1.3-gemini-b70f7c771194`; its complete patchset SHA-256 is
`b70f7c771194ea3da8a5411e1a0c53f702644360cb6083f4d3a948e969222f72`.
The packaged configuration has `CONFIG_MFD_MT6397=y`, the linked System.map
contains `mt6397_probe` and `mt6397_irq_init`, and the packaged MT6797 DTB
contains both `mediatek,mt6351` and `mediatek,mt6351-regulator`. This remains
build and representation evidence, not device-runtime validation.

Patches 11–13 extend that foundation without inventing board wiring:

1. [`Input: mtk-pmic-keys: add MT6351 support`](../../patches/v7.1.3/0011-Input-mtk-pmic-keys-add-MT6351-support.patch)
2. [`rtc: mt6397: add MT6351 support`](../../patches/v7.1.3/0012-rtc-mt6397-add-MT6351-support.patch)
3. [`arm64: dts: mediatek: mt6797: add MT6351 RTC`](../../patches/v7.1.3/0013-arm64-dts-mediatek-mt6797-add-MT6351-RTC.patch)

The key data uses the exact `TOPSTATUS`, `INT_MISC_CON`, and `TOP_RST_MISC`
bits above, enables distinct release IRQ handling, and retains the driver's
safe default of disabled hardware long-press reset. `mtk-pmic-keys.o` compiles
with `W=1`. No generic MT6797 key node is added: only the Gemini power key is
observed, while home/reset wiring remains unproven and belongs in a later
board DTS.

The MT6351 RTC layout matches the older shared MediaTek layout through its
write trigger at offset `0x3c`, rather than MT6358's `0x3a`. The shared RTC
object compiles with `W=1`; its compatible and fixed-function child node make
the MFD bind path complete, and both MT6797 DTBs pass the PMIC schema. Actual
read, set, alarm, wake, and power-cycle behavior remains untested on mainline.

The final clean thirteen-patch workflow built and checksum-verified
`linux-7.1.3-gemini-067dff99931c`, with patchset SHA-256
`067dff99931c412c31ce16b440c79911d4883e93506c1bcc3220b8f24d4af396`
and configuration SHA-256
`560b9dd3e4122072d34681749cd4823547e1a9b65972814a07201ea8cd197716`.
The project fragment pins MT6797 pinctrl/EINT and MT6351 MFD, keys, and RTC
support to built-in. The packaged System.map contains the MFD IRQ initializer,
key probe, and RTC probe, so none of these critical paths depends on an
unpackaged module.

The existing `mtk-pmic-keys` structure is a close fit. MT6351 uses `TOPSTATUS`
`0x220` bits 1/2, `INT_MISC_CON` `0x2da` bits 2/1, and `TOP_RST_MISC` `0x2b6`
enable bits 9/8 with timeout bits 13:12. Those semantics match the driver's
MT6331-style masks while requiring MT6351-specific addresses and release-IRQ
support. Long-press hardware reset must remain disabled initially unless the
board policy is explicitly proven.

## Mainline probe-safety boundary

The current Linux source audit adds an important runtime gate. The MT6797 pwrap
probe enables its declared clocks before checking whether the bootloader left
the wrapper initialized. If `PWRAP_INIT_DONE2` is clear, it resets the pwrap and
runs a stateful initialization sequence that resets/configures the serial slave,
programs wrapper arbitration and serial-delay state, and writes init-done
registers. Even when initialization is skipped, probe writes the dynamic-clock,
wrapper watchdog, timer, and interrupt-enable registers. Pwrap probe is therefore
not a read-only identity check.

The MT6351 MFD probe reads SWCID, then masks all four PMIC interrupt-enable
banks before creating the IRQ domain. This is intentional Linux ownership, but
it can remove interrupts from a still-running vendor policy if a mainline boot
fails afterward. The regulator child only reads the revision and active VSEL
selection. The key child would write interrupt-selection and long-press-reset
configuration if a key node were added; the current Gemini board DT has no key
child. The RTC child only allocates its resource/IRQ at probe; setting time or
alarms writes later through normal RTC operations.

Accordingly, the first PMIC runtime experiment must use a non-primary boot slot,
an external console, and an independent recovery path. Capture wrapper init
state and PMIC interrupt masks before and after probe, keep key/RTC/charger
consumers disabled, and do not treat pwrap or MFD probe success as a harmless
read-only test. Because the current Gemini DTB enables these nodes by implicit
default, this is an active boot-risk boundary rather than a dormant description.
See the [probe-safety audit](results/mt6351-probe-safety-audit-20260714.txt).

## Regulator architecture

The running vendor kernel exposes 31 regulator-class LDO devices, all provided
by `mt-pmic`. That number is not the hardware count. Its 32 descriptor
declarations contain two defects: the missing `regulator.18` is an invalid
`vsram_proc` LDO that combines an unrelated LDO enable with the real buck
selector, while `vldo28` and `vldo28_0` are duplicate names for the same enable
bit. MT6351 therefore has 30 unique LDO controls plus nine bucks. The bucks are
visible only through a vendor diagnostic path and were never registered with
the regulator core.

[`extract-regulators.py`](scripts/extract-regulators.py) independently resolves
the vendor enum accessors into raw register, mask, selector, and voltage-table
facts. It also compares those facts with the authored Linux driver. The check
passes for all 39 unique mainline descriptors while explicitly rejecting the
two vendor artifacts. Tables are indexed by raw selector encoding; this is
important for VA18, VTCXO24, VTCXO28, VCN28, VXO22, and VBIF28, whose four
hardware encodings are in descending voltage order. Live selector reads match
that recovered order for all six rails.

Eight bucks have a seven-bit selector and a 600000–1393750 microvolt range in
6250 microvolt steps. VPA is different: its direct, active, sleep, and DLC
fields are all six bits. The vendor diagnostic blindly assigns it the generic
128-entry range, but hardware can encode only selectors 0–63, or 600000–993750
microvolts under the otherwise confirmed formula. Mainline caps VPA at that
physical limit.

### Buck ownership and active voltage

The optional `--read-regulators` collector path reads only an explicit
allowlist of ordinary buck/LDO control registers. Like the chip-ID probe, each
access supplies one address token to the audited vendor `pmic_access` read
branch; it never supplies the second token that would select a PMIC write.
Private raw output is preserved as
`artifacts/device-inventory/20260711-live/pmic-regulators.txt`, with normalized
results in [`results/regulator-runtime-summary.txt`](results/regulator-runtime-summary.txt).

Each buck `CON0` bit 1 selects either its direct selector or its hardware
ON/sleep banks. `CON7` is an analog Gray-code readback. Converting every live
`CON7` value to binary exactly reproduced the selector in the active bank:

| Buck | Control owner | Direct | ON | Sleep | Active | Decoded active voltage |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| VCORE | hardware ON/sleep | 48 | 40 | 0 | 40 | 0.850 V |
| VGPU | software direct | 99 | 100 | 100 | 99 | 1.21875 V |
| VMODEM | hardware ON/sleep | 48 | 64 | 0 | 64 | 1.000 V |
| VMD1 | hardware ON/sleep | 48 | 40 | 0 | 40 | 0.850 V |
| VSRAM_MD | hardware ON/sleep | 64 | 80 | 0 | 80 | 1.100 V |
| VS1 | software direct | 64 | 64 | 64 | 64 | 1.000 V |
| VS2 | software direct | 12 | 12 | 12 | 12 | 0.675 V |
| VPA | software direct, disabled | 0 | 0 | 0 | 0 | 0.600 V selector value |
| VSRAM_PROC | hardware ON/sleep | 72 | 80 | 16 | 80 | 1.100 V |

This corrects the earlier vendor diagnostic snapshot for VCORE, VMODEM, VMD1,
VSRAM_MD, and VSRAM_PROC: that code always read the direct selector, even when
hardware mode had selected the ON bank. The decoded values are still transient
register observations, not electrically measured voltages or board-safe OPP
limits. The vendor DT's buck constraints are also non-operative evidence: it
marks VPA always-on even though VPA is live-disabled, because its buck nodes
never bind to a registered regulator.

The mainline-style driver follows the existing MT6331 pattern and chooses each
buck's active selector register at probe time from `VOSEL_CTRL`. It registers
all confirmed rails but does not add generic SoC constraints or consumers.
Board constraints, CPU/GPU OPPs, coupling, ramp behavior, and suspend selector
policy remain separate work and must not be inferred from this one snapshot.

An independent read-only comparison against the retained Gemian MT6797 header
also checks the control/status bit distinction that is easy to get wrong:

- buck `RG_*_EN` write fields are bit 0 of each `CON2`, while the hardware QI
  enable status (`DA_QI_*_EN`) is bit 13 of that same register; this matches the
  driver's `enable_mask = BIT(0)` and `mt6351_buck_get_status()` test;
- LDO `RG_*_EN` fields are bit 1 of `CON0`, matching the driver's
  `MT6351_LDO_EN` mask;
- buck `VOSEL_CTRL` is bit 1 of `CON0`, and the active `VOSEL_ON` selector is
  the corresponding `CON5` field used when hardware mode is selected.

The source anchors were hashed in the VM on 2026-07-14: vendor
`upmu_hw.h` `e376d2835dd32812b52caf6a51139cc7fd541de18eaad0f30ecf8194f70cebbe`,
vendor `pmic.c`
`3c67983e8840dacc434afd4b76701d9df225905331b9085e1bfd65f53030b324`, and
local patch 0015
`7dce9720c8944271d0166d4647f7988140fb2a846a7b3cae5b27964edc59e3cb`.
This validates register-field correspondence only; it is not permission to
enable regulators or claim electrical safety without a mainline boot.
The normalized, source-only result is
[`regulator-control-crosscheck-20260714.txt`](results/regulator-control-crosscheck-20260714.txt).

This work is implemented as patches 14–15:

1. [`dt-bindings: regulator: add MediaTek MT6351`](../../patches/v7.1.3/0014-dt-bindings-regulator-add-MediaTek-MT6351.patch)
2. [`regulator: mt6351: add regulator driver`](../../patches/v7.1.3/0015-regulator-mt6351-add-regulator-driver.patch)

The binding passes its focused `dt_binding_check`. The driver compiles with
`W=1`, and the evidence extractor validates all 39 descriptors in the clean
applied tree. Strict checkpatch has no errors; its remaining reports are the
generic new-file MAINTAINERS warning and the same array/table macro-argument
reuse checks used by adjacent MediaTek regulator drivers.

The earlier 15-, 61-, 62-, 65-, 70-, and 71-patch results are retained as
historical provenance. The authoritative current-tree result applies the
current 72-entry series to Linux 7.1.3, builds `Image` plus all 119 arm64 DTBs,
verifies every package checksum, compiles the MT6351 regulator and MT6397
MFD/IRQ objects, and passes the focused regulator binding check. See the
[current package validation](results/mainline-mt6351-current-72-validation-20260714.txt)
record for the current artifact and source hashes. Direct DT validation
confirms that the eMMC rails are children of the MT6351 `regulators` node; the
earlier 61-patch artifact had exposed them under the PMIC parent and is not
current.

The live device is MT6351 E2 (`SWCID 0x5120`). Patch 0015 therefore accepts only
that evidenced revision; the previously unvalidated `0x5130` E3 code is rejected
until independent register-table and behavior evidence exists. This is a safety
boundary, not a claim that E3 is electrically incompatible.

### Storage rails

| Rail | Enable field | Selector field | Nominal table | Live state |
| --- | --- | --- | --- | --- |
| VEMC | `0x0a28` bit 1 | `0x0ad2` bit 8 | 3.0, 3.3 V | 3.0 V, enabled, one user |
| VMCH | `0x0a2e` bit 1 | `0x0ace` bit 8 | 3.0, 3.3 V | 3.0 V, enabled, two users |
| VMC | `0x0aaa` bit 1 | `0x0ae2` bits 10:8 | 1.2, 1.3, 1.5, 1.8, 2.0, 2.9, 3.0, 3.3 V | 3.0 V, enabled, two users |

Each rail also has a five-bit calibration field in bits 4:0 of its selector
register. The regulator API should expose the nominal selector table and leave
the existing trim untouched. Calibration values are device-specific and must
never be copied into DT or logs.

VEMC, VMCH, and E2 VMC use direct selector order. The six reversed four-voltage
LDOs listed above use raw-order voltage tables in the new driver, avoiding the
vendor driver's confusing double-remapping in `get_voltage_sel()` and
`list_voltage()`.

## RTC

The live `mt-rtc` is `rtc0`, is selected for hctosys, and exposes alarm/wakeup
state. Its MT6351 register block starts at `0x4000`, spans `0x40` bytes, uses
16-bit registers every two bytes, and has write-trigger offset `0x3c`. The
layout is the older MT6397-style variant, not the MT6358 base at `0x0588`.

Linux 7.1.3's `rtc-mt6397` logic is structurally reusable with an MT6351 match
and MFD resource at `0x4000` plus PMIC IRQ 9. A controlled set/read/alarm and
power-cycle test is still required; this experiment intentionally did not
change the RTC or alarm.

## Mainline patch boundaries

The shortest dependency-correct series is:

1. Restore MT6797 infracfg simple-reset support and reset IDs.
2. Restore MT6797 EINT controller data, 172 pin mappings, and a safe direct
   representation for pseudo-GPIO262/EINT176; add the EINT resource to the SoC
   DTS.
3. Add the MT6797 pwrap DTS node using the real 26 MHz PMICSPI mux and PMIC_AP
   gate plus reset 64. This is implemented by local patch 7.
4. Add MT6351 register/IRQ headers, MFD core data, chip-ID check, and IRQ domain.
5. Add MT6351 regulator support, initially registering all rails but wiring
   only conservative always-on and storage consumers.
6. Add MT6351 keys and RTC data, then validate wake and alarm behavior.
7. Wire VEMC to eMMC and VMCH/VMC to microSD; start at legacy bus timing and do
   not enable UHS/HS200/HS400 until voltage transitions are measured.
8. Add sound, AUXADC, charger/fuel-gauge, cpufreq, GPU OPP, and suspend features
   as independent later series.

This order prevents the PMIC driver from being reviewed or tested atop missing
reset and interrupt infrastructure, and prevents storage from relying on fixed
regulator approximations.

## Limitations

- No PMIC register was changed and no rail was toggled, so regulator control is
  not runtime-validated on mainline.
- Voltage selector tables come from public GPL source and are cross-checked
  against raw live selectors and Gray-code readback; actual rail voltage was
  not measured electrically.
- Mainline registration and control have not run on the Gemini. No buck/LDO
  coupling, ramp, suspend transition, or OPP policy has been validated.
- PMIC IRQ register fields are recovered, but no mainline IRQ-domain code has
  been executed.
- The EINT pseudo-line design requires upstream-oriented implementation review.
- RTC timekeeping, alarm wake, reset, and power-off behavior remain untested.
