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

## Sealed offline candidate

Validated build `1a4f291e221e7bc42536b4e17594614dae269405`, profile
`mt6797-a53-wifi-tx-yield-measurement`.
[Build/source/fixture scalars](results/tx-yield-build-validation.json) confirm
byte-identical configuration to depth four, including HZ=250 and depth=4.
Actual prepared source matches the reviewed yield change; descriptor, depth,
HIF ledger, management and deadline code match the depth candidate.

- Candidate manifest: `d3b1c04e811330a00ff4f7dad7e93e808899eb5734aee851b195ee7195374a42`.
- Android boot: `04bd176f6f8dd9a91d3cc96ddfbcfe1286bde29ee9992ccee7cef85162bb68f4`.
- Full 16 MiB boot2: `8014a0dd67c5cf5641ef4134fa5412bba971a4c93c095d48c60f02a95051ccae`.
- Live notes: 84 bytes at Image offset 12900184, SHA-256
  `efdc05a727078927f49a07db0344d39493c04548a1ab8cadab9e68e650611052`.

Exact RAM/DT and parent reproduction pass. Sealed private host/installer
bindings are retained under `artifacts/wifi-tx-yield-work/`; helper changes
only its session label, classifier remains depth four. The embedded device
guard is byte-identical to the reviewed depth installer. Offline constructors
loaded these bindings and refused at the missing genuine installation receipt;
they must pass with the actual receipt after installation. No yield run has
happened at this offline checkpoint.
