# Experiment: the NT36772 touchscreen as a loadable module on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-touchscreen-module` |
| Status | `planned`: patches and config written; no device test has run |
| Subsystem | Novatek NT36772 touch controller, I2C4, EINT8, input multitouch |
| Device variant | Planet Computers Gemini PDA, MT6797X, boot2 station |
| Date(s) | 2026-11-02 |
| Investigator(s) | project session, device custody with the custodian session |
| Tracking issue | none |

## Question or hypothesis

Can a module on the mainline station read real multitouch from the controller,
without firmware update, without touching a rail, and without a reboot between
driver changes?

Hypothesis: with I2C4 enabled and the panel left on by firmware, loading
`novatek-nt36xxx.ko` reads trim suffix `72 66 03`, firmware `0x05`/`0xfa` and
project `0x0101`, registers an input device, and reports two contacts in
separate slots when two fingers touch the screen, with the console undisturbed.

## Provenance and environment

- Public vendor kernel `planet-community/android_kernel_planetcom_mt6797`, commit
  `8cfe6596a503612e3332d9c26e292a19525a7f07`, `aeon_nt36xxx/`.
- The DTB in the retained vendor boot image, read privately; only the touch and
  I2C4 facts below are recorded.
- Linux 7.1.3 with the station series; profile `mt6797-a53-station-a72`.
- Prior records: [touchscreen study](../2026-10-31-gemini-touchscreen/README.md),
  [input recovery](../2026-07-12-input-backlight-recovery/README.md).

## Design

The upstream `novatek-nvt-ts` driver does not fit. It reads a parameter block
and touch records at the client address, while this controller answers on a
second target, `0x01`, after a reset sequence on `0x62`, behind an xdata page
([protocol comparison](../2026-07-12-input-backlight-recovery/results/nt36772-protocol-compare-20260714.txt)).
Whether it also answers the upstream interface stays untested; the chip's trim
table has no NT36672A entry.

The separate driver already exists as patch
[0075](../../patches/v7.1.3/0075-input-touchscreen-novatek-add-NT36772-backend.patch),
compile-tested only, in the station series but not in the station config. Reading
it against the public vendor driver (commit `8cfe6596`) and the retained live DTB
found what would stop a first run, fixed in
[0474](../../patches/proposals/0474-Input-novatek-nt36xxx-follow-the-vendor-s-bring-up-s.patch):

| Found | Change |
| --- | --- |
| The reset-state poll selected a page first and gave up on the first failed read; the vendor reads without selecting and retries through firmware start | Follow the vendor |
| The binding required two supplies; the vendor's chip driver manages none | Supplies optional |
| The event page was reselected on every interrupt; the vendor never does | Removed |
| The interrupt was requested before the input device was registered | Reordered |
| A first run's discriminating values were not logged | Trim, firmware block, project ID and failed event reads logged |

[0475](../../patches/proposals/0475-arm64-dts-mediatek-gemini-station-describe-the-touch.patch)
adds the node to the station device tree:

- `&i2c4` at 400 kHz, as in the vendor DTB, with no pad state. The vendor node
  sets none, and the SoC has three I2C4 routes, so firmware's mux is left alone.
- GPIO85 as EINT8, bias disabled, rising. [0377](../../patches/proposals/0377-pinctrl-mediatek-mt6797-use-the-EINT-mux-mode-on-ded.patch)
  already makes this pad deliver, as shown on EINT10.
- No supplies. The vendor DTB names `vtouch-supply` as `vldo28` on the wrapper
  node, but the chip driver never uses a regulator, and the Gemian baseline
  shows `vldo28` disabled with touch working. Its resume path requires the
  display reset and DSI commands first. That the rails are the panel's is an
  inference, tested here.
- No reset line. The vendor driver defines a GPIO output macro and never calls
  it, so GPIO68 stays unclaimed. The earlier inventory's statement that the
  driver drives it is corrected in the [hardware document](../../docs/hardware/touchscreen.md).

A new boot is needed once, because the running device tree has I2C4 disabled and
the running image has no such module. After that the module can be swapped with
`rmmod` and `insmod`.

The driver has no firmware loader. It sends the vendor probe's reset commands
(`0x69`, `0xa5`, `0x35`), which change controller state and write no flash.

## Safety assessment

New activity on I2C4 only while the module is loaded. Enabling the bus sends
nothing, and nothing loads the module. No regulator, reset line, flash or
firmware write. The possible effect is a disturbance of the panel, if the
controller reset reaches the display side; the vendor runs the same commands
with the display up. USB SSH does not depend on the panel. The boot uses the
standing boot2 approval, and the owner selects boot2.

## Associated code

[`decode-events.py`](decode-events.py) summarizes an event capture on the host:
contacts, slots, how many at once and each contact's range.

## Procedure

The request sent to the custodian holds the exact package, hashes and commands.

1. Boot the package; confirm `/sys/bus/i2c/devices/4-0062` exists unbound.
2. One `insmod`. Read the probe lines, `/proc/bus/input/devices`, `/proc/interrupts`.
3. 30 s untouched: the EINT8 count.
4. Attended, 60 s capture of the event device: one finger at each corner, then
   two fingers down together and moved. Decode with
   [`decode-events.py`](decode-events.py).
5. `rmmod`, `insmod`, one more touch: reload without a boot.

## Decision table

| Observation | Meaning | Next |
| --- | --- | --- |
| Two contacts in separate slots, positions track fingers | Hypothesis holds | Record it; orientation fixes are module-only |
| `trim identity failed` with a transfer error | Bus, pads or panel rails | Read pad modes of GPIO234, 235, 238, 239, 242, 243 from pinctrl debugfs; no retry |
| `unknown trim` | Different chip state or part | Stop and compare the logged bytes |
| Reset state timeout | Firmware did not start after reset | Compare logged state with the vendor's; check panel state |
| Firmware block invalid | Wrong page or firmware state | Compare logged block; module change |
| Probe passes, no interrupt on touch | EINT8 pad or sensing idle | Read GPIO85's mode; module change or new diagnosis |
| Interrupts, `event read failed` | Long combined read on this bus | Module change to the transfer |
| Interrupts while untouched, over 100 a second | Storm | `rmmod` at once; rethink the trigger |
| Panel disturbed | Reset reaches the display | `rmmod`, preserve logs, stop, tell the owner |

## Observations

None yet.

## Analysis

None yet.

## Conclusion

Not yet run.

## Follow-up

Not established by this work, whatever the result: suspend and resume, behaviour
when the panel is powered off, and a kernel-owned panel rather than firmware's.
