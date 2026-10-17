# C7: two ping replies, then receive-length refusal; incomplete

Consumed once, 2026-10-17. WPA2 and DHCP completed, two individual ICMP
replies were retained, and Wi-Fi SSH was attempted but failed. Monitor disable
returned its credit; the following cleanup receive refused advertised/header
lengths 427/379. No healthy cleanup, ten-minute SSH or reconnect. C7 must not
be repeated unchanged. The device returned to independently confirmed Gemian.

## Identity and protocol

[Preparation](CCMP7_PREPARATION.md) pins clean kernel input `e7c669a0`, profile,
package, configuration, proposal 0197 and real receipt. Verified full boot2
SHA-256 was `5b4405e0060111173da65445e3e4b1ffcd13347c9cf0ddb23d36d85140665ee6`.
After owner physical selection, USB SSH identified aarch64 and release
`7.1.3-gemini-a53-wifi-ccmp-stable-monitor`, mainline boot
`ecf1b56b-8733-4207-be0d-76503d7faf35`. The new once-only credit line further
corroborates the installed C7 source chain.

Tooling `20ca46671684785b247b43b06b8a40793518676c` performed one Phase-A
capture (exit 0, ready for scan), then one actual session (exit 1). No preflight
retry, extra capture or alternate candidate. Historical source pins, current
credentials, all-RX 512/1 MiB, delivery 64, wall/deadline and cleanup gates
remained unchanged. Proposal 0197 adds retained scalars only.

## Established observations

- Initial WPA2 key negotiation completed. Five checked firmware-decrypted
  CCMP Ethernet frames were queued; native ciphertext queued 0. Ordinary
  data PIDs 5-9 each have a status-0 completion and credited pages. These are
  host observations, not independent proof of over-air ACK or firmware crypto.
- DHCP bound and wrote a lease, exit 0. The retained ping transcript contains
  replies for sequences 0 and 1, TTL 64, times 91.146 and 42.106 ms. It has no
  final transmission/loss summary or third reply. Leaf ping 0/0 are defaults
  from interrupted completion, not measured packet counts.
- The SSH listener passed its binary/readiness checks. The laptop helper saw
  the fresh boot/mode/after-ACTIVE marker and attempted SSH, exit 255, without
  authenticated boot match or ACK. A ready marker is not authentication.
- At all-RX count 512 the monitor state advanced DISABLE_PENDING to CLOSED.
  Its one-page credit returned. Deauthentication PID 10 was submitted, but no
  PID 10 completion or cleanup-stage advance followed before the RX refusal.

The [numeric chronology](results/ccmp7-numeric-chronology.txt) and
[scalars](results/ccmp7-runtime-scalars.json) publish fixed numeric observations
only. Network addresses, raw packet bytes, credentials and private paths stay
in ignored evidence. The partial cycle export remains classified incomplete.

## Separate verdicts

| Area | Established evidence | Limit / decision |
| --- | --- | --- |
| C6 timeout | C7 site 0, branch 4; monitor CLOSED, pending 0, shared debt 0. Last valid reconciliation WTQCR7 `0x00010001`, released 1, TC4 free 26, TC1 free 16; CPU/FFA/AC1 pending all 0. | C6's timeout did not recur. C7 does not retrospectively establish C6's missing counter or justify changing credit policy/deadlines. |
| Transport | Port 0 advertised 427, staged header 379, complete 432-byte transfer, setup/complete/header-valid all 1; post acquisition absent. Refused type word `0x4000`. Stop -71, branch 4. | Equality guard refused and poisoned before caller copy. Difference 48 recurs with the runtime post-read already omitted. Removing that read is insufficient to prevent this failure. No shorter read, prefix copy or subtraction is justified. |
| Network | WPA2, DHCP, two individual ping replies; SSH attempted. | No third reply, authenticated SSH ACK, ten-minute traffic or complete cycle. |
| Cleanup | Monitor-disable credit returned; deauthentication started. Cleanup stage 0, no completed station/resource teardown. | CLOSED is a monitor state, not queue-drain or healthy-lifetime proof. Fatal poison remains. |
| Security | Existing checked initial-PTK/host-PN diagnostic path only. | No ordinary-mode integrity/PN, GTK attribution, rekey, key deletion or safe slot-reuse proof. |

Times below are host log microseconds since boot, not firmware arrival times:

| Boundary | Time |
| --- | ---: |
| Data phase begins, 6196 ms budget / 5000 ms teardown margin | 112962296 |
| ACTIVE | 113007928 |
| First data submit / completion | 113406962 / 113408225 |
| Last ordinary completion, PID 9 | 115852260 |
| DISABLE_PENDING, 512 reads / 86258 logical bytes | 116042852 |
| Disable credit / CLOSED | 116066849 / 116073066 |
| Deauthentication PID 10 submitted | 116074401 |
| Its page credit / length refusal | 116098842 / 116100076 |
| Stop, -EPROTO branch 4 | 116114590 |

Terminal port 0 history: 611 attempts, 523 successes, 27 type-7 records,
status -71; port 1: 609 attempts, no successes, 467 opposite-half advertisements,
status -EAGAIN. Both last pre-WRPLR values were `0x000001ab`. These counts do
not prove an unserviced port-1 packet or a consuming WRPLR read.

The last valid guard return was `116052059622` ns (WHCR 0 / WHISR 3).
Receive return boundaries were `116053305314` / `116053247237` ns. Cached
credit values belong to that existing guard, not fault-time sampling.
The terminal worker timestamp `116056580622` ns precedes the printed records;
logging is not an exact acquisition timeline. Current in-flight PID 10 and
stored frame deadline `116778737391` ns differ from the last ordinary submit
PID 9 / return boundary `115780047776` ns. This is not C5's data-TX timeout.

## Source interpretation and next boundary

The existing HIF reads pre-WRPLR, completes the advertised span plus appended
word, checks its guard, then compares descriptor length before publishing type
or copying bytes. Runtime post-WRPLR is not reached or selected. No group
stripping occurs before the comparison. The pinned public
[gen3 receive path](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/wlan/gen3/nic/nic_rx.c#L2826-L2908)
also requires advertised/header equality; it supplies no 48-byte exception.

The untrusted staged type word has descriptor group bits zero. That is an
observation about refused bytes, not permission to parse or deliver the frame.
A mode-dependent queued-descriptor change and stale length/data pairing remain
hypotheses. Correlation after monitor disable does not distinguish them.

The next source review must trace monitor-disable completion versus pending
RX/descriptor ownership, and whole-WRPLR acquisitions versus each FIFO read.
Retain equality, full transfer, poison/no-copy and fatal retirement. Select a
correction only from a proved contract; otherwise specify one bounded
observation from existing reads that distinguishes these hypotheses before
building. Do not repeat C7, change credit refunds or extend deadlines. Ordinary
crypto and healthy lifecycle work remain required by the delivery plan.

## Preservation and recovery

The complete log is 163611 bytes, SHA-256
`ed07c4f42ad942f0f9c35c4868794969c82d57ecee3e21b6d24cd8629587d7a3`,
2073 contiguous records 0-2072, classified complete through explicit seal.
All 63 pre-recovery entries independently match seal SHA-256
`9c7e0c148e73a390888a1c811b968a8f782113b25c496d6a97900106a0e8c916`.

Owned helper SAFE/group-quiescent and boot-matched device-child quiescence
passed, without helper timeout/probe/kill error. A53 regression passed. One
reviewed native recovery request and three bounded watcher connection attempts
confirmed changed-boot Gemian `baff9c68-f74b-4797-8d28-1982211adba6`.
Separate read-only LAN SSH confirmed `3.18.41+` / aarch64 and the same boot.
C7 remains installed in boot2 but is consumed; no physical selection is pending.
