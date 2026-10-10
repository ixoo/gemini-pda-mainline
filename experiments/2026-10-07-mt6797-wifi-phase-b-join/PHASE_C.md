# Phase C design: protected association, keys and data on MT6797 Wi-Fi

Goal, as set by the owner: WPA2-PSK (CCMP) association to the owner's access
point, a working data path, DHCP, ping and sustained SSH over Wi-Fi. Phase B
([runtime 8](RUNTIME_8.md)) demonstrated one healthy bounded join whose
association response carried status 45; the request carried no RSN element,
which is the expected and inferred reason, not a measured cause. Phase C
adds, in three bounded stages, the RSN element, the keys and the data path.
Each stage has its own finite device protocol and is admitted only after
review; the owner's input is needed only for the private passphrase and the
physical boot.

Private target metadata (non-identifying, from the retained scan output): RSN
version 1, group cipher CCMP, pairwise cipher CCMP, AKM PSK, RSN capabilities
0x0000 (no management frame protection advertised). The SSID, BSSID and
passphrase stay private inputs.

## Facts the stages rest on

- The connect path is cfg80211's station management entity over mac80211's
  authenticate and associate (runtimes 5 to 8). Elements of the association
  request come only from the request (`nl80211_connect` copies `NL80211_ATTR_IE`
  into the connect parameters; mac80211 appends them). mac80211's default
  cipher list includes CCMP, and without a `set_key` operation it uses software
  crypto, so a connect naming CCMP and the PSK AKM is accepted by the stack.
- The driver's join path already handles an accepted association: the
  station transition to associated calls `mt6797_mac_join_associate` (BSS join,
  then station state 3 with the AID), logs `activation`, and the association
  request's completion requests the host-owned teardown with the driver-built
  deauthentication frame ([fixture](tests/host-test.py), accepted path). The
  BSS payload currently declares `AUTH_MODE_OPEN` and `ENUM_ENCRYPTION_DISABLED`
  (value 1 in the pinned `wlan_oid.h`).
- The receive path admits only unprotected management frames addressed to this
  station from the target (`join-rx.h`): a translated-Ethernet frame (header
  flag bit 7), a data frame or any other shape is refused, which ends the
  lifetime. The transmit path admits only management frames while the join is
  open (`mt6797_mac_tx`). Proposal 0140, tested offline and so far unselected,
  decodes exactly one received shape beyond that: a clear, non-aggregated,
  non-QoS From-DS WPA2 EAPOL-Key frame from the target to this station on the
  join channel, in both the native 802.11 and the translated-Ethernet layouts,
  with the vector and group-4 metadata bounds, the fixed frame control, the
  peer identity and complete EAPOL-Key framing (`eapol-rx.h`).
- Pinned vendor layouts for later stages (gen3 at revision `c5b0be85…`):
  `CMD_802_11_KEY` for `CMD_ID_ADD_REMOVAL_KEY` (add/remove, TX key, key type,
  authenticator flag, peer address, BSS index, algorithm, key id, key length,
  WLAN index, 32 bytes of material, 16 bytes of RSC); algorithm identifiers
  `CIPHER_SUITE_CCMP` = 4 (`mgmt/privacy.h`); `CMD_SET_BSS_INFO` carries
  `ucAuthMode` (`AUTH_MODE_WPA2_PSK` = 7) and `ucEncStatus`
  (`ENUM_ENCRYPTION3_ENABLED` = 6); the HIF TX header distinguishes 802.3 and
  802.11 payloads (`nic_tx.h`, `fgIs802_3`).

## Stage C1: accepted association, no keys, no data

Purpose: learn whether the AP accepts the association when the request carries
the RSN element, and, if it does, measure the first data frame the AP sends
(expected to be EAPOL-Key message 1) with the already tested decoder. The
station transmits no payload, sends no EAPOL reply and holds no key; it may
receive data-type frames from the AP, of which only the decoder-admitted
EAPOL shape is observed and all others are refused. Beyond the bounded
management exchange it transmits only the one driver-owned deauthentication.

Host delta (`helper/join-connect.c`): the connect request adds
`NL80211_ATTR_WPA_VERSIONS` = 2, `NL80211_ATTR_CIPHER_SUITES_PAIRWISE` = CCMP,
`NL80211_ATTR_CIPHER_SUITE_GROUP` = CCMP, `NL80211_ATTR_AKM_SUITES` = PSK and
`NL80211_ATTR_IE` holding the fixed 22-byte WPA2-PSK CCMP RSN element
(`30 14 01 00 00 0f ac 04 01 00 00 0f ac 04 01 00 00 0f ac 02 00 00`), which
contains no secret. No key attribute is sent. The dump fixture asserts the
exact attribute set. `join-once.sh` is unchanged.

Driver delta (proposal 0148, with 0140 selected into the Phase B series):

- No catch-all. Every received packet keeps today's rules: firmware events are
  parsed by the control-event parser with its fail-stop; beacons are skipped;
  management frames must satisfy `join-rx.h`; anything else is refused and
  ends the lifetime with the existing `frame refused` metadata, which is the
  finite first-unknown diagnostic.
- One new admitted shape, bound to the lifetime: after the validated status-0
  association response for the exact associated BSS and station, and before
  the deauthentication frame's TX done, a packet that the 0140 decoder accepts
  as a clear EAPOL-Key frame from the target to this station on channel 40,
  within its vector and group bounds, is logged as `eapol observed:
  translated=… frame=… activated=…` (layout, frame length, whether the local
  station activation had already completed; no key data, no addresses) and
  dropped. The decoder establishes framing and identity only: a complete
  EAPOL-Key frame of the WPA2 descriptor type from the target; it does not
  validate message 1, the nonce, the MIC or any handshake state, and the
  record claims none of those. The AP's first frame may arrive before the local activation event,
  so the window starts at the association response and the record says which
  side of activation it fell on. At most two such frames are admitted; a
  third, or one outside the window, falls through to the existing refusal and
  ends the lifetime with the `frame refused` metadata. Nothing is delivered
  to mac80211 and nothing is sent in reply.
- A finite hold before the single deauthentication: the driver-built
  deauthentication frame already queued at the association's completion is
  not dequeued for transmission until 250 ms after activation or until the
  first EAPOL frame is observed, whichever comes first. The hold never ends
  later than 1500 ms before the channel grant or the join deadline, which the
  deauthentication and the teardown already need, so it is inside the existing
  budgets; it adds no transmission and no retry. The deauthentication, its TX
  done and the teardown then proceed exactly as today. If the hold expires
  with nothing observed, the record simply shows zero observations.
- The BSS payload stays open and encryption-disabled: no key exists.

Branches of the single boot, stated in advance:

- association accepted, activation logged, one or two EAPOL frames observed,
  deauthentication acknowledged, healthy teardown: C2 can be scoped on a
  measured wire shape;
- association accepted and healthy teardown with zero EAPOL observations: the
  association is demonstrated but the wire shape is not resolved; the hold or
  the AP's timing is reconsidered before any repeat;
- association denied with any non-zero status, 45 included: the RSN element
  and the request are diagnosed against the selected sources and the private
  target metadata before any repeat;
- any refusal: diagnosed from its branch and metadata as in runtime 7.

Classifier: the accepted path requires exactly one accepted association
response, exactly one `activation`, the deauthentication TX with its TX done
status 0 and page return, and the ordered cleanup with `deauth=1`, as the
existing accepted-path grammar already does. `eapol observed` is a non-refusal
diagnostic valid at most twice and only between the status-0 association
response and the deauthentication's matched TX done, the driver's window; its
frame length must lie in the decoder's exact range for its layout (native
131 to 2084, translated 99 to 2052) and its activated field must agree with
the activation record's placement; the parsed metadata is reported separately
as EAPOL framing observations and never as part of the association verdict.

## Stage C2: keys

Purpose: complete the four-way handshake with the standard supplicant and
install the pairwise and group keys, bounded, with no ordinary data. Design
findings as of 2026-10-09, after runtime 12; every claim below names its
source. Nothing here is built or admitted into a runtime before review.

### Settled by measurement (runtime 12)

The AP's first frame after accepting the association is a clear, translated
Ethernet data frame without an RX vector, BSSID tag 15, WLAN index 1, carrying
complete EAPOL-Key framing, and it arrives 1610 µs before mac80211 processes
the association response and about 50 ms before the firmware station
activation. The association completes in mac80211 and the station
activates with the BSS declared open and encryption-disabled.

Runtime 15 (candidate 14, the first handshake measurement) settled one more
value: after the station activation the next clear translated EAPOL-shaped
packet from the AP (consistent with message 3, its body unexamined) carries
RXD BSSID tag 1 (byte 7 `0x04`), while message 1 before the activation
carries 15 as in runtime 12. Proposal 0158 binds the admission to those two
measured values and intervals; the field is firmware-filled and unused by the
pinned receive path, and its vendor own-MAC index (0 for the first BSS) does
not match it, so no meaning is claimed beyond the measurement, and the
decoder's remaining framing gates verify that packet on the next boot.

Runtime 16 (candidate 15) verified that framing: the after-activation packet
was delivered, message 4 was sent and the supplicant completed its handshake
and offered both keys. The join then fail-stopped on a 136-byte
software-defined frame (the vendor's management-processing layout) before any
key command; the refusal summary could not describe it. Proposal 0159 names
such frames (header, group set, frame control, peer flags, security mode) and
refused key commands, changing no admission; the frame's policy is decided
from the next measurement. Two foreseeable consequences remain unmeasured and
are stated here, not acted on: a management frame from the AP after message
4 ends the join before the keys, and once keys are installed the AP's
protected data frames, which no gate admits, would end the hold the same way.

Runtime 17 (candidate 16) measured the second consequence earlier than
expected: a protected group-flagged data frame from the AP (inferred from
the public descriptor layout to be its ordinary traffic encrypted with the
group key the station does not yet hold; receiver address, cipher and body
unrecorded) arrived before message 3 and ended the join at the gate. Proposal 0160 discards exactly that measured
class (group match bit, native protected FromDS data from the target, the
measured descriptor fields and status `0xc004`) undelivered while the station
is active and holds no group key. After the group key's credit the same
frames arrive decrypted or with another status and are not this class; what
they look like then is unmeasured, and whether they end the hold is the next
foreseeable question, not acted on. The runtime-16 software frame did not
recur and stays refused.

Runtime 18 (candidate 17) named the software frame it refused after message
4: an unprotected Action frame from the AP to this station (category
unrecorded); runtime 16's unclassified frame shared its type word and length
and is consistent with it, an inference. Proposal
0161 discards exactly that measured class undelivered while the station is
active, each recorded, at most eight per join. Runtime 18 also demonstrated
all four handshake messages on the air with the supplicant completing its
negotiation; the keys reached the driver only after the stop. The remaining
foreseeable questions after the keys (protected unicast and decrypted group
traffic during the hold) are unmeasured and unchanged.

### Settled by source

1. **Early EAPOL needs no deferral machinery.** The pinned mac80211
   (`net/mac80211/rx.c`, `ieee80211_rx_h_check`) lets a data frame from a
   known station through before the `WLAN_STA_ASSOC` flag when the interface
   is a station and the frame carries the control-port Ethernet type, with
   the comment naming exactly this AP-first-frame race;
   `ieee80211_frame_allowed` admits EAPOL to our address regardless of
   encryption and port state. The station exists in mac80211 from the
   authentication. The pinned wpa_supplicant 2.11 (`wpa_supplicant.c`,
   `wpa_supplicant_rx_eapol`) queues an EAPOL frame received while its state
   is below associated and (`events.c`, association event handling) processes
   it after the association notification when it is younger than 200 ms and
   from the connected BSSID. The driver therefore delivers the decoded frame
   to `ieee80211_rx` at once, as the 32-byte rebuilt 802.11 header plus the
   EAPOL body, with no delay, no buffering and no invented state.
2. **The supplicant must own the connection.** cfg80211 unicasts control-port
   frames only to `wdev->conn_owner_nlportid` and returns `-ENOENT` when
   there is none (`net/wireless/nl80211.c`, `__nl80211_rx_control_port`).
   wpa_supplicant sets `NL80211_ATTR_SOCKET_OWNER` and the control-port
   attributes on its authenticate and associate requests
   (`driver_nl80211.c`). The Phase C1 helper, which exits after the connect,
   cannot be the owner, so C2 retires the helper: the supplicant performs the
   scan, authentication and association itself through mac80211's SME path
   (`NL80211_CMD_AUTHENTICATE` and `NL80211_CMD_ASSOCIATE`), which produces
   the same open-system authentication frame and an association request whose
   RSN element body is the fixed WPA2-PSK CCMP body the driver admits with
   one difference the C2 design first missed: `wpa_supplicant_set_suites`
   (`wpa_supplicant.c` 2112 to 2117) claims WMM whenever the BSS carries the
   WMM vendor element, because the supplicant has no driver capability
   indication for the number of replay counters, and `rsn_supp_capab`
   (`rsn_supp/wpa_ie.c` 108 to 114) then declares 16 PTKSA replay counters
   in the RSN capabilities (value 0x000c). The target advertises WMM (the
   owner's metadata-only check of the retained runtime-12 scan), so the
   exact C1 comparison (capabilities 0) would refuse the request before
   transmission. Proposal 0157 compares the first 18 body bytes exactly and
   admits exactly the two capability values 0 and 0x000c; MFPC, MFPR, OCVC,
   extended key id, pre-authentication, no-pairwise and every other value
   stay refused, as do HT, VHT, mobility domain, fast transition and the WMM
   element itself, which mac80211 does not add with one hardware queue. The
   declaration is a station statement to the AP; no firmware command, key
   payload, BSS declaration or receive path depends on it, and no WMM or QoS
   support is claimed. Candidate 12, built without 0157, is preserved unused.
   The supplicant's fixed phrases are a separate observed result; they are
   never read as proof of a driver or firmware state.
3. **One passive single-channel scan, no extra scans.** With the documented
   global option `passive_scan=1` the supplicant requests a passive scan with
   no SSID (`scan.c`, "Use passive scan based on configuration"), and with
   `scan_freq=5200` and `freq_list=5200` in the network block it scans one
   channel. That is exactly the one scan the driver admits (no SSIDs, no
   flags, no duration, one channel, broadcast BSSID). After the lifetime's
   deauthentication the supplicant will request further scans; the driver
   refuses them without any firmware operation (`scan_used`), and the session
   stops the supplicant. No modified supplicant, no control-interface tricks.
   The flush flag (`only_new_results`) is set only for a manual scan with
   `only_new=1` or after `wpa_bss_flush`, which runs from the disabled-interface
   timeout and at deinit, never on interface start (`scan.c`, `bss.c`,
   `wpa_supplicant.c`), so the automatic initial scan carries no flag and the
   driver's exact no-flag guard stays.
4. **One driver change is required for the scan to be accepted.** The
   supplicant adds an extended-capabilities element to every scan request
   (`scan.c`, `wpa_supplicant_extra_ies`, from the capabilities mac80211
   advertises). The driver registers `max_scan_ie_len = 0`, and with a
   `hw_scan` operation mac80211 leaves that at zero, so cfg80211 rejects any
   user scan element (`net/mac80211/main.c`: "userspace will not be allowed
   to in that case") and the supplicant would loop on "Failed to initiate AP
   scan". The passive scan transmits no probe request, so the elements are
   never sent; the fix is to register a bounded `max_scan_ie_len` and leave
   `hw_scan` exactly as it is: it already refuses any SSID, flag, duration or
   second channel (the no-active-scan guard) and never reads the elements.
   Nothing else about scanning changes.
5. **EAPOL transmit is the vendor security-frame shape on TC4.** mac80211
   hands the supplicant's control-port frames to `.tx` as 802.11 data frames
   flagged `IEEE80211_TX_CTRL_PORT_CTRL_PROTO` and reports their status back
   to the supplicant (`ieee80211_tx_control_port`, the TX-status extended
   feature mac80211 advertises). The pinned gen3 driver sends every 802.1X
   frame as a security-frame command on TC4 with the 28-byte long descriptor,
   header format non-802.11 with the Ethernet II flag, Ethernet-type offset
   `(12 + 28) / 2`, TID 0, the station's WLAN index, own-MAC index, TC4
   lifetime and count, the BSS fixed rate and a PID with TX status to the MCU
   (`nicTxComposeSecurityFrameDesc`, `wlanProcessSecurityFrame`). The driver
   converts the 802.11 data frame back to 802.3 (destination from address 3,
   source from address 2, Ethernet type from the SNAP header) and submits it
   through the existing TC4 path and ledger, one frame in flight, pages
   `(28 + bytes + 127) / 128`, returned through the WTQCR word the ledger
   already reconciles.
6. **Key ownership: the firmware, as the pinned vendor implementation's
   choice.** C1 does not prove this necessary: the measured clear EAPOL
   translation says nothing about the layout of protected data, and the
   driver already reconstructs the 802.11 header, so software CCMP is not
   precluded. Firmware offload is chosen because it is the pinned vendor
   path: the vendor installs keys in the WTBL through
   `CMD_ID_ADD_REMOVE_KEY` (0x07, `CMD_802_11_KEY`, 64 bytes: add, TX key,
   unicast or group, authenticator flag, peer address, BSS index, algorithm
   `CIPHER_SUITE_CCMP` = 4, key id, key length, WLAN index 1 for the pairwise
   key and the BMC WLAN index 0 for the group key, 32 bytes of material of
   which 16 are used, 16 bytes of RSC) and declares the BSS `AUTH_MODE_WPA2_PSK`
   = 7 and `ENUM_ENCRYPTION3_ENABLED` = 6 in `CMD_SET_BSS_INFO` bytes 53 and 54
   at connect time, before any key exists, while clear EAPOL still flows
   (`wlanoidSetAddKey`, the BSS-info layout). mac80211 keeps keys in software
   only when the driver has no `set_key`; with one it marks the key uploaded
   and encrypts nothing. C2 therefore implements `.set_key`: `SET_KEY` submits
   the vendor command for the pairwise key (from the supplicant's first
   `NEW_KEY`, WLAN index 1) and the group key (BMC WLAN index 0, the AP's
   address as the peer, as the vendor substitutes the BSSID for the broadcast
   address). The command's RSC field is zero for both: the pinned
   `wlanoidSetAddKey` zeroes the whole command at its start and never writes
   `aucKeyRsc`, which only the WAPI function fills, so no receive sequence
   counter reaches the firmware for a CCMP key and replay protection is not
   validated by C2. Removals follow `wlanoidSetRemoveKey` exactly: the zeroed
   command with AddRemove 0, key id, peer and BSS index, unicast type 1 and
   WLAN index 1 for the pairwise key, type 0 and the BMC index for the group
   key, no TX-key flag, no algorithm, no length. The BMC WLAN index 0 is this
   driver's declared choice, bound to the station record and BSS payload it
   submits, where the vendor allocates one dynamically; whether the firmware
   accepts that bound index is a retained device branch. The driver's copies of key
   material, the command payload and the HIF transfer buffer, are cleared
   after submission; mac80211's own key stays for its normal lifetime, and no
   record carries a key byte or digest. The
   standard supplicant hands message 4 to the driver before installing the
   pairwise key (`rsn_supp/wpa.c`, message 3 processing), so `set_key`
   serializes on the existing TC4 ledger: it waits for an in-flight reply's
   TX done and credit within the frame and join deadlines, and a reply that
   is only queued stays queued while the key command's page is owed. A
   returned credit proves only
   that the firmware consumed the command buffer; the records and results say
   `key command submitted` and `credit returned`, never installed or
   accepted, because no acknowledgement with that meaning exists in the
   pinned source. Key retirement is explicit: on the healthy path the lifetime
   submits bounded `remove` commands for the pairwise key (WLAN index 1) and
   the group key (BMC index 0) before the station and BSS cleanup, each with
   its credit and sequence accounted, because removing the station record is
   not shown by the source to retire the group key held under the BMC index;
   `DISABLE_KEY` from mac80211 submits nothing itself. In the code's actual
   order the removals run inside the cleanup after the deauthentication has
   completed and before the station removal, channel abort and BSS-off
   stages. No protected data frame is admitted or delivered in C2 (the AP may
   send one; the refusal branch records its header), so no receive crypto
   flag is guessed.

### Retained uncertainty, as device branches

- Whether the firmware consumes the key commands (credit returned, no
  refusal record); whether it acts on them, and whether it accepts the
  declared BMC WLAN index 0 for the group key, is not observable in C2 and is
  not claimed; the zero RSC means replay handling is not validated. Whether declaring WPA2 at BSS configuration leaves the clear
  message 3 undisturbed, as it does in the vendor flow.
- Whether the firmware's BSSID tag changes after the BSS configuration; a
  frame tagged 15 after that point is refused with its header named, as today.
- Protected data in either direction is Stage C3 and is not claimed by C2.

### Lifecycle and budgets

The lifetime keeps the existing grant (9 s) and join deadline (10 s), one
scan, one authentication, one association, at most two received EAPOL frames
(messages 1 and 3) and at most two transmitted (messages 2 and 4), each
EAPOL frame submitted only after the firmware activation (held in the
existing queue otherwise), two key commands, two key removal commands on the
healthy path, and the single driver-built deauthentication.

The one queue stays one queue. Today the driver-built deauthentication is
queued at the association's completion and the worker holds it at the head
while the hold runs; a control-port frame queued behind it would be blocked.
The smallest change is in the dequeue step: the worker takes the first queued
frame that is not held (the held deauthentication is skipped, not moved), so
message 2 and message 4 are submitted while the deauthentication keeps its
place and its hold; after the hold the deauthentication is the next frame
taken. No second queue, no new state beyond the hold that exists. A
production worker and transmit fixture runs the whole sequence: early message
1 observed and delivered, association, the held deauthentication queued,
message 2 queued behind it before activation, activation, message 2 submitted
with its credit and status, message 3 delivered, message 4 submitted, the two
key commands with their credits, the hold's end, the single deauthentication,
then the two key removals and retirement with every page returned.

No ordinary data is transmitted. The candidate-11 kernel has `CONFIG_IPV6`
unset, so the kernel sends no IPv6 neighbour discovery or duplicate-address
detection after the port is authorized and no suppression is needed; no IPv4
client runs. The driver's transmit admission refuses any other data frame as
today. An unsolicited ordinary or protected frame received
after the keys is refused by the frame gate with its header named, a fail-stop
like every other refusal; no receive crypto flag is guessed to admit it. The
deauthentication hold becomes: until both key commands have returned their
credit plus one second, or four seconds after activation if they have not,
never later than 1.5 s before the grant or join deadline. The C1 fail-stop is
preserved exactly: only the healthy path runs the deauthentication, the
ordered key removals and the three-stage cleanup; any refusal, poisoned or ambiguous
credit, overflow or deadline ends the lifetime with no further command, as
today, and the evidence is sealed and the reviewed recovery follows.

### Supplicant and credential input

The static wpa_supplicant 2.11 (`0487b710…`) joins the RAM root as
`bin/wpa_supplicant` through the composer's member mechanism (63 members).
The bound session script writes a mode-0600 configuration in RAM from
private variables embedded by the private binding step (SSID, BSSID and the
64-hex PSK), from the template in [`helper/wpa_supplicant.conf.template`](helper/wpa_supplicant.conf.template):
`passive_scan=1`, `ap_scan=1`, one network with `proto=RSN key_mgmt=WPA-PSK
pairwise=CCMP group=CCMP ieee80211w=0 scan_freq=5200 freq_list=5200` and the
pinned `bssid`. The supplicant runs with `-d` and never `-K`, logging to a
RAM file; the session preserves that complete log privately before recovery
as unique handshake evidence (mode 0600, never uploaded or published) and
puts only fixed phrases with redacted addresses into the sanitized result
(`CTRL-EVENT-SCAN-RESULTS`, `Associated with`, `WPA: Key negotiation
completed`, `CTRL-EVENT-CONNECTED`, `CTRL-EVENT-DISCONNECTED`), then stops
the supplicant after the lifetime ends. The bound script that carries the
SSID, BSSID and PSK stays private: it is never composed into a candidate, no
secret appears in a command argument, a printed or logged SSH payload, a trace
or a diagnostic (the reviewed private stdin and file transport carries it over
SSH by design),
and the hashes and provenance of that script and the configuration stay
private as well, while candidate, boot and package checksums remain
publishable. The session, seal and reviewed recovery flow are the existing
ones.

The PSK comes from the credential already configured in Gemian, by owner
decision. [`helper/extract-gemian-credential.py`](helper/extract-gemian-credential.py)
runs on the laptop only, over the standard ssh client (host alias,
BatchMode, strict known host, no host-key update, IdentitiesOnly, no agent,
optional identity file) with `sudo -n` for the root-owned connman files: one
remote read program checks the exact boot id, kernel `3.18.41+` and Debian
`9.13` before and after the read in the same session, reads only the PSK services named with the target SSID's hex identifier
(other SSIDs, open, WEP and enterprise services are left unread) with GLib's
own key-file reader through ctypes (so the escaped value is decoded by GLib,
not re-implemented), refuses symlinked, non-regular, non-root-owned or
group-readable settings, requires exactly one such service whose group `Name`
equals the target SSID with `Name` and `Passphrase` present once and
`Security` absent or `psk` (ConnMan does not persist `Security`), and prints
a small report with the secret base64-encoded; that report is streamed straight
into a fresh mode-0600 file under a fresh mode-0700 directory, the PSK
(PBKDF2-HMAC-SHA1, 4096 rounds, the SSID as salt) is derived into a second
mode-0600 file, and a provenance record without any secret is written. No
secret reaches stdout, stderr, an argument, a log or this chat, failures print
generic messages without tracebacks, and nothing on the device is written,
reconfigured or copied in bulk. The tool is not run before it is reviewed.

### Classifier and evidence

The accepted C2 path adds, to the C1 grammar: `eapol delivered` (at most
two, each with layout, length, vector and BSS fields), `eapol sent` (at most
two, PID, pages), `key command: pairwise|group submitted` with its `credit
returned` (at most one each, no material, no id), `key removal: pairwise|group
submitted` with its credit, the supplicant's fixed phrases from the session as
a separate observed result, and the unchanged deauthentication and teardown.
`wifi_operational` stays false.

### Implementation status

Proposals 0153 (scan-element limit), 0154 (EAPOL delivery), 0155 (control-port
transmit on TC4 through the one queue) and 0156 (firmware keys, WPA2 BSS
declaration, ledger-serialized `set_key`, explicit removals after the
deauthentication) are written, fixture-covered and were reviewed at
0e333617; compile 17 built them (job
`0e333617…-mt6797-a53-wifi-phase-b-compile-m0`) into candidate 12, which is
held unused: proposal 0157 (RSN capabilities 0 or 0x000c admitted, found
from the pinned supplicant source before any boot) is under review and
needs one further compile and candidate 13. The session tooling
(`c2-session.py`, the `passive-host.py` hooks, the binder's hex SSID and
PSK, the join script's supplicant-owned mode) is under review; no candidate,
deployment or device action until that review's go.

### Device protocol, stated in advance

One boot: the supplicant's one passive channel-40 scan, its open-system
authentication and RSN association, the two EAPOL frames each way, the two
key commands, the hold, the driver's deauthentication, then the two key
removals and the three-stage teardown; reviewed native recovery; the sealed log and
sanitized phrases are the evidence. Branches: the supplicant reports key
negotiation completed and both key commands returned their credit, then the
healthy ordered teardown; EAPOL framing admitted but the supplicant does not
complete (its phrase and the driver records decide; the healthy teardown
still runs at the hold's end if nothing is poisoned); a key command refused
or its credit ambiguous or late (fail-stop: no further command, seal,
reviewed recovery); a scan or association shape refused by the driver (named
refusal, fail-stop); or the AP's behaviour differs. No branch repeats a boot
without a decision-changing change.

## Stage C3: data, DHCP, ping, SSH

Receive and transmit data frames between mac80211 and the firmware on the data
traffic classes with bounded page accounting, then busybox `udhcpc`, `ping`
and the existing dropbear SSH service over `wlan0`. Budgets, logging and the
teardown are defined when C2's measurements are in.

## Order and admission

C1 is implemented first and reviewed before its build; its single boot answers
whether the association is accepted and what the first data frame looks like.
C2's choices are then settled from that evidence and this document is updated
before C2 code. No stage repeats a boot without a decision-changing
measurement, and every stage keeps the reviewed recovery.
