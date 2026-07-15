# Experiment: Gemini hall, lid, and toggle-switch recovery

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-12-hall-lid-switch-recovery` |
| Status | `inconclusive` for mainline runtime; live vendor contract captured |
| Device | Gemini PDA running Gemian, Linux `3.18.41+` |
| Subsystem | Hall/lid sensor, anti-tamper/toggle input, PMIC keypad input |
| Date | 2026-07-12 |

## Question

Can the Gemini hall/lid and toggle inputs use standard Linux GPIO/input
consumers, or does the vendor behavior require another driver?

## Provenance and safety

- Live capture: private, Git-ignored
  `artifacts/device-inventory/20260712-live/hall-lid.txt`.
- Vendor source: Planet MT6797 tree commit
  `c5b0be85017ad0c599725e8273842efdbecdd88a`.
- Mainline comparison: prepared Linux 7.1.3 source in the development VM.
- Collector is [`collect-live-hall-lid.sh`](scripts/collect-live-hall-lid.sh).
- Source audit is [`analyze-hall-lid-contract.sh`](scripts/analyze-hall-lid-contract.sh);
  sanitized output is [`hall-lid-source-audit.txt`](results/hall-lid-source-audit.txt).
- Collection reads sysfs, the flattened DT, `/proc/interrupts`, and filtered
  logs only. It does not read `/dev/input/event*`, change GPIO or IRQ state,
  enable wakeup, or stimulate either physical switch.
- A small sanitized fact table is committed as
  [`runtime-summary.txt`](results/runtime-summary.txt); the full capture stays
  private because it includes device-specific runtime details.

## Live observations

The running kernel exposes Android switch-class devices `hall` and `switch`,
both with state `0`, and a separate `ACCDET` input device. The `ACCDET` device
has an `EV_SW` capability; the `mtk-kpd` input device is a separate platform
keypad. The hall and switch interrupt counters are both zero in the capture:

| Function | Vendor DT compatible | GPIO / EINT | DT debounce | Initial trigger | Live class/input |
| --- | --- | ---: | ---: | --- | --- |
| Hall/lid | `mediatek, hall-eint` | GPIO66 / EINT5 | `0xfa00` = 64,000 µs | level-low (`<66 8>`) | switch `hall` state 0; `ACCDET` EV_SW |
| Toggle/anti-tamper | `mediatek, sw-eint` | GPIO93 / EINT16 | `0x7d000` = 512,000 µs | level-low (`<93 8>`) | switch `switch` state 0; `ACCDET` key path |

Both active pinctrl states use GPIO mode with pull-up (`pins=0x4200` for
GPIO66 and `pins=0x5d00` for GPIO93). The default states are empty in the
flattened DT. No physical open/close, left/right, or tamper transition was
performed, so the logical meanings of the current level are not promoted to
hardware-validated facts.

The post-battery-recovery passive capture remains topologically identical. The
hall class and `ACCDET` `EV_SW` path are still state `0`; EINT5 reports `3`/`0`
counts in this sample, while EINT16 remains `0`/`0`. No transition was
stimulated and neither wake policy nor polarity was changed. The sanitized
record is [`live-hall-lid-recovery-20260714.txt`](results/live-hall-lid-recovery-20260714.txt).

## Vendor behavior

The vendor `hall.c` and `switch.c` drivers are not generic GPIO consumers:

- Hall queues work from a level-sensitive EINT, reads the GPIO, emits
  `EV_SW/SW_LID` on the shared `kpd_accdet_dev` (`ACCDET` in the live input
  inventory), updates the Android switch-class device `hall`, reverses the
  IRQ level polarity for the next state, reapplies debounce, and re-enables
  the IRQ.
- The toggle driver uses the same workqueue/level-IRQ pattern, emits a 10 ms
  `KEY_F9` pulse for the low/left state and `KEY_F10` for high/right, and also
  updates the Android switch-class device `switch`. The vendor board source
  labels this node `anti-tamper`; its user-visible meaning is not independently
  established.
- Both drivers carry Android wakelock and `kpd_wakeup_src_setting()` policy.
  That policy must not be copied until wake ownership is tested.
- Both probes read the GPIO before assigning the DT-derived GPIO number. This
  ordering can leave the initial state at the global default rather than the
  physical pin level; a mainline implementation must acquire the descriptor
  first and then sample it.

The source audit records the exact vendor hashes and anchors without copying
the implementation into this repository.

## Mainline comparison

Linux 7.1.3 has no Android switch-class API and no MT6797 hall/toggle driver.
Its `gpio-keys` driver and binding already support:

- GPIO descriptors and interrupt-driven input;
- `linux,input-type = <EV_SW>` with `linux,code = <SW_LID>`;
- `debounce-interval`; and
- optional `wakeup-source` policy.

Therefore the hall path is a standard-input candidate, not evidence for a new
MT6797 silicon driver. A disabled-only board description can use `gpio-keys`
for `SW_LID` once the GPIO polarity, debounce unit, and wake behavior are
confirmed. The toggle path is different: the vendor emits two mutually
exclusive key pulses and a legacy switch state. Do not invent a `switch` class
ABI; first determine whether GPIO93 is genuinely an anti-tamper input or a
user-facing slider, then choose a standard `EV_SW` or key policy.

Patch `0074-arm64-dts-mediatek-gemini-add-disabled-hall-gpio-keys-candidate`
records that boundary as a disabled-only `gpio-keys` consumer: GPIO66 with
`GPIO_ACTIVE_LOW`, `EV_SW/SW_LID`, and a 64 ms debounce. The pinmux hunk is
deliberately GPIO-mode only because the current MT6797 pinctrl binding does not
provide a verified board pull/drive configuration. The node has no
`wakeup-source`, and the package still leaves it disabled. The 75-patch package
audit confirms the exact DTB cells and `gpio_keys.ko`; see
[`mainline-display-input-current-75-package-20260714.txt`](../2026-07-12-input-backlight-recovery/results/mainline-display-input-current-75-package-20260714.txt).

## Conclusion

`inconclusive` for runtime mainline support, but the driver boundary is clear:
reuse standard Linux GPIO/input infrastructure for the hall/lid signal; do not
write a new MT6797 hall driver. The toggle signal needs a board-policy decision
before it can be represented safely, not a copy of the vendor Android switch
driver. The PMIC power-key path remains separately documented by the MT6351
experiment and should continue to use distinct press/release IRQs.

## Follow-up gates

1. With an external console and recovery path, capture a single owner-approved
   lid transition and confirm GPIO66 level, `SW_LID` value, and EINT polarity.
2. Identify GPIO93’s physical anti-tamper/slider function before selecting
   `EV_SW` versus `KEY_F9`/`KEY_F10` semantics.
3. Add only disabled DT input consumers first; keep wakeup disabled until a
   suspend/resume protocol and recovery path exist.
4. Validate that the mainline input device is separate from the PMIC keypad
   and does not reproduce Android switch-class files.
