# Experiment: Bluetooth on the station, as a module, up to A2DP audio

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-bluetooth` |
| Status | `completed` for A2DP. T3 to T5b: no voice crosses HCI. The CVSD SRAM path carried voice in loopback, and capture through the driver decodes at the right rate on one run. T5's hang is unexplained, playback is untested, and the bridge isn't built. Earlier: the owner heard A2DP audio from the station on a stock BlueZ stack, on one boot, including next to a joined Wi-Fi carrying only a ping. What fixed T2's stall is not established |
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

## T1b result: LE gone, refused at MWS (2026-11-03)

Same boot, by the custodian's judgment within the owner's T1 go-ahead, with
`btmt6797.ko` `24180242…`. Private evidence under
`artifacts/station-work-40/boot-7197708f/bt-t1b/`. **Wi-Fi was not up:** `wlan0` would
not come back up after T1's teardown (`Operation not supported`), so this run says
nothing about concurrent operation. Whether Bluetooth played a part is not
established. The code reads as if taking `wlan0` down closes it until `mac` reloads.

**Observed on all four opens:** no LE command, so 0523 does what it says. Init reaches
`0x140c`, Get MWS Transport Layer Configuration, which returns status `0x02`, so
`hciconfig up` fails. The link is healthy as in T1: `failed=0`, no assert, no call trace.

**Read from public source:** Gemian's 3.18 `hci_core.c` has this exact command under
`#if 0`, with a note that it fails the whole init because of the chip. So it is the
chip, not a state we failed to set.
[0524](../../patches/proposals/0524-Bluetooth-btmt6797-don-t-ask-for-the-MWS-transport-c.patch)
sets the core's existing quirk for it.

**For later LE work, inferred:** that same core's LE mask is `0x0f` plus LTK and
connection parameters, with nothing above `0x20`. The refused mask `d0 07` adds the
P-256, DHKey, enhanced-connection and direct-advertising events. So the refusal probably
concerns one of those, and the base LE events may be fine.

## T1c result: `hci0` up (2026-11-03)

Same boot, `btmt6797.ko` `44875a17…`, bluetooth `d1600d16…`, by the custodian's judgment
within the owner's go-ahead. Private evidence under
`artifacts/station-work-40/boot-7197708f/bt-t1c/`. Run with `wlan0` down and `mac`
loaded, so it shows nothing about `hci0` up next to a joined Wi-Fi. T1 did show
function-on next to one.

**Observed:** all 3 `hciconfig hci0 up` returned 0 and reported `UP RUNNING`. Four opens and
closes, 112 commands, every status 0, no LE command, and no inquiry, page, scan enable or
connection opcode. Every halt `failed=0 busy=0 discarded=0`, firmware assert 0, log 0.
No Oops, warning or call trace. Both modules unload.

**Not shown:** anything on the air. No ACL or SCO data has moved. The address is still the
placeholder, and no management step (`bluetoothd`) has run, so its commands, including
scan enable, are untested.

**Tested in the dev VM, no Bluetooth there:** the chroot's `dbus-daemon` and `bluealsa`
start, `bluealsa` lists SBC only, and the ALSA plugin resolves `bluealsa:` as far as its
D-Bus query. `bluetoothd` has no adapter there.

## T2 result: pairing works, the stream stops the link (2026-11-03)

First Bluetooth transmission on mainline, with the owner's go-ahead: first transmission
yes, `gemian_radio` off, placeholder address. Run by the custodian on boot `7197708f`,
`btmt6797.ko` `44875a17…`, `bt-root` `beb82037…`, Wi-Fi down. Budget used: 1 inquiry
session, 1 pairing, 1 A2DP connection, under 3 minutes radio-on. Evidence, including the
device's name and both addresses, is private under
`artifacts/station-work-40/boot-7197708f/bt-t2/`. The custodian ran a copy of the script
with one change to the `pair` step, since taken into the script: another client's
`scan off` doesn't stop an inquiry. **The owner reports:** "I heard the connection chime,
then silence." So no audio was heard, and whether any reached the headset's decoder is not
established. 0.19 s is probably shorter than its buffering (inferred).

**Observed:**
- `power on` passed, 29 commands, no refusal. So `bluetoothd`'s management step works,
  with the LE and MWS fixes.
- The headset was found 4 s into the inquiry. `pair`, `trust` and `connect` each returned 0,
  and BlueALSA listed the A2DP sink.
- A stream started: ACL frames of 850 and 136 bytes alternating, one pair about every
  23 ms, about 43 kB/s. It lasted **0.19 s** in the capture, 17 ACL packets.
- `STP link stopped (-110)`, an ACK timeout. Halt: `failed=-110 rx=676 tx=549 acks=676`,
  firmware assert 0, log 0, no Oops, no call trace. Function-off could not be sent, and the
  module unloaded cleanly. CONSYS was not reloaded, so Wi-Fi stayed out on that boot.
- The bytes the firmware sent just before show its ACK field staying at 7 across its
  last six frames, with two standalone ACKs for 7 in a row, while its completed-packet
  events kept coming. Then nothing, for 98 s until the module closed.

**Inferred:** the firmware lost or rejected one of our frames, and answered later ones
with duplicate ACKs, which is what the vendor's `stp_core.c` does on an out-of-order
frame. It was then waiting for a resend, which the link did not do. Vendor STP resends after
180 ms, up to 10 times, with four `0x7f` bytes first. Which frame it lost and why is
unknown. GNSS never showed it, at a higher burst rate. Candidates are a firmware buffer that
fills while the radio is busy, or a parser slip.

**Also seen, not understood:** `Inquiry Cancel` is refused with status `0x0c` (Command
Disallowed), twice, and no Inquiry Complete event appears anywhere in the capture. The kernel
leaves its `INQUIRY` flag set. Paging worked regardless. So the capture can't show when the
controller's inquiry ended, and the 30 s budget is what the host requested, not a measured
stop.

## After T2

[0525](../../patches/proposals/0525-soc-mediatek-mt6797-consys-resend-unacknowledged-STP.patch)
adds the vendor's resend. It changes the CONSYS module, so also GNSS, and halts now log
`timeouts` and `resent`. The [engine fixture](../2026-11-01-gemini-gnss-link/test-stp-engine.c)
covers order, resync bytes, ACKs during a resend and the final fail-stop, under ASan and
UBSan, and passes. That shows the logic only. Whether the firmware recovers, and how
often frames are lost, is the next device run's question. If frames are lost often, 180 ms
per loss will be audible and the cause needs finding. The test's starting volume goes from
30 to 50, as the tone is already at -20 dBFS.

## T2b result: audio heard (2026-11-03)

Run by the custodian on boot `64622312`, image `370f589b`, with `mt6797-consys.ko`
`74fb9566…` by reload (common init 285/285), `btmt6797.ko` `44875a17…`, `bluetooth.ko`
`d1600d16…`, [`bt-test.sh`](bt-test.sh) then named `bt-t2.sh` `0a123c55…`, `bt-start.sh`
`4a5fb9e9…`. Volume 50, `gemian_radio` off, placeholder address, BR/EDR only, SBC.
Evidence is private under `artifacts/station-work-40/boot-64622312/bt-t2b/`.

**The owner reports:** "I heard a tone left then right, then a melody played in both
ears", and during the soak "it works". They listened to part of the soak, so its audio is
not confirmed by ear throughout.

**Observed:**

| Phase | Wi-Fi | Result |
| --- | --- | --- |
| Tone, 31 s | down | `aplay=0`, 1.29 MB sent |
| Soak, 300 s, 10 plays | down | no `aplay` failure |
| Soak, 120 s, 4 plays | joined on 5 GHz pinned link, ping only | ping 260 of 260, 0 disconnects, RTT average 5.8 ms, maximum 15.7 ms |

- About 41 kB/s in every phase, 19.4 MB in all, 39772 ACL packets.
- Halt: `failed=0 busy=0 rx=40021 discarded=0 dup=0 tx=39863 acks=40021 timeouts=0
  resent=0`, assert 0. No Oops, warning, call trace or `nobody cared`. Both modules unload.
  Taint 0. SoC peak about 29.6 °C.
- Inquiry Cancel was refused with `0x0c` again, and the kernel's `INQUIRY` flag stays set.

**What this does not show:**
- **That 0525 fixed T2.** No resend ever ran. T2's stall simply did not recur. The runs
  also differ in a fresh boot and CONSYS lifetime (T2 ran after three T1 runs, charger tests
  and a Wi-Fi join and stop), and in 0525's other effects: the 20 ms tick and messages held
  in the queue until acknowledged. So the cause of the T2 stall stays open, and the resend
  path is untested on hardware.
- **Coexistence under load.** Wi-Fi carried a ping on 5 GHz, not traffic, and not 2.4 GHz.
- **Range, TX power, other headsets, or long runs.** One headset, a few metres, about 7
  minutes of audio, one boot. Nothing here measures RF.
- **That the placeholder address is safe to keep.** Two Gemini units nearby would collide.

**Budget used of the one the owner approved, T2 and T2b:** inquiry 2 of 3, pairing 2 of 3,
A2DP connections 2 of 5, soak 7 of 10 minutes. It covered this test only, so nothing
further should run on the remainder without asking.

## Recommended next

In this order, each its own request:
1. **A private address**, with `HCI_QUIRK_INVALID_BDADDR` and a value kept off Git, before
   daily use. Small.
2. **SCO over HCI**, one connection to the headset, since it decides what the microphone and
   HFP need: if the ROM refuses it, HFP needs a Gemini `btcvsd` node, a machine-driver link
   and a CVSD/mSBC bridge. A new radio action, so the owner's.
3. **A concurrent test with real Wi-Fi traffic**, on 2.4 and 5 GHz, watching `timeouts`.
4. **A boot-time path**, if the owner wants Bluetooth without SSH: the chroot and modules on
   `/mnt/data`, a pairing store that survives a boot.

**Not recommended now:** the control run with the old CONSYS module. Keep 0525 either way,
since it's what the vendor does, and `timeouts` will show if it ever runs.

## T3, prepared: does SCO over HCI work? (owner's question: does the microphone work?)

Not run. A2DP is one-way, so the microphone needs HFP, and that needs a voice link. Vendor
software routes voice through CVSD SRAM and never uses HCI SCO on this chip, so that this
works is the less likely outcome. One connection decides what the microphone costs.

**Read from the code and T1's replies:** no kernel change is needed. The H:4 parser and
`send` already carry SCO. `rfcomm.ko` and `sco.c` are in the package. The controller lists
Enhanced Setup Synchronous Connection (Supported Commands octet 29) and SCO, HV3 and eSCO
features. So the core will request a CVSD link with its data path set to HCI (`0x00`), which
is what this test asks of the firmware. Its reported SCO buffer is 184 bytes, 1 packet, and
the core does no SCO flow control without a quirk.

[`bt-test.sh`](bt-test.sh)'s `sco` step opens both directions through BlueALSA's
Hands-Free gateway, CVSD only: [`make-tone.py`](make-tone.py)'s 8 kHz notes out, the headset's
microphone in, while the owner speaks.

| Observation | Meaning | Next |
| --- | --- | --- |
| Connection complete status 0, owner hears the notes, capture has speech above the noise floor | HCI SCO works both ways. HFP needs no CVSD SRAM path | mSBC next, then daily use |
| Connected, notes heard, capture is silent or constant | Uplink isn't routed to HCI | Inspect capture and SCO RX counts offline |
| Connected, SCO packets move, nothing heard | Firmware takes frames and doesn't route them, or routes them to SRAM | Bridge path, see below |
| Connection refused or fails (status in the capture) | ROM refuses HCI voice, at least this way | Try the legacy setup command once, by quirk, then the bridge path |
| Link stops, assert | SCO timing upset the link or firmware | Stop; offline |

**Bridge path, if HCI SCO fails:** a Gemini `btcvsd` node, a machine-driver link and a CVSD
coder between the SRAM and userspace. That is substantial work.

## T3 result: the link connects, no voice over HCI (2026-11-03)

One SCO attempt of the approved 3, by the custodian on boot `64622312`, with `rfcomm.ko`
`b6e2127c…`, `bt-test.sh` `d11052c2…`, `bt-start.sh` `2ef2cc52…`, Wi-Fi down, placeholder
address, `gemian_radio` off, after a long CONSYS lifetime. Evidence is private under
`artifacts/station-work-40/boot-64622312/bt-t3/`.

**The owner reports:** "I hear static in the headset". No notes were reported at the time.

**Observed, from the capture:**
- Hands-Free connected. Enhanced Setup Synchronous Connection (`0x043d`) with HCI data path
  and 16-bit linear host format; Synchronous Connection Complete status 0, link type eSCO,
  air mode CVSD. **Not the refusal this record expected.**
- Voice Setting reads `0x0060`, matching the request.
- **SCO TX: 2608 packets over 30 s, 184 bytes each, about every 11.5 ms: 16 kB/s, the right
  rate. Their bytes are a smooth 16-bit waveform, so the host sent what it should.**
- **SCO RX: 0 packets in 30 s.** The capture file holds a header only, so there is nothing to
  measure. `aplay` returned 0; `arecord` ended with a read error.
- Link clean: `failed=0 timeouts=0 resent=0`, assert 0, no call trace.

**Inferred, and the leading explanation:** the firmware carries voice through the CVSD SRAM
path whatever the host asks, as [the vendor's design](../../docs/hardware/mt6797-bluetooth.md#bluetooth-audio)
does on this chip (`hw_if == 3`). So the uplink goes to SRAM and never reaches HCI, and the
downlink the headset hears comes from SRAM with nothing feeding it, so noise. HCI TX would be
ignored.

**Not established:** that SRAM is in use; nothing has read it. Another explanation for
the static would be firmware passing HCI samples to the air uncoded, though that wouldn't
explain the silent uplink. The legacy setup command (`0x0428`) and Set Voice and Set Codec are
untried, and vendor software has neither of those configured on this chip.

**Answer to "does the microphone work?": no, not over standard SCO.** A2DP is unaffected.

## T3b, proposed, needs the owner: where does the voice go?

The next step for the microphone is large, so one read is worth having first. During one more
eSCO link, sample the CVSD registers read-only: PKV `0x18000fd0`, `0x18000fd4`, `0x18000fd8`,
and INFRA_MISC `0x10001f00`.

| Observation | Meaning |
| --- | --- |
| Read or write pointer moves, or status bits change while connected | SRAM is the voice path. Build the bridge, or stop here |
| Nothing moves | SRAM needs enabling first, or voice goes elsewhere; the bridge has more unknowns |

**The bridge, if the owner wants the microphone:** a Gemini `btcvsd` node and a machine-driver
link (a device tree change, so one image), `CONFIG_SND_SOC_MTK_BTCVSD=m`, and a userspace piece
with a CVSD coder that connects those PCMs while `bluetoothd` and BlueALSA hold the link. The
upstream driver exists; that piece and its integration don't. Several device rounds.

## T3b result: stopped registers, all flags raised (2026-11-03)

Run by the custodian on boot `64622312`, with the owner's "Yes, run T3b", one 15 s eSCO link.
No read hung or faulted; link clean, SCO RX 0 again. Eight samples a second apart, about 4 to
12 s into the link, identical:

| Register | Value | Decoded with `mtk-btcvsd.c` |
| --- | --- | --- |
| INFRA_MISC | `0x11403200` | bit 11 clear: the CVSD interrupt gate is open |
| Read pointer | `0x00104000` | SRAM bank 2 offset `0x4000` |
| Write pointer | `0x001041c0` | SRAM bank 2 offset `0x41c0` |
| Control | `0x81e40000` | interrupt (31), RX overflow (24), TX underflow (23), RX ready (22), TX not ready (21), packet type 1 |

**The experiment's table was too coarse.** It read "all constant" as "SRAM not in use", but the
values matter. Packet type 1 means 60-byte packets, which is the length this eSCO link reported.
All the status flags are up, and SPI 286 has no handler here.

**Inferred:** the firmware did use the SRAM path, raised its interrupt once, and is waiting for
the host to clear the flags, which `mtk_btcvsd_snd_irq_handler` does on every interrupt. So the
pointers stay frozen, and RX overflows and TX underflows with nobody serving them. That fits
everything in T3, including the static.

**Not established:** there's no sample from before the first link in this CONSYS lifetime, so these
flags could be left from T3's link or an earlier state. Nothing has shown the pointers move.

## T3c, proposed, needs the owner: does it answer the host?

Without any image: during the last approved eSCO link, clear the control register's flags once a
second as the vendor and mainline handlers do, and sample again. This is the first write to this
block on mainline. If the flags come back and the pointers move, the SRAM path is alive and the
bridge has a known foundation. If nothing moves, the path needs something else first, and it's
better to know that before a new image.

## T3c result: the CVSD SRAM path answers the host (2026-11-03)

Run by the custodian on boot `64622312` with the owner's "Yes, run T3c", `bt-t3c.sh`
`13cab60b…`, one 15 s eSCO link, eight writes to the control register. Evidence is private
under `artifacts/station-work-40/boot-64622312/bt-t3c/`. The owner reports: "I didn't listen."
So there is no listening evidence for this run.

**Observed (`misc` was `0x11403200` throughout):**

| Moment | Read | Write | Control |
| --- | --- | --- | --- |
| Before the link | `0x00000000` | `0x00000000` | `0x00000000` |
| Link up, not yet cleared | `0x00104000` | `0x001041c0` | `0x81e40000` |
| After clear 0 | `0x001040dc` | `0x0010429c` | `0x80640004` |
| 1 s later | same | same | `0x81e40004` |
| After clear 1 | `0x00104000` | `0x001041c0` | `0x80640007` |
| 1 s later | same | same | `0x81e40007` |

Clears 2 to 7 alternate the same way. One sample caught the write pointer ahead of the read
pointer's move, with control `0x81640007`. After the link, control stayed at `0x81e40007`.

- **The flags belong to the link:** all zero before it, so T3b's weren't stale.
- **The pointers move once per clear,** between two buffers `0xdc` apart. **Inferred:** one packet
  per clear at this script's 1 Hz, so the firmware runs this path in step with the host, as the
  vendor and mainline drivers expect. Offsets stay within the same 0x1c0-apart pair.
- SCO RX over HCI was 0 again, SCO TX 1304 packets. Link clean: assert 0, no call trace.

**The STP resend ran on hardware for the first time:** the halt shows `timeouts=1 resent=7`, up from 0
and 0 at T3b's, and the link carried on. That is one event. Its timing isn't known, nor whether these
writes caused it, but it shows the firmware accepts the resync and resent frames. It makes the
T2 explanation more plausible without proving it.

**Not established:** that real audio can flow: the SRAM contents have not been read or written, the
interrupt has not been served, and the rate has not been reached. 1 Hz is far from what the link needs.

## What the microphone would need now

The foundation is shown, and T3's three attempts are spent. All of this is a new owner decision:

| Piece | Where | Size |
| --- | --- | --- |
| Gemini `btcvsd` node: two CONSYS windows, `mediatek,infracfg`, SPI 286 | Device tree, so **one image** | small |
| `CONFIG_SND_SOC_MTK_BTCVSD=m` and `BTCVSD_RX`/`TX` links on the existing machine driver or a tiny one | Modules | small |
| First proof: the driver's own `BT_DIRECT_LOOPBACK`, or capture while speaking | Device, owner | one or two runs |
| CVSD coder and bridge: PCM to and from the ALSA packet stream, with validity words, while `bluetoothd` holds the link | Userspace, new | the real work |
| A way for applications to reach it, e.g. ALSA loopback | Userspace | small |
| mSBC, later, through `libsbc` | Userspace | small once CVSD works |

The vendor's coder is proprietary and stays out; a CVSD coder from the public algorithm is short, but
its quality against this firmware is unknown. Upstream's `mtk-btcvsd` has not run on this SoC, and
the first image proves or breaks that.

## First step of the microphone work: the driver and a loopback (owner: "Yes, first step")

Built, not yet run. It answers one question cheaply: does the upstream `mtk-btcvsd` run this path
at full rate on this SoC? No coder is needed, because the driver has a loopback that copies
the coded microphone packets straight back to the headset.

| Change | What |
| --- | --- |
| [0527](../../patches/proposals/0527-ASoC-mediatek-btcvsd-stop-the-interrupt-before-unmap.patch) | Upstream's `remove` unmapped the registers while the interrupt was still live. Closes the gate and frees the interrupt first |
| [0528](../../patches/proposals/0528-ASoC-mediatek-mt6797-add-a-card-for-the-Bluetooth-vo.patch) | A separate small card, so the working audio card neither waits on this driver nor changes |
| [0529](../../patches/proposals/0529-arm64-dts-mediatek-gemini-station-describe-the-Bluet.patch) | The block and the card in the station's device tree. **Needs one new image** |

**Hazards read from the driver:**
- It requests the interrupt at probe, before it closes the gate, and the idle path of its handler
  writes to the PKV window. So load it only with CONSYS up. With CONN off, that write could hang the bus.
- It touches PKV and SRAM only from the handler.

Checked in the dev VM: both modules compile at W=1 with no warnings, the DTB has both nodes, the new
binding validates with `dt-doc-validate`, and `checkpatch` raises only line-length, MAINTAINERS and
Kconfig help-length notes. **The binding and the driver share 0528**, as the project's experiment
patches often do; split them before any upstream submission.

## T4 result: the owner heard their own voice (2026-11-03)

Run by the custodian on boot `71c6a822`, image `fa8ff860`, with the owner's go-ahead: `mtk-btcvsd.ko`
`2dc67005…`, `mt6797-btcvsd.ko` `c407d4e4…`, `mt6797-consys.ko` `74fb9566…`, `bt-loopback.sh`
`2bf06047…`. Wi-Fi off, `gemian_radio` off, placeholder address. One 30 s eSCO link. Evidence is
private under `artifacts/station-work-42/boot-71c6a822/bt-t4/`.

**The owner reports:** "I hear my own voice".

**Observed:**
- Both modules load, and the card appears. The main audio card is untouched.
- Before the loopback: flags up, `0x81e40000`, as in T3b. Once it's on: flags clear at each sample
  (`0x00040007`, once `0x00040003`), pointers moving.
- About 45 interrupts a second: 905 over the first 20 s, 1779 by the end of the link. That
  matches 180 bytes per interrupt at 8 kB/s.
- SCO over HCI as in T3: 2608 packets out, 0 in. The owner did not report hearing the notes
  sent that way; they weren't asked.
- Link clean: `failed=0 timeouts=0 resent=0`, assert 0, no Oops, no warning, taint 0. Both
  modules unload.
- INFRA_MISC reads `0x11403200` before the driver and `0x11403a00` after it. Bit 11 is the gate,
  and in `mtk-btcvsd.c` setting it disables: **closed**, as 0527 and the driver's idle state leave it.
  At boot it is open.

**What this settles:** on this SoC the firmware carries eSCO voice through the SRAM path, in both
directions, at the link's rate, with the upstream driver. HCI SCO packets are not what reaches the
air (inferred from T3 and from the notes not being reported, not tested on its own). The voice
really travelled from the microphone to the headset's earpiece through SRAM, heard by ear.

**What it does not:** no application can use the microphone. Loopback copies coded packets
without decoding them; the driver's PCM stream has not been opened; CVSD coding on the host
is not written. One boot, one headset, 30 s, Wi-Fi off, and the echo's quality was only noted as
heard.

## What is left for a usable microphone

| Piece | Status |
| --- | --- |
| Link: `bluetoothd` and BlueALSA hold eSCO | Works |
| Coded packets, SRAM to and from the driver | Works, in loopback |
| The driver's PCM stream carrying them | Not opened yet |
| CVSD coder and bridge: PCM to and from that stream, with validity words, in step with the link | Not written. The real work |
| How applications reach it: ALSA loopback or a BlueALSA change | Not chosen |

The natural next proof is small: a coder and a tool that plays a tone through the PCM stream and
captures the microphone to a file. That answers the coder's quality before any integration.

## The coder and T5, prepared

[`bt-voice.c`](bt-voice.c) encodes and decodes CVSD from the Bluetooth specification's
parameters, as a filter with no dependencies. The vendor's library is not used or read.
[`test-bt-voice.py`](test-bt-voice.py) passes a round trip under ASan and UBSan: at -20 dBFS,
35 dB at 440 Hz, 21 dB at 1 kHz, 14 dB at 2 kHz, and 14 dB for 1 kHz at half scale, where a slope of
1600 per bit passes the specification's limit of 1280. These measure the coder against itself only,
not against this firmware or a headset.

**Open, and T5 tests it:** which bit of a byte comes first in SRAM. A swapped byte only shuffles eight
bits within 125 microseconds, so a low tone survives it (19.5 dB against 35.5 dB). So the wrong order
is noisier, not obviously broken, and T5 plays both and captures the microphone to compare. Whether
the driver's stream runs at all with `aplay` and `arecord` is also new.

## T5 result: the device hung (2026-11-03)

Owner's approval: "approved, move on". Run by the custodian on boot `fcb98505`, image `3e429f70`,
modules as in T4, `bt-voice` `be973e27…`, `bt-voice-test.sh` `509cd0d8…`. Wi-Fi off. Stop row, no retry.

**Observed:**
- Scan, pairing and the Hands-Free connection passed.
- A first status poll 4 s after the test started still answered. Later polls did not, and the USB
  link stayed down. So the device hung about 4 to 19 s after the test started. `arecord` and `aplay`
  start at about 5 s, so the timing fits them, but the polls are coarse.
- The owner reports "I hear noise/static", and "I forced a restart".
- **No evidence survived.** It was all in RAM, and `/sys/fs/pstore` was empty on the next boot. A hard
  hang writes nothing, and a cold restart may clear that RAM anyway.

**Not established:** which of the coder, the driver's PCM path, the handler or a bus access is at
fault, or whether something else in this newer image contributed (T4 ran on `fa8ff860`). The handler
ran in T4 through the same SRAM with the same register pair, and that did not hang.

**One real fault in the test, read from the code, which does not explain a hang:** `aplay`'s default
start threshold is a full buffer of 1800 frames, but the driver's ring holds 18 packets of 60 bytes,
540 frames, and only drains after the stream starts. So `aplay`'s second write blocks forever
and playback never starts. Its bytes never reached the SRAM, so what the owner heard was not the
coder's output.

The owner restarted with "ESC+side key", a hardware path, which may be why pstore is empty, and says
"the screen was dark, off". The console's idle blank may already have applied, so that shows little.

## Comparing with the vendor: what T5 did differently

Requested by the owner after T5. Read from the public Gemian kernel at `59e00a91` and from the retained
`audio.primary.mt6797.so` statically, in the RE VM. No hang path was found in the kernel code, so the
hang's cause stays open. Two of T5's settings were wrong, and both are this project's test, not the driver:

| | Vendor | T5 | Effect |
| --- | --- | --- | --- |
| Rate | 8 or 16 kHz (inferred from the HAL; the kernel's list has no 64 kHz) | 64 kHz declared; about 4000 frames/s real | At 250 Hz, `pcm_lib.c` reads the first 22.5 ms interval as a lost buffer, jumps the pointer and reports an overrun from the interrupt, so capture never delivers. **Read and verified in 7.1.3; not measured** |
| Starting TX | `pcm_open`, then `pcm_start` at once | Full buffer of 1800 frames, into an 18-packet ring | `aplay` blocks in its second write, and never starts |
| Directions | Separate objects, each opened on its own path | Both together | Untested alone |
| Period | TX 1020 frames, count 2; RX 1024, count 2; `pcm_write` to 480 bytes; `pcm_read` 512 | 450 and 480 | Upstream accepts these; multiples are clean |

**So in T5, inferred:** `arecord` looped through overrun and restart every 45 ms, and neither direction
was being served once the ring filled, in step with the static the owner heard. Whether that
state hangs firmware or the bus is unknown.

**Vendor kernel against upstream, same:** pointer logic, locks, level-low interrupt, the gate, and no
wake lock, `wmt` or sleep calls around this path. **Different:** the vendor drains TX from prepare, upstream only
after start. The vendor's rings are smaller (TX 8 by 60, RX 16 by 32). Upstream checks `0xdeadfeed` on
pointers only. Upstream's loopback can run with streams, and turning it off leaves both RUNNING with
NULL substreams: the T4 script turned it off only after the link had ended, so no interrupt could hit it.

**Other known differences from the vendor's Bluetooth setup, none tested as causes:** no Set Radio, TX
offset or sleep timeout; LE hidden; no WMT sleep; the kernel asks for an eSCO link by Enhanced Setup
with an HCI data path, where the Gemian kernel's core uses the older command; no LTE IDC bridge.

## T5b, prepared

[`bt-voice-test.sh`](bt-voice-test.sh) now runs one direction per link, at a declared 8 kHz, with
`aplay` starting on its first write, and writes each step and the PCM's status to `/mnt/data` with a
`sync`, so a hang leaves evidence. It has not run.

## T5b result: capture ran, no hang (2026-11-03)

The owner's "go". Run by the custodian on boot `0633cf9d`, image `3e429f70`, modules as in T4,
`bt-voice-test.sh` `f43bf9d5…`, `DIR=rx`, Wi-Fi off, console blank off. One eSCO link. Evidence,
including the owner's voice, is private under `artifacts/station-work-43/boot-0633cf9d/bt-t5b/`.

**Observed:**
- `hw_ptr` climbed about 4320 frames a second for 20 s. `mic.cvsd` is 170880 bytes: 5340 records, 8.1 kB/s of
  coded bytes. No overrun, xrun, assert, warning or stopped link. `timeouts=0`.
- Of those records, 5324 are marked valid and 16 invalid.
- `bt-test.sh`'s HCI `aplay` ended early with 1, because this script's kill loop also matched it, so the
  link was cut at about 25 s of 30.

**Bit order settled: first bit in the low position.** Adjacent bits are equal about 21% of the time at
all eight positions in a byte with that order. With the other order, the boundary between bytes jumps to
49%, as unrelated bits would. Decoded in that order, 8 kHz, levels rise and fall over the 20 s by
20 times, from 239 to 4821 RMS per second. A cruder test, high-frequency energy, had favoured the wrong order,
so it is not a useful measure of this coder.

**Inferred:** T5's rate setting was at least part of what went wrong in capture. It shows only that
capture alone does not reach T5's hang, on one run. Playback alone, and both together, remain untested.
The owner reports: "I talked th whole time. I heard noise/static". Static fits no TX stream running; that is
inferred. **Whether the file is intelligible is the owner's to say**, and they have not yet said.

