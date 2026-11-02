# Experiment: the NT36772 touchscreen as a loadable module on the station

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-touchscreen-module` |
| Status | `running`: T1 showed real multitouch from the module on its first load, and no interrupts after `rmmod` and `insmod`; that reload failure is under test |
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

1. Boot the package; confirm the client exists unbound (`1-0062`: the bus is numbered 1 on mainline).
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

Package, not yet run: commit `99a93617`, profile `mt6797-a53-station-a72`, modules
built, Buildbox-2, `SHA256SUMS` `529ff1d4`, `Image.gz` `090cf797`, station-a72 DTB
`d65c3251`, `novatek-nt36xxx.ko` `34328321`. Its DTB carries the node at `0x62` with
EINT8 rising. Its patches and configs differ from boot2's `114d21cc` only by 0474,
0475 and the config line. The module compiled with no warnings at `W=1`; the DT
schemas and `dtbs_check` were not run. Request sent to the custodian.

### T1, boot `6c68923b`, boot2 image `cf18cd7f`, module `34328321`

The first load matched the hypothesis on all counts checked:

```text
novatek-nt36xxx 1-0062: trim 00 00 03 72 66 03
novatek-nt36xxx 1-0062: firmware information 05 fa 12 20 04 38 08 70 0e 0a 00 01 01 00 08 12
novatek-nt36xxx 1-0062: firmware 0x05, project 0x0101, 1080x2160
```

| Step | Result |
| --- | --- |
| Probe | `insmod` 0 in 152 ms, on no supply and no reset line; `Edge` on EINT8; tainted 0 |
| Console | Owner: unchanged after load |
| Untouched, 30 s | 0 interrupts |
| One finger, 60 s | 717 interrupts, 10 contacts, most at once 1 |
| Several fingers, 60 s | 1511 interrupts, 23 contacts, most at once 3, in slots 0, 1 and 2 |
| `rmmod`, `insmod` | Both 0, the same probe log |
| After the reload, 15 s, then 30 s more | 0 interrupts and 0 events; whether the owner touched is being confirmed |

`pin_config_group_set op failed for group 85` appears on both loads, including
the one that worked. It is the `bias-disable` of the pad state; the pad setup that
matters happens when the interrupt is requested.

Captures hold positions from x 187 to 2108 and y 157 to 899, inside the declared
0..2159 and 0..1079. Moves along the long side change x and moves along the short
side change y, and the first three taps of the corner sequence run left to right
along the top. That suggests the vendor's transform suits the landscape console,
but no one compared a touch with a mark on the screen. The corners did not reach
the range's ends, so edge accuracy is unmeasured.

Not shown: reload, a fourth or later contact, positions checked on screen, suspend
or a panel power cycle.

The second capture and the 30 s capture after reload were the custodian's
additions, both only reads of the event node.

## Analysis

The hypothesis holds for a first load: the rails are up without a supply being
named, the second target answers, EINT8 delivers rising edges, and contacts are
reported in separate slots. That supports the rails being the panel's or
otherwise always on; it does not identify them.

The reload does not work, so the module cannot yet be iterated without a boot,
which was part of the goal. Probe logs are identical on both loads, so the
controller answers I2C and its reset completes. T2 reads the dead state to place
the fault at the pad, the EINT controller, the INT line or the firmware.

## Conclusion

Partly `confirmed` on one boot: real multitouch from a loadable module on the
first load. Not confirmed: reload.

## Follow-up

Not established by this work, whatever the result: suspend and resume, behaviour
when the panel is powered off, and a kernel-owned panel rather than firmware's.
