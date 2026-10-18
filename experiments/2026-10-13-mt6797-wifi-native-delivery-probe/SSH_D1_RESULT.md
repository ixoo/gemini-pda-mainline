# D1 consumed: SSH succeeded; earlier failure stage remains unknown

One admitted session on unchanged C10, 2026-10-18 UTC, from pushed host input
`7c6156b2`. Fresh USB identity verified mainline boot
`85aad59e-8d65-4d9e-9090-29140734f123`, aarch64, expected release and mask-helper
symbol, with the pinned C10 installation/full-readback provenance. One capture
passed 285/285 steps, exit 0; one D1 session exited 0. No retry or new candidate.
See the [predeclared diagnostic](SSH_FAILURE_DIAGNOSTIC.md) and
[three-run C10 baseline](CCMP10_BASELINE.md); D1 is not a fourth unchanged sample.

| Run | Boot ID | Transport | DHCP | Pings | SSH | Host cleanup | Data actual/planned |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | `85aad59e-8d65-4d9e-9090-29140734f123` | Pass | Bound | 3/3 | Authenticated, fresh boot matched and guarded ACK written | Stage 3, debt 0 | 6.179 / 6.152 s |

Ping seq 0/1/2 replies: 97.875 / 40.402 / 43.882 ms, TTL 64. Checked PTK queues
36; data TX queued/done 28/28, failed 0, credits 59. No HIF refusal, framing hint,
join-stopped or unexplained timeout. The full finite data budget completed with
the unchanged 5000 ms teardown margin. No sustained-operation claim.

The single original Wi-Fi SSH process exited 0, stdout 173 bytes, stderr 0,
no timeout; host-monotonic elapsed 1678306666 ns (about 1.68 s). Helper readiness
3.8 s and final elapsed 5.8 s include the guarded ACK. Original boot/listener/
lease/mode checks passed. Client output files are mode 0600, private and included
in the pre-recovery seal. No command, option, I/O or timeout was added to SSH.

This takes the predeclared **success / prior failure unresolved** branch.
There is no captured failing client error to distinguish TCP, KEX or auth.
Do not infer that the earlier problem is fixed or repeat D1 unchanged. Host
observation can affect timing; neither D1 success nor the C10/C11 comparison
proves observer noninterference. The next observation is separately specified
in [D2](SSH_NEIGHBOR_DIAGNOSTIC.md), without a new kernel candidate.

All 66 seal entries independently rehashed, including all three client files.
Complete kmsg 170214 bytes, 2116 contiguous records, SHA-256
`59036910b4195dd0d68389295243f871342664bbb7c112be6d30234c49d133d6`.
Seal SHA-256
`0d9de0e0ed0d1749315d71a4c273d310b912042222626c014705a83df5c49f2a`.
Owned-helper and device quiescence, boot binding and A53 regression passed.
One reviewed native return and two watcher attempts confirmed changed-boot
Gemian; independent strict LAN SSH verified 3.18.41+/aarch64 and boot
`f2211c8d-d200-4d67-8540-8dcadfed4047`. No other device accessor or recovery retry.
See [scalars](results/ssh-d1-runtime-scalars.json) and
[numeric chronology](results/ssh-d1-numeric-chronology.txt).

GTK delivery, rekey, reuse and reconnect stay disabled. Cleanup is host protocol
evidence, not firmware/HIF key retirement. No -48 adjustment, longer transport
deadline or additional firmware reverse engineering. Wi-Fi remains incomplete.
