# Experiment: Gemini keyboard input research

## Record

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-keyboard-input` |
| Status | `completed` for the static source, independent-document and firmware study; no hardware behaviour is claimed |
| Subsystem | AW9523B matrix keyboard, PMIC power/volume keys, lid suppression, boot-chain key handling |
| Device variant | Planet Computers Gemini PDA, MT6797X, vendor Android/Gemian 3.18 stack |
| Date(s) | 2026-10-31 |
| Investigator(s) | Gemini mainline project |
| Tracking issue | keyboard acceptance items in the roadmap |

## Question or hypothesis

What else can be established about Gemini keyboard input from the vendor
driver, the shared Planet keyboard documentation, the boot chain and the
retained firmware — beyond the already-observed matrix, keymap and console
behaviour?

The hypothesis was that the remaining open items (unconnected contacts, the
Fn/Meta label, ghosting, wake, lid interaction, LEDs) are answerable from
source and independent documentation without new device work.

## Provenance and environment

- Vendor kernel `planet-community/android_kernel_planetcom_mt6797`, commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`:
  `drivers/misc/mediatek/aw9523/aw9523_key.{c,h}`,
  `drivers/input/hall/hall.c`, the MT6797 DTS key/hall nodes.
- Planet community keyboard documentation:
  `planet-community/planet-psion-kpd-driver` (`docs/key-matrix.md`,
  `docs/hardware-overview.md`, `docs/device-comparison.md`).
- LK `dguidipc/gemini-lk-android8` commit `f4988d74`: `platform/mt6797/mtk_key.c`,
  `mt_pmic.c`, `mt_boot.c`.
- Retained private preloader and LK images; Gemian configuration
  (`CONFIG_MTK_HALL=y`, `CONFIG_AW9523_HALL` enabled in the driver, FB gating
  commented out).
- Prior evidence: the [keyboard hardware document](../../docs/hardware/keyboard.md)
  and its experiment index.

## Safety assessment

Read-only. No device access, no input injection, no boot candidate. Private
firmware stayed outside Git; only conclusions and short public citations are
recorded.

## Procedure

1. Read the vendor keyboard keymap, scan work, ghost-suppression logic, lid and
   screen gating, IRQ setup and input-device registration.
2. Compare with the independent Planet keyboard documentation for the same PCB.
3. Read the boot-chain key handling in preloader and LK.
4. Reconcile with the current hardware document and record what changes.

## Observations

- [Keyboard input inventory](results/keyboard-input-inventory.md) — keymap,
  scan/ghost logic, lid/wake, boot chain and independent-document comparison
  with citations.

The decisive observations:

1. The four unknown matrix positions are exactly `P0_7 × P1_3/4/5/6`; the
   vendor keymap marks them `KEY_UNKNOWN`, and the shared Planet documentation
   calls them unconnected. The shared keyboard PCB is used on Gemini, Cosmo and
   Astro.
2. Gemini reports the modifier at `P0_4/P1_3` as `KEY_LEFTMETA`; `KEY_FN` is the
   Astro variant. The current vendor source agrees with the active binary, so
   the earlier source/binary discrepancy is a device-family mix-up, not a
   snapshot difference.
3. The physical power button is a PMIC key, not a matrix key. Bare power is
   reported as `KEY_ESC` on Android; `Meta + Esc` is the power action, and the
   Gemini HAL does not implement that interlock, so it is userspace policy.
4. The vendor scan is interrupt-driven: EINT → 1 ms delayed work → a 1 ms fast
   scan while keys change → 10 ms rescans while keys are held. Ghosting is
   suppressed by blocking ambiguous keys until a modifier is released, with a
   dedicated ctrl+shift z/x/c/v exception; columns 3 and 6 are swapped in the
   event loop.
5. The lid sensor is GPIO66/EINT with `CONFIG_MTK_HALL=y`; the keyboard driver
   registers a hall notifier and suppresses keys while the lid is closed. The
   independent Planet table that lists Gemini as lacking hall suppression does
   not match this source.
6. The keyboard driver registers no wakeup source (`device_init_wakeup`,
   `enable_irq_wake` and `input_dev` wakeup are absent), so the matrix does not
   wake the device; the PMIC power key is the wake path.
7. Gemini has no keyboard backlight; the AW9523 LED-mode and DIM registers are
   defined but unused. The legacy `IIC_ADDRESS_WRITE 0xB0` header value is a
   stale 7-bit 0x58; the driver uses the DT `reg = <0x5b>`.
8. The boot chain reads only PMIC keys: the preloader detects the power key and
   sets KPD GPIO mode, and LK uses PMIC power/volume keys for boot menus and
   charging-mode decisions. Neither scans the AW9523 matrix.

## Analysis

The remaining keyboard questions are mostly about policy and routing rather
than an unknown matrix. The vendor source answers ghosting, lid suppression and
wake: ghosting is explicitly limited and worked around, the lid suppresses
input through a hall notifier, and the matrix is not a wake source. The
independent Planet documentation resolves the unconnected positions and the
Meta/Fn split, but its Gemini hall and FM-wakeup rows conflict with this tree
and are treated as unverified.

The practical consequence for mainline is unchanged in architecture but clearer
in scope: polling is sufficient for typing, an IRQ path would need the GPIO87
EINT route, wake requires a different owner (PMIC power key), and the lid must
gate input if the matrix is enabled while the lid is closed.

## Conclusion

`confirmed`, scoped to this vendor tree, the LK tree, the retained firmware and
the published Planet keyboard documentation: the unconnected positions, the
Meta/Fn resolution, the power-key topology, the scan and ghosting policy, lid
suppression in source, absence of matrix wake, no keyboard backlight, and the
boot-chain key handling.

Not established: the lid suppression on hardware (source-only), the stale
address macro's history, the independent table's FM-wakeup claim, and any
latency/rollover measurement.

## Follow-up

- Durable update: [Gemini PDA keyboard](../../docs/hardware/keyboard.md).
- Next discriminating work: a lid-closed key injection on the station, and an
  IRQ-versus-polling latency comparison, before changing the mainline input
  profile.
