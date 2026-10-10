# Gemian Wi-Fi reference: one bounded connect, handshake, traffic and disconnect lifecycle at the firmware boundary

Status: protocol and observer design for review; nothing built, composed,
installed or run. The owner is sole device custodian and performs every
device step; Buildbox builds only after an explicit go.

## Why

Mainline Phase C reached the key commands one firmware event per boot
([runtime 20](../2026-10-07-mt6797-wifi-phase-b-join/RUNTIME_20.md)): each
boot answered one question about the firmware's command, event, credit and
descriptor behaviour and raised the next. No retained Gemian capture holds
that layer: the stock kernel offers only the `nop` tracer and the reference
kernels v1 to v9 traced WMT/CONSYS power, firmware load and stop and the DMA
path by function name, which cannot show command ids, event payloads, page
credits or receive descriptors. The owner's read-only audit of the current
stock boot's kernel log and of the retained reference captures found zero
command, event, key or TX-done records; the vendor `DBGLOG` runs at its
default level there. One instrumented Gemian lifecycle supplies the whole
expected sequence at once, so the remaining mainline behaviours can be
implemented together and replayed offline before the next boot2 handoff.

## Existing assets reused

- Reference kernel lane: [README](README.md), [toolkit decision](RE_TOOLKIT.md),
  pinned source `59e00a91…`, `build-on-buildbox.py` (`./scripts/buildbox
  build-gemian-wifi-reference`, `fetch-gemian-wifi-reference`),
  `build-candidate.py`, guarded `prepare-installer.py`, diagnostic patches
  0001 to 0009 (printk observers in the gen3 WLAN, WMT and EMI code). The
  v10 image adds one patch and changes nothing else.
- Device-side trace pattern: `trace-shared-off-v8.sh` (identity gates on
  release and boot ID, positive control, single-use budget, bounded
  restoration under `timeout`, outputs under `/var/tmp` with `umask 077`,
  `dmesg` before and after) and the private `collect-v*` collectors for the
  boot and return receipts.
- Dynamic debug: `CONFIG_DYNAMIC_DEBUG=y` in the reference configuration
  ([RE_TOOLKIT](RE_TOOLKIT.md) names it the mechanism for enabling compiled
  sites for one bounded cycle). The observer's records are `pr_debug` sites
  that stay silent until the cycle enables them and are disabled afterwards.
- Vendor source as the oracle: the pinned public gen3 extract and headers
  (`nic_cmd_event.h`: command ids from line 73, event ids from 198,
  `WIFI_CMD_T` 294, `WIFI_EVENT_T` 307, `CMD_802_11_KEY` 375,
  `EVENT_ADD_KEY_DONE_INFO` 548, `EVENT_ACTIVATE_STA_REC_T` 760,
  `EVENT_TX_DONE_T` 887, `CMD_BSS_ACTIVATE_CTRL` 899, `CMD_SET_BSS_INFO`
  929, `CMD_UPDATE_STA_RECORD_T` 963, `CMD_REMOVE_STA_RECORD_T` 1028;
  `nic_rx.h`: `HW_MAC_RX_DESC_T` 455 and the `HAL_RX_STATUS_GET_*`
  accessors from 656). Mainline's observations
  ([PHASE_C](../2026-10-07-mt6797-wifi-phase-b-join/PHASE_C.md)) are the
  comparison set.
- Not reused: Kprobes (unsupported on this arm64 3.18 tree), raising the
  vendor `DbgLevel` (its `RSN` and `RX` sites print station addresses and
  frame bytes), any packet capture tool (none installed; none needed).

## Observer design: diagnostic patch 0010, release `3.18.41-gemini-wifi-ref10+`

One patch in `drivers/misc/mediatek/connectivity/wlan/gen3/` adding a small
header of record helpers and calls at seven sites. Every record is one
`pr_debug` line prefixed `gwref10 <category>:` with a per-boot record number
and only index, flag, length, status and class fields. No address, SSID, key
byte, frame body or payload beyond the allow-listed fields below is ever
formatted. Each category has a cap; a category at its cap emits one
`gwref10 cap: <category>` line and then counts silently, and the final
counts are printed once at the first disabled call after the cycle so the
parser can prove completeness.

| Site (pinned source) | Record | Fields | Cap |
| --- | --- | --- | --- |
| `nicTxCmd` (`nic_tx.c` 1706) | `cmd` | `cid seq set len bss type` from `WIFI_CMD_T` and `CMD_INFO_T` | 512 |
| same, `cid == 0x07` (`CMD_ID_ADD_REMOVE_KEY`) | `key` | `addremove tx keytype auth bss alg keyid keylen peer=<class>`; `peer` is `bss`, `broadcast` or `other` from a compare, never printed; key material never read | within `cmd` |
| same, `cid` in `0x11` (`BSS_ACTIVATE_CTRL`), `0x13` (`UPDATE_STA_RECORD`), `0x14` (`REMOVE_STA_RECORD`), `0x15`/`SET_BSS_INFO` | `bss`, `sta`, `starm`, `bssinfo` | `bss active nettype bmcwlan`; `sta statype bss` plus the state fields present; `action sta bss`; `bss connstate authmode encstatus physet bmcwlan` | within `cmd` |
| `nicRxProcessEventPacket` (`nic_rx.c` 1637) | `event` | `eid seq len` for every event, header only | 1024 |
| same, allow-listed payloads: `0x24` (`ADD_PKEY_DONE`), `0x0f` (`TX_DONE`), `0x0c` (`ACTIVATE_STA_REC`), `0x11` (`BSS_ABSENCE_PRESENCE`) | `keydone`, `txdone`, `starec`, `absence` | `bss sta=<class>` (class as above); `pid status sn wlan count rate flag`; `sta bss`; the index fields only | within `event` |
| `nicTxReleaseResource` (`nic_tx.c` 561) | `credit` | released count per TC and free count after, only when any count is nonzero | 1024 |
| receive descriptor after `nicRxProcessRFBs` parses an RFB (`nic_rx.c` 2705 and the `HAL_RX_STATUS_GET_*` accessors) | `rxd` | `type len hdrlen pad trans bssid wlan tid sec mismatch fmt fc group` (frame control word and the group bit of the destination; no address, no body); beacons and probe responses are counted, not recorded | 2048 |
| transmit descriptor fill for data and management frames (`nicTxFillDesc` or its gen3 equivalent, located during authoring) | `txd` | `pid wlan bss len fc prot` | 1024 |
| `cnmStaRecChangeState` (`cnm_mem.c` 720), `cnmStaRecFree` (558), `nicDeactivateNetwork` (`nic.c` 1437) | `state` | `sta state`, `sta wlan bss`, `bss` | 256 |

Secret and identifier separation, stated once: `CMD_ID_ADD_REMOVE_KEY`
payload bytes other than the enumerated metadata are never dereferenced for
output; EAPOL and data frames appear only as `rxd`/`txd` header records
(their protected bit, security mode and cipher-mismatch flags are the
actual protected-frame observation); station and BSS addresses are compared
in the kernel and reported as classes; the vendor `DbgLevel` is left at its
default. The private capture therefore contains boot identity, timing and
the records above; publishing the sanitized ledger needs only the usual
review of timing and counts.

Open points to settle while authoring, each by reading the pinned 3.18
source, not by assumption: whether the gen3 tree's event dispatch and RFB
parse sites match the public extract's line numbers; the exact TX descriptor
fill function; whether command responses share the command's id and
sequence (mainline observed `0x0c`, `0x10`, `0x11` responses); and the
kernel log path (the reference configuration has `CONFIG_LOG_BUF_SHIFT=17`,
128 KiB, so the cycle script must stream `/dev/kmsg` to its output file for
the whole cycle rather than rely on `dmesg` afterwards; the retained
collectors' larger logs suggest the device already does something similar,
which the owner confirms before the cycle).

## Device protocol: `trace-lifecycle-v10.sh`, single use

Run by the owner as root on the verified v10 boot, boot ID passed as the
only argument, the whole script under `systemd-run` so it survives losing
the LAN; output under `/var/tmp/gemini-wifi-reference-lifecycle-v10`,
`umask 077`; the ConnMan service is discovered on the device from the
currently connected entry, so no identifier enters a command line; a marker
file makes the script refuse a second run.

1. Gates (abort on any failure, nothing changed): `uname -r` equals the v10
   release, boot ID matches, `wlan0` carrier 1 and an IPv4 default route,
   battery present and `Good`, external supply present, dynamic-debug control
   writable and every `gwref10` site present and disabled, `/dev/kmsg`
   readable, required commands (`connmanctl`, `ip`, `ping`, `timeout`,
   `systemd-run`, `sha256sum`) present.
2. Start the kmsg stream to `kmsg-cycle.log`; save `dmesg-before.log`,
   `ip -4 addr`, `ip route`, `connmanctl services` (private).
3. Arm: enable the `gwref10` sites (`format "gwref10 " +p`). Positive
   control within 10 s: at least one `cmd` and one `event` record from the
   driver's periodic queries; otherwise disarm and abort.
4. Teardown first: `connmanctl disconnect <service>`; wait up to 20 s for
   carrier 0. Expected records: key removals (`key addremove=0` pairwise then
   group or the vendor's order), `starm`, `state`, `bss active=0`, their
   response events and credits.
5. Connect: `connmanctl connect <service>`; wait up to 40 s for carrier 1
   and an IPv4 address. Expected: scan and join commands, authentication and
   association `txd`/`txdone`, EAPOL `rxd`/`txd` header records, `key`
   add pairwise and group with `cmd` sequence numbers, each `credit`, every
   `event` in order including `keydone` with its class, `starec`, `bssinfo`.
6. Traffic, 15 s total: `ping -c 5 -W 2 <gateway>` (protected unicast both
   ways), `ip neigh flush dev wlan0` then `ping -c 2 -W 2 <gateway>` (an ARP
   broadcast transmitted, its reply unicast). Received group-addressed
   protected frames are whatever the LAN sends in the window; the `rxd`
   records with `group=1 sec!=0` are the evidence and their absence is
   recorded as absence, not as failure.
7. Disconnect: `connmanctl disconnect <service>`; wait up to 20 s for
   carrier 0 (the second teardown, now from a fully keyed state).
8. Disarm (`-p`), stop the kmsg stream, save `dmesg-after.log`, the
   `gwref10` count summary, `connmanctl services` and `ip -4 addr`; hash every
   output file.
9. Restore: `connmanctl connect <service>` under `timeout 60`; record carrier
   and address; the script exits 0 only with LAN restored, otherwise exits 3
   with the evidence saved for the owner's existing recovery path.

Budget: 180 s of radio actions, one run per boot, no retries. Hypothesis:
the firmware's command, event, credit and descriptor sequence for one
complete lifecycle is recorded with every category below its cap. Unique
evidence: the `kmsg-cycle.log` record sequence with the count summary.
Branches: a positive-control failure aborts before any radio action; a cap
reached in `rxd` or `event` keeps the run but marks that category
incomplete; a missing restore ends in exit 3 and the owner's reviewed
recovery; nothing is repeated on the same image without a new measurement.

## Offline use of the ledger

`parse-lifecycle.py` (to be authored with the patch) turns the private
`kmsg-cycle.log` into a sanitized ordered ledger (JSON: record number,
monotonic time, category, fields) and checks completeness from the count
summary; the ledger is publishable after review because the records carry no
identifier by construction. The mainline join work then consumes it: the
expected command and event order after the group key, the credit pattern,
the `keydone` count and class for each key, the removal and station and BSS
teardown order, and the descriptor fields of protected unicast and group
frames become fixture inputs for `classify-join.py` and the ownership and
events fixtures, so the next mainline candidate implements the remaining
behaviours together and is replayed offline before one boot2 handoff.

## Order of work after review

1. Owner review of this protocol and the observer field list.
2. Author patch 0010 and `parse-lifecycle.py` with positive and negative
   fixtures (record formatting, caps, class computation, parser completeness)
   on Buildbox; publish for review. No build.
3. On the owner's go: one managed reference build v10, receipt, offline
   candidate and guarded installer as for v9; the owner installs, boots, runs
   the cycle once, returns through the reviewed path and uploads the receipts
   and the sanitized ledger.
