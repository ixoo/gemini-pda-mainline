# Phase C design: protected association, keys and data on MT6797 Wi-Fi

Goal, as set by the owner: WPA2-PSK (CCMP) association to the owner's access
point, a working data path, DHCP, ping and sustained SSH over Wi-Fi. Phase B
([runtime 8](RUNTIME_8.md)) demonstrated one healthy bounded join whose
association was denied because the request carried no RSN element. Phase C
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
  open (`mt6797_mac_tx`).
- Pinned vendor layouts for later stages (gen3 at revision `c5b0be85…`):
  `CMD_802_11_KEY` for `CMD_ID_ADD_REMOVAL_KEY` (add/remove, TX key, key type,
  authenticator flag, peer address, BSS index, algorithm, key id, key length,
  WLAN index, 32 bytes of material, 16 bytes of RSC); algorithm identifiers
  `CIPHER_SUITE_CCMP` = 4 (`mgmt/privacy.h`); `CMD_SET_BSS_INFO` carries
  `ucAuthMode` (`AUTH_MODE_WPA2_PSK` = 7) and `ucEncStatus`
  (`ENUM_ENCRYPTION3_ENABLED` = 6); the HIF TX header distinguishes 802.3 and
  802.11 payloads (`nic_tx.h`, `fgIs802_3`).

## Stage C1: accepted association, no keys, no data

Purpose: prove that the AP accepts the association when the request carries the
RSN element, and measure the one unknown this exposes, the wire shape of the
first data frame the AP sends (EAPOL message 1), without transmitting anything
beyond the bounded management exchange.

Host delta (`helper/join-connect.c`, `join-once.sh`): the connect request adds
`NL80211_ATTR_WPA_VERSIONS` = 2, `NL80211_ATTR_CIPHER_SUITES_PAIRWISE` = CCMP,
`NL80211_ATTR_CIPHER_SUITE_GROUP` = CCMP, `NL80211_ATTR_AKM_SUITES` = PSK and
`NL80211_ATTR_IE` holding the fixed 22-byte WPA2-PSK CCMP RSN element
(`30 14 01 00 00 0f ac 04 01 00 00 0f ac 04 01 00 00 0f ac 02 00 00`), which
contains no secret. No key attribute is sent. The dump fixture asserts the
exact attribute set.

Driver delta: between the `activation` record and the completion of the
driver's deauthentication frame, admit at most two received packets that are
neither firmware events nor parseable management frames, log their header
metadata only (logical length, wire type, header flag byte, frame control if
untranslated, Ethernet type if translated) and drop them; outside that window
or beyond the budget refuse as today. This is a bounded measurement of the
data-frame wire shape, not a data path: nothing is delivered, nothing is sent.
The BSS payload stays open and encryption-disabled, since no key exists.

Expected observation: `activation: sequence=… state=3`, the deauthentication
TX and its acknowledgement, `cleanup: stage=3 … deauth=1`, and zero to two
`data frame observed` records. Branches: association accepted and the data
frame shape measured (proceed to C2); association still denied with a status
other than 45 (diagnose against the RSN element); a new refusal (diagnose from
its branch).

Classifier: the accepted path already exists; the new record kind becomes a
non-refusal diagnostic admitted at most twice within the associated window.

## Stage C2: keys

Purpose: complete the four-way handshake and install the pairwise and group
keys so that protected data can flow.

Open design choices to resolve before coding, with the measurements that decide
them:

1. Supplicant. Either the pinned Debian arm64 `wpasupplicant` package added to
   the RAM root through the existing userspace receipt mechanism (several
   megabytes of dependencies; standard, well reviewed), or a minimal WPA2-PSK
   handshake in the static helper (PBKDF2, PRF, HMAC-SHA1, AES key unwrap;
   small but security-sensitive). Either reads the passphrase as a private
   runtime input and sends EAPOL over nl80211's control port
   (`NL80211_ATTR_CONTROL_PORT_OVER_NL80211`), which keeps EAPOL off the
   network device path.
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
