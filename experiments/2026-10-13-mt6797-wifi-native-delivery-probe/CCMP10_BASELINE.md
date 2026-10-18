# Unchanged C10 baseline — complete, SSH intermittent

Owner-directed after the [sealed C10/C11 comparison](CCMP11_RESULT.md#sealed-c10c11-comparison-and-ssh-boundary).
No new candidate, kernel build or runtime code change. The original C10 pass
counts as run 1 of at most 3. C11 is a separate observation, not a C10 repeat.

Hypothesis: the original C10 boot-bound SSH pass is repeatable without C11's
observer. Each run measures transport, DHCP, individual pings, SSH stage, host
cleanup and planned versus actual data duration separately. A short session is
not a duration pass. Retain the original diagnostic limits. One custodian,
one capture/session/reviewed return per fresh boot; no silent retries. Re-arm
and reconnect stay disabled, requiring a physical selection for each session.

| Run | Boot ID | Transport | DHCP | Pings | SSH | Host cleanup | Data duration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C10 run 1 | `c80f93fe-ea39-4d6e-86b8-bfec0254c65c` | Pass | Bound | 3/3 | Authenticated, fresh boot matched | Stage 3, debt 0 | 6.210 s / 6.200 s planned |
| C11 | `e86a098f-c62a-4b48-a1c6-153627abbef2` | Pass | Bound | 3/3 | Exit 255; no accepted server connection observed; exact TCP/KEX/auth stage unknown | Stage 3, debt 0 | 6.175 s / 6.156 s planned |
| C10 run 2 | `ae97a99b-abf8-4de5-b2cf-eb3c0f772bd5` | Pass | Bound | 3/3 | Exit 255; no accepted server connection observed; exact stage unknown | Stage 3, debt 0 | 6.167 s / 6.156 s planned |
| C10 run 3 | `77f1507f-141e-4de2-8fb1-0a14713fd5d1` | Pass | Bound | 3/3 | Authenticated, fresh boot matched | Stage 3, debt 0 | 6.223 s / 6.196 s planned |

## Run 2 guarded restore and consumed handoff

Exact retained C10 image and original runtime tools, with kernel input
`0d1f51194d7001fc9c6b9219726935ede36bc828`. Raw image SHA-256
`fbe72c31ced5efd7c81317d23e3336141bf44eaf8a8a9e02b682353822112d45`,
full 16 MiB boot2
`73e1ac21860e69f6e8f03fd3625022bd8d4c8e6f189c17ecc44d40f91066ed8d`,
candidate receipt
`807c8fb9f886ce0209688740f67193626a86311b76e02d198a66b7d749b2b11c`.

Fresh strict LAN identity verified Gemian 3.18.41+/aarch64, boot
`795d2999-8793-46ac-a4b5-b8a6bc69321b`. The existing reviewed installer was
bound privately to that identity, the actual C11 predecessor and a new run-2
evidence directory. No candidate, runtime or guard change. The generated
603-line shell is byte-identical to the original C10 installer under exactly
those identity/path/hash substitutions; Bash syntax and ShellCheck passed.
Derived shell SHA-256
`2ebfc660b4a79cefd7d0f671e2bd1e88987a701776328300e6e9b46ff4c8a8d4`.
Guard source remains
`0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf`.

One guarded installation completed with both live device gates, stable power,
sync/flush and independent full readback plus byte comparison. The predecessor
matched C11; final readback matched the exact C10 full image above. No fresh
backup or automatic reboot. Clean shutdown and unreachability were confirmed.
The actual 944-byte deployment summary, SHA-256
`0c90978b2e6bd14bd322d8bc8ef328ed60bbf533489e463a095d5edd73235872`,
was seal-verified and copied byte-exact/mode 0600 into the fresh run-2 root.
Complete offline host preparation passed using the original pinned sources,
with helper key/boot variables unset. Only the deployment summary exists in
the session directory; no capture or execution claim yet.

Owner physical selection subsequently started run 2. The preparation and
handoff above are consumed; the actual result follows.

## Run 2 result: SSH failure also occurs without the observer

Executed from pushed checkout `cbc7913adacbd3e28c584c7a991a6d0400c3d996` after
fresh strict USB identity and mask-helper checks. One Phase-A capture completed
285/285 initialization steps, exit 0; one session exited 1 for failed SSH. No
retry, new candidate or instrumentation. The five C10 adapter files were
byte-compared to their original validated cohort and unchanged.

DHCP bound, lease written and exit 0; individual ping seq 0/1/2 replies were
87.143 / 33.774 / 45.498 ms, TTL 64. Seven checked PTK frames were queued;
seven data TX completed, zero TX failure, eleven credits. ACTIVE type-2 26,
type-7 99; CLOSED type-2 0, type-7 10. The other 19 ACTIVE type-2 frames were
not classified by this unchanged image; legacy zero drop counts cannot establish
zero discards. No framing hint, HIF refusal or join-stopped record occurred.
Data duration 6167 ms covered its calculated 6156 ms budget, with unchanged
5000 ms teardown margin. It was not a shortened run or sustained-operation test.

SSH helper readiness was 4.3 s, final elapsed 14.3 s, exit 255, generic
`exchange failed`, no served-boot match and no guarded ACK. The 146-byte server
log contains listener startup and termination with no accepted connection,
KEX or auth event. The frozen client discarded stderr and did not retain
nonzero stdout; exact failure stage remains unknown. This reproduces C11's
observable SSH failure pattern without its observer. C11-specific causality
is therefore not required to explain an SSH failure; it is not proved absent.

Host cleanup reached CLOSED/deauth/stage 3, no in-flight frame and zero terminal
pending credit. This is not firmware key/queue retirement proof. Owned-helper
quiescence, boot-matched device quiescence and A53 regression passed. All 63
seal entries independently rehashed; complete kmsg has 166109 bytes and 2092
contiguous records, SHA-256
`49b781b50b8fc7713aa6281ae1f9b3441dde16cc5513e51e212b043cc41afb6f`.
Seal SHA-256
`316bb0245b651d041312f1f0a950a56757e9b022e1320ec62e743fab0a6c0b84`.
One reviewed native return, three finite watcher attempts, and independent
strict LAN SSH confirmed Gemian 3.18.41+/aarch64 on changed boot
`d1e05167-ed31-4f0a-9835-4c0deba2e470`. Raw evidence remains private.
See [run-2 scalars](results/ccmp10-run2-runtime-scalars.json) and
[numeric chronology](results/ccmp10-run2-numeric-chronology.txt).

## Run 3 admission

The third and final unchanged C10 session completes the owner-directed baseline
sample. Run 2 already establishes that SSH can fail without the observer. Keep
all original limits and separate verdicts; no fourth unchanged baseline run.
C10 is already installed: the guarded installer must verify it, skip a matching
write, perform independent full readback and clean shutdown. No re-arm, rekey,
reuse, reconnect or GTK delivery. A fresh physical boot2 selection is required.

## Run 3 verified preparation and consumed physical handoff

The 603-line installer is byte-identical to the original C10 script under
exact identity/path/hash substitutions only. Bash syntax and ShellCheck passed;
derived shell SHA-256
`877288a80c79ba68f439ebf4b66178903fd7e202ff98d902d6f8e8a8aee14ee8`.
Live Gemian boot `d1e05167-ed31-4f0a-9835-4c0deba2e470` and the matching C10
predecessor were verified. One guarded invocation reported
`skipped-already-matching`: no partition write. Independent full 16 MiB readback
and byte comparison matched C10; clean shutdown and unreachability confirmed,
no automatic reboot or fresh backup.

The 925-byte actual deployment summary, SHA-256
`3fcddd0263180a9a4e5121881deb7e903687e4c3f671b9f81b0e97d7ae5ecf08`,
was seal-verified and copied byte-exact/mode 0600 into a separate fresh run-3
session root. Complete actual offline host preparation passed, helper key/boot
variables unset. The session contains only the deployment summary; capture and
execution claim are absent. No run-3 session or helper has started.

Owner physical selection subsequently started the single run-3 capture and
session; the preparation above is consumed. No physical selection is pending
for a fourth unchanged baseline run.

## Run 3 result and completed baseline decision

Executed from pushed input `b8f83eb2` on fresh strict USB-verified mainline boot
`77f1507f-141e-4de2-8fb1-0a14713fd5d1`, bound to the exact installed C10 image
and mask-helper check. One Phase-A capture passed 285/285, exit 0; one session
exited 0. Original C10 tools and limits unchanged; no retry or new candidate.

DHCP bound/lease-written/exit 0; ping seq 0/1/2 replies 80.020 / 50.299 /
41.983 ms, TTL 64. SSH readiness 3.8 s, authenticated fresh-boot/listener/lease/
mode exchange and guarded ACK by 5.8 s. Data budget 6196 ms, actual 6223 ms,
unchanged 5000 ms teardown margin. No shortened-session pass or sustained claim.
Checked PTK deliveries 36; data TX queued/done 28/28, failed 0, credits 59.
ACTIVE type-2 66 and type-7 141; CLOSED type-2 1/type-7 10. The other 30 ACTIVE
type-2 packets are unclassified by the retained counters, not proved drops.
No framing hint, HIF refusal or join-stopped record. CLOSED/deauth/stage 3,
no in-flight frame and zero terminal credit debt. Local key-disable success
is host cleanup, not firmware queue/key retirement proof.

All 63 sealed entries independently rehashed. Complete kmsg 169684 bytes,
2113 contiguous records, SHA-256
`0c2f341f41e11c7522ace38d79062a7ed3937bb9ea28b7ad5d6344dab823db0f`.
Seal SHA-256
`b117453e29526840296256615ca679f6f268a36cf58ae79829b8f7f048eea3ed`.
Owned-helper/device quiescence and A53 regression passed. One reviewed native
return, two watcher attempts, and independent strict LAN SSH confirmed Gemian
3.18.41+/aarch64 on changed boot `38038581-a960-46ee-a6e3-06121192308e`.
See [run-3 scalars](results/ccmp10-run3-runtime-scalars.json) and
[numeric chronology](results/ccmp10-run3-numeric-chronology.txt).

C10 SSH passed 2/3, failed 1/3. All three finite transport/network/host-cleanup
windows passed, but this is not reliable SSH or sustained operation. C11's
observer is not necessary for an SSH failure; its individual timing effect
remains unresolved. Failed C10 and C11 both lack a server-side accepted
connection record; client error output is missing, so exact stage remains
unknown. Select the [single bounded host-output diagnostic](SSH_FAILURE_DIAGNOSTIC.md)
before any driver fix or new kernel candidate. No fourth unchanged baseline run.

## Predeclared decision branches — intermittent branch selected

Consistent C10 SSH passes select C11-specific observer diagnosis. Intermittent
C10 failures select an independent SSH investigation: first establish TCP/KEX/
auth stage, then evaluate legitimate-frame crypto/PN rejection, TCP stalls or
drops and RX/credit accounting. Specify one bounded diagnostic with hypothesis
and decision branches before implementing. Do not infer a cause from missing
client output. After baseline, review 60 s, 2 min and 10 min lifetimes and report
the first failure point. These extensions have not been built or admitted yet.

GTK delivery, rekey, key reuse and reconnect remain disabled. No -48 adjustment,
longer transport deadlines or unresolved-callback reverse engineering without
a specific test need. Full Wi-Fi acceptance remains incomplete.
