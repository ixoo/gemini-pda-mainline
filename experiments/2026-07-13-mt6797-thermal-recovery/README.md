# Experiment: MT6797 thermal controller and AUXADC recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-13-mt6797-thermal-recovery` |
| Status | `inconclusive` (runtime enablement remains untested) |
| Subsystem | MT6797 thermal controller, AUXADC, and calibration |
| Device variant | Gemini PDA, Gemian installation; exact keyboard/modem variant not inferred |
| Date(s) | 2026-07-13–2026-07-14 |
| Investigator(s) | Codex |
| Tracking issue | None |

## Question or hypothesis

Can the MT6797 thermal controller be represented by Linux 7.1.3's generic
MediaTek AUXADC thermal architecture, or does its hardware contract require a
new backend?

The hypothesis was that the thermal framework and IIO interfaces may be
reusable, but the MT6797 register, sensor-bank, and calibration contract must
be recovered before selecting an existing SoC driver.

## Provenance and environment

- Kernel release: live device `3.18.41+`, AArch64, MT6797X.
- Vendor source: `planet-mt6797-3.18`, commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline source: Linux `7.1.3` in the development VM.
- Live evidence: private, mode-0600
  `artifacts/device-inventory/20260714-live/thermal-auxadc.txt` (SHA-256
  `2013253cc362a4eac02b98d94d0f8c2cdd693f7ff6b6317d6ed1f67d84586bd0`); it is
  Git-ignored and contains no serials, keys, or raw firmware. The earlier
  20260713 capture remains private evidence as well.
- Source evidence: `results/mainline-thermal-source-validation.txt`.

## Safety assessment

The device procedure was read-only. The collector reads bounded sysfs, procfs,
the flattened device tree, debugfs clock summaries, interrupt counters, and
symbol names. It does not write thermal policies, enable zones, change clocks,
read `/dev/mem`, access firmware partitions, or perform suspend or thermal-trip
tests. Vendor source is treated as immutable evidence; no vendor source or
calibration dump is copied into the repository.

## Associated code

- `scripts/collect-live-thermal-auxadc.sh` — bounded device collector; run as:
  `ssh ... 'sudo -n /path/to/collect-live-thermal-auxadc.sh'`.
- `scripts/analyze-thermal-contract.sh` — bounded vendor-versus-Linux source
  comparison; run with `./scripts/dev-vm run bash -lc ...`.
- `scripts/compare-thermal-formulas.py` — deterministic arithmetic comparison
  of the vendor conversion and Linux V1 using sanitized calibration defaults;
  pass `--help` to substitute other reviewed values.
- `results/mainline-thermal-source-validation.txt` — VM ShellCheck and source
  audit output.
- `patches/v7.1.3/0057-thermal-mediatek-add-MT6797-AUXADC-support.patch` —
  disabled-only MT6797 variant for the generic AUXADC thermal framework.
- `results/mt6797-mainline-variant-validation.txt` — focused object, DTB,
  binding, and full artifact validation.
- `results/mainline-thermal-current-validation.txt` — historical component
  validation from the prior 61-patch build; current package provenance is
  recorded in the kernel-integration result after the VTS fallback safety
  correction.
- `scripts/audit-current-package-policy.sh` — read-only package, DTB, source,
  and live-capture audit; it does not load modules or touch hardware.
- `results/mainline-thermal-current-72-policy-20260714.txt` — reproducible
  audit of the authoritative package `linux-7.1.3-gemini-c2d9eea95daa`,
  including the built `auxadc_thermal.ko` and `mt6577_auxadc.ko` paths. The
  older 71-patch result remains historical provenance.
- `scripts/audit-thermal-safety-contract.sh` — read-only source/package audit
  of calibration fallback, global sensor indexing, bank/mux topology, and
  AUXADC probe side effects.
- `results/mainline-thermal-safety-contract-20260714.txt` — twice-run,
  byte-identical audit of the authoritative package (normalized output
  SHA-256 `7d43762ab7ac94e86ed248962c040cbe50cbfddf4960c63483804f0086545484`,
  final result SHA-256 `a7973d9e3c84ccbde05eff8448be06b5b8f017f69758766bc6dbf83f0c17b0ec`,
  script SHA-256 `5ec9aa877413e0f8ba18ded90dafde76469fc4f518d4ccdcc00d7802900ff2a7`).
- `scripts/audit-calibration-ownership.sh` — read-only VM audit of the
  vendor calibration word contract, LK handoff, Linux NVMEM provider matches,
  and current DT wiring.
- `results/mainline-thermal-calibration-ownership-20260714.txt` —
  byte-identical twice-run audit (normalized output SHA-256
  `2770533d1c40f792eeb561619197f4de62e3e219cd8bc9189b0ed76a79f0b30a`, final
  result SHA-256 `5dbd28df710ce1522857f3bd6bca5036a2753336c3848bb93b2ff2a119df962a`,
  script SHA-256 `3ad69980bb279539f11667adc6bc2d559c4cc64a8feed3493d54159e56c80bff`).
- `scripts/validate-atag-devinfo-contract.py` — value-redacting parser and
  synthetic self-test for the 103-word LK property, little-endian opaque-byte
  encoding, malformed-input rejection, and thermal cell ordering; its
  byte-identical self-test result is
  `results/atag-devinfo-contract-self-test-20260714.txt` (script SHA-256
  `bdb4575817757fad9026be259a23ac027eeb9d16d4a1fe4d4a2d6f66c5f18db9`, output
  SHA-256 `47ee8faf1efc8884bb43b7ef660edc3dc0cf40104af5949e7a3a74268a2662a9`).
- `results/mt6797-calibration-provider-design.md` — implementation boundary,
  exact tag layout, candidate Linux provider choices, and enablement
  invariants.
- `patches/v7.1.3/0057a-nvmem-mediatek-add-MT6797-LK-calibration-provider.patch`
  — read-only, root-only NVMEM provider for the validated LK handoff payload;
  it exposes only the ordered 12-byte thermal cell and never maps `efusec`.
- `results/mt6797-calibration-provider-build-20260714.txt` — reproducible
  72-patch prepare/configure, provider object, Gemini DTB, focused binding
  schema validation, and the completed guest-only Image/Image.gz/DTB package
  (`linux-7.1.3-gemini-a9a7c5002038`). The only remaining DTB diagnostics are
  pre-existing USB `ranges_format` warnings.
- `results/live-atag-devinfo-handoff-20260714.txt` — read-only live-device
  confirmation that the post-LK `/chosen/atag,devinfo` property has the exact
  103-word shape and expected tag; only its length and whole-property hash are
  recorded, never calibration payload words.

## Procedure

1. Read the thermal zones, vendor thermal proc entries, DT resources, debugfs
   clocks, interrupt counters, and symbol names from the named Gemian device.
2. Hash and inspect only bounded source matches from the pinned vendor tree and
   Linux 7.1.3; do not print complete vendor files.
3. Run the formula comparison with sanitized defaults, then run ShellCheck and
   the source analyzer in the development VM.

No thermal zone was enabled and no write or hardware-reset step was attempted.

## Observations

### Live device

- Thirteen vendor thermal zones enumerated. Every zone reported
  `mode=disabled` and `policy=backward_compatible` in the capture.
- The CPU thermal proc path reported approximately 25.1 °C. Other plausible
  values included battery 23.0 °C, PMIC 25.6 °C, WMT 21.0 °C, AP 26.0 °C,
  and `mtkts1`/`mtkts2` near 24.7/25.1 °C. `mtktspa=-127000`,
  `mtktsdram=2`, and `mtktsimgsensor=-275000` are sentinel/invalid values;
  they are not temperature conclusions.
- The flattened DT exposes `mediatek,mt6797-therm_ctrl` at
  `0x1100b000` + `0x1000`, vendor SPI 78 level-low (global Linux IRQ 110),
  with `therm-main`. It exposes `mediatek,mt6797-auxadc` at
  `0x11001000` + `0x1000`, vendor SPI 74 (global IRQ 106), and `efusec` at
  `0x10206000` + `0x1000`.
- The debugfs `infra_therm` clock was enabled at 136.5 MHz. The AUXADC clock
  was enabled but had no reported rate in this vendor debugfs view. The
  thermal IRQ counter was zero in the sample.
- `tzcpu_read_temperature` exposed sanitized calibration fields:
  `GE=587`, `OE=516`, `DEGC=55`, calibration enabled, slope 0, ID 0, and
  sensor offsets `155/138/133/133/129`. These are evidence of the ABI, not a
  board-wide calibration recommendation.

### Vendor source contract

- The thermal controller selects six logical banks: BIG/TS_MCU1, GPU/TS_MCU4,
  SOC/TS_MCU2+TS_MCU3, CPU-L/TS_MCU2, CPU-LL/TS_MCU2, and MCUCCI/TS_MCU2.
  The shared TS_MCU2 mapping is significant: a generic one-sensor-per-zone
  description would be wrong.
- Calibration comes from three efuse words at `0x10206180`, `0x10206184`, and
  `0x10206188`, with bitfields for ADC gain/offset, five VTS MCU/ABB offsets,
  calibration temperature, calibration-enable, ID, and slope. The vendor
  path applies ID-dependent slope handling and validity ranges before the
  integer raw-to-temperature formula.
- The pinned vendor tree contains the complete thermal implementation, not only
  headers: `mtk_tc.c`, the common `mtk_ts_cpu.c` zone glue, and the MT6797
  AUXADC driver are all present. The controller programs AUXADC channel 11
  (data register `0x40`) through indirect valid/voltage addresses, selects
  banks through `PTPCORESEL`, samples `TEMPMSR0..3`, and handles thermal
  interrupt/protection status in the controller block. This is a
  thermal-controller-plus-AUXADC contract, not merely an IIO ADC channel.
- The vendor initialization differs from Linux's current generic V1 data in
  hardware-significant constants: `TEMPADCVALIDMASK=0x2c`, a two-of-four
  sampling filter (`TEMPMSRCTL0=0x492`), and `TEMPAHBPOLL=0x30d`. It also turns
  on the APMIXED temperature-sense buffer and contains an IRQ/hardware-trip
  path. These are variant parameters and safety behavior, not evidence that
  the standard thermal framework must be replaced.

### Linux 7.1.3 comparison

Linux 7.1.3 contains generic MediaTek AUXADC and AUXADC-thermal drivers, but
their compatible tables do not include `mt6797`; their calibration and clock
data describe other SoCs. The generic thermal driver already models multiple
banks, shared sensors, mux values, efuse calibration, and optional APMIXED
buffer control, so its framework/data architecture is a close fit. However,
its V1 path omits the vendor ADC offset term and hardcodes different filter,
poll, and valid-mask values (`0x0`, `0x300`, and `0x1020` respectively, versus
the vendor `0x492`, `0x30d`, and `0x2c`). The upstream `mt6797.dtsi` also has
no enabled thermal/AUXADC nodes. Patch 0057 adds a V4 data table with the
recovered six-bank/five-sensor topology, vendor timing and valid-mask values,
APMIXED buffer controls, and an ADC-OE-aware conversion/calibration path. It
maps the MT6797 AUXADC compatible to the existing mt8173 register-shape
implementation as a compile-time candidate. Both DT nodes remain disabled
while runtime semantics and calibration ownership are unproven.

The first current-package audit also found a configuration gap: the fragment
selected the standalone AUXADC module but not the generic thermal framework.
`configs/gemini.fragment` now explicitly selects `CONFIG_MTK_THERMAL=m` and
`CONFIG_MTK_SOC_THERMAL=m`. The rebuilt package contains both
`auxadc_thermal.ko` and `mt6577_auxadc.ko`; this proves packaging and module
linkage, while the disabled DT nodes continue to prevent an unvalidated probe.

The safety-contract audit makes the remaining gate explicit. The generic
driver initializes `GE=512`, `OE=512`, every VTS slot to `260`, and `DEGC=40`;
missing or invalid `calibration-data` is logged and converted to a successful
probe. The local board DTS now wires a fixed 12-byte cell supplied by the
validated LK `/chosen/atag,devinfo` provider, while both thermal/AUXADC nodes
remain disabled. The provider rejects malformed handoff data before the
thermal parser can consume it; generic fallback defaults still must not be
treated as thermal protection. The same audit
confirms that the six-bank table passes global sensor IDs (including shared
TS_MCU2) into the conversion function, while the MT6797 AUXADC is still only
mapped to the existing `mt8173_compat` register/idle-polling candidate.

The calibration-ownership audit resolves an important boundary that the
hardware `efusec` name alone does not establish. The vendor thermal code calls
`get_devinfo_with_index(31..33)`; the vendor devinfo implementation populates
that array from the flattened `/chosen` `atag,devinfo` property rather than
reading efuse MMIO itself. The retained MT6797 LK source injects a 100-word
payload into that property on every final-FDT handoff. Linux 7.1.3's generic
MediaTek MMIO efuse provider is built into the current package, but has no
MT6797 compatible and no board DT node. Therefore direct MMIO efuse access is
not proven safe or equivalent. The vendor AUXADC source contains an efuse-MMIO
reader only under the `EFUSE_CALI` compile-time guard; the MT6797 header leaves
that guard disabled, and its calibration-preparation function is a no-op. The
preferred mainline boundary is therefore the bounded, read-only
provider/parser now present in patch 0057a (with explicit size, endian, and
validity checks); the thermal nodes stay disabled until runtime behavior and a
fail-safe invalid-calibration policy are validated.

The LK property is an opaque little-endian byte payload, not a normal
big-endian Device Tree cell array: three tag words (`size=103`,
`tag=0x41000804`) precede 100 raw `devinfo` words, followed by a
`devinfo_data_size=100` word. The vendor parser subtracts the three-word
header and consumes the first 100 words. A Linux calibration cell must expose
the MT6797 words in the order expected by `mtk_thermal_extract_efuse_v4` —
word 32, then 31, then 33 — or the extractor must be changed to parse the
payload by index. It must also reject short/overflowing tags, validate the
payload size before indexing, and convert the little-endian words explicitly.

## Analysis

The source-level result is more specific than the initial hypothesis. The
thermal framework, trip/cooling interfaces, bank model, and IIO concepts are
reusable, but the existing Linux tables do not describe MT6797. The local
variant extends `auxadc_thermal.c` rather than forcing the SoC into another
thermal compatible, and the generic mt8173 AUXADC register shape is reused only
as a candidate. The vendor ADC-offset formula differs from Linux V1 by about
0--11 °C across the representative sanitized raw values in
`compare-thermal-formulas.py`, so using V1 unchanged would be unsafe. A wholly
separate thermal driver is not justified by the recovered source yet, but it
remains an acceptable fallback if controlled runtime tests expose semantics the
generic framework cannot express.

The patch is compile- and schema-validated, not hardware-validated: the
focused thermal/AUXADC/provider objects, Gemini DTB, focused provider binding
schema, and full Image/Image.gz/DTB package pass in the VM (see the associated
build result). The MT6797 thermal nodes remain disabled, and
the AUXADC idle/wakeup mapping, IRQ/protection behavior, and no-calibration
VTSABB default are explicit runtime gates.

The first `BUILD_MODULES=1` attempt intentionally exposed a patch defect:
modpost rejected the new OF match table because it lacked a NULL sentinel.
Patch 0057 now includes the sentinel and corrected hunk metadata; the rebuilt
module package and `validate-kernel` pass. This is a source/build correction,
not hardware evidence.

Runtime support remains unproven: all vendor zones were disabled, the IRQ was
quiet, and no raw register read or mainline boot was attempted. Sentinel values
also prevent treating the vendor virtual zones as a complete sensor inventory.

## Conclusion

`confirmed` for the MT6797-specific hardware variant and source contract;
`inconclusive` for runtime thermal support. The generic MediaTek thermal
architecture is now represented by a local disabled-only MT6797 variant; no
runtime support or safe-to-enable claim is made.

## Follow-up

- The disabled-only patch now initializes the complete `MAX_NUM_VTS` fallback
  array, including `VTSABB`; do not enable the node until the new NVMEM
  provider's consumer-side behavior and an explicitly fail-closed
  invalid-calibration policy are validated.
- Preserve `/chosen/atag,devinfo` in every final LK/FDT handoff. A live
  post-LK capture now confirms the exact structural tag shape, but the
  supported-boot-path invariant still needs to be checked on a mainline
  candidate.
  Design the
  Linux calibration provider around words 31, 32, and 33 without committing
  raw values. Do not add a `mediatek,efuse`/MMIO node merely because the vendor
  tree names an `efusec` region; its MT6797 register semantics remain
  unproven.
- Recover the MT6797 AUXADC register/idle contract rather than assuming the
  `mt8173_compat` mapping is sufficient.
- Recover register reset/clock/valid-bit sequencing and IRQ status/clear rules
  from source and controlled non-primary boot tests.
- Validate AUXADC idle/wakeup behavior and raw temperatures on a controlled
  mainline boot before enabling the DT nodes; introduce trips/cooling
  separately.
- Keep vendor thermal procfs, vendor trip policy, and firmware/calibration blobs
  out of the mainline ABI.
