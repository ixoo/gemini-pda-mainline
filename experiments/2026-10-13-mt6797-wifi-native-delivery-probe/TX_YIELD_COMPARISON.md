# Pump-yield comparison: predeclaration

[Depth four](TX_DEPTH_RESULT.md) measured TX 0.506 Mbit/s and RX 7.061
Mbit/s, idle 84.3% / 77.3%. Its TX completion gaps cluster near 4.2 ms and
31.8 ms. The pump counts all immediate iterations and eventually requests a
20 ms delay while work is pending, delaying completion retirement/refill.
The hypothesis is that replacing this starvation delay materially raises TX.
Individual holes were not traced to scheduler decisions; completion spacing
is not a direct airtime measurement.

## One variable

Patch 0233 changes only pump progress/yield semantics. Successful frame
submission or matched completion retirement resets the no-progress counter.
After 32 consecutive immediate iterations without progress, pending work
requests a 1 ms yield. Only genuinely idle state gets 20 ms: no queue,
in-flight owner, page debt or pending command credit. The guard remains bounded.

Use the existing delayed-work mechanism and unchanged HZ=250 configuration.
Thus the requested 1 ms is rounded to one 4 ms jiffy; it is not a guaranteed
1 ms wall-clock wakeup. No HZ change or new timer mechanism is included.
Depth stays four, TC1/TC4 pools/debt and PID ownership stay unchanged, as do
status accounting, deadlines, admission, management/reserved/key ownership,
firmware commands, descriptor rate and aggregation. The fixed nominal TX rate
remains `d[11]=0x80`, `d[26..27]=0x4b<<2`.

## One finite run

Build clean pushed inputs with the yield measurement profile. The actual
configuration must be byte-identical to the depth-four package. Validate
package/source/candidate identity; preserve exact RAM/DT. Reviewed boot2 guard,
full readback, clean shutdown, then owner-operated physical boot2 selection.
Verify fresh live identity before the single firmware start and join.

DHCP, three pings, Wi-Fi SSH. Same plain nc data/SSH control protocol: TX then
RX, five chunks per direction, each 1 s or 1 MiB, 100 ms gaps. Keep periodic
progress, independent keepalive, receiver streaming counter and 2 MiB logger.
Report chunk and aggregate rates, CPU idle, status/nonzero counts, valid
firmware-count histograms, and completion-gap histograms. Gap bins and filter
must match the recorded depth-four analysis; compute within each active chunk
so the intentional gaps do not become starvation evidence. Full-direction
intervals may be reported separately. Retain short-chunk/byte-cap limitations.

Prompt EOS-derived standard disconnect; record delivery and whole-ledger
stage 3 honestly. Seal/export, reviewed return, independent changed-boot Gemian
confirmation. One attempt, no retry of this or any consumed run. No sampler.

## Falsifiable decisions

- TX near 2.5–3 Mbit/s with fewer long completion holes supports the starvation
  hypothesis and its stated target. Rate adaptation remains another pass.
- TX improves but stays below target: record the partial effect and unmet
  target; do not change depth, credit rules or rate to force success.
- TX does not move: the yield was not the binding refill limit; the next
  question is where completions are retired. Report and stop.
- Any first driver/link error, credit anomaly, identity failure or link loss:
  stop, preserve/export and reviewed return. RX harness failure is unmeasured.

This pass does not demonstrate reconnect, rekey, key-slot reuse, maintained
Wi-Fi support or sustained throughput. DMA remains deferred. No rate change
or additional boot follows automatically from any branch.
