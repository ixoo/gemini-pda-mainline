# Gemian Wi-Fi reference: one bounded connect, handshake, traffic and disconnect lifecycle at the firmware boundary

Status: source-backed protocol and observer design for review (revision 2,
after the custodian's review of revision 1). Nothing built, composed,
installed or run. The laptop custodian performs every device step under the
standing authorization for reviewed tests and boot2 installation; the owner's
only action is the physical boot2 selection. Buildbox agents have no device
access and build only on an explicit go after the exact patch is reviewed.

## Why

Mainline Phase C reached the key commands one firmware event per boot
([runtime 20](../2026-10-07-mt6797-wifi-phase-b-join/RUNTIME_20.md)): each
boot answered one question about the firmware's command, event, credit and
descriptor behaviour and raised the next. No retained Gemian capture holds
that layer: the stock kernel offers only the `nop` tracer, and the reference
kernels v1 to v9 traced WMT/CONSYS power, firmware load and stop and the DMA
path by function name, which cannot show command ids, event payloads, page
credits or receive descriptors. The custodian's read-only audits of the
current stock boot's kernel log and of the retained reference captures found
zero command, event, key or TX-done records; the vendor `DBGLOG` runs at its
default level there. One instrumented Gemian lifecycle supplies the whole
expected sequence at once, so the remaining mainline behaviours can be
implemented together and replayed offline before the next boot2 handoff.

## Pinned inputs

- Parent: the full Gemian tree at `59e00a9144d782e148332009a835b99c43382467`
  (`gemian/gemini-linux-kernel-3.18`), the parent of every reference image;
  the v10 patch applies on top of patches 0001 to 0009 with the pinned
  configuration (`CONFIG_MTK_COMBO_WIFI=y`: the gen3 driver is built in under
  module name `wlan_gen3`; `CONFIG_LOG_BUF_SHIFT=17`, a 128 KiB kernel log
  ring; `CONFIG_DYNAMIC_DEBUG=y`; `CONFIG_PRINTK_TIME=y`).
- Oracle: the pinned public gen3 extract. Every site below was resolved on
  the `59e00a91` tree itself (the extract's line numbers coincide for the
  files it holds): `nic/nic_tx.c` `nicTxCmd` 1706, `nicTxReleaseResource`
  561, `nicTxComposeDesc` 1019, `nicTxComposeSecurityFrameDesc` 1161,
  `nicTxProcessTxDoneEvent` 2377; `nic/nic_rx.c` `nicRxFillRFB` 285,
  `nicRxProcessRFBs` 2705 (dispatch on `ucPacketType`: `RX_PKT_TYPE_RX_DATA`
  to `nicRxProcessDataPacket` 1313, `RX_PKT_TYPE_SW_DEFINED` to
  `nicRxProcessEventPacket` 1637 and `nicRxProcessMgmtPacket` 2473);
  `mgmt/cnm_mem.c` `cnmStaRecFree` 558, `cnmStaRecChangeState` 720;
  `nic/nic.c` `nicDeactivateNetwork` 1437; `common/wlan_lib.c`
  `wlanSendCommand` 1308 and the key-command gate at 1146;
  `os/linux/gl_cfg80211.c` `mtk_cfg80211_get_station` 359 (`wlanoidQueryRssi`
  416, which sends `CMD_ID_GET_LINK_QUALITY` `0x81`, `wlan_oid.c` 3715),
  `mtk_cfg80211_disconnect` 1033 (`wlanoidSetDisassociate`, `wlan_oid.c`
  6493); `os/linux/include/gl_kal.h` 630 (`kalPrint` is `pr_debug`, so every
  vendor `DBGLOG` is already a dynamic-debug site behind the module level
  gate, left untouched); `os/linux/gl_proc.c` 633 to 710 (the existing
  `/proc/net/wlan/` controls, not extended).
- Types and lengths, `include/nic_cmd_event.h` at `59e00a91`: `WIFI_CMD_T`
  294 and `WIFI_EVENT_T` 307 (8-byte header: `u2PacketLength`,
  `u2PacketType`, `ucEID`, `ucSeqNum`, two reserved); `CMD_802_11_KEY` 375
  (`ucAddRemove`, `ucTxKey`, `ucKeyType`, `ucIsAuthenticator`,
  `aucPeerAddr[6]`, `ucBssIdx`, `ucAlgorithmId`, `ucKeyId`, `ucKeyLen`,
  `ucWlanIndex`, reserved, `aucKeyMaterial[32]`, `aucKeyRsc[16]`);
  `EVENT_ADD_KEY_DONE_INFO` 548 (8 bytes); `EVENT_ACTIVATE_STA_REC_T` 760
  (address, `ucStaRecIdx`, `ucBssIndex`); `EVENT_TX_DONE_T` 887 (16 bytes);
  `CMD_BSS_ACTIVATE_CTRL` 899; `CMD_SET_BSS_INFO` 929;
  `CMD_UPDATE_STA_RECORD_T` 963; `CMD_REMOVE_STA_RECORD_T` 1028.
  `include/nic/nic_rx.h`: `HW_MAC_RX_DESC_T` 455 (16 bytes: byte count,
  packet type word, match flags, channel, header length byte, BSSID byte,
  WLAN index, TID/security byte, status flags, filter info) and the
  `HAL_RX_STATUS_GET_*` accessors from 656; `RX_STATUS_FLAG_CIPHER_MISMATCH`
  140. Command responses are events with their own ids correlated to the
  command by `ucSeqNum` (`nicGetPendingCmdInfo`, `nic_rx.c` 1819 and
  following), so header-only event records already give the correlation.

## Existing assets reused

- Reference lane: [README](README.md), [toolkit decision](RE_TOOLKIT.md),
  `build-on-buildbox.py` (`./scripts/buildbox build-gemian-wifi-reference`,
  `fetch-gemian-wifi-reference`), `build-candidate.py`, the guarded
  `prepare-installer.py`, diagnostic patches 0001 to 0009. The v10 image adds
  one patch and changes nothing else.
- Device-side pattern: `trace-shared-off-v8.sh` (identity gates on release
  and boot ID, positive control, single-use budget, bounded restoration under
  `timeout`, outputs under `/var/tmp` with `umask 077`, `dmesg` before and
  after) and the private `collect-v*` collectors for boot and return
  receipts; the passive-scan reference's `/sbin/iw` link sampling for the
  disconnected state.
- Not reused: Kprobes (unsupported on this arm64 3.18 tree), raising the
  vendor `DbgLevel` (its `RSN` and `RX` sites print station addresses and
  frame bytes), dynamic debug as the on/off control (it cannot print a count
  snapshot while the driver is idle), any packet capture tool (none installed
  and none needed), a new procfs or debugfs file.

## Observer design: diagnostic patch 0010, release `3.18.41-gemini-wifi-ref10+`

One patch under `drivers/misc/mediatek/connectivity/wlan/gen3/`: a small
header of record helpers plus calls at the sites below. Control is one
integer `module_param_cb` named `gwref10` on the built-in `wlan_gen3`
module, so it appears as `/sys/module/wlan_gen3/parameters/gwref10` through
the existing sysfs interface with no new file type:

- write `1`: arm. Resets every counter, records the monotonic time and
  prints `gwref10 arm: n=1` synchronously from the writer's context.
- write `2`: seal. Clears the armed flag first, then prints `gwref10 seal:`
  with every category's recorded and suppressed count and the total, again
  synchronously, so the snapshot exists whether or not the driver runs
  another call. A second arm or seal in the same boot is refused (`-EBUSY`)
  and the parameter stays at its value: the observer is single use per boot.
- read: the current state (`0` idle, `1` armed, `2` sealed).

Records are `pr_info` lines `gwref10 <category>: n=<record> <fields>`,
emitted only while armed. The record number is one `atomic_t` incremented
with `atomic_inc_return`; each category's recorded and suppressed counters
are `atomic_t` too, so the RX softirq, the TX thread, the HIF interrupt and
the writer never share a non-atomic word, and the order of records is the
kernel log's own sequence. A category at its cap suppresses further records
and counts them; one `gwref10 cap: <category>` line marks the moment. The
overall bound is the sum of the caps (about 6,000 records, under 1 MiB).
Every field is an index, flag, length, status or class. No address, SSID,
key byte, RSC, frame body or payload beyond the allow-listed fields is ever
formatted or read for output.

| Site (`59e00a91`) | Record | Fields | Cap |
| --- | --- | --- | --- |
| `nicTxCmd` 1706, every command | `cmd` | `cid seq set len bss type` from `WIFI_CMD_T` and `CMD_INFO_T` | 512 |
| same, `cid == 0x07`, only when `u2InfoBufLen` covers the 16 metadata bytes before `aucKeyMaterial` | `key` | `addremove tx keytype auth bss alg keyid keylen wlan peer=<class>`; `peer` is `bss` (equals the BSS's target address), `broadcast` or `other`, compared in the kernel, never printed; `aucKeyMaterial` and `aucKeyRsc` are never read | within `cmd` |
| same, `cid` in `0x11`, `0x13`, `0x14`, `0x15`, each only when the length covers the struct | `bss`, `sta`, `starm`, `bssinfo` | `bss active nettype bmcwlan`; `sta statype bss` and the state fields present in `CMD_UPDATE_STA_RECORD_T`; `action sta bss`; `bss connstate authmode encstatus physet bmcwlan` | within `cmd` |
| `nicRxProcessEventPacket` 1637, every event | `event` | `eid seq len` from the 8-byte header | 1024 |
| same, allow-listed payloads with `u2PacketLength` at least 8 plus the struct size, otherwise header only with `short=1`: `0x24`, `0x0f`, `0x0c` | `keydone`, `txdone`, `starec` | `bss sta=<class>` (class as above); `pid status sn wlan count rate flag`; `sta bss` | within `event` |
| `nicTxReleaseResource` 561 | `credit` | released count per TC and the free count after, only when any released count is nonzero | 1024 |
| `nicRxFillRFB` 285, after the descriptor fields are parsed, before dispatch | `rxd` | `type len hdrlen pad trans bssid wlan tid sec mismatch fmt` from the 16-byte descriptor; `fc=<word> group=<bit>` from the first two header bytes and the destination's group bit only when the header is not translated and `u2PacketLen` is at least 24; `eth=<type>` instead when translated and at least 14 bytes are present; beacons and probe responses are counted in `suppressed`, not recorded | 2048 |
| `nicTxComposeDesc` 1019 and `nicTxComposeSecurityFrameDesc` 1161, after the PID is assigned | `txd` | `pid wlan bss len fmt tid sec=<class>` where `sec` is `eapol`, `mgmt` or `data` from the MSDU's own type fields, no body read | 1024 |
| `cnmStaRecChangeState` 720, `cnmStaRecFree` 558, `nicDeactivateNetwork` 1437 | `state` | `sta state`, `sta wlan bss`, `bss` | 256 |

Unknown or refused events and commands are header-only by construction; a
payload record exists only for the allow-listed ids with a strict length
check against the pinned struct size.

## Device protocol: `trace-lifecycle-v10.sh`, single use

Run by the custodian as root on the verified v10 boot, the boot ID as the
only argument, under `systemd-run` so it survives losing the LAN; outputs
under `/var/tmp/gemini-wifi-reference-lifecycle-v10`, `umask 077`; a marker
file refuses a second run. The ConnMan service is the one currently in state
`online` or `ready`; the script compares its identifier with the custodian's
private approved-AP file (mode 0600, read on the device, never echoed) and
refuses any other service, so the capture cannot be broadened to another
network. That identifier does appear in the custodian's own command lines on
the device and in the private output files; the only sanitized product is the
parsed `gwref10` ledger.

1. Gates, nothing changed on failure: `uname -r` equals the v10 release,
   boot ID matches, `wlan0` carrier 1, `/sbin/iw dev wlan0 link` reports
   connected, an IPv4 address and default route exist, battery present and
   `Good`, external supply present, `/sys/module/wlan_gen3/parameters/gwref10`
   reads `0`, `/dev/kmsg` readable, commands present (`connmanctl`, `ip`,
   `ping`, `timeout`, `systemd-run`, `sha256sum`, `/sbin/iw`), the approved
   service matches, and its `AutoConnect` property is recorded.
2. Record `dmesg-before.log`, `ip -4 addr`, `ip route`, `connmanctl services`
   and the service's properties (all private). Set `AutoConnect` off for the
   approved service for the cycle, so the connect and disconnect counts below
   are exactly the script's own; the original value is restored in step 9.
3. Start the kmsg stream: `cat /dev/kmsg` into `kmsg-cycle.log` bounded by
   `head -c 8388608`, started before arming and stopped after sealing, so the
   128 KiB ring size does not matter; each line carries the kernel's sequence
   number, and the parser verifies the sequence is contiguous (a gap is a
   drop and is reported as such).
4. Arm: write `1` to the parameter and confirm the `arm` line in the stream.
   Positive control, source-backed and read-only: one `/sbin/iw dev wlan0
   station dump`, which reaches `mtk_cfg80211_get_station` and sends
   `CMD_ID_GET_LINK_QUALITY` (`0x81`); within 5 s the stream must show
   `cmd` with `cid=0x81` and an `event` with the same `seq` (the firmware's
   response, `EVENT_ID_LINK_QUALITY` `0x02` by the pinned enum). Otherwise
   seal, stop the stream and exit 2 before any radio action.
5. Teardown one: `connmanctl disconnect <service>`; wait up to 20 s until
   three consecutive `/sbin/iw dev wlan0 link` samples, one second apart,
   report `Not connected` (carrier 0 alone is not the gate). Expected
   records: `key addremove=0` for each key, `starm`, `state`, `bss active=0`
   or `bssinfo connstate`, their response events and credits.
6. The measured connect: `connmanctl connect <service>`; wait up to 40 s for
   `iw` connected and an IPv4 address. Expected: scan and join commands,
   authentication and association `txd`/`txdone`, EAPOL `rxd`/`txd` header
   records, `key` add pairwise then group with their `cmd` sequences, every
   `credit`, every `event` in order including each `keydone` with its class,
   `starec`, `bssinfo`.
7. Traffic, 15 s, target only: `ping -c 5 -W 2 <gateway>`. The evidence of
   protected unicast is the `rxd` records of the replies (`sec` nonzero and
   `mismatch=0`) and the `txd` records of the requests, not the ping result.
   No neighbour flush, no broadcast ping, no interface-wide action. Group
   downlink traffic is whatever the LAN sends in the window; a `rxd` with
   `group=1` and `sec` nonzero is the evidence, and its absence is recorded
   as missing group evidence, not as failure. If the custodian wants group
   evidence in this run, the laptop on the same LAN may send three ARP
   requests for the gateway during step 7 (its own `arping -c 3`), which
   arrive at the station as group-addressed protected frames; that is the
   only group trigger, optional and bounded.
8. Teardown two: `connmanctl disconnect <service>`; the same three-sample
   `iw` gate, up to 20 s. This is the teardown from a fully keyed station.
9. Seal: write `2`, confirm the `seal` line, stop the stream, save
   `dmesg-after.log`, the parameter value, `connmanctl services`, the
   service's properties and `ip -4 addr`; restore `AutoConnect` to its
   recorded value; hash every output file into `SHA256SUMS`.
10. Restoration connect, outside the capture: `connmanctl connect <service>`
    under `timeout 60`, then `iw` connected and an address. Exit 0 only with
    the LAN restored; otherwise exit 3 with the evidence saved and the
    custodian's reviewed recovery path takes over.

Counts stated in advance: two disconnects and one connect inside the capture,
one restoration connect outside it, one `station dump` as positive control,
five pings. Budget: 180 s of radio actions after the positive control, one
run per boot, no retries. Hypothesis: the firmware's command, event, credit
and descriptor sequence for one complete lifecycle is recorded with every
category below its cap and the kmsg sequence contiguous. Unique evidence:
`kmsg-cycle.log` with its `arm` and `seal` lines and the seal counts.
Branches: a positive-control failure seals and exits before any radio action;
a cap in `rxd` or `event` keeps the run and marks the category incomplete; a
kmsg gap marks the ledger incomplete; a failed teardown gate stops the
sequence at that step and proceeds to seal and restoration; a failed
restoration ends in exit 3 and the reviewed recovery; nothing is repeated on
the same image without a new measurement.

## Offline use of the ledger

`parse-lifecycle.py` (authored with the patch) turns the private
`kmsg-cycle.log` into a sanitized ordered ledger (JSON: kernel sequence,
monotonic time, record number, category, fields) and checks completeness
against the seal counts and the kmsg sequence. The ledger carries no
identifier by construction and is the only publishable product; the raw
logs, `ip` and `connmanctl` outputs stay private. The mainline join work then
consumes the ledger: the expected command and event order after the group
key, the credit pattern, the `keydone` count and class per key, the removal
and station and BSS teardown order, and the descriptor fields of protected
unicast and group frames become fixture inputs for `classify-join.py` and
the ownership and events fixtures, so the next mainline candidate implements
the remaining behaviours together and is replayed offline before one boot2
handoff.

## Order of work

1. Custodian review of this revision.
2. Author patch 0010, `trace-lifecycle-v10.sh` and `parse-lifecycle.py` with
   offline fixtures (record formatting and caps, class computation, strict
   length checks, arm and seal semantics, the script's gates against a mocked
   environment, parser completeness and gap detection); publish for review.
   No build.
3. On the custodian's go after reviewing the exact patch: one managed
   reference build v10, receipt, offline candidate and guarded installer as
   for v9; the custodian installs and runs the cycle once, the owner selects
   boot2 physically, the custodian returns through the reviewed path and
   uploads the receipts and the ledger.
