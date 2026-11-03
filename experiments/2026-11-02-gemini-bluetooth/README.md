# Experiment: Bluetooth on the station, as a module, up to A2DP audio

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-bluetooth` |
| Status | `running`: T1 reached the controller next to a running Wi-Fi, and `hci0` did not come up: the core's LE init is refused. Fix built on that result; no audio yet |
| Subsystem | MT6797 CONSYS STP link, `drivers/bluetooth`, BlueZ, A2DP |
| Device variant | Planet Computers Gemini PDA, MT6797X, boot2 station |
| Date(s) | 2026-11-02 |
| Investigator(s) | project session, device custody with the custodian session |
| Tracking issue | none |

## Question or hypothesis

Can the normal Linux Bluetooth stack drive the CONSYS controller from a module on
the running station, next to Wi-Fi, and play audio to a headset over A2DP?

Hypothesis: A2DP needs only HCI commands, events and ACL data over STP task 0. With
the ROM patches and calibration the CONSYS start already performs, a small `hci_dev`
on the existing link gives working `hci0`, scanning, pairing and SBC audio. It is
falsified if the controller does not come up, or the link cannot carry the stream.

## What changed since the earlier records

The [Bluetooth document](../../docs/hardware/mt6797-bluetooth.md) and the
[2026-10-06 design](../2026-10-06-mt6797-bt-hci-design/README.md) predate the station.
Read from the current code:

- **Common init runs at every CONSYS start**, with both ROM patches and calibration,
  so the patch question in [runtime 3](../2026-10-05-mt6797-bt-h1/RUNTIME_3.md) is
  answered: the controller is patched before Bluetooth is touched.
- **A persistent STP link exists.** GNSS proved it on the device
  ([record](../2026-11-01-gemini-gnss-link/README.md)), next to a running Wi-Fi,
  including function control. It runs only while a client is attached. It takes one
  client, and a failed link can take the firmware's Wi-Fi with it.
- **`mt6797-consys` is a module, and modules load unversioned.** The running image
  has the crypto Bluetooth selects built in. The resolved configuration differs only
  by the `BT` lines, so no boot is needed.

## The change

[0511](../../patches/proposals/0511-soc-mediatek-mt6797-consys-let-Bluetooth-share-the-S.patch)
lets several clients share the link and exports Bluetooth function control.
[0512](../../patches/proposals/0512-Bluetooth-add-the-MT6797-CONSYS-controller.patch)
adds the `btmt6797` module. [The fragment](../../configs/gemini-a53-station-bluetooth.fragment)
builds the core and driver as modules, and nothing loads them at boot.

**Loading `btmt6797` powers Bluetooth for about 2 s.** `hci_register_dev` always
queues the core's setup stage, which opens the device, whatever `AutoEnable` says.
That starts the STP link next to Wi-Fi, sends the link check, turns VCN33-BT on,
sends WMT function-on and runs HCI init, then closes. With no `bluetoothd` on the
management interface, a plain `hciconfig up` does the same and leaves scans off
(read in `hci_sync.c`). A code review found this after the first version of these
patches said a loaded module touches nothing, which was wrong.

**Hazard, each time:** a WMT timeout or a link failure stops the link until the
next CONSYS reload, and the [GNSS T2 stop](../2026-11-01-gemini-gnss-link/README.md)
lost Wi-Fi's command path the same way. Recovery is a CONSYS reload. A deferred
registration would make loading inert, but adds a trigger with no other use: the
insmod is already that trigger, and nothing runs it at boot.

| Decision | Why |
| --- | --- |
| Reassemble H:4 in the link's interrupt, deliver from a work item | An unbounded queue of whole packets replaces the 2026-10-07 draft's 16-slot ring, which stopped the link when full |
| Never refuse a frame to the link | A refusal stops the link for GNSS and Wi-Fi's firmware; a bad stream resets Bluetooth only |
| Keep Gemian's Set Radio and Set TX Offset behind `gemian_radio`, off by default | They change radio settings no mainline run has changed, so turning them on is an owner decision. Without them the controller keeps its own settings |
| Leave out the vendor's sleep timeout | Nothing here sleeps or wakes the chip. It costs idle power while `hci0` is up, and none while it is down |
| Use the controller's own address | Whether it is unique is checked by the first run, without publishing it. `set_bdaddr` exists for the other case |

## Userspace recommendation

**BlueZ with [BlueALSA](https://github.com/arkq/bluez-alsa), in a small Alpine
chroot** on the RAM root.

| Option | Needs | Verdict |
| --- | --- | --- |
| BlueZ + BlueALSA | `dbus-daemon`, `bluetoothd`, `bluealsad`, about 30 MB | Standard BlueZ, plain A2DP source with SBC. `bluealsa-cli open` takes PCM on stdin, and an ALSA plugin exists |
| BlueZ + PipeWire | The above plus PipeWire, WirePlumber, Lua, session management | Nothing on the station needs a graph or policy daemon |
| A standalone A2DP stack on a raw HCI socket | No D-Bus | Not standard BlueZ; the owner asked for standard userspace |

The chroot exists because BlueZ needs `glib` and D-Bus, and the station is busybox
plus static tools. It is a distribution's signed packages at pinned versions, is
not in Git, and needs no path rewriting. Audio tools already on the station are
unaffected.

## HFP and SCO

Not built. The vendor path is the CVSD SRAM described in the
[Bluetooth document](../../docs/hardware/mt6797-bluetooth.md#cvsd-hardware-contract),
not HCI SCO. The cheap discriminating test is one SCO connection over HCI to a
headset; `BT_RFCOMM` is already in the module set so BlueALSA can try it. If the ROM
refuses it, HFP needs a Gemini `btcvsd` node, a machine-driver link and a CVSD/mSBC
bridge in userspace.

## What was and was not tested

| Check | Result |
| --- | --- |
| `btmt6797.o`, `mt6797-consys.o` in the dev VM, W=1, station configuration | no warnings |
| `checkpatch --strict` on both patches | only the MAINTAINERS note and the line length of commit text |
| [H:4 fixture](../2026-10-06-mt6797-bt-hci-design/test-bt-h4.c) on the header with the new 2048-byte buffer, ASan and UBSan | passes |
| Resolved configuration against package `27f7a9b2` | differs only by `BT`, `BT_BREDR`, `BT_LE`, `BT_LE_L2CAP_ECRED`, `BT_RFCOMM`, `BT_MT6797`, plus compiler identification |
| Buildbox package `27dd9299` (inventory `c4259df0…`), Buildbox-3 | validated; Gemini DTB identical to `27f7a9b2`; every symbol `bluetooth.ko` needs is exported by the running image |
| Review fixes (`gemian_radio`, second attach gets `-EBUSY`), dev VM, W=1 | no warnings; Buildbox package to follow |
| On the device | [T1](#t1-result-no-hci0-link-healthy-2026-11-03), below |

## T1 result: no `hci0`, link healthy (2026-11-03)

Owner approved T1. Run by the custodian on boot `7197708f`, image `6bc70ab8`'s kernel,
package `b590193b`: `btmt6797.ko` `14acf6f3…`, `bluetooth.ko` `d1600d16…`,
`mt6797-consys.ko` `2f46f1dd…`. Taint 0 before and after. Evidence is private under
`artifacts/station-work-40/boot-7197708f/bt-t1/`. Next to a live Wi-Fi on a pinned
link, with common init 285/285. No inquiry, page, scan or connection was issued.

**Observed, the same on all four opens (one on load, three cycles):**
- STP link check `result=0`. WMT BT function-on and function-off `result=0`, reply
  `02 06 01 00 00`, on patched firmware next to Wi-Fi.
- HCI init answered 24 commands with status 0, then LE Set Event Mask (`0x2001`,
  mask `d0 07 00 00 00 00 00 00`) returned status `0x20`. The core gave up with
  `Opcode 0x2001 failed: -95`, and `hciconfig up` failed.
- `STP link halted: failed=0 busy=0 discarded=0 dup=0 wmt-unsolicited=0`, firmware
  assert 0, log 0. Gateway ping 120 of 120, no disconnect. Both modules unloaded, and
  the interrupt line was gone. No Oops, warning or call trace.
- Controller: HCI and LMP version `0x08` (4.2), manufacturer 70 (MediaTek), HCI
  revision `0x0010`, LMP subversion `0x0307`. Read Local Features byte 4 is `0xdb`, so
  the LE bit is set. Read Buffer Size reports ACL 1021 bytes, 6 packets, and SCO 184
  bytes, 1 packet, so the 2048-byte H:4 buffer fits.
- Read BD_ADDR returned the **placeholder** `00:00:46:02:79:01`, the template constant
  in the vendor's `bt_conf.h`, on all three cycles.

**Read from the reply, not tested:** the Supported Commands octets 25 to 28 are all
zero, which is LE Set Event Mask and all the basic LE commands, while octets 33 and 34
list the later LE security commands. So the controller's own list contradicts its
LE feature bit. Which mask bit it refuses is unknown, and so is whether LE works on
this firmware. Gemian came up on a 3.18 core, which by inference sent a different LE mask; that mask
isn't in a capture.

**What this settles:** function-on and HCI over the shared link work next to a running
Wi-Fi at this light traffic. That is one boot, 4 opens and no ACL.

## After T1

[0523](../../patches/proposals/0523-Bluetooth-btmt6797-keep-the-core-off-LE.patch) clears
the LE bit in the Read Local Features reply, so the core skips LE init. Classic
Bluetooth is what A2DP uses. This gives up LE until someone shows it works, including
LE keyboards; the alternative, chasing each LE step the core takes with one device run
per refusal, buys nothing for this goal.

**Address.** No code changes yet. A placeholder is shared by every unit that returns it,
and `00:00:46` isn't an assignment this project holds. It works for one Gemini paired
to one headset, and pairing keys are tied to it. The standard fix is
`HCI_QUIRK_INVALID_BDADDR` plus a privately kept address set with `btmgmt public-addr`,
or a `local-bd-address` in a private device tree. The owner decides at T2 whether to
transmit with the placeholder for this first test.
