# Runtime 14: the supplicant initialised and stopped at the packet socket the kernel lacks

Status: negative tool-environment result on candidate 13 (compile 18,
proposal 0157); the corrected invocation worked (the supplicant initialised,
read its configuration and reached the nl80211 driver), and it then failed to
add `wlan0` because the kernel has no packet sockets. No scan, management,
EAPOL or key command was submitted; the driver recorded no refusal and no
terminal record; the session, log seal, A53 regression and reviewed native
recovery all passed. This is not a handshake measurement.

## Identity

- Candidate 13, receipt `adc7a4a5…`, installed as [deployment 13](results/deployment-13.json)
  (full padded boot2 `ec412ce9…`), unchanged since runtime 13.
- Mainline boot `1c6d67ad-36a3-49db-b8ce-05205537a8d2`, release
  `7.1.3-gemini-a53-wifi-phase-b-compile`; capture 14 and session 14 each ran
  exactly once from the frozen `e7bcb6e5` laptop wrappers after both offline
  preflights passed, with the custodian's regenerated PSK-bound script from the
  corrected `join-once.sh`.
- Return: changed-boot Gemian `572f3ea9-7191-48eb-acc0-45a8b33a7fbd`, confirmed
  independently over the Gemian LAN. Complete sealed kernel log 146282 bytes,
  SHA-256 `e12c77d2…`; preservation manifest `0d7d3558…`; evidence roots
  consumed and retained privately; no raw log, stdout, command or credential
  left the laptop.

## Observations

- Capture 14 (Phase A on this boot): WMT common init 285/285, calibration ACK 1,
  task-4 reply 382 bytes, PA rails off, prerequisites ready.
- Session 14: the join phase completed its framed stdout under the
  authenticated boot (`transport_complete` true); `supplicant_exit=255`,
  `connect_exit=255`, `join_terminal=0`, `channel40_ir_after_beacon=0`,
  `scan_exit=1`, all five fixed-phrase counts 0. The private export of the
  complete supplicant log is complete: 5779 bytes, SHA-256 `fbb42cfc…`,
  the same byte count the join reported, zero supplicant processes, the same
  phrase counts; the C2 conjunction is false.
- Fixed diagnostic lines in that log, as the custodian reported them:
  `Successfully initialized wpa_supplicant`; `l2_packet_init: socket(PF_PACKET):
  Address family not supported by protocol`; `Failed to add interface wlan0`;
  on de-initialisation `nl80211: Getting wowlan status failed` and
  `set_key failed err=-22 Invalid argument` twice.
- Driver: zero management submissions, zero EAPOL observations, zero key
  commands, zero firmware commands from the join path, no refusal, no
  terminal record. The two `set_key` failures are the supplicant clearing
  keys it never installed: mac80211 refuses the removal of an absent key
  before the driver is reached, and the classifier shows no key command.

## Diagnosis, from the pinned sources and the candidate's configuration

wpa_supplicant 2.11 opens one `PF_PACKET` socket per interface in
`wpa_supplicant_update_mac_addr` (`wpa_supplicant/wpa_supplicant.c`, called
when the interface is added): `l2_packet_init` (`src/l2_packet/l2_packet_linux.c`,
`socket(PF_PACKET, …)`) runs whenever the interface is not a dedicated P2P
device, and a failure returns -1, which is "Failed to add interface". The
nl80211 control port changes only what the socket is used for: with
`WPA_DRIVER_FLAGS_CONTROL_PORT` and `CONTROL_PORT_RX` the EAPOL receive
callback is `NULL` (`wpas_eapol_needs_l2_packet`), but the socket is still
opened and the station's own address is read from it
(`l2_packet_get_own_addr`). The pinned build uses the default
`CONFIG_L2_PACKET=linux` backend. The kernel side: the arm64 defconfig sets
`CONFIG_PACKET=y`, and `configs/gemini-usbdiag.fragment` (in the profile
since 2026-07-16 for the minimal diagnostic link) unsets it; the candidate's
`kernel.config` (`153ea2d0…`, identical since compile 7) therefore carries
`# CONFIG_PACKET is not set`, and `socket(PF_PACKET)` fails with
`EAFNOSUPPORT`, exactly the measured line.

## Decision

The smallest standard fix is the kernel dependency itself: the Wi-Fi Phase B
fragment, which the profile applies after the usbdiag fragment, sets
`CONFIG_PACKET=y` again (the defconfig value); no other symbol, no change to
the firmware or driver resource ownership, and the nl80211 control-port path
for EAPOL stays as designed. The supplicant's standard l2 dependency is not
bypassed. This changes the kernel configuration for the first time since
compile 7, so a new compile (19), candidate (14) and deployment follow the
review; runtime 15 is then the first possible handshake measurement. Runtimes
13 and 14 remain startup failures of the tool environment, not handshake
results.
