# Experiment: the caps lock LED under a Wayland session

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-13-gemini-capslock-led` |
| Status | `planned`: patches written and compile-checked in the VM, no image or boot yet |
| Subsystem | input: `matrix_keypad` caps lock LED; LEDs: `leds-aw9120` trigger |
| Device variant | named Gemini PDA (MT6797X), boot2 station and the microSD Arch root |
| Date(s) | 2026-11-13 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question or hypothesis

The owner reported that the caps lock LED never lit on the microSD Arch root under
sway (boot `e7e3b009`). The device session found `red:indicator-7` on the
`kbd-capslock` trigger, and no `inputN::capslock` LED for the keyboard.

Hypothesis: `kbd-capslock` follows the console keyboard's lock state, which doesn't
change while a compositor owns the keyboard. wlroots keeps caps lock in its own xkb
state and sends it as `EV_LED` to keyboards that declare `LED_CAPSL`.
`matrix_keypad` declares no LEDs, so nothing reached the LED. The cause is inferred
from the code, not measured.

## Change

- [0771](../../patches/proposals/0771-dt-bindings-input-gpio-matrix-keypad-add-linux-capsl.patch)
  adds `linux,capslock-trigger` to the keypad binding.
- [0772](../../patches/proposals/0772-Input-matrix_keypad-report-caps-lock-through-an-LED-.patch):
  with the property, `matrix_keypad` declares `LED_CAPSL` and passes its state to an
  LED trigger named `<device>-capslock`. The console sends its lock state to keyboards
  that declare `EV_LED`, so the one trigger serves the console too.
- [0773](../../patches/proposals/0773-arm64-dts-mediatek-gemini-station-follow-caps-lock-f.patch)
  sets the property on the station keypad and moves `red:indicator-7` from
  `kbd-capslock` to `keyboard-matrix-capslock`.
- `backlight-policy` restores `keyboard-matrix-capslock` after the screen wakes, and
  falls back to `kbd-capslock` on a kernel without it.

`matrix_keypad` is built in on the station, so this needs a new image.

Side effects, from the code:

- With `CONFIG_INPUT_LEDS`, the keyboard gains an `inputN::capslock` LED, whose default
  trigger is `kbd-capslock`. A console lock change, or that LED's first setup, sends the
  console's state to the keypad and so to the indicator. Under sway that can briefly
  show the console's state, for instance after a VT switch, until sway next sets it.
- Software that looks for `*::capslock` LEDs now finds one, such as Noctalia's lock-key
  display. That display polls, which the Arch root turned off to save wakeups.

**Checked:** the station series applies; `matrix_keypad.o` and both station DTBs
build with `W=1` on the station configuration; the binding check and `CHECK_DTBS`
report nothing for the keypad; checkpatch reports only the missing sign-off;
`backlight-policy` builds with `-Werror`. **Not checked:** no image, no boot.

## Test (predeclared)

On the first image with 0771–0773:

1. `/proc/bus/input/devices` shows the keypad with `EV_LED` and an LED bitmap of 4.
   `/sys/class/leds/red:indicator-7/trigger` reads `[keyboard-matrix-capslock]`.
2. Console: Caps Lock on, `red:indicator-7` brightness non-zero; off, 0.
3. Arch under sway: the same, read from sysfs.
4. The screen darkens and wakes: the trigger is `keyboard-matrix-capslock` again,
   and the LED shows the current state.
5. Lid closed and reopened with Caps Lock on: the LED shows the state again after
   opening.

Brightness is read from sysfs; nobody needs to judge the colour.

**Decisions.**

- If 1 fails, the property or the build is missing.
- If 2 passes and 3 fails, sway doesn't send `EV_LED`: read `EVIOCGLED` on the keypad
  while Caps Lock is on.
- If 5 fails, the lid inhibit drops the update; look at whether reopening restores
  the LED state.

## Observations

None yet.
