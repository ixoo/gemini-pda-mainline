# CCMP5 — earlier timeout; INCOMPLETE / PAUSED

**Checkpoint only. Maintained Wi-Fi remains incomplete and work is PAUSED.**
Exactly one capture (exit0) and one session (exit1) completed. No unchanged C5
retry, next candidate, implementation or further experiment is selected.
See [resume checkpoint](RESUME_CHECKPOINT.md) for the stop boundary.

## Frozen test identity

| Item | Identity |
|---|---|
| Kernel source | `85d1d6212d24f8c1d53050dcc4be7060820c06af` |
| Kernel input | `ea1fc0056738453a6e0d76cbea1d82db7ebbea48` |
| Profile | `mt6797-a53-wifi-ccmp-runtime-no-post` |
| Package inventory | `47d14ae59c49ea72d97ea3de7355e466b3aac0c553e2a4f7eea48048d48ed23b` |
| Executed tooling | `0f70e74bcd0d1fcafa4b47f8e94996e04cedc65a` |
| [Real receipt](results/ccmp-stable-monitor-candidate-5.json) SHA256 | `1b1d668c15754b75e36fac6d24d4a31a3bc21eda042ead307a198c560e58597d` |
| Raw image / candidate leaf suffix,12670976B | `e0ca6fa2cc59225c3b3c0bdc710d4940396adc6dc284309f9809e959b38b6dc8` |
| Installed full boot2,16777216B | `776cccbe841af9e36ccf981f19ec30456c61b819c6fa3d113dcd59c59533b812` |
| Deployment identity | `mt6797-wifi-ccmp-stable-monitor-deployment-5` |
| Deployment summary SHA256, custodian-verified | `f42da2f4ed5b1b55dfe8967ed481d0ed9b450b6502f99d8d6d43a811edb14878` |
| Mainline boot | `ba6e4498-7d2c-4a4d-8e8f-ea2348ee35ed` |
| Release / architecture | `7.1.3-gemini-a53-wifi-ccmp-stable-monitor` / aarch64 |

Custodian verified the live new `mt6797_hif_receive_runtime_packet` entry point
in addition to the installed candidate, release and changed boot. The deployment
summary's exact checksum was supplied separately by the custodian after byte-
exact/mode0600 verification. Its original text is not published or independently
rehashed by this checkpoint author. Do not use this note as a replacement
deployment receipt.

[Preparation](CCMP5_PREPARATION.md) owns exact package/config/series/compositor
pins. [Approved source/API/test record](RUNTIME_NO_POST_PROPOSAL.md) owns patch
and body hashes and source invariants: exact C4 ordered689+0195=690, same26
fragments/config/DT/release; boot API retains its post metadata and boot-drain
decisions, while only MAC scan/join use the no-success-post-read entry point.
Selected/header equality, poison/no-copy/refusal hint, arbitration and finite
crypto/lifecycle/cleanup protocol were not relaxed. No code/tool/candidate is
changed by recording this result.

## Observations and negative result

Phase-A readiness passed. AUTH/ASSOC responses were status0; supplicant records
messages1–4, initial PTK/GTK installation and key negotiation completed. One
checked CCMP Ethernet frame was queued (347B, flags0x40200512); native ciphertext
queued0. These observations do not prove firmware integrity/replay or hardware
key deletion.

The join stopped at status **-110**, printed first0, branch1, debt0, cleanup0.
This is the recorded earlier guard-timeout outcome, not a post-CLOSED HIF length
refusal. Printed first0 is not success; debt0 does not prove TX completion or
healthy cleanup. The exact timeout-producing acquisition/deadline and cause
remain unclassified; no new driver diagnosis is made in this checkpoint.

The [sanitized chronology](results/ccmp5-numeric-chronology.txt) matches43 exact
rows in the hash-verified full log. Times are microseconds since boot:

| Boundary | Time | Fields |
|---|---:|---|
| Data phase begins | 138714183 | budget6144ms / teardown margin5000ms |
| ACTIVE | 138763507 | total0 / bytes0 |
| First data TX | 139090557 | pid5 / pages3 / bytes342 |
| Data TX-done | 139510530 | pid5 / status0 |
| First checked Ethernet | 139511923 | bytes347 |
| Join stopped | 140327968 | -110 / branch1 / debt0 / cleanup0 |
| Data footer | 140846446 | reason=disconnect / elapsed2132ms / TXqueued2 / TXdone1 |

Phase counters: pending0; ACTIVE463 type2+2 type7=465; drain0; CLOSED0.
ACTIVE beacon counter7 is separate, not seven extra reads. No DISABLE/CLOSED
transition or HIF-refusal record appears in the full log. Subsequent local key
disable records have removal_command_credit0/status-110/no_reuse1; no hardware
deletion or healthy-cleanup claim follows.

DHCP did not bind: exit137, bound0/lease_written0. Only a145B udhcpc log was
exported for the cycle; cycle export is incomplete. No WLAN SSH server readiness,
host READY or ACK, and no SSH attempt. Leaf ping0/0 does not demonstrate a ping
test: the normal DHCP prerequisite was unmet. Full protocol/maintained support
and healthy cleanup are **false**; WPA2 completion must not be confused with the
classifier's missing fresh SSH authentication/ACK.

**Zero HIF-refusal lines is not proof that gap48 was fixed:** this trial failed
earlier, without reaching the earlier post-CLOSED comparison point. No FIFO-pop
trigger, read-sequence cause or successful repair is established. The positive
DHCP/single-ping observations and later gap48 failures in [C3](CCMP3_RESULT.md)
and [C4](CCMP4_RESULT.md) remain distinct evidence, not C5 results.

## Preservation, return and evidence limits

All13 supplied sanitized payload hashes verified against manifest
`bda095e02305787c4f9d43070c04b0ef14743b2346592fdda563395b4dced1d3`.
The full log was independently hash/size/mode verified:160188B, SHA256
`6abbd402c844b113ee63104cdaf600c48a01af8536f6917f880c6d8c6039c72f`,
2057 contiguous records0–2056. Raw content, addresses, paths and identifiers are
not published. [Minimal supporting scalars](results/ccmp5-checkpoint-scalars.json)
retain classifications/counts/hashes and sanitized boot identities only.

Custodian independently verified all63 seal entries, manifest
`57966de4f1566359b1b67c0fa290339e3628880309d19bf41cd70441bf20215f`;
the checkpoint author verified the supplied seal-validation payload, not a
second copy of all original63 files. Full log-through-seal, owned helper SAFE/
group-quiescent and device children quiesced; A53 regression PASS. Exactly one
reviewed recovery, two connection attempts; strict changed Gemian
`d09f829e-2a7e-4b5f-a240-b718c63f26ff`,3.18.41+/aarch64 confirmed.

Current reported state: device in Gemian, boot2 still contains C5 full776cccbe.
This is retained status, not a fresh live inspection or permission to boot it.
Evidence is preserved; work remains paused, with no retry or next fix decided.
