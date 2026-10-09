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
(expected to be EAPOL-Key message 1) with the already tested decoder, without
transmitting anything beyond the bounded management exchange and the one
driver-owned deauthentication.

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
- association denied with a status other than 45: the RSN element is
  diagnosed against the selected sources and the private target metadata;
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

Purpose: complete the four-way handshake and install the pairwise and group
keys so that protected data can flow.

Open design choices to resolve before coding, with the measurements that decide
them:

1. Supplicant. The pinned Debian arm64 `wpasupplicant` package, added to the
   RAM root through the existing userspace receipt mechanism with its
   dependencies, is the preferred choice: standard and widely reviewed. A
   custom WPA2 handshake in the helper is not planned unless a concrete
   constraint (such as RAM-root size) forces it. The supplicant reads the
   passphrase as a private runtime input and sends EAPOL over nl80211's
   control port (`NL80211_ATTR_CONTROL_PORT_OVER_NL80211`), which keeps EAPOL
   off the network device path.
2. EAPOL transport in the driver. Control-port frames arrive at the driver as
   data frames through `.tx`, so C2 needs a data transmit path: the HIF TX
   header for an 802.11 data frame on a data traffic class, with page
   accounting like the management path. The C1 measurement of the received
   EAPOL frame decides whether received data arrives translated to Ethernet
   (then mac80211 needs it untranslated, or the firmware must be configured to
   stop translating) or as 802.11.
3. Key placement. mac80211 software crypto needs no firmware key; the firmware
   then sees protected frames it cannot inspect. Whether the firmware forwards
   protected data frames for a BSS declared encryption-disabled is unmeasured;
   if not, C2 installs the keys in the firmware through `CMD_ID_ADD_REMOVAL_KEY`
   with `CIPHER_SUITE_CCMP` and declares `AUTH_MODE_WPA2_PSK` and
   `ENUM_ENCRYPTION3_ENABLED` in the BSS payload, with a `set_key` operation.

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
