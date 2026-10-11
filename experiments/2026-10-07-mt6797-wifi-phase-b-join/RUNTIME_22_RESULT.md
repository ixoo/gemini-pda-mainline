# Runtime 22 result: negative, fail-stop at the frame gate before the key commands

Boot: mainline `e9fa7967-4cfa-427a-a021-a92d2e131de6` on candidate 21 (compile 26,
package `dd35c1d2…`, boot2 `79cde346…`), session tools at c3d74015, launched by the
custodian after deployment 21 (predecessor candidate 20 `d01f3304…`, stock boot
`a2265c06…`). Evidence: the custodian's sanitized uploads (join diagnostic records,
log and supplicant-log results); kernel log sealed complete (153971 bytes, 2026
records, SHA-256 `d214e63b…`); supplicant log complete (24060 bytes, SHA-256
`c5cab8a2…`). No raw log, address, body or identifier is published.

## Observed

- Authentication and association (status 0) exchanged and acknowledged; station
  activated; EAPOL messages 1 to 4 delivered and sent as in runtime 21; the
  target's directed clear Action frame discarded once (the runtime 18 class).
- Then one packet refused at the frame gate: 110 bytes in all, type word 0x4000
  (data, no groups), header at 16, descriptor bytes 08 28 18 04 02 00 04 c0,
  untranslated, frame control first bytes 0x6208, FromDS, security mode 0.
  Fail-stop: stopped with status -71, branch 7. The supplicant's key commands then
  arrived and were refused (-71 and -95).
- The runtime 21 class (proposal 0168) was not observed in this boot: no
  `group action frame discarded` record before the stop.
- No key command, channel release, data phase, DHCP, ping or listener ran; the
  laptop's Wi-Fi SSH check saw no readiness marker within its budget (92 s) and
  attempted nothing. Verdicts: C2 false, C3 false; the classifier at c3d74015
  reports the run as a recorded refusal with a terminal failure, not malformed
  (`group_action_frame_discards` 0).

## Diagnosis

The refused packet's observed descriptor and first frame-control bytes match
runtime 17's protected group-addressed data class (`group-data.h`: 110 bytes,
broadcast match flag, BSSID field 1, security mode 0, status 0xc004 with the
cipher-mismatch flag, frame control 0x6208) with one difference: WLAN index 2 where
runtime 17 measured 0. The transmitter, receiver, fragment field and body were not
retained, so that it was the full class (the target as transmitter, a group
receiver, fragment 0) is conditional on the decoder's checks on the next such
packet, not measured here. Proposal 0164 made the station record declare broadcast
WLAN entry 2 (runtime 17 ran with entry 0 declared), and the decoder pinned index 0,
so the packet fell through to the general gate. Inference, not measured: the
firmware tags the target's group-addressed frames with the broadcast entry the
station record declares.

## Not observed and not claimed

The frame's receiver address, body and cipher header were not retained; nothing is
claimed about them beyond the descriptor's flags. No network function, no key
installation in firmware, no data path. The fail-stop was triggered by the driver's
own receive-frame gate; no firmware fault was reported, and the firmware's execution
after the stop was not independently measured.

## Recovery

One reviewed native restart was requested after the evidence was sealed, with the
live identity and the reboot tool checked. The native return collector consumed its
budget (12 slots, 165.02 s) with `recovery_confirmed` false and `regression_pass`
false, and one subsequent bounded known-good LAN identity check reported the host
down; those receipts are preserved as recorded. Separately and later, after the owner
reconnected the device to Wi-Fi from its UI, one read-only identity check confirmed
stock Gemian 3.18.41+ on boot `720fcced-58b4-4a7a-a7f1-5afa066f728b` (distinct from
the mainline boot and from the preceding stock boot); the custodian uploaded that
stdout (SHA-256 `fce9c82c…`). The late confirmation does not change the original
timeout receipts. The installed boot2 remains candidate 21 (`79cde346…`). No
additional restart, recovery retry or alternate recovery path was performed.

## Decision

Proposal 0169 makes the group-data class take the declared broadcast entry from the
caller (the driver passes the constant 0164 declares) and require exactly it; under
entry 0 the runtime 17 bytes remain the class, under entry 2 the runtime 22 bytes
are. No budget, window or other condition changes. Compile 27 follows the custodian's
source review; a candidate and one boot follow after that. No repeat of candidate 21.
