# Experiment: first-boot probe dependency audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-14-first-boot-probe-audit` |
| Status | `completed` for static source/DT/package analysis; runtime mainline boot remains untested |
| Subsystem | MT6797 boot console, PWRAP/MT6351, regulator, and MSDC probe ordering |
| Device variant | Gemini PDA running Gemian; exact retail sub-variant is not independently established |
| Date | 2026-07-14 |

## Question

Is the deliberately small “UART + eMMC” first-boot target independent of the
PMIC, or does the board DT make PWRAP/MT6351 part of the storage probe path?

## Method and safety

The audit reads the exact Linux 7.1.3 source tree and the selected packaged
kernel artifact,
its generated Gemini DTB, configuration, and `System.map`. It decompiles the
DTB with `dtc`, queries properties with `fdtget`, and prints source anchors and
hashes. It is entirely read-only: no device access, driver bind/unbind, bus
scan, boot, or hardware write was performed.

Run it in the VM with:

```sh
./scripts/dev-vm run env \
  CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-c2d9eea95daa \
  experiments/2026-07-14-first-boot-probe-audit/scripts/audit-first-boot-probes.sh
```

The historical package output is
[`results/first-boot-probe-audit-20260714.txt`](results/first-boot-probe-audit-20260714.txt)
(SHA-256 `de807cd43b9e48bae709800f21bf4da067fb921c6ad4e460933edd7bbce6984a`).

The current 72-patch integrated rerun adds the generic ARM64 entry, GIC, PSCI,
and architectural-timer ownership to the same graph:
[`results/first-boot-probe-audit-current-72-package-20260714.txt`](results/first-boot-probe-audit-current-72-package-20260714.txt)
(audit output SHA-256
`90bcaf200ca914949774e8ed75f032f9f9c1355a904db97766b512a8b6b433b2`).
The expanded collector/audit script SHA-256 is
`c7d7873b70eb94e331a3449428de668fe2aeed88fd502bd3c04f960e78036caa`.

The current Gemini DTB is also validated against the merged Linux schema with
the bounded helper (it does not rebuild unrelated arm64 boards):

```sh
./scripts/dev-vm run env \
  CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-c2d9eea95daa \
  experiments/2026-07-14-first-boot-probe-audit/scripts/validate-gemini-dtb-schema.sh
```

The current 72-patch result is
[`results/gemini-dtb-schema-current-72-package-20260714.txt`](results/gemini-dtb-schema-current-72-package-20260714.txt): `dt-validate` 2026.6
passes with an empty diagnostic stream for the packaged Gemini DTB, and a
second run is byte-identical. The helper generates the merged schema through
Linux's `dt_binding_schemas` target, which is the portable 7.1.x interface;
invoking the generated JSON path directly is not reliable. This is a
binding/schema result only; it does not prove that the bootloader hands Linux
the same DTB or that any consumer probes on hardware.

The decompiler's two warnings on each MT6797 DTB are the same upstream-style
`ranges_format` diagnostics for the SSUSB parent: its empty `ranges` property
intentionally has local one-cell child address/size declarations while the
root uses two cells. They are decompilation-format warnings, not
`dt-validate` failures; the merged schema check remains empty for all three
boards.

Because the series changes shared `mt6797.dtsi` data, the three packaged
MT6797 boards are also checked together with the bounded validator
[`scripts/validate-mt6797-dtb-schema.sh`](scripts/validate-mt6797-dtb-schema.sh).
Run it with:

```sh
./scripts/dev-vm run env \
  CURRENT_PACKAGE=/home/julien.guest/artifacts/gemini-pda/linux-7.1.3-gemini-c2d9eea95daa \
  experiments/2026-07-14-first-boot-probe-audit/scripts/validate-mt6797-dtb-schema.sh
```

The current result
[`results/mt6797-dtb-schema-bounded-current-72-20260714.txt`](results/mt6797-dtb-schema-bounded-current-72-20260714.txt)
passes `mt6797-evb.dtb`, `mt6797-gemini-pda.dtb`, and `mt6797-x20-dev.dtb`
with zero diagnostics, and its output is byte-identical on a second run
(result SHA-256 `81ba6033a0ec217c1cc367a1e9e83380807a8fa44bd759b2f1e08f121d8bf600`).
This guards reference-board schema compatibility; it remains static evidence
only.

The first-boot source path is also checked with compiler warnings and sparse:

```sh
./scripts/dev-vm run \
  experiments/2026-07-14-first-boot-probe-audit/scripts/audit-first-boot-static-check.sh
```

The [recorded result](results/first-boot-static-compile-20260714.txt) passes
all seven targeted directories (`8250_mtk`, MT6797 pinctrl, PWRAP, MT6351
MFD/regulator, watchdog, and MSDC) with zero diagnostics. This raises
confidence in the static source path only; it does not replace a UART boot or
PMIC/eMMC hardware readback.

A fresh owner-authorized, read-only vendor snapshot was collected after the
static checks. The sanitized comparison is
[`results/live-runtime-snapshot-20260714.txt`](results/live-runtime-snapshot-20260714.txt);
its SHA-256 is
`8692a4368704f850e0c7a31bbf7f53d1f1b770ddaf439c9ad88ea9abfe64b178`.
The raw captures remain mode-0600 and Git-ignored under
`artifacts/device-inventory/20260714-live/`. It confirms the same `3.18.41+`
`MT6797X` baseline, `ttyMT0` console, MT6351-backed storage rails, and DF4064
eMMC on MSDC0. No stateful PMIC chip-ID, regulator-register, or MSDC-register
read was repeated, and no hardware was written.

The private LK candidate used for the next gate is independently tied to the
same package/Image.gz/DTB hashes in the
[current 72-patch boot-candidate result](../2026-07-12-boot-contract-recovery/results/mainline-72-lk-candidate-current-20260714.txt).
Its parser checks pass, but LK acceptance and runtime boot remain unobserved.

The current 76-patch rerun uses package
`linux-7.1.3-gemini-db59a88057b4`. The Gemini DTB and all three MT6797 board
DTBs pass the merged Linux schema with zero diagnostics, and the built-in
first-boot chain remains generic ARM64 entry/GIC/PSCI/timer, UART0, pinctrl,
watchdog, PWRAP/MT6351, and conservative 25 MHz MSDC0. The sanitized current
record is
[`first-boot-probe-audit-current-76-package-20260714.txt`](results/first-boot-probe-audit-current-76-package-20260714.txt).
This is still static evidence; the matching 76-patch LK candidate is private,
untransferred, and unbooted.

## Observations

The integrated current-package audit confirms that the board's first consumers
sit below a generic built-in ARM64 handoff: ten CPU nodes use PSCI, the GIC and
architectural timer are present, and the corresponding PSCI/CPU-idle/timer/GIC
probe symbols are linked into `Image`. The DT has no CPU OPP, idle-state,
release-address, or per-CPU frequency properties, so no DVFS or vendor deep-idle
path is silently pulled into this first-boot graph.

The packaged DTB enables UART0 and MSDC0. PWRAP, its MT6351 child, the
regulator container, and the watchdog have no `status` property, so they are
implicitly enabled. MSDC0’s `vmmc-supply` and `vqmmc-supply` point into the
MT6351 regulator container: `vemc_3v3` is `regulator-boot-on` at 3.0–3.3 V,
and `vio18` is `regulator-always-on` at 1.8 V. The microSD host remains
disabled.

The built-in `8250_mtk` probe enables the named baud and bus clocks before
registering the 8250 port; console activity later adds normal UART register
writes. The built-in `mtk_wdt` probe reads `WDT_MODE` and, if LK left TOPRGU
running, rewrites the timeout and reloads the watchdog during registration.
With `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y`, the watchdog core also schedules
kernel keepalives until userspace takes over. A disabled TOPRGU is only
registered and does not start itself through this path.

The source path is not read-only even when LK has initialized PWRAP:

* `pwrap_probe()` enables its clocks, checks `PWRAP_INIT_DONE2`, and, after the
  optional init path, writes PWRAP watchdog source, timer, interrupt-enable,
  and IRQ state before populating the PMIC child.
* `mt6397_probe()` reads the PMIC ID, and `mt6397_irq_init()` writes all four
  MT6351 interrupt mask banks before registering the nested IRQ.
* `mt6351_regulator_probe()` reads `SWCID` and buck VSEL-control state and
  registers the rail descriptors without selecting a new voltage.
* `msdc_drv_probe()` obtains both regulator supplies. During MMC power-state
  transitions, the host can enable `vqmmc` and set the `vmmc` OCR, so the
  eMMC consumer can change PMIC rail state after host registration.

## Analysis and conclusion

The hypothesis that the first-boot storage path is PMIC-independent is
rejected for this exact DT and package. The minimum dependency chain is:

```text
ARM64 entry -> GIC + PSCI + architectural timer
        |
        v
UART0/pinctrl + clocks
        |
        v
PWRAP -> MT6351 MFD/IRQ -> MT6351 regulator provider
                                      |
                                      v
                               MSDC0/eMMC
```

This does not imply that the rail tables or voltage programming are correct on
hardware. It means a first mainline runtime test must capture PWRAP/PMIC state
before and after boot, use an external recovery path, and keep the eMMC at the
conservative 25 MHz legacy timing until the probe and read-only I/O are proven.
The current board DT therefore remains intentionally conservative; no patch
was changed by this experiment.

## Follow-up

The same read-only dependency audit was rerun against the current 74-patch
module-bearing package after the SPI additions. The result is
[`results/first-boot-probe-audit-current-74-package-20260714.txt`](results/first-boot-probe-audit-current-74-package-20260714.txt).
It preserves the same first-boot chain and confirms that patches 0072–0073 do
not alter the UART/PWRAP/MT6351/MSDC dependency boundary. The two direct VM
runs were byte-identical; this remains static package evidence and not a
mainline hardware boot.

The bounded merged-schema check was also rerun against the same current
package. [`results/mt6797-dtb-schema-bounded-current-74-20260714.txt`](results/mt6797-dtb-schema-bounded-current-74-20260714.txt)
passes `mt6797-evb`, `mt6797-gemini-pda`, and `mt6797-x20-dev` with zero
diagnostics and byte-identical output on the repeat run.

The focused 75-patch package rerun is
[`results/first-boot-probe-audit-current-75-package-20260714.txt`](results/first-boot-probe-audit-current-75-package-20260714.txt)
(SHA-256 `b55b4c6b183786077beeac84cef1de7f8a0f3645036a46ae53d27c90c4e11c55`).
It preserves the same built-in ARM64 → UART0 → PWRAP → MT6351 → regulator →
MSDC0 chain; patch 0074 only adds a disabled GPIO-key consumer and does not
change first-boot ownership. Runtime mainline boot remains untested.

* Add a recovery-backed first boot with serial logging and before/after PWRAP,
  PMIC interrupt-mask, and regulator selector capture.
* If PWRAP is already initialized by LK, compare its post-probe register image
  against the vendor baseline before enabling additional PMIC consumers.
* Keep audio, USB, display, sensor, and modem consumers disabled until their
  own ownership boundaries are separately evidenced.
