# Experiment: Bluetooth on the station, as a module, up to A2DP audio

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-bluetooth` |
| Status | `running`: driver compile-checked; nothing has run on the device yet |
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

| Decision | Why |
| --- | --- |
| Reassemble H:4 in the link's interrupt, deliver from a work item | An unbounded queue of whole packets replaces the 2026-10-07 draft's 16-slot ring, which stopped the link when full |
| Never refuse a frame to the link | A refusal stops the link for GNSS and Wi-Fi's firmware; a bad stream resets Bluetooth only |
| Send Set Radio and Set TX Offset from setup, on every open | Gemian sends them with these bytes. Function-on returns the controller to defaults |
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
| On the device | nothing yet |
