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

Purpose: complete the four-way handshake and install the pairwise and group
keys so that protected data can flow.

Research state (2026-10-09, hardware-free, public sources only; nothing here
is admitted into a runtime or a build before the runtime-9 evidence):

### Supplicant, pinned

Upstream wpa_supplicant 2.11 (tarball SHA-256 `912ea06f74e30a8e36fbb68064d6cd
ff218d8d591db0fc5d75dee6c81ac7fc0a`, release signature good under the hostap
release key `EC4A A0A9 91A5 F246 4582 D52D 2B6E F432 EFC8 95FA`) with libnl
3.11.0 (SHA-256 `2a56e1edefa3e68a7c00879496736fdbf62fc94ed3232c0baba127ecfa76
874d`, release signature good under the libnl release key `49EA 7C67 0E08 50E7
4195 14F6 29C2 366E 4DFC 5728`, which has since expired). The reproducible
static aarch64 build is [`helper/build-wpa-supplicant.sh`](helper/build-wpa-supplicant.sh)
with [`helper/wpa_supplicant.config`](helper/wpa_supplicant.config): nl80211
driver only, internal crypto, Unix control socket, file backend without
writes or blobs, no D-Bus, P2P, AP, mesh, WPS, EAP methods or SAE. Two builds
produced the same binary, SHA-256 `0487b7109c0a456eabf3aef33d74d38e5aa4e6dddcb
586c03bb203803dd27da7`, 1719888 bytes. It is preferred over the Debian package
because it has no shared-library closure to add to the RAM root. The binary
links libnl (LGPL-2.1) statically; it is a private test artifact built from
pinned sources that allow relinking and is not redistributed. The pinned
supplicant requests the nl80211 control port whenever the driver advertises
it (`driver_nl80211.c`), and mac80211 advertises it unconditionally
(`net/mac80211/main.c`), so EAPOL never touches the network-device path. Its
completion is the `WPA: Key negotiation completed` log line, with
`CTRL-EVENT-CONNECTED`; the passphrase stays a private runtime input.

### EAPOL transmit: the vendor security-frame shape (pinned gen3 source)

- The vendor driver sends every 802.1X frame as a *security frame command* on
  TC4, the MCU port, queue 1 (`nicTxGetFrameResourceType`,
  `wlanProcessSecurityFrame`), not on the data access categories. Its
  descriptor (`nicTxComposeSecurityFrameDesc`) is the 28-byte long format
  with header format `NON_802_11` and the Ethernet II flag, the ether-type
  offset `(12 + 28) / 2`, TID 0, the station's WLAN index, own-MAC index,
  TC4 lifetime and count limits, the BSS default fixed rate, and, because the
  vendor wants a completion, a PID with TX status to the MCU. The payload is
  the 802.3 frame; the firmware builds the 802.11 header.
- Consequence: C2 can reuse the existing TC4 management path and ledger for
  EAPOL. mac80211 hands the control-port frame to `.tx` as an 802.11 data
  frame (`ieee80211_tx_control_port`, flag `IEEE80211_TX_CTRL_PORT_CTRL_PROTO`);
  the driver converts it back to 802.3 and submits it with a second descriptor
  builder for the security-frame shape, keeping the management builder
  unchanged. Pages are counted as for management, `(28 + bytes + 127) / 128`,
  and returned through the same WTQCR word 7 (CPU and FFA halves) the ledger
  already reconciles. Only one EAPOL frame is in flight at a time, as today.
- The data access categories are a C3 matter: AIS maps best-effort traffic to
  TC1 (LMAC port 0, queue AC1; 36 buffers of 13 pages in the vendor's
  host-side quota table) with an 8-byte short descriptor, and their releases
  arrive in WTQCR words 0 to 3, which the present ledger refuses as a
  fail-stop. Extending the ledger is C3 work, not C2.

### EAPOL receive

The 0140 decoder already covers both layouts the firmware may use. For the
translated layout it rebuilds the 32-byte 802.11 header plus LLC/SNAP from
RXD group 4 (`prefix`), so the driver can deliver `prefix + EAPOL body` to
`ieee80211_rx` without any mac80211 change; for the native layout the frame
is delivered as received. mac80211 then routes the frame to the supplicant
through `cfg80211_rx_control_port` (`net/mac80211/rx.c`). Which layout the
firmware uses for this BSS is exactly what runtime 9 measures. Translation is
decided by the firmware; the pinned headers expose no command that selects it.

### Crypto ownership

- Vendor fact: the firmware encrypts only when the TXD protected bit is set,
  and the vendor sets it only when the BSS is declared encrypted
  (`secIsProtectedFrame` → `secIsProtectedBss`); the key lives in the WTBL
  entry installed by `CMD_ID_ADD_REMOVAL_KEY` (`CMD_802_11_KEY`: add, TX key,
  unicast type, peer address, BSS index, `CIPHER_SUITE_CCMP` = 4, key id,
  16-byte material, the station's WLAN index for the pairwise key and the BMC
  WLAN index for the group key, RSC) and the BSS payload declares
  `AUTH_MODE_WPA2_PSK` = 7 and `ENUM_ENCRYPTION3_ENABLED` = 6.
- mac80211 fact: with no `set_key` operation the key stays in software
  (`net/mac80211/key.c`), mac80211 encrypts CCMP itself, sets the protected
  bit in the frame control and expects to decrypt received frames itself.
- Two admissible designs, decided by measurement, not preference:
  (a) software crypto, BSS stays encryption-disabled, no key command, TXD
  protected bit clear; requires that the firmware forwards frames whose frame
  control carries the protected bit for an unencrypted BSS in both directions,
  which no pinned source answers; (b) firmware keys through `set_key` with the
  vendor command, BSS declared WPA2-PSK/encryption 3, TXD protected bit set
  on data; requires knowing whether the hardware strips the CCMP header and
  MIC on receive (`RX_FLAG_DECRYPTED`, `RX_FLAG_IV_STRIPPED`), which the
  translated layout implies and the native layout leaves open. The handshake
  itself needs no key in either design; C2 installs the keys at its end and
  measures one protected frame in each direction before C3.

### Station record

The submitted station record declares no QoS (`ucIsQoS` = 0). mac80211 will
emit QoS data frames if the association response advertises WMM; for EAPOL
this is moot because the driver re-encapsulates to 802.3 on TC4, but C3's
data path must either declare QoS in the record or strip it from frames.

Open until runtime 9: the AP's acceptance with the RSN element, the EAPOL
layout on the wire, and whether the first frame arrives before or after the
local activation. C2 code follows this document's update with that evidence.

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
