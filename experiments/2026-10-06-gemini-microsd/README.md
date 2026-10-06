# Experiment: microSD H3 on the board-services package

| Field | Value |
| --- | --- |
| ID | `2026-10-06-gemini-microsd` |
| Status | DT derivation and protocol draft for review; no new kernel needed; not booted |
| Package | board-services `275a9dbf…` (input `eee771ec`) |
| Date | 2026-10-06 |
| Device action | None |

## Purpose

[microSD H3](../2026-10-04-gemini-lid-microsd-usb-re/README.md): microSD at
3.0 V should work with VMCH as `vmmc`, VMC as `vqmmc`, GPIO67 active-high card
detect and no UHS, without reproducing the vendor's trim arithmetic.

The board-services kernel already has `MMC_MTK` (which matches
`mediatek,mt6797-mmc`), `MMC_BLOCK`, `REGULATOR_MT6351`, VFAT, EXT4 and MBR
partitions. Only a composed DT is needed.

## Board facts used (public board DWS at `c5b0be85…`)

- **MSDC1 pads.** GPIO129–134 (CMD, DAT0–3, CLK) default to mode 1, MSDC1.
  DAT0–3 have pull-up enabled in the DWS; the loader applies it, and mainline
  cannot set MT6797 pull fields.
- **Card detect.** GPIO67 defaults to mode 1, named `EINT6`. Mainline's
  descriptor routes EINT6 in GPIO mode 0, and a `cd-gpios` request switches
  the pin to GPIO mode, the same path as the lid on GPIO66.

## Candidate DT

[microsd-dt.sh](microsd-dt.sh) runs the board-services derivation, then adds:

- `ldo-vmch` and `ldo-vmc` regulator nodes under the MT6351, each pinned at
  3.0 V, the vendor's value.
- One pinmux-only MSDC1 pad state, used as both `default` and `state_uhs`.
  `mtk-sd` requires both; UHS is never used.
- `&mmc1` okay: 4-bit, at most 50 MHz, `cap-sd-highspeed`, `no-1-8-v`,
  `disable-wp`, `cd-gpios = <&pio 67 GPIO_ACTIVE_HIGH>`, VMCH as `vmmc` and
  VMC as `vqmmc`.

It checks that the decompiled difference is exactly these additions. The
output is reproducible: SHA-256
`0bca279867c9c013b0ee6131b9ddd6f69718990b27fdbfa49cffa2d1865b6ede`. There is
no new schema diagnostic relative to the board-services DT.

## Protocol draft (for the custodian's review)

Admitted effects, beyond board-services:

- **Regulator registration.** VMCH and VMC at a fixed 3.0 V. The VOSEL
  register is written only if it differs; the live record shows both already
  at 3.0 V (S3).
- **Late regulator cleanup.** Both rails now have nodes, so with no card the
  core may switch them off after about 30 s; the vendor leaves VMCH on. This
  is benign for an empty slot.
- **MSDC1.** Pinmux writes to mode 1, where they already are; GPIO67 to GPIO
  mode with its EINT6 card-detect interrupt; MSDC1 clocks and controller
  init; MMC core power cycling of VMCH and VMC on card insert.
- **Not done.** No VMCH/VMC calibration write (S4), no 1.8 V switch, no
  over-current handling (S5), no write to the card.

Run:

1. Boot with no card. Record mtk-sd probe, the `vmch` and `vmc` states, and
   that the card-detect interrupt is requested.
2. Insert a known card holding a known file. Record the card enumeration
   line, the partition table, a read-only mount of the first partition, and
   the known file's checksum.
3. Remove the card and record the removal event; preserve the log; reviewed
   recovery.

Decision branches, as in H3:

- **Enumerates and reads.** The vendor trim (S4) is a non-issue at 3.0 V.
- **`vmmc` over-current or no CMD response.** Stop. Read the MT6351
  over-current status before changing anything.
- **Card detect never fires.** EINT6 routing or pull; same family as the lid
  question.

Limit: sensors H9 asks for the IOCFG_B pad fields at entry. This kernel has
no debugfs or `/dev/mem`, so that comparison stays open.
