# Experiment: Gemini input and backlight recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-input-backlight-recovery` |
| Status | `completed` for static/live contract capture; hardware mainline runtime remains untested |
| Subsystem | Novatek touchscreen, AW9523 keyboard matrix, display PWM/backlight |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant not independently established |
| Date(s) | 2026-07-12 through 2026-07-14 |
| Investigator(s) | Repository maintainer with Codex assistance |
| Tracking issue | None |

## Question or hypothesis

Can the running Gemian device's input and brightness paths be represented by
existing Linux 7.1.x drivers and standard device-tree consumers, or do the
Gemini's chip-specific contracts require new driver work?

The working hypothesis is deliberately split by component: the physical
touchscreen controller may fit the upstream Novatek NVT protocol, the AW9523
should be modeled as an I2C GPIO/IRQ expander plus a matrix-keyboard consumer,
and the display brightness should use the existing MediaTek display-PWM
framework after adding MT6797 clock/resource data.

## Provenance and environment

- Live kernel: Linux `3.18.41+`, AArch64, Gemian Debian 9 userspace.
- Vendor source: Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline comparison: Linux `7.1.3` in the development VM.
- Live device: `gemini@192.168.1.50` over the owner's private LAN.
- Raw capture: `artifacts/device-inventory/20260714-input-live/input-backlight.txt`
  (Git-ignored and access-restricted; it is not a repository artifact).

## Safety assessment

The collector is read-only. It reads sysfs, procfs, the flattened live
device-tree, and filtered kernel messages. It does not read NVT firmware
interfaces, inject input events, write I2C/PWM/LED controls, scan unbound I2C
addresses, suspend the device, or access block devices and unique identifiers.

## Associated code

Run from the repository root:

```sh
mkdir -p artifacts/device-inventory/20260714-input-live
ssh -i artifacts/credentials/gemini_ed25519 \
  -o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes \
  gemini@192.168.1.50 'bash -s' \
  < experiments/2026-07-12-input-backlight-recovery/scripts/collect-live-input-backlight.sh \
  > artifacts/device-inventory/20260714-input-live/input-backlight.txt
chmod 700 artifacts/device-inventory/20260714-input-live
chmod 600 artifacts/device-inventory/20260714-input-live/input-backlight.txt
```

The output must remain below the ignored `artifacts/` tree. Review it before
sharing: even a sanitized sysfs capture can reveal local topology.

The source comparison runs in the development VM and emits only hashes,
symbols, constants, and the decision record:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-input-backlight-recovery/scripts/analyze-nvt-contract.sh
```

The vendor-kernel ELF cross-check runs without executing the image:

```sh
./scripts/dev-vm run bash -lc \
  experiments/2026-07-12-input-backlight-recovery/scripts/analyze-nvt-vendor-elf.sh
```

Its bounded output is recorded in
[`linux-nvt-elf-validation.txt`](results/linux-nvt-elf-validation.txt).

The AW9523 scan-polarity comparison is read-only and emits only source hashes,
anchors, and the consumer-level decision:

```sh
./scripts/dev-vm run env \
  VENDOR_TREE=/home/julien.guest/src/reference/planet-mt6797-3.18 \
  LINUX_TREE=/home/julien.guest/src/gemini-pda/linux-7.1.3 \
  PATCH_FILE=/mnt/gemini-pda-mainline/patches/v7.1.3/0054-arm64-dts-mediatek-add-disabled-Gemini-AW9523-keyboard-candidate.patch \
  /mnt/gemini-pda-mainline/experiments/2026-07-12-input-backlight-recovery/scripts/audit-keyboard-polarity.sh
```

Its normalized result is
[`keyboard-polarity-contract-20260714.txt`](results/keyboard-polarity-contract-20260714.txt).

## Procedure

1. Confirm the key-only, noninteractive SSH path with `BatchMode=yes`.
2. Run the collector once while the device is idle.
3. Repeat after an owner-authorized display wake/suspend cycle if lifecycle
   timing evidence is needed; do not automate a state-changing cycle.
4. Compare the capture with the pinned vendor source and Linux 7.1.3 source.

## Observations

### Touchscreen

- I2C bus 4, address `0x62`, node `/soc/i2c@11011000/cap_touch@62`.
- Runtime name/modalias are `cap_touch`/`i2c:cap_touch`; bound driver is the
  vendor `NVT-ts` driver.
- The vendor I2C node has only `compatible = "mediatek,cap_touch"`, `reg`, and
  `status`. The actual interrupt/reset/power contract lives in a separate
  pseudo-node `/soc/touch@` with `compatible = "mediatek,mt6797-touch"`.
- The live pinctrl states select GPIO85 as EINT8 for the interrupt and GPIO68
  as a reset output. The EINT summary shows `cap_touch` on line 8 with live
  activity (`534` and `70` counts in the 2026-07-14 sample; the earlier
  capture was `353` and `52`).
- The pseudo-node requests `vtouch-supply`, a `debounce` tuple, and vendor
  resolution/filter properties. The registered logical input is `mtk-tpd`,
  `phys=input/ts`, with multitouch ABS capabilities; its logical input is
  virtual rather than a direct I2C child.
- Display notifications are coupled to touch power state: the live log shows
  `mtk-tpd: LCD ON Notify`, `NVT-ts nvt_ts_resume`, `LCD OFF Notify`, and
  `NVT-ts nvt_ts_suspend` around the PWM transitions.

Linux 7.1.3 already contains `drivers/input/touchscreen/novatek-nvt-ts.c`
with `novatek,nt36672a-ts`. That driver reads controller parameters, uses two
named regulators (`vcc` and `iovcc`), a reset GPIO, an explicit IRQ, and the
standard multitouch protocol. The vendor `NVT-ts` tree is a larger NT36xxx
family implementation with trim-ID probing, DMA I2C, firmware-update work,
gesture handling, and display-notifier coupling. A fresh filtered vendor
`dmesg` capture records trim bytes `00 00 03 72 66 03`, PID `0x0101`, firmware
`0x05`/bar `0xFA`, and IRQ 392 on GPIO85. Those bytes match masked trim-table
entry 8, selecting NT36772 and event map `0x11e00`; see
[`nvt-live-trim-identity-20260714.txt`](results/nvt-live-trim-identity-20260714.txt).
This identifies the live family, but does not prove the alternate `0x01`
target-address path or mainline event protocol is runtime-compatible.
If the chip is a different NT36xxx variant, a separate driver/data path is
appropriate rather than changing the generic driver to preserve vendor
behavior.

Static source evidence makes the distinction stronger: the pinned vendor
`trim_id_table` contains NT36772 signatures (`0x55`/`0xaa` with `0x72`) and
other NT36xxx families (NT36525, NT36870, NT36676F), but no NT36672A entry.
The configured vendor driver reports ten contacts and rising-edge IRQs, while
Linux 7.1.3's small driver expects a parameter block with chip ID `0x08` for
NT36672A. The live trim capture confirms this is not an NT36672A table match;
a mainline protocol/runtime test is still required.

The vendor transport is materially different from the upstream small driver:

- hardware reset commands target address `0x62`, while bootloader and
  firmware/event transfers target address `0x01` in the vendor source. The
  vendor transfer helpers assign that supplied value directly to
  `i2c_msg.addr`; it is an alternate target address after the controller state
  transition, not a second DT client or merely an xdata-page selector;
- trim probing sends hardware reset `0x69`, software-idle `0xa5`, clear-status
  `0x35`, selects xdata `0x01f600`, then reads command `0x4e` and compares six
  ID bytes; the vendor performs another `0x69` bootloader reset before the
  reset-state and firmware-information reads;
- the NT36772 map places the event buffer at `0x11e00`; runtime reads select
  that xdata page and fetch 65 bytes from event offset `0x00`;
- firmware info is read from event offset `0x78`, and project ID from `0x9a`;
- the vendor input path reports ten slots, pressure up to 1000, touch-major up
  to 255, swaps X/Y, and reverses the resulting Y axis.

The immutable vendor-kernel ELF independently retains the NVT implementation.
Its `nvt_ts_probe` calls the reset/trim path, and the data region contains the
same eleven masked six-byte signatures and memory-map pointers as the pinned
source: eight NT36772 entries, then NT36525, NT36870, and NT36676F. Because the
vendor probe rejects an unmatched trim ID, the successful live `NVT-ts` binding
is evidence that at least one of those signatures matched during probe. The
fresh sanitized capture records the exact bytes and selected map as NT36772;
the ELF also confirms the
ten-slot/1000-pressure/255-width geometry and the explicit `0x62`/`0x01`
addressed transfer helpers; see
[`linux-nvt-elf-validation.txt`](results/linux-nvt-elf-validation.txt).

These alternate-address, xdata-bank, reset, and coordinate-transform requirements
are enough to rule out a compatible-string-only adaptation of
`novatek-nvt-ts.c`. They point to a separate NT36xxx protocol driver or a new
chip-data backend, with the firmware-update path kept opt-in and disabled by
default. A mainline transport should copy the `i2c_msg` address for each
bounded transfer and must not register an ordinary client at `0x01`.

The compact transport record is retained in
[`nt36xxx-protocol.txt`](results/nt36xxx-protocol.txt) for driver design and
review tooling. The source-derived implementation boundary and unresolved
hardware gates are in [`nt36xxx-mainline-design.md`](results/nt36xxx-mainline-design.md).
Patch `v7.1.3/0075-input-touchscreen-novatek-add-NT36772-backend.patch` now
records a disabled-by-default NT36772 backend boundary: one `0x62` I2C client,
per-message logical `0x01` transfers, bounded trim/reset probing, standard
regulator/reset/IRQ resources, and no firmware-update worker. Its object/module
compile and binding checks are recorded in
[`nt36772-mainline-boundary-20260714.txt`](results/nt36772-mainline-boundary-20260714.txt)
and the source-to-driver offset audit is in
[`nt36772-protocol-compare-20260714.txt`](results/nt36772-protocol-compare-20260714.txt);
the DT node and hardware runtime remain intentionally unvalidated.
The exact eleven masked trim entries and per-family event/memory maps are
normalized in [`nt36xxx-trim-map-metadata-20260714.txt`](results/nt36xxx-trim-map-metadata-20260714.txt)
and reproduced by [`audit-nt36xxx-trim-maps.sh`](scripts/audit-nt36xxx-trim-maps.sh).
This metadata narrows a future driver to map selection after the bounded trim
read; it does not identify the live unit by itself.
The exact vendor/Linux source revisions, blob hashes, and comparison decision
are reproducible with [`analyze-nvt-contract.sh`](scripts/analyze-nvt-contract.sh)
and recorded in [`linux-nvt-compare.txt`](results/linux-nvt-compare.txt).
The corresponding AW9523 silicon/consumer comparison is reproducible with
[`analyze-aw9523-contract.sh`](scripts/analyze-aw9523-contract.sh) and
recorded in [`aw9523-mainline-design.md`](results/aw9523-mainline-design.md).
The current source recheck confirms that Linux's AW9523 driver implements the
candidate's pull, direction, level, and port-0 open-drain pinconf operations;
its nested GPIO IRQs are edge-both while the DT `IRQ_TYPE_LEVEL_LOW` applies
only to the external INTN parent. Reset polarity, parent EINT polarity, and
the matrix electrical behavior remain hardware gates. The subsequent
source-level polarity audit narrows the matrix behavior: the generic consumer
needs `gpio-activelow` and `drive-inactive-cols` to match the vendor's
active-low scan, and patch 0054 lacked them. Follow-up patch 0076 adds both
properties while keeping the expander and matrix consumer disabled; its
source-backed decision and patch dry-run are recorded in
[`keyboard-polarity-mainline-patch-20260714.txt`](results/keyboard-polarity-mainline-patch-20260714.txt).
The normalized recheck is recorded in
[`aw9523-source-validation-20260713.txt`](results/aw9523-source-validation-20260713.txt).

The timing boundary is audited separately with
[`audit-keyboard-timing.sh`](scripts/audit-keyboard-timing.sh), using the same
immutable vendor tree and Linux 7.1.3 source:

```sh
./scripts/dev-vm run env \
  VENDOR_TREE=/home/julien.guest/src/reference/planet-mt6797-3.18 \
  LINUX_TREE=/home/julien.guest/src/gemini-pda/linux-7.1.3 \
  /mnt/gemini-pda-mainline/experiments/2026-07-12-input-backlight-recovery/scripts/audit-keyboard-timing.sh
```

The vendor driver waits 1 ms after its external interrupt, performs its first
scan after another 1 ms, and then rescans at 100 Hz. A normal transition can
therefore keep the interrupt masked while the driver performs up to 100 ten-ms
rescans; its four-row/three-column ghost-suppression path skips 50 cycles.
The retained `mediatek,aw9523-eint` node has no `debounce` tuple even though
the source asks for one and ignores the property-read error, leaving an
initialized `0,0` tuple as the source-level fallback. Linux 7.1.3
`gpio-matrix-keypad` instead schedules a full scan from row IRQs after the
optional `debounce-delay-ms` and has optional settling delays; the current
candidate omits all three timing properties, so its defaults are zero and it
has no periodic rescan. These numbers are not interchangeable. Do not add a
timing property until a mainline event trace measures bounce and settling on
the named device. The normalized result is
[`keyboard-timing-contract-20260714.txt`](results/keyboard-timing-contract-20260714.txt).

### `KEY_UNKNOWN` spare-position semantics

The vendor key table contains `KEY_UNKNOWN` at `(row=7,col=3..6)`, while the
disabled mainline DT candidate leaves those four positions out. The Linux
7.1.3 source audit shows that this is a meaningful distinction: the expanded
matrix map is zero-initialized (`KEY_RESERVED`), the scanner still emits
`MSC_SCAN`, but the input core drops the unsupported `EV_KEY` event. An
explicit `KEY_UNKNOWN` entry would advertise and emit keycode 240. The
candidate therefore continues to omit these contacts until an owner-assisted
evdev trace establishes whether they are physically populated. The normalized
source anchors and hashes are in
[`keyboard-keycode-semantics-20260714.txt`](results/keyboard-keycode-semantics-20260714.txt),
and the audit is reproducible with
[`audit-keyboard-keycode-semantics.sh`](scripts/audit-keyboard-keycode-semantics.sh).

The source and ELF audits were rerun against the same immutable vendor tree
and Linux 7.1.3 source on 2026-07-14; their normalized records are
[`nvt-source-validation-current-20260714.txt`](results/nvt-source-validation-current-20260714.txt),
[`nvt-elf-validation-20260714.txt`](results/nvt-elf-validation-20260714.txt),
and [`aw9523-source-validation-20260714.txt`](results/aw9523-source-validation-20260714.txt).
The current source rerun was byte-identical on a second invocation. The current package check is
[`mainline-input-current-71-validation-20260714.txt`](results/mainline-input-current-71-validation-20260714.txt):
the AW9523, matrix-keypad, display-PWM, and PWM-backlight objects are present,
but the Novatek touchscreen symbol is not selected, the I2C5/keyboard and
display-PWM nodes remain disabled, and no touchscreen or standard backlight
consumer is represented in the DTB. The repeatable combined package/module/DT
audit for the earlier 72-patch package is
[`mainline-display-input-current-72-package-20260714.txt`](results/mainline-display-input-current-72-package-20260714.txt);
the current 74-patch SPI-enabled package audit is
[`mainline-display-input-current-74-package-20260714.txt`](results/mainline-display-input-current-74-package-20260714.txt).
The complete 77-patch Image/DTB package, including the NT36772 and AW9523
polarity patches in the
provenance series, is recorded in
[`mainline-display-input-current-77-package-20260714.txt`](results/mainline-display-input-current-77-package-20260714.txt).

To decode a fresh capability capture without opening an input device, run the
passive parser in the VM:

```sh
./scripts/dev-vm run python3 \
  /mnt/gemini-pda-mainline/experiments/2026-07-12-input-backlight-recovery/scripts/decode-input-capabilities.py \
  /mnt/gemini-pda-mainline/artifacts/<capture>/input-backlight.txt \
  --header /home/julien.guest/src/gemini-pda/linux-7.1.3/include/uapi/linux/input-event-codes.h \
  --keymap /mnt/gemini-pda-mainline/experiments/2026-07-12-input-backlight-recovery/results/keyboard-keymap.txt
```

For the source/build comparison, create a temporary source file from the
immutable vendor checkout and add `--vendor-source <temporary-file>`; the
parser extracts the vendor driver's explicit `input_set_capability()` list
without copying the source into Git.

### Runtime capability and active-ELF provenance

A fresh passive capture on 2026-07-14 independently decodes the
`Integrated keyboard` evdev capability bitmap. It reports 53 codes: the
source-derived 52-key set is present except for `KEY_FN`, while `KEY_LEFTMETA`
and `KEY_UNKNOWN` are present instead. The installed XKB file maps `<LWIN>` to
`ISO_Level3_Shift`, which is consistent with the runtime `KEY_LEFTMETA` bit.
The retained vendor source checkout is dated 2019-04-02, whereas the running
kernel identifies itself as built on 2019-03-29; it therefore cannot be
assumed to be the exact source used for the running image. The normalized
comparison is [`live-keyboard-capability-compare-20260714.txt`](results/live-keyboard-capability-compare-20260714.txt),
and the passive decoder is [`decode-input-capabilities.py`](scripts/decode-input-capabilities.py).

The exact active boot image was then extracted from the captured `boot.img` and
reconstructed to a private ELF. Its build string matches the running kernel;
the compiled AW9523 capability list contains `KEY_LEFTMETA` and
`KEY_UNKNOWN`, not `KEY_FN`. The compiled 56-entry table maps the physical
`(row=4,col=3)` record to `KEY_LEFTMETA`, while retaining `KEY_UNKNOWN` at
`(row=7,col=3..6)`. The active-ELF result is
[`active-aw9523-elf-keymap-20260714.txt`](results/active-aw9523-elf-keymap-20260714.txt),
and the read-only analyzer is
[`analyze-active-aw9523-elf.sh`](scripts/analyze-active-aw9523-elf.sh).

This resolves the source/build discrepancy for the disabled mainline map, but
does not replace a physical transition test: no key was pressed during the
passive capture. Keep the consumer disabled until an owner-assisted evdev
press/release trace validates the physical legend, modifier behavior, and
userspace function layer.
It was built without installing loadable modules; the focused driver module
check remains recorded separately above.
The bounded current-package module recheck builds the upstream AW9523 and
matrix-keypad objects together with the new NT36772 backend and records their
guest-side hashes and aliases in
[`mainline-selected-modules-current-77-20260714.txt`](results/mainline-selected-modules-current-77-20260714.txt).
The prior 76-patch package remains historical build evidence; patch 0076 is
present in the new package but the keyboard consumer remains disabled.
This remains build/package evidence only; no mainline input, brightness, or
display runtime test was attempted.

## Current package boundary

The current reproducible package for this display/input audit is
`linux-7.1.3-gemini-a21fac4139df` (75 non-comment series entries; patchset
SHA-256 `a21fac4139dfff0f448d5e8a30a15530bf3c9bb8ae7d04f17355062478c857e3`). It packages the upstream-compatible AW9523
GPIO/IRQ expander, matrix keypad, MediaTek display PWM and backlight helpers,
the MT6797 DRM/DSI/PHY stack, and the Novatek NT36672E panel object. The
Gemini DTB keeps I2C5, the AW9523, the matrix consumer, display PWM, all eleven
display components, DSI, and the MIPI-TX PHY disabled. It contains no
touchscreen node, standard backlight consumer, or panel graph; the vendor
touchscreen's NT36xxx transport remains unresolved and is not represented by
the packaged Novatek touchscreen driver.

Run the combined audit from the VM:

```sh
./scripts/dev-vm run bash -lc \
  'CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-a21fac4139df \
   experiments/2026-07-12-input-backlight-recovery/scripts/audit-current-package-display-input.sh'
```

The corresponding read-only audit is
[`mainline-display-input-current-75-package-20260714.txt`](results/mainline-display-input-current-75-package-20260714.txt).
It confirms `gpio_keys.ko` and `CONFIG_KEYBOARD_GPIO=m`, and that the disabled
hall `SW_LID` candidate is encoded in the packaged DTB. The candidate remains
unclaimed until polarity, debounce, wake, and a controlled transition are
validated on hardware.

The audit is read-only and byte-repeatable. No input event, I2C transaction,
brightness change, display command, clock/rail transition, or hardware write
was attempted.

The disabled mainline resource-node build and targeted PWM object compile are
recorded in [`mainline-pwm-build.txt`](results/mainline-pwm-build.txt); this is
compile evidence only, not hardware support.

The mainline configuration now selects the existing `pinctrl-aw9523` and
`gpio-matrix-keypad` drivers as modules, and patch 0054 adds a disabled-only
Gemini AW9523/keymap candidate. The earlier targeted DTB build (retained as
historical evidence), focused
binding-document validation, focused schema validation, and clean object
compiles are recorded in
[`mainline-keyboard-dtb.txt`](results/mainline-keyboard-dtb.txt). This is
still compile/binding evidence, not runtime keyboard support. The authoritative
current-package keyboard boundary is recorded in
[`mainline-display-input-current-75-package-20260714.txt`](results/mainline-display-input-current-75-package-20260714.txt);
the 74- and 72-patch package records remain historical comparison evidence.

The private firmware inventory contains `novatek_ts_fw.bin`; the vendor source
requires exactly 118,784 bytes and checks version bytes at offsets `0x1a000`
and `0x1a001`. Its boot-update work is enabled in the vendor configuration and
queued 14 seconds after probe. Mainline support must not silently reproduce
that write-capable behavior. Seven private copies collected independently from
the inventory and recovery sessions are byte-identical (SHA-256
`4cab8b83dfabe89864521539fb4da9ee0fbea1737b03d5f0d3e159cd076f4f1c`); this
supports one reproducible firmware variant but does not identify the live
controller trim. The metadata-only comparison is recorded in
[`nvt-firmware-copy-audit-20260714.txt`](results/nvt-firmware-copy-audit-20260714.txt)
and can be rerun with [`audit-novatek-firmware-copies.sh`](scripts/audit-novatek-firmware-copies.sh).

The vendor `/proc/NVTflash` entry is not a safe read-only probe despite its
0444 mode: its `read` handler consumes the caller's buffer as an I2C command,
and a clear high bit selects an I2C write. It is deliberately not read by the
collector. A future ID capture must use a source-audited instrumented driver
path or the already logged probe values, never `cat /proc/NVTflash`.

The metadata-only [NVT identity-surface inventory](scripts/list-nvt-identity-surfaces.sh)
was rerun on 2026-07-14. The bound client has no attribute files, the driver
directory exposes only `bind`/`uevent`/`unbind`, and `/proc/NVTflash` remains the
only apparent endpoint. Its sanitized result is
[`nvt-identity-surface-20260714.txt`](results/nvt-identity-surface-20260714.txt);
it does not weaken the `/proc/NVTflash` safety boundary.

The earlier post-battery-recovery bounded live check found `4-0062` named
`cap_touch` and bound to `NVT-ts`, with `mtk-tpd` and EINT8 activity. `/dev/i2c-4`
is absent; this sample reports EINT8 counts `38`/`3` and no trim-ID/identity
line in the filtered dmesg. The private capture is
`artifacts/device-inventory/20260714T164000Z-touchscreen-recovery/input-backlight.txt`
(SHA-256 `75c1c38ce8383b6f0dedb0aca7c4053dafc2372fa039558418241979a8240928`).
The sanitized record is [`live-input-touchscreen-recovery-20260714.txt`](results/live-input-touchscreen-recovery-20260714.txt).
The earlier repeat result remains in
[`live-input-repeat-20260714.txt`](results/live-input-repeat-20260714.txt), and
the bounded search of readable boot/system logs also found no retained trim-ID
line (`artifacts/device-inventory/20260713-live/nvt-log-search.txt`). The
earlier sanitized identity note remains in
[`nvt-live-identity-attempt.txt`](results/nvt-live-identity-attempt.txt).

A fresh focused capture now retains the probe identity lines: trim bytes
`00 00 03 72 66 03`, PID `0x0101`, firmware `0x05`/bar `0xFA`, and IRQ 392.
The bytes match NT36772 trim-table entry 8 and select event map `0x11e00`.
The private raw capture is
`artifacts/device-inventory/20260714T181500Z-nvt-trim/nvt-trim-log.txt`
(SHA-256 `9eda78664abb02951821f3afe638c8819950d48551cd0fa7f5444c5a3cb95525`),
with sanitized evidence in
[`nvt-live-trim-identity-20260714.txt`](results/nvt-live-trim-identity-20260714.txt).
The masked-byte/source-map cross-check is reproducible with
[`validate-live-nvt-trim.py`](scripts/validate-live-nvt-trim.py) and passes in
[`nvt-trim-consistency-20260714.txt`](results/nvt-trim-consistency-20260714.txt).
The same capture records the vendor's delayed `novatek_ts_fw.bin` request,
direct-load `-2`, user-helper fallback, and checksum match; whether an update
actually occurred is not determined, and the collector itself made no
firmware request.

The live flattened device tree also contains a static
`novatek-mp-criteria-nvtpid` child under the touchscreen. Reading only its
properties reports 18 X channels, 30 Y channels, four key channels, and
configuration sizes 18/32/4; the exact arrays are retained in
[`touch-mp-criteria.txt`](results/touch-mp-criteria.txt). These are
manufacturing-test mappings, not a controller trim ID or proof that the
upstream NT36672A register protocol applies. The collector now captures these
properties in the private `input-backlight.txt` output for repeatable variant
comparisons.

### Keyboard expander

- I2C bus 5, address `0x5b`, node `/soc/i2c@1101c000/aw9523_key@5b`.
- Runtime name/modalias are `aw9523_key`/`i2c:aw9523_key`; bound driver is the
  vendor `Integrated keyboard` driver.
- The vendor DT uses GPIO58 as an expander shutdown/reset output and GPIO87 as
  EINT10 with pull-up. The live EINT summary shows `aw9523-eint` on line 10
  with activity (`367` and `5` counts in the 2026-07-14 sample; the earlier
  capture was `303` and `1`).
- Vendor source configures AW9523 port 0 as eight matrix rows, port 1 bits
  0–6 as seven scanned columns, enables port-0 interrupts, and polls/rescans
  at a 100 Hz hrtimer cadence. Its static map covers the Gemini keyboard's
  digits, letters, modifiers, arrows, punctuation, space, backspace, and
  enter; the source records the exact row/column/key-code mapping.
- The vendor scan is active-low: the selected P1 column is driven physically
  low while inactive columns are driven high, and a low P0 row bit is reported
  as a press. The generic Linux matrix consumer exposes the matching
  `gpio-activelow` and `drive-inactive-cols` properties. Patch 0054 currently
  omits both, so its disabled DT is not yet an electrically equivalent scan
  description; the source-vs-candidate comparison is in
  [`keyboard-polarity-contract-20260714.txt`](results/keyboard-polarity-contract-20260714.txt).
- The vendor driver also owns screen-notifier suspend/resume, shutdown pin
  sequencing, and an input device named `Integrated keyboard`.
- The retained-source table in `results/keyboard-keymap.txt` records all 56
  row/column positions without copying the vendor implementation. The exact
  active-boot-normalized table is
  `results/keyboard-keymap-active-boot.txt`; it changes only the physical
  `(row=4,col=3)` code to `KEY_LEFTMETA` and retains the four `KEY_UNKNOWN`
  positions.
- [`validate-keyboard-keymap.py`](scripts/validate-keyboard-keymap.py) compares
  the selected table with every `MATRIX_KEY()` entry in patch 0054. The
  current active-boot result is
  [`keymap-consistency-active-boot-20260714.txt`](results/keymap-consistency-active-boot-20260714.txt):
  52 assigned positions match exactly and the four spare positions remain
  unassigned in the DT keymap. The retained-source result is historical.
- A fresh passive capture after battery recovery again reports the separate
  `Integrated keyboard` input device, AW9523 `0x5b` binding, GPIO87/EINT10,
  and active interrupt activity (`26`/`1`). The sanitized record is
  [`live-keyboard-recovery-20260714.txt`](results/live-keyboard-recovery-20260714.txt).
- The map affects only the matrix-keypad consumer and userspace layout; it does
  not require a Gemini-specific AW9523 silicon driver. A future enabled DT
  candidate should use the active-boot-normalized matrix table, then validate
  physical legends, modifiers, rollover, and the `planetgemini` XKB model.
- The installed userspace symbols are `/usr/share/X11/xkb/symbols/planet_vndr/gemini`
  (XKB layout `us`, SHA-256
  `56baafdde43da9e3d66474f231a9bfd9d8d9fda40cd4c4af939ae1251db426cb`). They
  define the ISO-Level3/Mod5 function layer, common sleep/power/delete and
  navigation levels, and media/brightness/F1–F10 symbols. This is userspace
  symbol policy over ordinary Linux keycodes, not a reason to reproduce the
  vendor keyboard driver in kernel space; the metadata is recorded in
  [`live-keyboard-recovery-20260714.txt`](results/live-keyboard-recovery-20260714.txt).
- The vendor probe reads chip-ID register `0x10` and requires value `0x23`
  before initializing the matrix; software reset is register `0x7f` value
  `0x00`. This is source-confirmed silicon identification, while the live
  chip-ID byte was not present in the sanitized kernel-log capture. See
  [`aw9523-silicon.txt`](results/aw9523-silicon.txt).

Linux 7.1.3 already contains a generic `pinctrl-aw9523` GPIO/IRQ expander
driver (`awinic,aw9523-pinctrl`) and its binding includes a keyboard-matrix
example. Patch 0054 now supplies a disabled-only standard
`gpio-matrix-keypad`/matrix-keymap consumer, the source-derived keymap,
GPIO58 reset, GPIO87/EINT10 interrupt, and AW9523 port pinctrl states. The
candidate deliberately leaves the I2C bus, expander, and matrix consumer
disabled: expander GPIO-range mapping, electrical timing, and wake/suspend
policy still need a recoverable hardware test. Follow-up patch 0076 adds the
source-derived `gpio-activelow` and `drive-inactive-cols` properties without
enabling the consumer. No second AW9523 silicon driver or vendor polling ABI is
introduced.

### Display brightness

- No `/sys/class/backlight` device exists on the live system.
- `/sys/class/leds/lcd-backlight` exists, but the vendor display path logs
  `disp_pwm_set_backlight_cmdq(id = 0x1, level_1024 = ...)` and powers the
  display PWM around the DSI panel lifecycle. This LED-class entry is not
  evidence that the standard backlight API drives the panel.
- The live platform node is `1100f000.pwm_disp` with vendor compatible
  `mediatek,pwm_disp`; the register aperture is `0x1100f000+0x1000`. The
  vendor PWM register layout is enable `0x00`, commit `0x08`, control `0x10`,
  and period/high-width `0x14`. The source uses 1024 brightness levels and
  gates the PWM when level reaches zero.
- The vendor CCF path maps the display-PWM handle to exactly one
  `INFRA_DISP_PWM` clock. Its separate `DISP_MTCMOS_CLK` handle powers the
  display domain, while `MUX_PWM` selects the parent source. This is not the
  two-clock (`main` plus `mm`) contract assumed by the existing mainline
  `pwm-mtk-disp` binding.
- The vendor `lcd-backlight` DT entry uses `led_mode = 5` and
  `pwm_config = <0 0 0 0 0>`: source selector 0 (the vendor mux labels this
  ULPOSC/29 MHz) and divider 0, with the remaining legacy fields unused by the
  display-PWM driver. This gives a reproducible starting clock contract but
  not a verified panel-safe period until the PWM output is measured.
- The vendor panel init writes DCS `0x51, 0xff` once. Runtime brightness
  changes are logged through the display PWM path, so the current evidence
  supports a PWM-controlled backlight with DCS initialization, not a pure
  DCS brightness consumer.

Linux 7.1.3's `pwm-mtk-disp` driver already has the same register/commit shape
under the nearest `mt8173` data record. The local MT6797 extension adds a
named compatible and makes the secondary `mm` clock optional so the vendor's
single `INFRA_DISP_PWM` contract can be represented. A standard backlight
consumer is still required before the panel graph can be enabled. The ordinary `pwm-mediatek` block at
`0x11006000` is a separate four-channel infrastructure PWM and must not be
confused with the display PWM.

A 2026-07-16 audit of bsg100's hardware-working native-fbcon commit adds
contradictory but stronger runtime evidence for the mainline consumer
contract: its successful DTS uses `CLK_TOP_MUX_PWM` as `main` and
`CLK_INFRA_DISP_PWM` as `mm`, matching the upstream driver's two-clock
interface. It also records unused-clock cleanup gating the infra clock and
backlight. Patch `0044` therefore remains a disabled, source-derived
hypothesis and its optional-`mm` design must be re-audited before native
enablement. This does not contradict the narrow Candidate-E diagnostic: a
simplefb reference to `CLK_INFRA_DISP_PWM` enables its `pwm_sel` parent through
the clock tree without probing or programming the PWM controller.

## Analysis

The chipset split is real at the contract boundary, not just a naming issue:

| Function | Existing 7.1.x support | Gemini-specific gap |
| --- | --- | --- |
| NVT touch protocol | `novatek-nvt-ts`, NT11205/NT36672A | vendor node split, reset/rail names, alternate `0x01` target and NT36772 event protocol, display power coupling |
| AW9523 silicon | `pinctrl-aw9523` GPIO/IRQ | matrix keymap and board shutdown/IRQ policy |
| Display PWM | `pwm-mtk-disp` register/data framework | Resolve the vendor one-handle evidence against the hardware-working two-clock mainline consumer, then validate display-domain sequencing and the backlight graph |

No claim of runtime mainline input or backlight support is made by this
experiment. The live identity gate is now closed at the family level: the
vendor log selects NT36772 entry 8. Remaining touch gates are a source-audited
mainline transport for the alternate `0x01` target, rail/reset validation, and
runtime event/suspend testing; firmware-update paths remain excluded. Other
gates are a static AW9523 chip-ID correlation from the existing bound driver
and a mainline-disabled-DT build of the PWM/keyboard bindings.

## Conclusion

`confirmed` the live device contracts and the reuse boundaries above. The
touch controller family is identified as NT36772 from the live trim log, but
its mainline protocol/runtime remains untested; the AW9523 silicon is strongly
supported by the vendor register map and address but its mainline consumer
wiring is not yet tested; the backlight PWM register contract is strongly
supported by live sysfs, dmesg, and vendor source but no mainline consumer is
enabled.

## Follow-up

- Add a source-audited bounded NT36772 transport/runtime probe, explicitly
  excluding firmware-update interfaces; document any reset/xdata writes as
  state-changing but non-firmware activity.
- Validate the disabled AW9523 and matrix-keymap description on hardware after
  confirming GPIO range, row/column polarity, IRQ behavior, and reset timing;
  only then consider enabling the I2C bus and consumer.
- The local series currently adds an MT6797 display-PWM compatible, provisional
  one-clock contract, and disabled resource node. Re-audit it against the
  hardware-working two-clock reference before modelling a standard PWM
  backlight consumer or authorizing a full display power test.
- Link any resulting patches from `docs/HARDWARE_SUPPORT.md` and
  `docs/hardware/mt6797-live-resource-map.md`.
