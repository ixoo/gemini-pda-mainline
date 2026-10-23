# Corrected PIO throughput baseline 2 — offline gates before one boot

Owner instruction after [invalid baseline 1](THROUGHPUT_BASELINE_RESULT.md):
one separately named run, unchanged installed image, no rebuild. The baseline-1
SSH policy error and [independent loss-path audit](LOSS_PATH_TEARDOWN_AUDIT.md)
are recorded separately. Neither P2E-D1/D2 nor baseline 1 may be repeated.

## Fixed conditions and hypothesis

Use installed `3da69187ec93fd15b28fda3fbdbf118c37ad55a5`, release
`7.1.3-gemini-a53-private-p2e-delivery`, boot2 SHA-256
`5f63e2d32fc0b921b4fc60d5a50baeb045d1155598ad4108fb0afe6629bfefdd`,
with exact fresh live identity, notes and RAM-member checks before firmware
start. Fresh namespace `artifacts/wifi-throughput-baseline-2/`, capture and
session `*-throughput-2`. Same AP/channel/setup, MTU, CPU/driver/firmware and
existing finite resource caps. No image change, sampler or new firmware command.

Hypothesis: progress plus independent SSH control traffic prevents the known
30 s server-idle refusal, allowing separate bounded PIO measurements and a
prompt standard disconnect. This does not assert a firmware lifetime boundary,
correct the known loss-path waiter candidate or reopen reconnect.

## Procedure and bounds

1. After owner-operated physical boot2 selection, verify live identity, then
   one existing start/join, DHCP, three pings and authenticated Wi-Fi SSH.
2. Prefer iperf3 if present, with interval output and JSON. The validated
   installed RAM member inventory has **no iperf3**, so this run selects the
   existing BusyBox dd/nc fallback; do not install anything during the run.
3. Device TX first, device RX second: **five chunks each**, each TCP connection
   bounded by a **10 s** device netcat timeout and **1 MiB** known maximum.
   Print chunk start/end status lines over SSH. Maximum transfer activity is
   50 s/direction, 5 MiB/direction; known-size completion can finish sooner.
   Never claim that a shorter known-size result saturated a 50 s interval.
4. Independently keep SSH alive with `ServerAliveInterval=5` and
   `ServerAliveCountMax=3`. The retained server's `-I 30` remains unchanged.
   Each data command ends or emits progress within 10 s; no quiet 60 s command.
   The complete tagged remote owner retains its 135 s outer bound and existing
   no-late-start/one-acquisition protections. Host sockets are cancellable;
   each chunk has a 12 s receive/send safety bound and one accepted peer.
5. Read aggregate device `/proc/stat` and six netdev counters immediately
   before/after each direction. These are direction-boundary CPU samples, not
   a resident sampler. Retain per-chunk host bytes/time, device RX file counts,
   termination status and direction CPU idle/iowait deltas. Report actual rates
   only for a valid measurement. Host-sent RX bytes are not device-delivered
   bytes; the bounded device `wc -c` counts are the delivery measure.
6. After the final chunk, prove tagged remote group and host endpoints gone,
   then issue **one** standard supplicant disconnect immediately. Use the
   observed EOS and existing [E,E+30 s] bound with precheck by E+15 s. If SSH
   failed before its EOS line, the boot-matched USB quiescence observation is
   the observed stream end; it does not claim an earlier exact EOF timestamp.
   No retry. A named driver fault or unknown process ownership withholds control.
7. Report stage 3/whole ledger and reserved-deauth completion independently;
   seal/export, regression, reviewed return and changed-boot Gemian confirmation.

Offline idle-policy tests must reject a planned 31 s quiet chunk or removal
of progress lines. Test actual sequential connections, cancellation, peer
refusal, CPU arithmetic, shell syntax/ShellCheck and actual capture/session
constructors before physical handoff. The installed image has already been
checked to lack iperf3; a mismatched live member inventory refuses the run.

## Decision branches

- Identity, cold-start or admission refusal: record once, preserve/return; no retry.
- SSH idle/error, data stall, cap, first driver/link/credit error: withhold later
  traffic, prove quiescence, promptly disconnect only if still admitted, seal and
  return. Keep partial transfers out of the valid baseline.
- Both directions complete the bounded protocol: report throughput, CPU idle,
  completion/error counts and actual chunk durations; do not call it DMA data.
- Disconnect refused: harness result, no second attempt. Whole-ledger stage 3
  missing: cleanup failure, even if traffic and reserved delivery succeeded.

One corrected boot is authorized only after the offline protocol checks and
loss-path audit have answers. No automatic retry, new image, TX DMA programming
or comparison boot follows it. DMA remains held on its separate unknowns;
reconnect remains closed, single-lifetime baseline and dormant safeguards kept.
