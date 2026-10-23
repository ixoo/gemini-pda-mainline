# PIO throughput baseline 1 — predeclared, physical boot2 selection pending

Owner request, 2026-10-23: measurement first, one boot of the unchanged installed
image, no rebuild or image change. Reconnect is **closed as a limitation**, not
pending development. There is no key-installation guarantee or firmware event
ordering point; the proposed probe requires a new protected native TX shape and
another internal owner. Keep the single-lifetime baseline and dormant 0229/0230.
Do not reopen reconnect without a new owner decision.

## Exact identity and fixed conditions

Kernel `3da69187ec93fd15b28fda3fbdbf118c37ad55a5`, release
`7.1.3-gemini-a53-private-p2e-delivery`, boot2 SHA-256
`5f63e2d32fc0b921b4fc60d5a50baeb045d1155598ad4108fb0afe6629bfefdd`,
16,777,216 bytes. A read-only live-Gemian GPT-label lookup and full-partition
checksum verified that installed identity before this handoff. No write,
installation, fresh backup or automatic reboot was performed.

One fresh host namespace: `artifacts/wifi-throughput-baseline-1/`, with
`capture-throughput-1` and `session-throughput-1`. P2E-D1/D2 stay consumed; this
is a different, explicitly admitted measurement protocol, not another P2E run.
The retained capture, credential/host-key/live identity, cold-start, helper
custody, complete-log seal, regression and reviewed-return mechanisms remain
in place. Existing image/firmware/driver limits are unchanged.

Use the existing AP, band/channel, position, power state, MTU and one initial
PTK/GTK lifetime. Do not change rate control, aggregation, power save, CPU
configuration, firmware or calibration. Record the actual fixed configuration
from the existing protocol evidence; do not claim RF conditions are controlled
beyond this setup. No periodic test pings run during the measurements.

The validated 64-member RAM root contains BusyBox `dd`/`nc`, not iperf3. Use the
requested fallback with known zero payload, one TCP stream per direction,
64 KiB userspace chunks, maximum 64 MiB per direction and a **60 s** direction
bound. The host receives device TX on port 48001, then sends device RX on 48002;
connections accept only the currently authenticated leased peer. Each listener
accepts once; no traffic or connection retry. Known-size completion before
60 s is reported with its actual duration, not as a saturated 60 s result.

## Single execution and measurements

1. Owner physically selects boot2; verify new live boot, release, notes, USB
   script/logger and RAM member identities **before firmware start**. A cold
   start that misses the retained guard refuses, without retry.
2. One reviewed firmware bootstrap/join, DHCP, three pings and authenticated
   Wi-Fi SSH. The TCP transfer runs inside that one owned SSH-controlled PTY
   process group, with the retained output, timeout and ownership bounds.
3. Device→host: one bounded `dd`/`nc` zero stream for up to 60 s. Retain host
   received bytes/elapsed nanoseconds and termination status. Snapshot device
   aggregate `/proc/stat` and netdev counters immediately before/after.
4. Host→device: same limits, separately, after the first direction. Retain host
   sent bytes, device receive count, elapsed time and status, with two matching
   device CPU/netdev snapshots. No resident sampler or per-packet observer is
   added; these are direction-boundary software-counter reads only.
5. Verify owned remote process group/session and local socket endpoints are
   quiescent. Issue **one** guarded standard supplicant disconnect while the
   driver data window is still open. Its eligibility is EOS-relative: [E,E+30 s],
   with a precheck no later than E+15 s, retaining the existing bounded USB call
   and three-second CLI operation. No absolute PM+604..608 window and no retry.
6. Require whole-ledger stage 3 and preserve reserved-deauthentication status,
   submission/completion timing and cleanup phase. Seal complete evidence,
   perform existing regression and reviewed return, and confirm changed-boot
   Gemian. Do not infer a firmware stop from a retained-state log.

Throughput is application bytes × 8 / actual elapsed time, in decimal Mbit/s.
Device CPU idle is the aggregate idle-tick delta divided by total delta of the
first eight `/proc/stat` CPU fields; guest fields are not double-counted.
Report iowait separately. Retain netdev packet/error/drop deltas and per-direction
TX completion/nonzero-status counts from the sealed kmsg timestamp interval.
Device phase timestamps have 10 ms resolution; completion intervals are half-open
and carry one tick of boundary uncertainty. Host→device host-sent bytes are not
claimed as device-delivered bytes: retain
and report the device `wc -c` receive count too.

The installed caps are 8,192 checked handoffs, 32,768 total RX and 16 MiB RX,
with the existing 2 MiB logger bound. Saturation may hit a cap before both
60-second directions finish. That is a **censored baseline result**: report
actual bytes/time/counters and the first binding limit; stop and return. Do not
raise a limit, rebuild, claim a completed direction or retry the boot. Separate
TCP timeout/EOF/known-size completion, device errors, driver cap stops and
cleanup/return verdicts. Any first driver/ownership/identity error withholds the
next measurement; missing quiescence holds recovery rather than guessing.

## Readiness and remaining scope

Seven actual local-socket/CPU/claim/shell fixtures pass; Bash syntax and
ShellCheck pass for the generated device program. Both actual retained capture
and session constructors pass offline with the new reviewed/private leaf and
measurement helper bindings. Image bytes and prepared source hashes verify.
No kernel build was performed. This is preparation evidence, not throughput.

Physical boot2 selection is still required. This measurement consumes the
standing one-boot allowance when executed. No runtime throughput or CPU result
is claimed yet. The [DMA map](DMA_TRANSFER_CONTRACT.md) has unresolved address
routing and error-quiescence semantics, so TX DMA implementation and the second
comparison boot are held under the refusal-on-unknown rule. RX DMA remains
separate later work. If TX DMA is eventually admitted, repeat exactly these
measurement conditions and compare both directions/CPU plus reserved-deauth
behavior; no comparison result exists now.
