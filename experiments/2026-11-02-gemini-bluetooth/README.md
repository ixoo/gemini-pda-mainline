# Experiment: Bluetooth on the station, as a module, up to A2DP audio

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-bluetooth` |
| Status | `completed` for A2DP. T3 to T6: no voice crosses HCI. Through the CVSD SRAM path, loopback carried voice, the owner heard our coder's notes, noisily, and a capture matched a known recording played at the microphone (T6). The noise in the earpiece is unexplained, as is T5's hang, and the bridge isn't built. Earlier: the owner heard A2DP audio from the station on a stock BlueZ stack, on one boot, including next to a joined Wi-Fi carrying only a ping. What fixed T2's stall is not established |
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

**The owner reports on the decoded file:** "I didn't hear my voice". So capture is not shown to work, and the
level check above is not evidence of speech.

**Checked offline, on the capture's statistics only:**
- Framing is continuous: bit statistics show no break at any 30-, 60- or 180-byte boundary.
- Of the 16 invalid records, 10 are at the start, and 6 are in three pairs.
- The HCI notes are not what was captured: correlation against them is at most 0.11.
- The decoded signal comes in bursts, 0.25 s to 1 s long, with quiet gaps at about 11 to 30 RMS. In
  87 of 159 loud frames it is periodic, mostly 80 to 110 Hz.
- Energy sits mostly between 300 and 700 Hz, with little above 1 kHz.

**Reading:** that shape suggests something structured, possibly heavily muffled speech, and not random noise.
It does not show that the coder decodes this firmware's stream correctly, or that the owner's voice is there.
The coder has only ever been tested against itself, so a mismatch with the spec could look like this.

## T5c result: playback crashed on a driver bug (2026-11-03)

The owner's "Yes, run T5c". Run by the custodian on boot `0633cf9d`, `bt-voice-test.sh` `11657cf8…`, `DIR=tx`, Wi-Fi
off. One eSCO link. The live kernel log on the laptop caught it, private under
`artifacts/station-work-43/boot-0633cf9d/bt-t5c/private/`.

**Observed:** 23 ms after the stream started, a NULL write in `aplay`'s context: virtual address `0x384`,
`__pi_memset_generic`, from `snd_pcm_format_set_silence`, `fill_silence`, `snd_pcm_playback_silence`,
`snd_pcm_sw_params`. Then `pstore: backend (ramoops) writing error (-28)`, `aplay exited with irqs
disabled`, and SSH and USB ping stopped.

**Verified in the code:** the driver sets no `dma_area`, and ASoC cannot supply `fill_silence`, so ALSA's default writes at
`NULL + offset`, here 450 frames. It holds the stream lock with interrupts off, which fits the system
stopping. alsa-lib's `snd_pcm_hw_drain` asks for that silence: 800 frames here, which is the fault's size.
[0531](../../patches/proposals/0531-ASoC-mediatek-btcvsd-don-t-let-the-core-fill-silence.patch) gives
playback an area for it and stops declaring MMAP, which nothing backs. No notes reached the headset, so
this says nothing about the coder.

**Not explained:** `aplay` drained after writing just one 450-frame chunk, as if the file had ended, when it
should hold 80000 bytes. In the VM the same pipeline gives 40000 bytes per order, so 5 s each, not the 10 s the
T5c request said. The test now logs the file's size.

**T5's hang may be a different fault.** T5's `aplay` waited for a full buffer, so it should never have started
or reached that drain until the timeout. An earlier statement that this explains T5 would be inference.

**pstore:** `ramoops` failed on the Oops with `-28`, which may be why T5 left nothing. It affects every crash on the
station, and is separate from Bluetooth.

**The owner asked whether the format or codec could be wrong.** For the crash, no. For T3's static, no: nothing was
serving the path. For T5b's capture, it remains possible:
- **Ruled out:** mSBC, since its sync byte shows no 60-byte pattern, and the controller reports CVSD. Bit order and framing.
- **Not ruled out:** that `bt-voice.c`'s CVSD differs from what the firmware and headset do. It is written from
  the specification's parameters, and has only been tested against itself. The vendor's coder library isn't in the
  extraction to compare with.
- **What decides it:** playback of known notes, and a capture with a known tone held near the microphone.

## T5d result: the owner heard our notes, with noise (2026-11-03)

The owner's "Yes, run T5d". Run by the custodian on boot `7978f9ea`, image `8f2c1167`, `mtk-btcvsd.ko` `0ce985d2…`,
`bt-voice-test.sh` `5c89eba1…`, `DIR=tx`, Wi-Fi off. One eSCO link. Evidence private under
`artifacts/station-work-44/boot-7978f9ea/bt-t5d/`.

**The owner reports:** "I hear the tones, but it's still noisy, like there are interferences".

**Observed:**
- No crash, so 0531 stops T5c's fault. `tx bytes 80000`, so the file was right here. Why T5c's `aplay` ended after
  one chunk stays unexplained.
- `hw_ptr` climbed 4050 frames a second for about 10 s, about the rate of the file.
- No xrun, assert or stopped link; `timeouts=0`.
- `wait_for_bt_irq()` logged a timeout about 25 times a second. Reading the driver, that is a 22.5 ms limit
  on a 22.5 ms interrupt, retried; no underrun was logged, so it does not by itself show missing packets.

**What this settles:** host-coded CVSD reaches the earpiece as recognisable tones, so the coder and the driver's
TX path work at least roughly, and T5b's low-bit-first order is consistent. **Not settled: where the noise comes
from.** BlueALSA's HCI stream was running throughout: if the firmware also acts on those packets, that could
be heard as interference (a hypothesis). So could the coder, or a TX timing fault.

## Separating the noise

1. The coder alone, offline: `coder-only.wav`, from the exact bytes sent, decoded by `bt-voice`: what a perfect link
   would deliver. By the same decoder, only the coder's self-consistency is measured. If the owner hears
   the same noise there, it is the coder's quality, not the path.
2. If it's cleaner: run again with no HCI playback holding the link, which tests the HCI hypothesis.

**The owner compared them:** the offline file "is noisier than what I hear on the headset". So the path adds no noise
that the coder alone doesn't already have, and may well be delivering our bytes faithfully. The owner also
described the headset's noise as "a noise feedback loop, maybe picking up the mic?", which remains untested. The
coder's SNR on these notes is about 28 dB at any level from -30 to -3 dBFS, so raising the level won't help.

## T6, prepared: capture of known speech

Capture is what's still unexplained. Speech by the owner can't be measured against anything, so T6 plays a known recording
from the laptop's speaker next to the headset's microphone, and correlates the decoded capture with it. Holding
the link no longer plays anything over HCI (`SCO_NO_PLAY`), which removes that as a suspect.


## T6 result: the capture is the microphone's signal (2026-11-03)

Owner's approval: "go for t6". Boot `3fb07fd4`, image `8f2c1167`, `mtk-btcvsd` `0ce985d2`, `bt-test` `63d6af09`,
`bt-voice-test` `da743ab6`, `bt-voice` `be973e27`, `DIR=rx`, Wi-Fi off. Used 1 inquiry, 1 pairing, 1 eSCO
(status 0, air mode CVSD). No crash: link `failed=0 timeouts=0 resent=0`, assert 0, xrun 0, every `rmmod` 0, and
HCI SCO counts stayed 0. The laptop played the known synthetic recording (`known-speech`, not anyone's voice)
for 20 s from its speaker, across the capture; its output level wasn't read and the mic's distance was the owner's.

**Measured**, from `mic.cvsd` (`4019e050`, kept private), decoded low bit first against the recording:

| Measure | Result |
| --- | --- |
| Records | 5340, 20.025 s; only the first 10 invalid |
| Waveform correlation, 200 to 3400 Hz | -0.459 at 0.893 s, about 295 times the median |
| Level contour correlation | 0.831 at 0.90 s |
| Spectrogram correlation | 0.835 at 0.89 s |
| Lag in 9 successive 2 s windows | 893.0 to 893.6 ms in 7, 897.2 and 898.8 ms in the others; first and last both 893.1 ms; the sign is negative in 6 windows, positive in 3 |
| Capture before the sound starts | -75.7 dBFS |
| Capture in the recording's quiet frames, loud frames | -62.6 dBFS, -23.6 dBFS (medians) |
| Same correlations with high bit first | -0.421 and 0.813 and 0.785 |

**What that establishes:** the capture carries the microphone's signal through SRAM, driver and decoder. The first and last windows
have the same lag, so no net bytes were lost or added over the run. The two windows that differ return to it, so they aren't lasting
slips, though what moves them isn't established. The peak matches the laptop's clock, which put
playback 0 to 1 s after the stream started. Low bit first scores better on all three, supporting the earlier adjacency
statistic, though this isn't a sharp test: reversing the bits inside a byte keeps much of the low-frequency content.

**Not established:**
- How good the voice is. A linear fit from recording to capture explains only about 6 dB, and that mixes the
  laptop's speaker, the room, the headset's processing and our decoder, so it doesn't measure the path.
- Polarity. The overall correlation is negative, but the sign varies between windows, so this says nothing yet about
  the sense of a bit. It's inaudible.
- Why the owner couldn't recognise their voice in T5b, which had HCI playback running and a different input.

**The noise.** The owner: "I still hear the noise, it sounds like it starts when you open the mic". HCI SCO
counts were 0, so HCI audio isn't the source, and nothing was feeding the transmit side of SRAM.
The capture is quiet before the sound starts, so this noise isn't in the uplink we read.

**Inferred, not measured:** the headset is hearing whatever sits in the transmit SRAM. The upstream driver writes
to it only while a playback stream runs, and fills it with the CVSD idle pattern (`0xaa`) only after one has
been used. Nothing has read that SRAM on the air side, the owner's timing doesn't distinguish the stream from the link, and
T5d's noise, with playback running, isn't explained by this. A headset's sidetone would also fit, as the
owner suggested.

**No call was signalled.** In T6's trace BlueALSA answers `AT+CIND?` with `call` and `callsetup` both 0 and sends no
`+CIEV` or `RING` around the eSCO link, and it answers the headset's `AT+CLCC` with `ERROR`. HFP has no separate
mode for this: the audio link opens without a call state. The capture still matched, so this headset's microphone
isn't gated on a call. Whether a call state changes its processing or the earpiece noise is untested.

## T7, prepared: does sending silence stop the noise?

T6's trace left one cheap test of the unfed-SRAM reading. `DIR=both` captures for 24 s on one link, sends the
driver's own idle pattern (`0xaa`) from 8 s to 18 s, and then closes playback, which makes the driver write the idle pattern to
SRAM once more. The pattern decodes to silence offline, peak 4 of 32767. Nothing here needs a new module.

So one link gives three conditions: unfed, fed with silence, and left after feeding. The owner reports when the noise changes
without being told when to expect it. The laptop plays 5 s of the known recording from 13 s, to check
capture still matches with both directions running, which the bridge needs and which hasn't been run through ALSA.

| Observation | Meaning | Next |
| --- | --- | --- |
| Noise stops from about 8 s, capture matches | Unfed SRAM was the noise | Write idle to SRAM in the driver at stream start, then voice both ways |
| Noise stays, capture matches | SRAM isn't the source; the headset's mic path or call state remains | Test a call state through `bluealsa-rfcomm` |
| Capture degrades once playback runs | The directions interfere | Offline with the bytes |
| Hang or Oops | Stop, the first evidence on T5's hang | Keep everything; no retry |

## T7 result: silence didn't change the noise (2026-11-03)

The owner's "Yes, run T7". Boot `3fb07fd4`, image `8f2c1167`, `mtk-btcvsd` `0ce985d2`, `bt-test` `63d6af09`,
`bt-voice-test` `60e6dca0`, `bt-voice` `be973e27`, `DIR=both`, Wi-Fi off. Used 1 inquiry, 1 pairing, 1 eSCO (status 0, air
mode CVSD). Evidence private under `artifacts/station-work-44/boot-3fb07fd4/bt-t7/`; `mic.cvsd` is `e3652b21`.

**The owner reports:** "noise issue started" during the run and, asked afterwards without the timings, "No change".

**Observed:**
- No crash or hang, the first run of both directions through ALSA. Link `failed=0 timeouts=0 resent=0`, assert 0,
  xrun 0, every `rmmod` 0, HCI SCO counts 0.
- Silence ran 8 to 18 s (`silence ended 0`), and the driver then wrote idle to both transmit SRAM addresses it had learned.
- The recording arrived at 15.66 s, later than planned. `afplay -t 5` took 7 s, so the laptop may have started late.

| Same stretch of the recording | T7 contour | T6 contour |
| --- | --- | --- |
| While silence was sent | 0.805 | 0.834 |
| After sending stopped | 0.925 | 0.926 |
| Whole 5 s (waveform -0.366 and -0.453) | 0.890 | 0.896 |

- Capture level on that stretch was -30.5 dBFS, against -28.7 in T6.
- 10 pairs of records were invalid after the first 10 records, from about 5 s on, some before anything was sent. T6 had none. Cause not established.
- The playback side logged 389 `wait_for_bt_irq` timeout warnings. T5d logged 339 and T6 none. Effect not established.

**Reading:** capture isn't harmed by playback running, so a bridge has no known obstacle there. The unfed-SRAM reading of the noise
fails: the owner heard no change with the idle pattern sent, and T5d showed that bytes written this way reach the
earpiece. One listener's report is the only evidence here, with no measurement of the earpiece.

**Still open:** the noise is present whatever we send, in T5d, T6 and T7. That leaves the headset's own handling of this link, with no call
signalled, the downlink's radio quality, or something in firmware. A2DP was not reported noisy, so it isn't simply
the headset's analog output, though nobody compared them directly. Nothing yet separates these.

## T8, prepared: does a call state change the noise or the microphone?

T6 and T7 opened voice with no call signalled. `BT_CALL=1` opens a BlueALSA RFCOMM client before the link, sends
`+CIEV: 1,1` and `+CIEV: 2,1`, answers any `AT+CLCC`, and sends `+CIEV: 2,0` 10 s into the capture. Everything else is
T7's `DIR=both`. The FIFO and reply logic ran in `ash` with a stub in place of the client; the client itself hasn't run.

The owner again reports changes without the timings. The laptop plays the first 5 s of the known recording twice,
once in each state, so the same sound compares level and spectrum between them.

| Observation | Meaning | Next |
| --- | --- | --- |
| Noise is gone or changes with the call state | The headset treats this link differently without a call | Signal a call on every voice link, by the bridge |
| Capture differs between the two states, noise doesn't | The call state changes the headset's mic processing only | Pick the better state; the noise stays open |
| No change in either | Call state isn't it | Phone comparison, then decide whether voice is usable as it is |
| The client fails to open or the headset drops | Test fault or headset's response | Keep the logs; no retry without a new decision |
| Hang or Oops | Stop | Keep everything; no retry |

## T8 result: the headset noticed the call, and the capture didn't change (2026-11-03)

The owner's "Yes, run T8". Boot `3fb07fd4`, image `8f2c1167`, modules as T7, `bt-voice-test` `f5ced0da`, `bt-test` `63d6af09`,
`BT_CALL=1 DIR=both`, Wi-Fi off. Used 1 inquiry, 1 pairing, 1 eSCO (status 0, air mode CVSD). Evidence private under
`artifacts/station-work-44/boot-3fb07fd4/bt-t8/`; `mic.cvsd` is `e7ee2bc4`.

**The owner reports:** "at the beginning and at the end I heard a bip like a call started or ended. The noise was still
there even after the call". Whether it changed during the call wasn't said.

**Observed:**
- The trace shows `+CIEV: 1,1` and `+CIEV: 2,1` about 1 s before the link, and `+CIEV: 2,0` about 14 s after it opened, which is 10 s
  into the capture. The owner's two beeps fit these. No crash: `failed=0 timeouts=0 resent=0`, assert 0, xrun 0.
- The headset sent no `AT+CLCC` during the run. Its only one came before the client opened, and BlueALSA answered `ERROR`. So the reply logic never ran,
  and `rfcomm.log` wasn't created. BlueALSA logged `AT handler IO error: Invalid argument` at some point; when and why isn't established.

| The same 5 s of the recording | During the call | After the call |
| --- | --- | --- |
| Arrived at | 1.96 s | 16.20 s |
| Contour correlation | 0.865 | 0.885 |
| Waveform correlation | -0.429 | -0.381 |
| Level | -32.8 dBFS | -31.5 dBFS |

- Spectra agree within 4 dB in every 500 Hz band. Capture with the laptop quiet was -65.8 dBFS during the call (7 to 10 s), and -70.0 after (11 to 14 s).
- Invalid records after the first 10: 4 at 4.2 s and 8 at about 10 s, the moment the call ended.

**Reading:** the call state has no measurable effect on this capture, and by the owner's report didn't stop the noise.
So signalling a call isn't a fix for it, though a call may still be wanted for a real bridge, since the headset reacts to it.

**Still open:** the noise's source. Remaining candidates are the headset's own voice path, such as sidetone that any
phone would also get, the radio link towards the headset, or firmware. Comparing with a phone call separates the first from the others.

## The voice link's parameters, and T9, prepared: Gemian's radio settings

T8's trace shows what the kernel asked for and got: Enhanced Setup with packet types `0x0380` (only 2-EV3 is allowed), maximum latency
10 ms, retransmission effort 1; and back, eSCO with an interval of 12 slots, a retransmission window of 2 slots and 60 bytes each way. So voice
uses the faster modulation with little room to retry, where A2DP can resend until the data gets through. Towards the Gemini, invalid
records after the first 10 were 0 of 5330 in T6, 20 of 6410 in T7 and 12 of 6410 in T8. Nothing here sees the path towards the headset.

**The owner's decision:** "I would test the gemian radio theory, to do like gemian", having read that the bytes aren't decoded, that power isn't
measured, and that Gemian may send either of two sets.

T9 is T7 with `gemian_radio=1`: it sends Set Radio `0xfc79` `06 80 00 06 03 06` and Set TX Power Offset `0xfc93` `ff ff ff` during
setup, each time the controller opens. `DIR=both` now also reads `hcitool tpl`, `rssi` and `lq` every 6 s, a first
measurement of the controller's own view of power and link. There's no reading from before these settings, so T9 alone can't compare them.

| Observation | Meaning | Next |
| --- | --- | --- |
| Noise clearly less, capture matches | These settings matter for voice | Decode what they set, consider keeping them on, compare with `07 80 00 06 05 07` |
| Noise the same, capture matches | These settings aren't it; radio not excluded | Move the Gemini against the headset to test distance |
| A command refused, or `hci0` doesn't come up | The driver's setup fails at this point | Keep the logs; no retry without a new decision |
| Capture or link worse | The settings hurt here | Leave them off |
| Hang or Oops | Stop | Keep everything; no retry |

## T9 result: Gemian's radio settings left the noise about the same (2026-11-03)

The owner's decision as above. Boot `3fb07fd4`, image `8f2c1167`, `btmt6797` `44875a17` with `gemian_radio` reading Y, other modules as T7,
`bt-voice-test` `92ac0828`, `bt-test` `63d6af09`, `DIR=both`, Wi-Fi off. Used 1 inquiry, 1 pairing, 1 eSCO (status 0, air mode CVSD). Evidence
private under `artifacts/station-work-44/boot-3fb07fd4/bt-t9/`; `mic.cvsd` is `296f2c43`.

**The owner reports:** "About the same", against the earlier runs. Whether it changed during the run wasn't said.

**Observed:**
- The trace shows `0xfc79` `06 80 00 06 03 06` and `0xfc93` `ff ff ff`, each with status 0. No crash: `failed=0 timeouts=0 resent=0`,
  assert 0, xrun 0.
- Link settings as before: 2-EV3 by request, interval 12, window 2, 60 bytes.
- `hcitool`, at four points on the link: transmit power 8, RSSI -7, -6, -9, -12, link quality 1.

| The same 5 s of the recording | T7, default | T9, Gemian's |
| --- | --- | --- |
| Contour correlation | 0.890 | 0.850 |
| Waveform correlation | -0.366 | -0.242 |
| Level | -30.5 dBFS | -32.8 dBFS |
| Invalid records after the first 10 | 20 of 6410 | 40 of 6410 |

**Reading:** these settings aren't a fix, on one run and by ear. Capture is no better and possibly a little worse, though the headset's position
wasn't controlled. This doesn't exclude a weak radio link: the settings' effect on power isn't measured, there's no baseline for the `hcitool` readings,
and this firmware's scales aren't known. `gemian_radio` stays off by default. Its settings may have remained active after this run until CONSYS powered off.

## A phone doesn't have the noise (2026-11-03)

**The owner reports:** "It doesn't have the issue when connected on my phone". So the noise isn't simply how this headset sounds on any voice link.

Which codec the phone uses wasn't observed. In T6's trace the headset offers codec negotiation and eSCO S4 (`AT+BRSF=703`), while
BlueALSA, with mSBC turned off here, offers no codec negotiation (`+BRSF:2272`), so every run so far has been CVSD at S3. Differences left to
separate: mSBC against CVSD, the eSCO parameters, and the Gemini's radio or firmware. The owner also asked whether the headset's noise cancellation
is involved. It's on the phone too, so it wouldn't explain the difference alone, but its behaviour on this link is untested.

## T10, prepared: mSBC

**The owner's decision:** "try mSBC". The phone is clean, and every run here has been CVSD. Nothing in the driver needs changing for a first run:
- The controller lists transparent voice and Enhanced Setup, and reports codecs CVSD and transparent. Whether its SRAM path carries mSBC is untested.
- BlueALSA has mSBC, turned off here so far. `BT_MSBC=1` leaves it on. The kernel then asks for T2: 2-EV3, 13 ms, retransmission effort 2, falling back to T1.
- The driver passes bytes either way, so its `BTCVSD Band` control only chooses the silence it writes when playback closes.

`bt-msbc.py` wraps ffmpeg's SBC codec. An offline round trip through 32-byte capture records, starting on the wrong record, decoded all 1333 frames with
silence at peak 0 and correlation 0.984 with the notes. The file holds no voice.

`BT_MSBC=1 DIR=both` sends nothing for 8 s, then 4 s of mSBC silence, then 6 s of the notes. Silence alone couldn't tell a clean link from a headset muting frames it can't
read, so the notes must be heard too. The laptop plays 5 s of the known recording from 1 s.

| Observation | Meaning | Next |
| --- | --- | --- |
| `+BCS` and eSCO with air mode transparent, notes heard, noise gone | CVSD was the difference | Make mSBC the default; the bridge next |
| Same, with the noise still there | Not the codec | Distance test, then the radio |
| Notes not heard, or capture holds no H2 frames | The SRAM path doesn't carry mSBC as sent | Offline with the bytes |
| Link refused, or BlueALSA falls back to CVSD | Controller or negotiation | Read the trace; no retry without a new decision |
| Hang or Oops | Stop | Keep everything; no retry |

**A correction on link time:** T5b to T9 asked for a 30 s link, but `bt-test.sh sco` holds it until `arecord` times out, about 45 s, as no data reaches it. Each voice run's budget said 30 s. T10's says 45 s.

## T10 result: the controller refused the mSBC link (2026-11-03)

The owner's "try mSBC". Boot `3fb07fd4`, image `8f2c1167`, CONSYS reloaded first, `gemian_radio` N, `bt-start` `bb17b859`, `bt-voice-test` `35b79212`.
Used 1 inquiry, 1 pairing, 0 links. No crash: `failed=0 timeouts=0 resent=0`, assert 0. Evidence private under
`artifacts/station-work-44/boot-3fb07fd4/bt-t10/`. Nothing was captured or sent.

**Observed:**
- Codec negotiation completed: the headset sent `AT+BAC`, and `+BCS` and `AT+BCS` were exchanged. So it does offer mSBC to us.
- The kernel then sent Enhanced Setup `0x043d` once: transparent air and host coding, 60-byte frames, host data path 0, 2-EV3 (`0x0380`), latency 13, effort 2.
- The controller answered Command Status `0x20`, Unsupported LMP or LL Parameter Value. A Command Status error means no link attempt, and the kernel makes no fallback from it.
  BlueALSA logged `Couldn't establish SCO link: Not supported`. The T1 fallback I expected only follows a failed link, not a refused command.
- `hcitool` on the ACL alone read transmit power 10, RSSI -11 to -14, link quality 255. That isn't comparable with T9: there was no eSCO, and other settings.

**Reading:** this controller lists transparent coding but refuses this command. Which parameter it objects to isn't established. CVSD's accepted
command differs in coding formats, sizes and transport units. The firmware may also need the older Setup Synchronous Connection `0x0428` for this.
**The owner reports:** "I didn't hear any noise, but I didn't hear any notes either". So with HFP connected and no voice link, there was no noise. On this one
run, the noise needs an open eSCO link, which fits the owner's "starts when you open the mic". It doesn't say which end produces it or whether CVSD matters.

## T11, prepared: mSBC by the older command

The owner's "Yes, prepare T11". `BT_MSBC=1` now lets BlueALSA negotiate and fail as in T10, then sends Setup Synchronous Connection `0x0428` with `hcitool`: voice setting `0x0063`
(transparent), bandwidth 8000 each way, latency 13, effort 2, packet types `0x0380`, T2's values. It disconnects after 30 s. The kernel skips the complete event for an eSCO link it didn't request, so the link has no socket,
which a test doesn't need and a real driver would. The earpiece and laptop are as T10.

| Observation | Meaning | Next |
| --- | --- | --- |
| Accepted, air mode 3, notes heard, noise gone | CVSD was the difference | Driver change so the kernel uses this command; mSBC as default |
| Accepted, air mode 3, notes heard, noise there | Not the codec | Distance test, then the radio |
| Accepted, notes not heard or no H2 frames in capture | The SRAM path doesn't carry mSBC as sent | Offline with the bytes |
| Command refused, or the link fails | This firmware path won't do it this way | Read how the vendor's stack sets up wideband; no retry |
| Hang or Oops | Stop | Keep everything; no retry |

## T11 result: an mSBC link, and the noise went away (2026-11-03)

The owner's "Yes, run T11". Boot `3fb07fd4`, image `8f2c1167`, `gemian_radio` N, `bt-voice-test` `7d085b37`, `bt-start` `bb17b859`, `msbc-tx.bin` `9d701c5a`.
Used 1 inquiry, 1 pairing, 1 eSCO. Evidence private under `artifacts/station-work-44/boot-3fb07fd4/bt-t11/`; `mic.cvsd`, here mSBC frames, is `0b968a74`.

**The owner reports:** "ok much better!" and "I think the noise is gone". Asked about the notes: "I heard the notes, and it was all good, no noise (or not significant, definitely not what I heard before)".

**Observed:**
- `0x043d` refused with `0x20` as T10, then `0x0428` status 0, then Sync Conn Complete: status 0, eSCO, interval 12, window 4, 60 bytes each way, air mode 3 (transparent). No crash:
  `failed=0 timeouts=0 resent=0`, assert 0, xrun 0.
- Capture holds real mSBC: 3199 frames with a good H2 header and sync, 11 bad, from 6420 records of which 20 invalid, 10 of those the first ones.
- The recording arrived at 1.53 s. Level contour correlation 0.910, waveform 0.280, level -32.1 dBFS. Capture is now 16 kHz.
- **The notes appear in the capture:** the first 4 s of the sent notes correlate 0.576 at 12.13 s, where 12 s was scheduled, about 51 times the median, at about -55 dBFS. So the headset was playing what we sent, and it reached its own mic. That's what rules out a headset muting frames it can't read.
- `hcitool`: transmit power 10, RSSI -6 to -15, link quality 255 then 5. The scale isn't known.

**Reading:** the Gemini can carry mSBC both ways through the SRAM path with no driver change, and on this run the noise was gone. Not separated: transparent air mode as such, the wider retransmission window (4 against 2), or the older command. One run, by ear.
How the notes reached the mic, leakage or the headset's own path, isn't established. The test link is outside the kernel's knowledge, so a real path needs the kernel to use this command, and a coder between the voice path and ALSA.

## T12, prepared: the kernel opens the mSBC link

The owner's "Yes, driver change". 0532 sets `HCI_QUIRK_BROKEN_ENHANCED_SETUP_SYNC_CONN`, so the core uses `0x0428` for every voice link, with T2 then T1 for mSBC. So the by-hand path is gone from `bt-voice-test.sh`
(T11 ran it at `f290bc4b`), and `BlueALSA` opens the link. T12 is T11 with this module. It also changes CVSD's setup, which is untested.

| Observation | Meaning | Next |
| --- | --- | --- |
| `0x0428`, air mode 3, no `0x043d`, notes heard, no noise, capture matches | The kernel path works | The bridge, on the owner's decision |
| Link up, noise back | T11's clean sound depended on something else there; compare the two traces | Offline, then decide |
| Link refused or falls back to CVSD | Read the trace | No retry without a new decision |
| Hang or Oops | Stop | Keep everything; no retry |

## T13, prepared: AAC against SBC for music

**The owner asked:** "can we test AAC for music? I'd like the best sound possible". The traces show what the headset offers: SBC up to bitpool 53, about 328 kbps, and AAC with variable bitrate allowed, up to 192 kbps (`c0ff8c82ee00`). BlueALSA here links `libfdk-aac`,
kept in the private chroot. Its licence would need a separate decision before anything public carried it.

`BT_AAC=1` offers AAC with the afterburner, and runs `bluetoothd -E`, as switching codec on a connection may need its experimental remote endpoints. `bt-test.sh ab` plays 30 s of `make-music.py`'s file, or the owner's own, once per codec in the order given, and logs the rate. The listener doesn't know the
order. A soak of 5 minutes on AAC follows, as T2 stalled on a stream and AAC's lower rate hasn't been tried. This doesn't touch the voice path. Nothing here has run.

| Observation | Meaning | Next |
| --- | --- | --- |
| Owner prefers AAC blind, soak clean | Worth having | Decide default and the licence |
| Owner prefers SBC, or no difference | Keep SBC; AAC's rate is capped at 192 kbps | Consider SBC XQ if more is wanted |
| Switching fails | No blind A/B this way | Keep logs; two sessions need a new decision |
| Link stalls | `timeouts` and `resent` count | Keep logs; no retry |

## T12 result: the kernel's own mSBC link, heard clean (2026-11-03)

The owner's "Yes, run T12". Boot `3fb07fd4`, image `8f2c1167`, `btmt6797` `754ad753` with 0532 (insmod 0), `bt-test` `90a27bb3`, `bt-start` `4f936a8b`, `bt-voice-test` `1c76747a`, `gemian_radio` N. Used 1 inquiry, 1 pairing, 1 eSCO. Evidence private under
`artifacts/station-work-44/boot-3fb07fd4/bt-t12/`; `mic.cvsd`, mSBC frames, is `c6182174`.

**The owner reports:** "quality is good I heard it all" and "no obvious noise".

**Observed:**
- `+BCS:2` and `AT+BCS=2`, then `0x0428` with status 0 and no `0x043d`. Sync Conn Complete: status 0, eSCO, interval 12, window 4, 60 bytes each way, air mode 3. The kernel's voice setting is `0x0003`, where T11's by hand was `0x0063`; the result was the same.
- No crash: `failed=0 timeouts=0 resent=0`, assert 0, xrun 0, every `rmmod` 0, HCI SCO counts 0.
- Capture: 3203 good frames, 7 bad. The recording arrived at 3.70 s, contour correlation 0.891, waveform 0.441, level -32.1 dBFS. The notes appear at 12.16 s, correlation 0.414, about -60 dBFS.
- `hcitool`: transmit power 10, RSSI -10 to -17, link quality 16.

**What's proven now, on this headset, by ear and by correlation, on two runs:** mSBC through the kernel's own eSCO link and the SRAM path, in both directions, without the noise CVSD had. Not separated: whether the noise's cure was mSBC itself or the setup's retransmission window, and how CVSD sounds under 0532, which is untested.
Not done: other headsets, long runs, Wi-Fi at the same time, a bridge to ALSA. The test still uses a raw stream and an offline decoder.

## T13 result: the link hiccuped, so AAC against SBC isn't settled (2026-11-03)

Boot `3fb07fd4`, image `8f2c1167`, `btmt6797` `754ad753`, `bt-test` `90a27bb3`, `bt-start` `4f936a8b`, `music.wav` `9d6dab45` (synthetic), `BT_AAC=1`, Wi-Fi off. Used 1 inquiry, 1 pairing, 1 ACL.
Hidden order `AAC SBC AAC SBC`. Evidence private under `artifacts/station-work-44/boot-3fb07fd4/bt-t13/`.

**The owner reports:** "the 1st one was the best I think. It didn't disconnect or skip contrary to the other ones." In the soak: "I hear a short skip at the beginning". Also "is there buffering?" and "I suspect lower bw requirement of AAC is an advantage for BT".

**Observed:**
- Switching codec on one connection works: `switch=0` four times, each confirmed by `Selected codec`.
- By transmitted bytes: AAC 199 and 193 kbps, SBC 333 and 344 kbps. The soak on AAC ran 300 s at about 196 kbps and stayed connected. `bluealsa` read 0% CPU in the one sample.
- **Link: `timeouts=40 resent=270 wmt-unsolicited=1`, assert 0, and no stop.** T12 on this boot read 0, and T2b's 5 minute SBC soak read 0, on an older module.
- The trace has 148 more completed packets than ACL packets sent, and the kernel logged `sent 0 < count 1` 161 times. Earlier runs in this experiment have none of these. By when they fall: clip 1 none, clip 2 none, clip 3 (AAC) 12, clip 4 (SBC) 5, soak 134, with 22 in its first 10 s. They arrive in groups of about 4 to 6.
- Gaps of 0.33 s every 30.5 s in the soak are `aplay` restarting the file. Others, 0.2 to 0.5 s, cluster 20 to 35 s into the soak.
- The ACK timeout logic reads correctly: it only fires after 180 ms with frames pending and no ACK. So these look like real stalls, though the code reading isn't proof.

**Inferred, not established:** after a timeout, resent frames the firmware already had reach the air a second time, since the groups match a resend's size and 40 timeouts roughly account for them. Duplicates could be what a listener hears. Why the ACKs stall, and why from about 180 s into this run, isn't known. The screen, the codec switch or radio conditions aren't separated.

**Not settled:**
- Which codec sounds better. The owner's pick rested on skips, and clip 3, also AAC, was heard skipping. Clip 2's skip has no link event near it, so it's unexplained.
- Whether a lower rate helps. All the soak's events were on AAC, and SBC's 5 minutes in T2b had none, so this run gives no support for that, while one run can't refute it.

**On buffering:** yes. ALSA, BlueALSA and the headset each hold audio, which should ride out a short stall, and how much isn't measured here. A longer stall or duplicated data can still be heard.

**The soak's skip, followed up.** The owner: "at the very beginning of every cycle". Each cycle is `aplay` restarting `tone.wav`, with a 0.33 s gap in ACL traffic every 30.5 s, so this is most likely the test's own restart, though nothing separates that from a start-of-stream fault. The over-completions don't line up with it: by seconds after a restart they run 17, 30, 12, 10, 9, 0, 15, 30, 6, 5 in 3 s bins. So the recurring skip and the 40 timeouts look like separate things, and the timeouts weren't what the owner picked out in the soak. Whether they were audible at all is open.

## Review of the patches, and what came of it (2026-11-03)

An independent reader went through 0511, 0512, 0523 to 0525, 0527 to 0529, 0531 and 0532, by reading only. Nothing below has run on the device.

**Fixed, compile-checked with W=1 and checkpatch-clean:**
- 0537: `mtk-btcvsd` requested its interrupt before mapping, and its remove unmapped under a live component. It now maps with devres and starts with the gate closed and the interrupt off.
- 0538: writing 0 to the loopback switch opened the gate with no stream, so `alsactl restore` could leave it open. This is what made 0529's claim about the gate untrue. It holds again from probe, until a stream or loopback opens it.
- 0539: halt could have a tick write the interrupt enables back.
- 0533 now also logs `pending` and `peer-ack` per timeout and each unsolicited WMT message. T13's was `02 03 02 00 00 03`.
- The messages of 0525 and 0532 now say what's inferred, and that CVSD moved too.

**Not fixed, on purpose:**
- **Resend (the review's biggest finding).** Surplus completions look like resent frames sent twice, so the firmware may take some resent frames as new, which the sequence discard in 0525 assumed it wouldn't. The four `0x7f` bytes might reset its expected sequence; not established. Probing with only the oldest frame might be better, but `mt6797-consys` ships in the RAM root and carries GNSS, and this can't be tested tonight. 0525 stays; 0533's log should show what happens first.
- **btcvsd without CONSYS power.** `prepare` and loopback can still open the gate with CONN off, and nothing links the two drivers. It needs an interface between them and a device test. Until then, these modules are only for hand-loading with CONSYS up. Whether this explains T5's hang isn't established; T5 had CONSYS up.

**Read and open, not verified or fixed:**
- `hdev->send` waits up to 1 s, less than the 2 s recovery, and a timeout loses the buffer and a credit.
- Clients aren't told when the link dies, so `hci0` stays up returning errors.
- A failed WMT function-off could drop the rail with the function on.
- The placeholder address is treated as real; the core could mark it invalid.
- A full window can read a stale ACK as a full one.
- The 20 ms tick runs while idle, which costs power.

**For submission:** no sign-offs yet and none invented, the binding in 0528 needs splitting, MAINTAINERS, Fixes tags on 0527, 0531 and 0537, 0537 and 0527 could fold together, and `gemian_radio` will likely be challenged.

Later the same night, no device test: 0540 makes the routine `wait_for_bt_irq` messages, about 25 a second on a normal stream, debug only, and limits by rate the warning for a wait that really failed. 0541 declares the two ROM patch files `mt6797-consys` loads. My three review patches moved from 0534 to 0536 to 0537 to 0539, as display had used those numbers.

## T14, prepared: why the link stalls during music

**The owner's decision:** music reliability next, then the voice bridge ("Accept all four").

T13 mixed several things: codec switching, `bluetoothd -E`, `aplay` restarts, and a soak. T14 removes them in turn. `bt-test.sh stream` plays one `aplay` fed in a loop, so nothing restarts, and 0533 logs each resend with `pending`, `peer-ack`, and the frame counts, which line up with the trace by time.

- T14a: SBC only, no `BT_AAC`, no `-E`, no switching, 5 minutes. Closest to T2b, which had no timeouts.
- T14b: a fresh load with `BT_AAC=1`, switching to AAC once before any audio, 5 minutes.

**Hypothesis, not established:** an ACK stall makes the host resend frames the firmware already took, and the firmware sends them again. If so, each `STP resend` line is followed within tens of milliseconds by over-completions of about its `unacked`. If `rx` keeps rising across a timeout, the firmware was still talking and only its ACK stayed put.

| Observation | Meaning | Next |
| --- | --- | --- |
| No timeouts in either, no skips | T13's came from switching, restarts or `-E`, or from something that varies | Repeat once with switching to separate them, then the blind comparison |
| Timeouts in AAC or `-E` only | Tied to that setup | Read which; compare stacks |
| Timeouts in both, over-completions follow each resend | The resend duplicates data | Offline: a resend that probes before repeating, with a fixture, then a device test |
| Timeouts without over-completions | The frames were really lost, and the resend is right | Look for the cause of the loss |
| Link stops, hang or Oops | Stop | Keep everything; no retry |
