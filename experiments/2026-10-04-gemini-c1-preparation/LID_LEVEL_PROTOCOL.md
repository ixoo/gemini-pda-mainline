# Lid level-low EINT delivery positive control: protocol draft

Status: draft for coordinator review, 2026-10-06. Patches c1/0013 (driver)
and c1/0014 (disabled DT node) are in the C1 profile. No candidate or device
action yet. Device custody, composition and the run belong to the laptop.

## Question

Under the vendor's configuration (GPIO66 in mode 0 with pull-up, input and
Schmitt enabled) does one real lid closure deliver a level-low EINT5 interrupt
to the mainline kernel?

The C1-5 boot saw GPIO66 go high, low, high with zero EINT5 dispatches under
gpio-keys, which requests both edges emulated by polarity flipping. Gemian
counted both transitions with a level-triggered interrupt on the same pin. One
delivery here proves the pad-to-EINT5-to-parent-IRQ path in this
configuration, and moves the diagnosis to edge emulation and sensitivity. No
delivery leaves routing, the detector and the upstream IRQ open. Neither
result shows that mode 1 is needed.

## Candidate shape

- **Kernel.** The C1 package built with c1/0013, c1/0014 and
  `CONFIG_GEMINI_LID_EINT_PROBE=y`. Identify it by boot2 SHA-256 and package
  inventory.
- **Device tree.** The candidate's parent DT with exactly two status edits:
  `/lid-eint-probe` okay, and the gpio-keys lid node disabled. That gives the
  probe exclusive ownership of the lid pins, GPIO66 and EINT5. GPIO mode 0 and
  the C1 pull-up, input-enable, Schmitt and debounce-0 settings are unchanged.
  Every other service is unchanged.

## Ownership and effects

| Step | Effect | Bound |
| --- | --- | --- |
| Probe | `devm_gpiod_get` input; IRQ request as level-low with auto-enable off. Standard EINT setup writes GPIO66 mode 0, direction input and Schmitt, as C1 already does, plus EINT5 sensitivity and polarity. | Once, at boot |
| Arm | One write of N seconds (1 to 300) to `/sys/kernel/debug/gemini-lid-eint-probe/arm`. It refuses unless GPIO66 reads raw high (lid open). It unmasks EINT5. | Write-once; a second write returns busy, and a refused arm is final |
| Delivery | Hard IRQ masks EINT5 at once (`disable_irq_nosync`), counts one delivery, and records the level and time. | At most one handled delivery; the line is never re-enabled |
| Timeout | If nothing arrives in N seconds, a work item masks EINT5 and records the level. | Once |
| Status | Read-only `status` file: state, delivery count, window, IRQ number and trigger type, and levels at arm, fire, timeout and now. Fire latency in ms. | Unlimited reads; no writes |

There is no polarity alternation, re-enable loop, software trigger, wake,
suspend, PMIC, radio or calibration action. No register is written outside
the standard GPIO and irqchip paths.

## Run sequence (for the custodian)

1. Boot the candidate; verify boot identity and that the probe logged "lid
   EINT probe ready … (not armed)" and that gpio-keys did not bind the lid.
2. With the lid open, read `status` (expect `state=idle`, `level_now=1`) and
   one EINT snapshot from `/sys/kernel/debug/mtk-eint-snapshot`.
3. Write the window, for example 60, to `arm`; read `status` (`state=armed`).
4. The owner closes the lid once and holds it closed for at least 2 s.
5. Read `status` and one EINT snapshot; then open the lid and read both
   again.
6. Preserve the sealed log and readings, then use the reviewed recovery path.
   No second arm in the same boot.

## Decision branches

- **`state=fired`, `deliveries=1`, `level_at_fire=0`.** The EINT5 path
  delivers in this configuration; next, compare edge emulation.
- **`state=timed-out` with `level_at_timeout=0`.** The line was low with
  level-low armed and unmasked and nothing arrived. Use the read-only snapshot
  (status, mask, sensitivity, polarity, domain) to separate a detector that
  latched without dispatch from no detection.
- **`state=timed-out` with `level_at_timeout=1`.** The closure was not
  observed or held; inconclusive. Do not repeat in this boot.
- **`state=refused`.** The lid was not open at arm; inconclusive.
- **`deliveries > 1`.** This would contradict the masking design: fail stop and
  preserve evidence.

## Limits

The `gemini,lid-eint-probe` compatible is experiment-only and has no binding,
so the composed DT gains one undocumented-compatible schema note. The probe
cannot measure detector timing finer than the snapshot reads.
