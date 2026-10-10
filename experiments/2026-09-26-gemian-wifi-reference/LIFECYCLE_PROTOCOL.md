# Gemian Wi-Fi reference: one bounded connect, handshake, traffic and disconnect lifecycle at the firmware boundary

Status: revision 4, with the reviewable code after the custodian's reviews of
revisions 2 and 3: [patch 0010](patches/0010-diagnostic-record-Gemian-WLAN-firmware-boundary-life.patch),
the device script `trace-lifecycle-v10.sh` with its Python 3.5 helper
`lifecycle/cycle-check.py`, the parser `lifecycle/parse-lifecycle.py`, the
laptop trigger `lifecycle/lan-group-trigger.py` with the window orchestration
`lifecycle/laptop-trigger-window.py`, and their fixtures under `tests/`,
including the executor run against a fake device through its complete cycle
and every failure path. Nothing built, composed, installed or run; the
custodian reviews the exact patch before any compile. The laptop custodian performs every device step under the
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

## Observer: diagnostic patch 0010, release `3.18.41-gemini-wifi-ref10+`

[Patch 0010](patches/0010-diagnostic-record-Gemian-WLAN-firmware-boundary-life.patch)
adds `common/gwref10.c` and `include/gwref10.h` to the gen3 driver (the same
files as `lifecycle/gwref10.c` and `lifecycle/gwref10.h`, which the host
fixtures compile; a test keeps them identical), one field in `SW_RFB_T` and
calls at the resolved sites. Nothing else in the driver changes; the vendor
`DBGLOG` level is untouched.

- Control: one integer `module_param_cb` named `gwref10` on the built-in
  `wlan_gen3` module, so `/sys/module/wlan_gen3/parameters/gwref10` exists
  through the ordinary sysfs interface. Write `1`: arm once (counters reset,
  deadline set, `gwref10 arm:` marker). Write `2`: seal once (`gwref10 seal:`
  with the record total, the truncation count and recorded/suppressed/filtered
  counts per category), printed synchronously from the writer's context, so it
  works while the driver is idle. A repeated arm or seal returns `EBUSY`; the
  parameter reads the state (0 idle, 1 armed, 2 sealed).
- Synchronisation: one spinlock covers the state, the deadline, the record
  number and every counter and is held across each record's single `printk`,
  so every admitted record precedes the seal line in the kernel log and no
  record is counted or printed after it. The 240 s internal deadline is checked
  on every admission, every filtered count and every parameter write, so an
  idle driver past the deadline is sealed by whichever call comes first. The
  unlocked state read before formatting is an early exit only.
- Bounds: caps per category (cmd 512, event 1024, credit 1024, rxd 2048, txd
  1024, state 256; about 6,000 records, under 1 MiB); one `gwref10 cap:` marker
  per category at its cap, the rest counted; a record longer than the 256-byte
  line bound is marked `trunc=1` and counted, and the parser refuses it.
- Console back-pressure: records are `KERN_DEBUG`, which the device's console
  threshold (`7 4 1 7`, consoles `tty0` and `ttyMT0`) does not print; only the
  arm, seal and cap markers are `KERN_INFO`. The script refuses to run if the
  console level is above 7 and records the `printk` tuple before and after.
- Delivered bytes: the three HIF ingress paths (`nicRxReadBuffer`,
  `nicRxEnhanceReadBuffer`, `nicRxSDIOAggReceiveRFBs`) store the byte count
  the HIF delivered in the buffer (`u2GwrefHifLen`) before any descriptor field
  is interpreted; the event and descriptor helpers read header and payload
  fields only within that count and the buffer size and otherwise write
  `shorthdr`, `badlen` or `shortdesc` records. Command header fields are read
  only when the buffer exists and covers the `WIFI_CMD_T` header.
- Addresses are compared in the kernel against the BSS's target and own
  address and reported as a class (`bss`, `own`, `bcast`, `zero`, `group`,
  `other`); no address, SSID, key byte, RSC or frame body is ever formatted.
- Receive descriptor reads: the descriptor's byte count must cover the 16-byte
  descriptor and be covered by the delivered bytes; the header pointer the
  driver derived must lie inside that count; the frame-control word, group bit
  or Ethernet type are read only within the span from the header to the
  declared end (the driver's own `u2PacketLen`, which wraps on a short count,
  is reported and never used as a bound); the raw status word is recorded so
  the analysis applies the data path's own acceptance test.

| Site (`59e00a91`) | Record | Fields |
| --- | --- | --- |
| `nicTxCmd` 1706, every command | `cmd` | `cid seq set len bss type`; frame commands `type frame=1 len bss sta`; a short or absent buffer `short=1` |
| `cid 0x07` with the 16 metadata bytes present | `cmd key` | `seq addremove tx keytype auth bss alg keyid keylen wlan peer=<class>` (material and RSC never read) |
| `cid 0x11`, `0x12`, `0x13`, `0x14` with the struct covered | `cmd bss`, `bssinfo`, `sta`, `starm` | index, state, mode, auth, encryption and WLAN index fields; SSID and addresses never read |
| `nicRxProcessEventPacket` 1637, every event | `event` | `eid seq len hif`, then `badlen=1` when the declared length is not covered |
| allow-listed events with the pinned struct covered | `event keydone`, `txdone`, `starec`, `linkq`, `scandone`, `chpriv`, `bcntimeout`, `aging`, `addba`, `delba`, `bubble`, `absence`, `psmode`, `quota` | the ids `0x24`, `0x0f`, `0x0c`, `0x02`, `0x0d`, `0x10`, `0x13`, `0x19`, `0x0a`, `0x0b`, `0x2a`, `0x11`, `0x12`, `0x16` that the active dispatcher handles; index, status, token, quota, block-ack parameter and sequence fields; station classes for `keydone` and `starec` |
| every other event | header only | debug, memory, PMKID, association, scan result, statistics, BA drop-SN and unknown ids |
| `nicTxReleaseResource` 561 | `credit` | `rel0..rel5 free0..free5`, only when any release is nonzero |
| `nicRxFillRFB` 285 | `rxd` | `type len span off hdrlen pad trans bssid wlan tid sec status mismatch fmt uc2me mc bc grp fc havefc eth`; the frame-control word and group bit from an untranslated header span of at least 24 bytes, the Ethernet type and group bit from a translated span of at least 14; `shortdesc`, `badlen` or `badhdr` refusals; beacons and probe responses counted as filtered |
| `nicTxComposeDesc` 1019, `nicTxComposeSecurityFrameDesc` 1161 | `txd` | `cls=<eapol,mgmt,data> pid wlan bss sta len fmt tid prot is80211 tc`; `prot` is the composed descriptor's own protection bit, `cls` the MSDU's type, named separately |
| `cnmStaRecChangeState` 720, `cnmStaRecFree` 558, `nicDeactivateNetwork` 1437 | `state` | `stastate sta wlan bss from to`; `stafree sta wlan bss state`; `bssdeact bss` |

Fixtures: `tests/run-gwref10-test.py` (core: idle, arm and seal semantics,
exact caps under eight concurrent writers, unique contiguous record numbers,
no record after a seal that races four writers, the deadline from a writer
and from a filtered call, truncation marking); `tests/run-gwref10-vendor-test.py
<gen3 tree>` (the helpers compiled against the pinned declarations extracted
from the real headers, enumerations resolved by the C preprocessor with the
real `config.h` and Makefile flags, every stand-in field audited against the
real structures: short and absent command buffers, metadata-only key records
with every peer class, length one byte short, out-of-range BSS index, SSID
never formatted; event header gating below 8 delivered bytes, declared length
beyond the delivered or the buffer with a poisoned tail, struct one byte
short, queue-management structs, header-only ids; credit, descriptor records
for protected unicast, filtered beacons and probe responses, translated
broadcast ARP with the group bit, refused lengths, maximal field values under
the line bound; transmit classes and the protection bit; state records; no
address bytes anywhere in the output); `tests/patch-0010-consistency-test.py`.

## Device protocol: `trace-lifecycle-v10.sh`, single use

Run by the custodian as root on the verified v10 boot, the boot ID as the
only argument, launched as `systemd-run --unit=gemini-wifi-lifecycle-v10 -p
RuntimeMaxSec=300 -p KillMode=control-group .../trace-lifecycle-v10.sh
<boot-id>` (systemd 232) so it survives losing the LAN; outputs under
`/var/tmp/gemini-wifi-reference-lifecycle-v10`, which must not exist (an
earlier run's evidence is moved first), `umask 077`. Phase budgets on the
monotonic clock (`/proc/uptime`): preflight 30 s, setup 20 s, capture 150 s
after arm (the observer's own deadline is 240 s), seal 10 s (control 3 s,
logger stop 3 s, parser the rest), preservation 20 s, restoration 60 s,
finalisation 5 s, 295 s in all. Every external call runs under `timeout
--kill-after=2` clamped to the active phase deadline, and a call whose
remaining allowance after that reserve is gone is not started. Live identity
(root, aarch64, the v10 release, the boot ID) is checked before every
observer write and every radio call, including the restoration; a loss stops
all further actions and is reported. Operation counts are kept in the parent
shell. The owner-LAN gateway comes from unambiguous on-link routes (`ip -4
route show default dev wlan0`, `ip -4 addr show dev wlan0`, `ip -4 route show
dev wlan0`): exactly one default gateway, one IPv4 address on `wlan0`, the
gateway inside that address's prefix (16 to 30) with a `scope link` route
for it, RFC 1918 and not the local address, rechecked after the connect.
`ip route get` is not used: the pinned kernel's reply carries the
Android-specific `RTA_UID` attribute (number 18 in its `rtnetlink.h`,
emitted by `rt_fill_info` in `net/ipv4/route.c`), which iproute2 4.9
(`iproute2-ss161212`) prints as an unknown-family `via ??? ???`. The kernel log is copied by `cycle-check.py kmsg-stream`, which opens
`/dev/kmsg` non-blocking, flushes every read, counts `EPIPE` drops, reports
any other read failure, stops at an exact byte bound and ends normally on
`SIGTERM` with a `bytes capped drops failure stopped_by` report; the seal
requires that clean stop. The private files `/root/.gemini-wifi-reference/
approved-service` and `ap-target.json` are validated by the helper (regular
file, owner root, mode 0600, one link, schema); the connected service must be
the only wifi service and equal the approved one; the association must equal
the bound target through `iw dev wlan0 link` with iw 4.9's exact SSID
escaping (interior spaces kept, leading or trailing spaces, the backslash and
non-ASCII bytes as `\xNN`); only booleans are exported. Exit codes: 0
complete and restored, 2 refused before any radio action, 3 restoration or
AutoConnect restoration failed, 4 a budget exhausted, 5 a step failed, 6 the
seal not captured, 7 identity lost. The ConnMan service is the one currently in state
`online` or `ready`; the script compares its identifier with the custodian's
private approved-service file (mode 0600, read on the device, never echoed)
and refuses any other service. The association itself is compared with the
custodian's private bound target (`ap-target.json`: SSID, BSSID, frequency
and channel, the same file the mainline runs are bound to) through `iw dev
wlan0 link` before the cycle and after the measured connect, and the run
exports only the booleans `target_match_before` and `target_match`; a
connect that lands on another BSSID or band stops the sequence, so the
reference stays directly comparable with runtime 20 and cannot roam. That identifier does appear in the custodian's own command lines on
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
   Positive control, source-backed and read-only: two `/sbin/iw dev wlan0
   link` queries one second apart. `iw link` (iw 4.9) issues a get-station
   request for the associated BSS, which reaches `mtk_cfg80211_get_station`
   (`gl_cfg80211.c` 359; the driver has no dump-station handler) and
   `wlanoidQueryRssi`; that query returns the cached value only within
   `CFG_LINK_QUALITY_VALID_PERIOD` (500 ms, `wlan_oid.c` 3699), so the second
   query, one second later, sends `CMD_ID_GET_LINK_QUALITY` (`0x81`) and the
   firmware answers with `EVENT_ID_LINK_QUALITY` (`0x02`). The stream must
   show the arm line, a `cmd` with `cid=0x81` and an `event` with `eid=0x02`
   within 3 s; otherwise the script seals, stops the stream and exits 2 before
   any radio action.
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
   protected unicast is the `rxd` records of the replies (`sec` nonzero,
   `mismatch=0`, `grp=0`) and the `txd` records of the requests with
   `prot=1`, never the ping result or the transmit class. No neighbour flush,
   no broadcast ping, no interface-wide action. Group downlink evidence is a
   `rxd` with `grp=1` (from the descriptor's broadcast or multicast match flag,
   so a translated Ethernet header counts too) and `sec` nonzero; during this
   step the custodian runs `lifecycle/laptop-trigger-window.py <ssh alias>
   <approved key> <boot id> <laptop address> <prefix>` on the laptop: it polls
   the device's `traffic-window` marker (`start end boot-id`) over the LAN SSH
   path on a monotonic budget with each SSH call clamped to what remains, using
   only the approved key (`IdentitiesOnly`, no agent, strict host keys, no key
   updates), requires the marker's boot ID to equal the verified boot and at
   least four seconds of window left, then sends the three 8-byte UDP
   datagrams with TTL 1 one second apart to the private directed broadcast
   from the owner LAN address. Whether the access point forwards them to the station is
   an observation; the parser reports group evidence as observed or missing,
   and no group behaviour is concluded without the records.
8. Teardown two: `connmanctl disconnect <service>`; the same three-sample
   `iw` gate, up to 20 s. This is the teardown from a fully keyed station.
9. Seal: write `2` (after the identity gate), confirm the control reads `2`,
   stop the logger and require its clean report, and run the parser-backed
   seal check (one arm, one seal after it, no record after the seal, the
   kmsg sequence contiguous, record numbers and seal counts consistent, every
   record valid against the schema). Preservation: save `dmesg-after.log`,
   the parameter value, the console tuple, `ip -4 addr` and the allow-listed
   service properties (`State`, `AutoConnect`, `Favorite`, `Type`,
   `Security`, `Strength`; never `Name` or anything else), check identity
   again, then write `MANIFEST` with the size and digest of every closed
   capture file, naming any missing required file, and make them read-only.
   `frozen=1` only when the manifest is complete. The full private outputs
   are complete on the device before the restoration connect.
10. Restoration connect, outside the capture and after the identity gate:
    one `connmanctl connect <service>`, then connected with an address, on the
    bound target, the gateway still directly attached and identity intact.
    Only then is `AutoConnect` set back to its recorded value and the property
    read back; an original `False` counts as restored when it reads `False`.
    `run.log`, `restore.log` and `receipt.txt` are hashed into
    `SHA256SUMS.final` after they are closed. Exit 0 only with the LAN
    restored and `AutoConnect` verified; otherwise `AutoConnect` stays off,
    the receipt says so, and the custodian's reviewed recovery path takes
    over.

Counts stated in advance: two disconnects and one connect inside the capture,
one restoration connect outside it, two `iw link` queries as positive
control, five pings, three laptop datagrams. Budget: 180 s of radio actions after the positive control, one
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

Executor fixtures (`tests/trace-lifecycle-test.py`): the script runs against
a fake device (fake sysfs, procfs, kmsg, `iw`, `connmanctl`, `ip`, `ping`,
`uname`, `id`, with a fake kernel arming and sealing on the control file)
through the complete cycle and the failure paths: refusals before any change
(wrong boot ID, bound file mode, existing output directory, console level,
off-target association), a failed positive control (no radio action, the
restoration still verified), an off-target reconnect, a missing seal, a failed
connect, a failed restoration, an original `AutoConnect` of `False`, a failed
`AutoConnect` write, and identity loss after the connect (no restoration
attempted). Each scenario checks the admitted operation counts, the receipt
lines, the manifest and the exit code. `tests/cycle-check-test.py` covers the
private file checks, iw 4.9 escaping, link and service matching, the
correlated positive control, the seal check (seal before arm, malformed seal,
wrong counts, a dropped kmsg line, a logger stopped mid-line) and the kmsg
copier's bound, signal stop and idle stop. Short phases are not divided by the
fixture's budget divisor, so the seal, preservation and finalisation stages
run at their real length in the fixture.

## Offline use of the ledger

`parse-lifecycle.py` turns the private `kmsg-cycle.log` into a sanitized
ordered ledger (JSON: kernel sequence, monotonic time, record number,
category, subtype, fields) validated against a per-category schema of
allow-listed subtypes, fields and types, and reports two verdicts:
`stream_intact` (one arm, one seal, contiguous kmsg sequence, contiguous
record numbers, seal counts equal to the records parsed, no duplicate or
unknown `gwref10` line, every record valid) and `complete`, which also
requires zero suppressed and zero truncated records. Its summary counts
protected unicast and group frames only for accepted data (status word with
no error bit in `0x07fe`, the data path's own `0x07f8` test plus the FCS and
cipher-mismatch bits, not non-data, not a fragment; security mode nonzero;
consistent unicast or group match flags) and counts other security metadata
separately; the add-key-done attribution limit is stated in the summary. The
ledger carries no identifier by construction and is the only publishable
product; the raw logs, `ip` and `connmanctl` outputs stay private. The mainline join work then
consumes the ledger: the expected command and event order after the group
key, the credit pattern, the `keydone` count and class per key, the removal
and station and BSS teardown order, and the descriptor fields of protected
unicast and group frames become fixture inputs for `classify-join.py` and
the ownership and events fixtures, so the next mainline candidate implements
the remaining behaviours together and is replayed offline before one boot2
handoff.

## Order of work

1. Custodian review of patch 0010, the script, the parser, the trigger and
   the fixtures (all passing on Buildbox-1; the vendor fixture against the
   pinned tree read from the public mirror).
2. On the custodian's go after that review: one managed reference build v10
   (`build-on-buildbox.py` lists the ten patches, release
   `-gemini-wifi-ref10`, and asserts the observer's markers in the linked
   image), receipt, offline candidate and guarded installer as for v9 (their
   v10 entries follow the build receipt); the custodian installs and runs the
   cycle once, the owner selects boot2 physically, the custodian returns
   through the reviewed path and uploads the receipts and the ledger.
